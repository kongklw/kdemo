from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import File
from .models import MediaAsset
from django.conf import settings
from django.http import FileResponse
from django.core.files.storage import default_storage
from django.shortcuts import redirect
from uuid import uuid4
from pathlib import Path
import boto3
from botocore.config import Config
import mimetypes
import re
import tempfile
import os
import shutil
import subprocess
from urllib.parse import unquote

class CommonFileUpload(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file', None)
        if not file:
            return Response({'code': 400, 'msg': 'No file uploaded', 'data': None})
        
        # 保存文件记录到数据库并关联用户
        # FileField 会自动处理文件保存到 MEDIA_ROOT/files/... (由 user_directory_path 定义)
        file_obj = File(user=request.user, file=file, upload_method='upload')
        file_obj.save()
        
        # 获取相对路径或URL
        # 注意：这里假设前端需要的是相对路径或完整URL，根据 FileField 的 url 属性
        file_url = file_obj.file.url
        name = file_obj.file.name # 包含路径的文件名

        return Response({'code': 200, 'data': {'id': file_obj.id, 'name': name, 'url': file_url}, 'msg': 'ok'})

        # files = request.FILES.getlist("file", None)
        # file_list = []
        # for file in files:
        #
        #     name = file.name
        #     file_list.append(name)
        #     path = os.path.join(MEDIA_ROOT + name)
        #
        #     with open(path, 'wb') as f:
        #         for content in file.chunks():
        #             f.write(content)
        #
        # return Response({'code': 200, 'data': file_list, 'msg': 'ok'})


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


def _make_object_key(purpose: str, filename: str) -> str:
    safe_purpose = purpose.strip().lower()
    ext = Path(filename or '').suffix
    ext = ext[:20] if ext else ''
    uid = uuid4().hex
    if ext and not ext.startswith('.'):
        ext = f'.{ext}'
    if safe_purpose == 'baby_album':
        prefix = 'baby_album'
    elif safe_purpose == 'growth':
        prefix = 'growth'
    elif safe_purpose == 'files':
        prefix = 'files'
    else:
        prefix = 'uploads'
    return f'{prefix}/{uid}{ext}'


def _ffmpeg_available() -> bool:
    return bool(shutil.which('ffmpeg'))


def _run_ffmpeg(args: list[str]) -> bool:
    try:
        p = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return p.returncode == 0
    except Exception:
        return False


def _extract_video_poster(input_path: str, output_path: str) -> bool:
    ok = _run_ffmpeg([
        'ffmpeg',
        '-y',
        '-ss', '00:00:01.000',
        '-i', input_path,
        '-frames:v', '1',
        '-q:v', '2',
        output_path,
    ])
    return bool(ok and os.path.exists(output_path) and os.path.getsize(output_path) > 0)


class PresignInitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            return Response({'code': 400, 'msg': 'S3 media not enabled', 'data': None})

        payload = request.data or {}
        purpose = (payload.get('purpose') or '').strip()
        filename = (payload.get('filename') or '').strip()
        content_type = (payload.get('content_type') or '').strip()
        size_bytes = payload.get('size')
        is_video = bool(payload.get('is_video', False))

        if not purpose:
            return Response({'code': 400, 'msg': 'purpose 必填', 'data': None})
        if not filename:
            return Response({'code': 400, 'msg': 'filename 必填', 'data': None})

        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        if not bucket or not endpoint or not access_key or not secret_key:
            return Response({'code': 500, 'msg': 'S3 configuration incomplete', 'data': None})

        object_key = _make_object_key(purpose, filename)
        asset = MediaAsset.objects.create(
            user=request.user,
            bucket=bucket,
            object_key=object_key,
            original_name=filename[:255],
            content_type=content_type[:255] if content_type else None,
            size_bytes=size_bytes if isinstance(size_bytes, int) else None,
            is_video=is_video,
            purpose=purpose[:64],
            status=MediaAsset.Status.INIT,
        )

        s3 = _get_s3_client()
        put_params = {'Bucket': bucket, 'Key': object_key}
        if content_type:
            put_params['ContentType'] = content_type
        upload_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params=put_params,
            ExpiresIn=int(payload.get('expires_in', 600) or 600),
        )

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'asset_id': asset.id,
                'bucket': bucket,
                'object_key': object_key,
                'upload_url': upload_url,
                'headers': {'Content-Type': content_type} if content_type else {},
            }
        })


class PresignCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            return Response({'code': 400, 'msg': 'S3 media not enabled', 'data': None})

        payload = request.data or {}
        asset_id = payload.get('asset_id')
        if not asset_id:
            return Response({'code': 400, 'msg': 'asset_id 必填', 'data': None})

        asset = MediaAsset.objects.filter(id=asset_id, user=request.user).first()
        if not asset:
            return Response({'code': 404, 'msg': 'asset 不存在', 'data': None})

        s3 = _get_s3_client()
        try:
            head = s3.head_object(Bucket=asset.bucket, Key=asset.object_key)
        except Exception:
            return Response({'code': 400, 'msg': '对象未找到或不可访问', 'data': None})

        etag = head.get('ETag')
        size = head.get('ContentLength')
        content_type = head.get('ContentType') or asset.content_type

        asset.etag = (etag or '').strip('"') if etag else asset.etag
        asset.size_bytes = int(size) if isinstance(size, int) else asset.size_bytes
        asset.content_type = content_type
        asset.status = MediaAsset.Status.UPLOADED
        asset.save(update_fields=['etag', 'size_bytes', 'content_type', 'status', 'updated_at'])

        return Response({
            'code': 200,
            'msg': 'ok',
            'data': {
                'asset_id': asset.id,
                'bucket': asset.bucket,
                'object_key': asset.object_key,
            }
        })


class PresignGetUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            return Response({'code': 400, 'msg': 'S3 media not enabled', 'data': None})

        asset_id = request.query_params.get('asset_id')
        if not asset_id:
            return Response({'code': 400, 'msg': 'asset_id 必填', 'data': None})

        asset = MediaAsset.objects.filter(id=asset_id, user=request.user).first()
        if not asset:
            return Response({'code': 404, 'msg': 'asset 不存在', 'data': None})

        s3 = _get_s3_client()
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': asset.bucket, 'Key': asset.object_key},
            ExpiresIn=int(request.query_params.get('expires_in', 600) or 600),
        )

        return Response({'code': 200, 'msg': 'ok', 'data': {'url': url}})


class FileRedirectView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, file_id=None, *args, **kwargs):
        key = None
        if file_id is not None:
            file_obj = File.objects.filter(id=file_id).first()
            if not file_obj or not getattr(file_obj, 'file', None):
                return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)
            key = getattr(file_obj.file, 'name', None) or None
        else:
            key = (request.query_params.get('key') or '').strip() or None

        if not key:
            return Response({'code': 400, 'msg': 'key required', 'data': None}, status=400)
        if '..' in key:
            return Response({'code': 400, 'msg': 'invalid key', 'data': None}, status=400)

        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return Response({'code': 500, 'msg': 'S3 bucket not configured', 'data': None}, status=500)
            s3 = _get_s3_client()
            expires_in = int(request.query_params.get('expires_in', 600) or 600)
            try:
                s3.head_object(Bucket=bucket, Key=key)
                url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=expires_in,
                )
                return redirect(url)
            except Exception:
                src = (request.query_params.get('src') or '').strip()
                if src:
                    src = unquote(src)
                if (
                    src
                    and key.startswith('baby_album/posters/')
                    and key.lower().endswith('.jpg')
                    and re.match(r'^[a-zA-Z0-9/_\-.]+$', src)
                    and '..' not in src
                    and _ffmpeg_available()
                ):
                    tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=Path(src).suffix or '.mp4')
                    os.close(tmp_in_fd)
                    tmp_out_fd, tmp_out = tempfile.mkstemp(suffix='.jpg')
                    os.close(tmp_out_fd)
                    try:
                        try:
                            s3.download_file(bucket, src, tmp_in)
                        except Exception:
                            pass
                        if _extract_video_poster(tmp_in, tmp_out):
                            with open(tmp_out, 'rb') as f:
                                s3.upload_fileobj(f, bucket, key, ExtraArgs={'ContentType': 'image/jpeg'})
                            try:
                                s3.head_object(Bucket=bucket, Key=key)
                                url = s3.generate_presigned_url(
                                    ClientMethod='get_object',
                                    Params={'Bucket': bucket, 'Key': key},
                                    ExpiresIn=expires_in,
                                )
                                return redirect(url)
                            except Exception:
                                pass
                    finally:
                        for p in [tmp_in, tmp_out]:
                            try:
                                if p and os.path.exists(p):
                                    os.remove(p)
                            except Exception:
                                pass

        content_type, _ = mimetypes.guess_type(key)
        try:
            f = default_storage.open(key, 'rb')
        except Exception:
            return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)
        return FileResponse(f, content_type=content_type or 'application/octet-stream')


class ImageBestRedirectView(APIView):
    authentication_classes = []
    permission_classes = []

    _SAFE_BASE_RE = re.compile(r'^[a-zA-Z0-9/_\-.]+$')
    _WIDTH_RE = re.compile(r'_w(\d+)$')

    def get(self, request, *args, **kwargs):
        base = (request.query_params.get('base') or '').strip()
        if not base or not self._SAFE_BASE_RE.match(base) or '..' in base:
            return Response({'code': 400, 'msg': 'base required', 'data': None}, status=400)

        src = (request.query_params.get('src') or '').strip()
        if src:
            src = unquote(src)
            if not self._SAFE_BASE_RE.match(src) or '..' in src:
                return Response({'code': 400, 'msg': 'invalid src', 'data': None}, status=400)

        accept = (request.headers.get('Accept') or '').lower()
        candidates = []
        if 'image/avif' in accept:
            candidates.append(f'{base}.avif')
        if 'image/webp' in accept:
            candidates.append(f'{base}.webp')
        candidates.append(f'{base}.jpg')

        expires_in = int(request.query_params.get('expires_in', 600) or 600)
        m = self._WIDTH_RE.search(base)
        width = 400
        if m:
            try:
                width = int(m.group(1))
            except Exception:
                width = 400

        if getattr(settings, 'USE_S3_MEDIA', False):
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            if not bucket:
                return Response({'code': 500, 'msg': 'S3 bucket not configured', 'data': None}, status=500)
            s3 = _get_s3_client()
            for key in candidates:
                try:
                    s3.head_object(Bucket=bucket, Key=key)
                except Exception:
                    continue
                url = s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': bucket, 'Key': key},
                    ExpiresIn=expires_in,
                )
                return redirect(url)

            if src:
                tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=os.path.splitext(src)[1] or '.jpg')
                os.close(tmp_in_fd)
                tmp_dir = tempfile.mkdtemp(prefix='img_variants_')
                try:
                    try:
                        s3.download_file(bucket, src, tmp_in)
                    except Exception:
                        return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)

                    try:
                        from PIL import Image
                    except Exception:
                        return Response({'code': 500, 'msg': 'PIL not available', 'data': None}, status=500)

                    out_webp = os.path.join(tmp_dir, 'thumb.webp')
                    out_jpg = os.path.join(tmp_dir, 'thumb.jpg')
                    out_avif = os.path.join(tmp_dir, 'thumb.avif')
                    try:
                        with Image.open(tmp_in) as im:
                            im = im.convert('RGB')
                            w = int(width) if int(width) > 0 else 400
                            h = int(im.height * (w / float(im.width))) if im.width else w
                            im = im.resize((w, max(1, h)))
                            try:
                                im.save(out_webp, 'WEBP', quality=80, method=6)
                            except Exception:
                                pass
                            try:
                                im.save(out_avif, 'AVIF', quality=50)
                            except Exception:
                                pass
                            im.save(out_jpg, 'JPEG', quality=82, optimize=True, progressive=True)
                    except Exception:
                        return Response({'code': 500, 'msg': 'image processing failed', 'data': None}, status=500)

                    if os.path.exists(out_webp):
                        with open(out_webp, 'rb') as f:
                            s3.upload_fileobj(f, bucket, f'{base}.webp', ExtraArgs={'ContentType': 'image/webp'})
                    if os.path.exists(out_avif):
                        with open(out_avif, 'rb') as f:
                            s3.upload_fileobj(f, bucket, f'{base}.avif', ExtraArgs={'ContentType': 'image/avif'})
                    if os.path.exists(out_jpg):
                        with open(out_jpg, 'rb') as f:
                            s3.upload_fileobj(f, bucket, f'{base}.jpg', ExtraArgs={'ContentType': 'image/jpeg'})

                    for key in candidates:
                        try:
                            s3.head_object(Bucket=bucket, Key=key)
                        except Exception:
                            continue
                        url = s3.generate_presigned_url(
                            ClientMethod='get_object',
                            Params={'Bucket': bucket, 'Key': key},
                            ExpiresIn=expires_in,
                        )
                        return redirect(url)
                finally:
                    try:
                        if tmp_in and os.path.exists(tmp_in):
                            os.remove(tmp_in)
                    except Exception:
                        pass
                    try:
                        if tmp_dir and os.path.exists(tmp_dir):
                            for root, dirs, files in os.walk(tmp_dir, topdown=False):
                                for name in files:
                                    try:
                                        os.remove(os.path.join(root, name))
                                    except Exception:
                                        pass
                                for name in dirs:
                                    try:
                                        os.rmdir(os.path.join(root, name))
                                    except Exception:
                                        pass
                            try:
                                os.rmdir(tmp_dir)
                            except Exception:
                                pass
                    except Exception:
                        pass

            return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)

        for key in candidates:
            if default_storage.exists(key):
                return redirect(f'/file/r?key={key}')
        if src and default_storage.exists(src):
            try:
                from PIL import Image
            except Exception:
                return Response({'code': 500, 'msg': 'PIL not available', 'data': None}, status=500)

            tmp_in_fd, tmp_in = tempfile.mkstemp(suffix=os.path.splitext(src)[1] or '.jpg')
            os.close(tmp_in_fd)
            tmp_dir = tempfile.mkdtemp(prefix='img_variants_')
            try:
                try:
                    with default_storage.open(src, 'rb') as rf:
                        with open(tmp_in, 'wb') as wf:
                            wf.write(rf.read())
                except Exception:
                    return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)

                out_webp = os.path.join(tmp_dir, 'thumb.webp')
                out_jpg = os.path.join(tmp_dir, 'thumb.jpg')
                out_avif = os.path.join(tmp_dir, 'thumb.avif')
                try:
                    with Image.open(tmp_in) as im:
                        im = im.convert('RGB')
                        w = int(width) if int(width) > 0 else 400
                        h = int(im.height * (w / float(im.width))) if im.width else w
                        im = im.resize((w, max(1, h)))
                        try:
                            im.save(out_webp, 'WEBP', quality=80, method=6)
                        except Exception:
                            pass
                        try:
                            im.save(out_avif, 'AVIF', quality=50)
                        except Exception:
                            pass
                        im.save(out_jpg, 'JPEG', quality=82, optimize=True, progressive=True)
                except Exception:
                    return Response({'code': 500, 'msg': 'image processing failed', 'data': None}, status=500)

                if os.path.exists(out_webp):
                    with open(out_webp, 'rb') as f:
                        default_storage.save(f'{base}.webp', f)
                if os.path.exists(out_avif):
                    with open(out_avif, 'rb') as f:
                        default_storage.save(f'{base}.avif', f)
                if os.path.exists(out_jpg):
                    with open(out_jpg, 'rb') as f:
                        default_storage.save(f'{base}.jpg', f)

                for key in candidates:
                    if default_storage.exists(key):
                        return redirect(f'/file/r?key={key}')
            finally:
                try:
                    if tmp_in and os.path.exists(tmp_in):
                        os.remove(tmp_in)
                except Exception:
                    pass
                try:
                    if tmp_dir and os.path.exists(tmp_dir):
                        for root, dirs, files in os.walk(tmp_dir, topdown=False):
                            for name in files:
                                try:
                                    os.remove(os.path.join(root, name))
                                except Exception:
                                    pass
                            for name in dirs:
                                try:
                                    os.rmdir(os.path.join(root, name))
                                except Exception:
                                    pass
                        try:
                            os.rmdir(tmp_dir)
                        except Exception:
                            pass
                except Exception:
                    pass
        return Response({'code': 404, 'msg': 'file not found', 'data': None}, status=404)
