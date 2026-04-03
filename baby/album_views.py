from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import BabyAlbum, AlbumPhoto
from fileUpload.models import MediaAsset
from .serializers import BabyAlbumSerializer
from django.conf import settings
from django.core.files.base import File
import json
import logging
import mimetypes
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

def _ffmpeg_available() -> bool:
    return bool(shutil.which('ffmpeg'))


def _run_ffmpeg(args: list[str]) -> bool:
    try:
        p = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return p.returncode == 0
    except Exception:
        return False


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


def _process_album_photo_video(photo: AlbumPhoto, asset: MediaAsset | None = None) -> None:
    if not photo or not getattr(photo, 'is_video', False):
        return
    if not _ffmpeg_available():
        return

    key = getattr(photo.image, 'name', None) or ''
    if not key:
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
            if not _optimize_faststart(tmp_in, tmp_out):
                return
            content_type = None
            if asset and getattr(asset, 'content_type', None):
                content_type = asset.content_type
            if not content_type:
                content_type, _ = mimetypes.guess_type(key)
            _upload_file_to_s3(s3, bucket, key, tmp_out, content_type=content_type)
            if _extract_poster(tmp_out, tmp_poster):
                with open(tmp_poster, 'rb') as f:
                    poster_name = f'{Path(key).stem}.jpg'
                    photo.poster.save(poster_name, File(f), save=False)
                photo.save(update_fields=['poster'])
            return

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            return
        local_path = (Path(media_root) / key).resolve()
        if not local_path.exists() or local_path.is_dir():
            return
        shutil.copyfile(str(local_path), tmp_in)
        if not _optimize_faststart(tmp_in, tmp_out):
            return
        os.makedirs(str(local_path.parent), exist_ok=True)
        shutil.move(tmp_out, str(local_path))
        if _extract_poster(str(local_path), tmp_poster):
            with open(tmp_poster, 'rb') as f:
                poster_name = f'{Path(key).stem}.jpg'
                photo.poster.save(poster_name, File(f), save=False)
            photo.save(update_fields=['poster'])
    finally:
        for p in [tmp_in, tmp_out, tmp_poster]:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


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
                album = serializer.save()
                
                # Handle images
                # FormData should append images with same key 'images' or 'file'
                images = request.FILES.getlist('images')
                if not images:
                    # Try 'file' as well just in case
                    images = request.FILES.getlist('file')

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
                                else:
                                    AlbumPhoto.objects.create(album=album, image=image, is_video=True)
                            finally:
                                for p in [in_path, out_path, poster_path]:
                                    try:
                                        if p and os.path.exists(p):
                                            os.remove(p)
                                    except Exception:
                                        pass
                        else:
                            AlbumPhoto.objects.create(album=album, image=image, is_video=is_video)
                elif isinstance(media_asset_ids, list) and media_asset_ids:
                    assets = list(MediaAsset.objects.filter(user=request.user, id__in=media_asset_ids, status=MediaAsset.Status.UPLOADED))
                    by_id = {a.id: a for a in assets}
                    for aid in media_asset_ids:
                        asset = by_id.get(aid)
                        if not asset:
                            continue
                        photo = AlbumPhoto.objects.create(album=album, image=asset.object_key, is_video=asset.is_video)
                        try:
                            _process_album_photo_video(photo, asset=asset)
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
