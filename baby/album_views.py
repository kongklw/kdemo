from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import BabyAlbum, AlbumPhoto
from fileUpload.models import MediaAsset
from .serializers import BabyAlbumSerializer
from django.conf import settings
from django.core.files.base import File
from django.db.utils import DataError
from django.http import HttpResponse
from django.shortcuts import redirect
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config
from PIL import Image

logger = logging.getLogger(__name__)

_STREAMS_PREFIX = 'baby_album/streams'
_THUMBS_PREFIX = 'baby_album/thumbs'


def _safe_stem_from_key(key: str, fallback: str) -> str:
    raw = (key.rsplit('/', 1)[-1].rsplit('.', 1)[0] if key else '').strip()
    if not raw:
        return fallback
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '_', raw)[:80]
    return safe or fallback


def _ffmpeg_available() -> bool:
    return bool(shutil.which('ffmpeg'))


def _run_ffmpeg(args: list[str]) -> bool:
    try:
        p = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return p.returncode == 0
    except Exception:
        return False


def _ffprobe_has_audio(input_path: str) -> bool:
    if not shutil.which('ffprobe'):
        return True
    try:
        p = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', input_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        return bool((p.stdout or '').strip())
    except Exception:
        return True


def _optimize_faststart(input_path: str, output_path: str) -> bool:
    return _run_ffmpeg([
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-c', 'copy',
        '-movflags', '+faststart',
        output_path,
    ])


def _extract_poster(input_path: str, output_path: str) -> bool:
    ok = _run_ffmpeg([
        'ffmpeg',
        '-y',
        '-ss', '00:00:01.000',
        '-i', input_path,
        '-frames:v', '1',
        '-q:v', '2',
        output_path,
    ])
    if ok:
        return True
    return _run_ffmpeg([
        'ffmpeg',
        '-y',
        '-ss', '00:00:00.000',
        '-i', input_path,
        '-frames:v', '1',
        '-q:v', '2',
        output_path,
    ])


def _write_uploaded_to_temp(uploaded) -> tuple[str, str]:
    suffix = Path(getattr(uploaded, 'name', '') or '').suffix or ''
    if len(suffix) > 16:
        suffix = ''
    fd, in_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    with open(in_path, 'wb') as f:
        for chunk in uploaded.chunks():
            f.write(chunk)
    out_fd, out_path = tempfile.mkstemp(suffix=suffix or '.mp4')
    os.close(out_fd)
    return in_path, out_path


def _get_s3_client():
    verify = True
    if hasattr(settings, 'MINIO_VERIFY_SSL'):
        verify = bool(settings.MINIO_VERIFY_SSL)
    return boto3.client(
        's3',
        aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
        aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
        endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
        region_name=getattr(settings, 'AWS_S3_REGION_NAME', None),
        verify=verify,
        config=Config(
            signature_version=getattr(settings, 'AWS_S3_SIGNATURE_VERSION', 's3v4'),
            s3={'addressing_style': getattr(settings, 'AWS_S3_ADDRESSING_STYLE', 'path')},
        ),
    )


def _download_s3_object_to_file(s3, bucket: str, key: str, local_path: str) -> None:
    with open(local_path, 'wb') as f:
        s3.download_fileobj(bucket, key, f)


def _upload_file_to_s3(s3, bucket: str, key: str, local_path: str, content_type: str | None) -> None:
    extra = {'ContentType': content_type} if content_type else None
    with open(local_path, 'rb') as f:
        if extra:
            s3.upload_fileobj(f, bucket, key, ExtraArgs=extra)
        else:
            s3.upload_fileobj(f, bucket, key)


def _s3_key_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except Exception:
        return False


def _content_type_for_path(path: str) -> str | None:
    p = (path or '').lower()
    if p.endswith('.m3u8'):
        return 'application/vnd.apple.mpegurl'
    if p.endswith('.ts'):
        return 'video/mp2t'
    if p.endswith('.mpd'):
        return 'application/dash+xml'
    if p.endswith('.m4s'):
        return 'video/iso.segment'
    if p.endswith('.mp4'):
        return 'video/mp4'
    if p.endswith('.webp'):
        return 'image/webp'
    if p.endswith('.avif'):
        return 'image/avif'
    if p.endswith('.jpg') or p.endswith('.jpeg'):
        return 'image/jpeg'
    return None


def _upload_dir_to_s3(s3, bucket: str, local_dir: str, key_prefix: str) -> None:
    local_dir_path = Path(local_dir)
    for file_path in local_dir_path.rglob('*'):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(local_dir_path).as_posix()
        key = f'{key_prefix.rstrip("/")}/{rel}'
        _upload_file_to_s3(s3, bucket, key, str(file_path), content_type=_content_type_for_path(rel))


def _ensure_parent_dir(path: Path) -> None:
    os.makedirs(str(path.parent), exist_ok=True)


def _write_text_response(text: str, content_type: str) -> HttpResponse:
    resp = HttpResponse(text, content_type=content_type)
    resp['Cache-Control'] = 'public, max-age=60'
    return resp


def _generate_hls_variants(input_path: str, out_dir: str) -> bool:
    hls_dir = Path(out_dir) / 'hls'
    os.makedirs(str(hls_dir), exist_ok=True)
    has_audio = _ffprobe_has_audio(input_path)
    base = [
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-filter_complex',
        '[0:v]split=3[v1][v2][v3];[v1]scale=w=-2:h=360:force_original_aspect_ratio=decrease[v360];[v2]scale=w=-2:h=480:force_original_aspect_ratio=decrease[v480];[v3]scale=w=-2:h=720:force_original_aspect_ratio=decrease[v720]',
        '-map', '[v360]',
        '-map', '[v480]',
        '-map', '[v720]',
    ]
    if has_audio:
        base += ['-map', '0:a:0?']
        audio_args = ['-c:a', 'aac', '-ac', '2', '-ar', '48000', '-b:a', '96k']
        var_map = 'v:0,a:0,name:360p v:1,a:0,name:480p v:2,a:0,name:720p'
    else:
        audio_args = ['-an']
        var_map = 'v:0,name:360p v:1,name:480p v:2,name:720p'

    base += [
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-profile:v', 'main',
        '-crf', '23',
        '-g', '48',
        '-keyint_min', '48',
        '-sc_threshold', '0',
        *audio_args,
        '-maxrate:v:0', '700k', '-bufsize:v:0', '1400k',
        '-maxrate:v:1', '1200k', '-bufsize:v:1', '2400k',
        '-maxrate:v:2', '2200k', '-bufsize:v:2', '4400k',
        '-f', 'hls',
        '-hls_time', '4',
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', str(hls_dir / 'v%v' / 'seg_%05d.ts').replace('\\', '/'),
        '-master_pl_name', 'master.m3u8',
        '-var_stream_map', var_map,
        str(hls_dir / 'v%v' / 'prog_index.m3u8').replace('\\', '/'),
    ]
    return _run_ffmpeg(base)


def _generate_dash_variants(input_path: str, out_dir: str) -> bool:
    dash_dir = Path(out_dir) / 'dash'
    os.makedirs(str(dash_dir), exist_ok=True)
    has_audio = _ffprobe_has_audio(input_path)

    cmd = [
        'ffmpeg',
        '-y',
        '-i', input_path,
        '-filter_complex',
        '[0:v]split=3[v1][v2][v3];[v1]scale=w=-2:h=360:force_original_aspect_ratio=decrease[v360];[v2]scale=w=-2:h=480:force_original_aspect_ratio=decrease[v480];[v3]scale=w=-2:h=720:force_original_aspect_ratio=decrease[v720]',
        '-map', '[v360]',
        '-map', '[v480]',
        '-map', '[v720]',
    ]
    if has_audio:
        cmd += ['-map', '0:a:0?']
        audio_args = ['-c:a', 'aac', '-ac', '2', '-ar', '48000', '-b:a', '96k']
        adapt_sets = 'id=0,streams=v id=1,streams=a'
    else:
        audio_args = ['-an']
        adapt_sets = 'id=0,streams=v'

    cmd += [
        '-c:v', 'libx264',
        '-preset', 'veryfast',
        '-profile:v', 'main',
        '-crf', '23',
        '-g', '48',
        '-keyint_min', '48',
        '-sc_threshold', '0',
        *audio_args,
        '-f', 'dash',
        '-seg_duration', '4',
        '-use_template', '1',
        '-use_timeline', '1',
        '-init_seg_name', 'init-$RepresentationID$.mp4',
        '-media_seg_name', 'chunk-$RepresentationID$-$Number%05d$.m4s',
        '-adaptation_sets', adapt_sets,
        str(dash_dir / 'manifest.mpd'),
    ]
    return _run_ffmpeg(cmd)


def _ensure_video_streams(photo: AlbumPhoto, input_path: str, s3=None, bucket: str | None = None) -> None:
    key = getattr(photo.image, 'name', None) or ''
    sid = _safe_stem_from_key(key, fallback=str(getattr(photo, 'id', '')))
    hls_master_key = f'{_STREAMS_PREFIX}/{sid}/hls/master.m3u8'

    if getattr(settings, 'USE_S3_MEDIA', False):
        if not s3 or not bucket:
            return
        if _s3_key_exists(s3, bucket, hls_master_key):
            return
    else:
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_master = (Path(media_root) / hls_master_key).resolve()
        if local_master.exists():
            return

    work_dir = tempfile.mkdtemp(prefix='album_streams_')
    try:
        ok_hls = _generate_hls_variants(input_path, work_dir)
        ok_dash = _generate_dash_variants(input_path, work_dir)
        if not ok_hls and not ok_dash:
            return

        if getattr(settings, 'USE_S3_MEDIA', False):
            if ok_hls:
                _upload_dir_to_s3(s3, bucket, str(Path(work_dir) / 'hls'), f'{_STREAMS_PREFIX}/{sid}/hls')
            if ok_dash:
                _upload_dir_to_s3(s3, bucket, str(Path(work_dir) / 'dash'), f'{_STREAMS_PREFIX}/{sid}/dash')
            return

        media_root = Path(getattr(settings, 'MEDIA_ROOT', ''))
        if ok_hls:
            for fp in (Path(work_dir) / 'hls').rglob('*'):
                if fp.is_dir():
                    continue
                rel = fp.relative_to(Path(work_dir) / 'hls')
                dst = (media_root / _STREAMS_PREFIX / sid / 'hls' / rel).resolve()
                _ensure_parent_dir(dst)
                shutil.copyfile(str(fp), str(dst))
        if ok_dash:
            for fp in (Path(work_dir) / 'dash').rglob('*'):
                if fp.is_dir():
                    continue
                rel = fp.relative_to(Path(work_dir) / 'dash')
                dst = (media_root / _STREAMS_PREFIX / sid / 'dash' / rel).resolve()
                _ensure_parent_dir(dst)
                shutil.copyfile(str(fp), str(dst))
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def _ensure_video_streams_for_src(stream_id: str, src_key: str, s3=None, bucket: str | None = None) -> None:
    if not stream_id or not src_key or '..' in src_key:
        return
    if not re.match(r'^[a-zA-Z0-9/_\-.]+$', src_key):
        return
    if not getattr(settings, 'USE_S3_MEDIA', False) or not s3 or not bucket:
        return
    if not _ffmpeg_available():
        return

    hls_master_key = f'{_STREAMS_PREFIX}/{stream_id}/hls/master.m3u8'
    if _s3_key_exists(s3, bucket, hls_master_key):
        return

    tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=Path(src_key).suffix or '.mp4')
    os.close(tmp_in_fd)
    work_dir = tempfile.mkdtemp(prefix='album_streams_')
    try:
        _download_s3_object_to_file(s3, bucket, src_key, tmp_in)
        ok_hls = _generate_hls_variants(tmp_in, work_dir)
        ok_dash = _generate_dash_variants(tmp_in, work_dir)
        if not ok_hls and not ok_dash:
            return
        if ok_hls:
            _upload_dir_to_s3(s3, bucket, str(Path(work_dir) / 'hls'), f'{_STREAMS_PREFIX}/{stream_id}/hls')
        if ok_dash:
            _upload_dir_to_s3(s3, bucket, str(Path(work_dir) / 'dash'), f'{_STREAMS_PREFIX}/{stream_id}/dash')
    finally:
        try:
            if tmp_in and os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


def _ensure_image_variants(photo: AlbumPhoto, input_path: str, s3=None, bucket: str | None = None) -> None:
    key = getattr(photo.image, 'name', None) or ''
    sid = _safe_stem_from_key(key, fallback=str(getattr(photo, 'id', '')))
    base_key = f'{_THUMBS_PREFIX}/{sid}_w400'

    _ensure_image_variants_for_base(base_key=base_key, input_path=input_path, width=400, s3=s3, bucket=bucket)


def _ensure_image_variants_for_base(base_key: str, input_path: str, width: int, s3=None, bucket: str | None = None) -> None:
    if not base_key:
        return

    if getattr(settings, 'USE_S3_MEDIA', False):
        if not s3 or not bucket:
            return
        if _s3_key_exists(s3, bucket, f'{base_key}.webp') or _s3_key_exists(s3, bucket, f'{base_key}.jpg'):
            return
    else:
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_webp = (Path(media_root) / f'{base_key}.webp').resolve()
        local_jpg = (Path(media_root) / f'{base_key}.jpg').resolve()
        if local_webp.exists() or local_jpg.exists():
            return

    try:
        with Image.open(input_path) as im:
            im = im.convert('RGB')
            w = int(width) if int(width) > 0 else 400
            h = int(im.height * (w / float(im.width))) if im.width else w
            im = im.resize((w, max(1, h)))

            tmp_dir = tempfile.mkdtemp(prefix='album_thumb_')
            try:
                out_webp = Path(tmp_dir) / 'thumb.webp'
                out_jpg = Path(tmp_dir) / 'thumb.jpg'
                out_avif = Path(tmp_dir) / 'thumb.avif'
                try:
                    im.save(str(out_webp), format='WEBP', quality=75, method=6)
                except Exception:
                    pass
                try:
                    im.save(str(out_jpg), format='JPEG', quality=80, optimize=True, progressive=True)
                except Exception:
                    pass
                try:
                    im.save(str(out_avif), format='AVIF', quality=50)
                except Exception:
                    pass

                if getattr(settings, 'USE_S3_MEDIA', False):
                    if out_webp.exists():
                        _upload_file_to_s3(s3, bucket, f'{base_key}.webp', str(out_webp), content_type='image/webp')
                    if out_avif.exists():
                        _upload_file_to_s3(s3, bucket, f'{base_key}.avif', str(out_avif), content_type='image/avif')
                    if out_jpg.exists():
                        _upload_file_to_s3(s3, bucket, f'{base_key}.jpg', str(out_jpg), content_type='image/jpeg')
                    return

                media_root = Path(getattr(settings, 'MEDIA_ROOT', ''))
                if out_webp.exists():
                    dst = (media_root / f'{base_key}.webp').resolve()
                    _ensure_parent_dir(dst)
                    shutil.copyfile(str(out_webp), str(dst))
                if out_avif.exists():
                    dst = (media_root / f'{base_key}.avif').resolve()
                    _ensure_parent_dir(dst)
                    shutil.copyfile(str(out_avif), str(dst))
                if out_jpg.exists():
                    dst = (media_root / f'{base_key}.jpg').resolve()
                    _ensure_parent_dir(dst)
                    shutil.copyfile(str(out_jpg), str(dst))
            finally:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception:
                    pass
    except Exception:
        return


def process_image_variants_for_key(*, key: str, base_key: str, width: int = 400) -> None:
    key = (key or '').strip().lstrip('/')
    base_key = (base_key or '').strip().lstrip('/')
    if not key or not base_key:
        return

    tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=Path(key).suffix or '.jpg')
    os.close(tmp_in_fd)
    try:
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return
            s3 = _get_s3_client()
            _download_s3_object_to_file(s3, bucket, key, tmp_in)
            _ensure_image_variants_for_base(base_key=base_key, input_path=tmp_in, width=width, s3=s3, bucket=bucket)
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return
        shutil.copyfile(str(local_path), tmp_in)
        _ensure_image_variants_for_base(base_key=base_key, input_path=tmp_in, width=width)
    finally:
        try:
            if tmp_in and os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass



def _process_album_photo_video(photo: AlbumPhoto, asset: MediaAsset | None = None) -> None:
    if not photo or not getattr(photo, 'is_video', False):
        return

    key = getattr(photo.image, 'name', None) or ''
    if not key:
        return
    if not _ffmpeg_available():
        return

    tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=Path(key).suffix or '.mp4')
    os.close(tmp_in_fd)
    tmp_out_fd, tmp_out = tempfile.mkstemp(suffix=Path(key).suffix or '.mp4')
    os.close(tmp_out_fd)
    tmp_poster_fd, tmp_poster = tempfile.mkstemp(suffix='.jpg')
    os.close(tmp_poster_fd)

    try:
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return
            s3 = _get_s3_client()
            _download_s3_object_to_file(s3, bucket, key, tmp_in)
            content_type = None
            if asset and getattr(asset, 'content_type', None):
                content_type = asset.content_type
            if not content_type:
                content_type, _ = mimetypes.guess_type(key)

            stream_input = tmp_in
            if _optimize_faststart(tmp_in, tmp_out):
                _upload_file_to_s3(s3, bucket, key, tmp_out, content_type=content_type)
                stream_input = tmp_out

            if _extract_poster(stream_input, tmp_poster):
                poster_key = f'baby_album/posters/{_safe_stem_from_key(key, fallback=str(getattr(photo, "id", "")))}.jpg'
                _upload_file_to_s3(s3, bucket, poster_key, tmp_poster, content_type='image/jpeg')
                photo.poster.name = poster_key
                photo.save(update_fields=['poster'])
            _ensure_video_streams(photo, stream_input, s3=s3, bucket=bucket)
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return
        shutil.copyfile(str(local_path), tmp_in)

        if _optimize_faststart(tmp_in, tmp_out):
            os.makedirs(str(local_path.parent), exist_ok=True)
            shutil.move(tmp_out, str(local_path))

        if _extract_poster(str(local_path), tmp_poster):
            with open(tmp_poster, 'rb') as f:
                poster_name = f'{Path(key).stem}.jpg'
                photo.poster.save(poster_name, File(f), save=False)
            photo.save(update_fields=['poster'])
        _ensure_video_streams(photo, str(local_path))
    finally:
        for p in [tmp_in, tmp_out, tmp_poster]:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


def _process_album_photo_image(photo: AlbumPhoto, asset: MediaAsset | None = None) -> None:
    if not photo or getattr(photo, 'is_video', False):
        return

    key = getattr(photo.image, 'name', None) or ''
    if not key:
        return

    tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=Path(key).suffix or '.jpg')
    os.close(tmp_in_fd)
    try:
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return
            s3 = _get_s3_client()
            _download_s3_object_to_file(s3, bucket, key, tmp_in)
            _ensure_image_variants(photo, tmp_in, s3=s3, bucket=bucket)
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return
        shutil.copyfile(str(local_path), tmp_in)
        _ensure_image_variants(photo, tmp_in)
    finally:
        try:
            if tmp_in and os.path.exists(tmp_in):
                os.remove(tmp_in)
        except Exception:
            pass


class AlbumVideoPlaybackInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, stream_id: str, *args, **kwargs):
        photos = AlbumPhoto.objects.filter(album__user=request.user, is_video=True)
        photo = None
        for p in photos.only('id', 'image', 'poster', 'is_video'):
            key = getattr(getattr(p, 'image', None), 'name', None) or ''
            sid = _safe_stem_from_key(key, fallback=str(p.id))
            if sid == stream_id:
                photo = p
                break
        if not photo:
            return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)

        key = getattr(getattr(photo, 'image', None), 'name', None) or ''
        mp4_url = ''
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if bucket and key:
                s3 = _get_s3_client()
                try:
                    mp4_url = s3.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=600,
                    )
                except Exception:
                    mp4_url = ''
        else:
            try:
                mp4_url = request.build_absolute_uri(photo.image.url)
            except Exception:
                mp4_url = ''

        hls_url = request.build_absolute_uri(f'/baby/albums/video/{stream_id}/hls/master.m3u8')
        dash_url = request.build_absolute_uri(f'/baby/albums/video/{stream_id}/dash/manifest.mpd')
        poster_url = ''
        try:
            poster_url = request.build_absolute_uri(photo.poster.url) if getattr(photo, 'poster', None) else ''
        except Exception:
            poster_url = ''

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'mp4': mp4_url,
                'hls': hls_url,
                'dash': dash_url,
                'poster': poster_url,
            }
        })


class AlbumVideoHlsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, stream_id: str, playlist_path: str, *args, **kwargs):
        rel = (playlist_path or '').lstrip('/')
        if '..' in rel or not rel:
            return Response({'code': 400, 'msg': 'invalid path', 'data': None}, status=400)

        key = f'{_STREAMS_PREFIX}/{stream_id}/hls/{rel}'
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return Response({'code': 500, 'msg': 'S3 bucket not configured', 'data': None}, status=500)
            s3 = _get_s3_client()
            if rel.lower().endswith('.m3u8'):
                try:
                    obj = s3.get_object(Bucket=bucket, Key=key)
                    text = obj['Body'].read().decode('utf-8', errors='ignore')
                except Exception:
                    src = (request.query_params.get('src') or '').strip()
                    if src:
                        _ensure_video_streams_for_src(stream_id=stream_id, src_key=src, s3=s3, bucket=bucket)
                        try:
                            obj = s3.get_object(Bucket=bucket, Key=key)
                            text = obj['Body'].read().decode('utf-8', errors='ignore')
                        except Exception:
                            return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
                    else:
                        return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
                out = (text or '')
                if out and not out.endswith('\n'):
                    out += '\n'
                return _write_text_response(out, content_type='application/vnd.apple.mpegurl')
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=600,
            )
            return redirect(url)

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return Response({'code': 500, 'msg': 'MEDIA_ROOT not configured', 'data': None}, status=500)
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
        if rel.lower().endswith('.m3u8'):
            try:
                text = local_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
            out = (text or '')
            if out and not out.endswith('\n'):
                out += '\n'
            return _write_text_response(out, content_type='application/vnd.apple.mpegurl')
        return redirect(f'/media/{key}')


class AlbumVideoDashView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, stream_id: str, dash_path: str, *args, **kwargs):
        rel = (dash_path or '').lstrip('/')
        if '..' in rel or not rel:
            return Response({'code': 400, 'msg': 'invalid path', 'data': None}, status=400)

        key = f'{_STREAMS_PREFIX}/{stream_id}/dash/{rel}'
        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return Response({'code': 500, 'msg': 'S3 bucket not configured', 'data': None}, status=500)
            s3 = _get_s3_client()
            if rel.lower().endswith('.mpd'):
                try:
                    obj = s3.get_object(Bucket=bucket, Key=key)
                    text = obj['Body'].read().decode('utf-8', errors='ignore')
                except Exception:
                    src = (request.query_params.get('src') or '').strip()
                    if src:
                        _ensure_video_streams_for_src(stream_id=stream_id, src_key=src, s3=s3, bucket=bucket)
                        try:
                            obj = s3.get_object(Bucket=bucket, Key=key)
                            text = obj['Body'].read().decode('utf-8', errors='ignore')
                        except Exception:
                            return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
                    else:
                        return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
                return _write_text_response(text, content_type='application/dash+xml')
            url = s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=600,
            )
            return redirect(url)

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return Response({'code': 500, 'msg': 'MEDIA_ROOT not configured', 'data': None}, status=500)
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
        if rel.lower().endswith('.mpd'):
            try:
                text = local_path.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                return Response({'code': 404, 'msg': 'Not found', 'data': None}, status=404)
            return _write_text_response(text, content_type='application/dash+xml')
        return redirect(f'/media/{key}')


class BabyAlbumListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            page_size = 20
        try:
            page_num = int(request.query_params.get('page_num', 1))
        except (TypeError, ValueError):
            page_num = 1

        if page_size <= 0:
            page_size = 20
        if page_num <= 0:
            page_num = 1

        queryset = BabyAlbum.objects.filter(user=request.user).order_by('-happened_at', '-created_at')
        total = queryset.count()

        start = (page_num - 1) * page_size
        end = start + page_size
        page_data = queryset[start:end]

        serializer = BabyAlbumSerializer(page_data, many=True, context={'request': request})
        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'list': serializer.data,
                'total': total,
                'page_num': page_num,
                'page_size': page_size
            }
        })

    def post(self, request):
        try:
            # Avoid using copy() on QueryDict if it contains files to prevent pickling errors
            if hasattr(request.data, 'dict'):
                data = request.data.dict()
            else:
                data = request.data.copy()
                
            # Handle tags if they come as string (FormData)
            tags = data.get('tags')
            if tags and isinstance(tags, str):
                try:
                    # If tags are like "['tag1', 'tag2']" or just a string
                    # If it's just a comma separated string, split it
                    if tags.startswith('['):
                        data['tags'] = json.loads(tags)
                    else:
                         data['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
                except:
                    data['tags'] = []
            
            media_asset_ids = data.get('media_asset_ids') if isinstance(data, dict) else None
            serializer = BabyAlbumSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                try:
                    album = serializer.save()
                except DataError as e:
                    msg = str(e)
                    if 'incorrect string value' in msg.lower() or 'invalid utf8' in msg.lower():
                        return Response({'code': 400, 'msg': '内容包含表情/特殊字符，当前数据库编码不支持，请将 MySQL 字符集改为 utf8mb4', 'data': None})
                    raise
                
                # Handle images
                # FormData should append images with same key 'images' or 'file'
                images = request.FILES.getlist('images')
                if not images:
                    # Try 'file' as well just in case
                    images = request.FILES.getlist('file')

                if images and getattr(settings, 'USE_S3_MEDIA', False):
                    return Response({'code': 400, 'msg': '请使用 MinIO 直传上传', 'data': None})

                if images:
                    for image in images:
                        is_video = False
                        if hasattr(image, 'content_type') and image.content_type.startswith('video/'):
                            is_video = True
                        elif hasattr(image, 'name') and image.name.lower().endswith(('.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm')):
                            is_video = True
                        if is_video and _ffmpeg_available():
                            in_path, out_path = _write_uploaded_to_temp(image)
                            poster_fd, poster_path = tempfile.mkstemp(suffix='.jpg')
                            os.close(poster_fd)
                            try:
                                if _optimize_faststart(in_path, out_path):
                                    photo = AlbumPhoto(album=album, is_video=True)
                                    with open(out_path, 'rb') as f:
                                        photo.image.save(Path(getattr(image, 'name', 'video.mp4')).name, File(f), save=False)
                                    if _extract_poster(out_path, poster_path):
                                        with open(poster_path, 'rb') as pf:
                                            photo.poster.save(f'{Path(getattr(image, "name", "video")).stem}.jpg', File(pf), save=False)
                                    photo.save()
                                    try:
                                        _process_album_photo_video(photo)
                                    except Exception:
                                        logger.exception("album video post-process failed")
                                else:
                                    photo = AlbumPhoto.objects.create(album=album, image=image, is_video=True)
                                    try:
                                        _process_album_photo_video(photo)
                                    except Exception:
                                        logger.exception("album video post-process failed")
                            finally:
                                for p in [in_path, out_path, poster_path]:
                                    try:
                                        if p and os.path.exists(p):
                                            os.remove(p)
                                    except Exception:
                                        pass
                        else:
                            photo = AlbumPhoto.objects.create(album=album, image=image, is_video=is_video)
                            if is_video:
                                try:
                                    _process_album_photo_video(photo)
                                except Exception:
                                    logger.exception("album video post-process failed")
                            else:
                                try:
                                    _process_album_photo_image(photo)
                                except Exception:
                                    logger.exception("album image post-process failed")
                elif isinstance(media_asset_ids, list) and media_asset_ids:
                    assets = list(MediaAsset.objects.filter(user=request.user, id__in=media_asset_ids, status=MediaAsset.Status.UPLOADED))
                    by_id = {a.id: a for a in assets}
                    for aid in media_asset_ids:
                        asset = by_id.get(aid)
                        if not asset:
                            continue
                        photo = AlbumPhoto.objects.create(album=album, image=asset.object_key, is_video=asset.is_video)
                        try:
                            if asset.is_video:
                                _process_album_photo_video(photo, asset=asset)
                            else:
                                _process_album_photo_image(photo, asset=asset)
                        except Exception:
                            logger.exception("album video post-process failed")
                        asset.ref_type = 'baby_album'
                        asset.ref_id = album.id
                        asset.status = MediaAsset.Status.BOUND
                        asset.save(update_fields=['ref_type', 'ref_id', 'status', 'updated_at'])
                
                # Refresh to include photos in response
                return Response({'code': 200, 'msg': 'ok', 'data': BabyAlbumSerializer(album, context={'request': request}).data})
            
            return Response({'code': 400, 'msg': str(serializer.errors), 'data': None})
        except Exception as e:
            logger.exception("BabyAlbum create error")
            return Response({'code': 500, 'msg': str(e), 'data': None})

class BabyAlbumDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            album = BabyAlbum.objects.get(pk=pk, user=request.user)
            album.delete()
            return Response({'code': 200, 'msg': 'ok', 'data': None})
        except BabyAlbum.DoesNotExist:
            return Response({'code': 404, 'msg': 'Not found', 'data': None})
