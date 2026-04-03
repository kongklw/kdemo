from __future__ import annotations

import mimetypes
import shutil
import tempfile
from pathlib import Path

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from baby.models import AlbumPhoto
from baby.album_views import _ensure_image_variants, _ensure_video_streams


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


def _head_object(s3, bucket: str, key: str):
    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except Exception:
        return None


def _build_dest_key(prefix: str, photo_id: int, src_name: str) -> str:
    basename = Path(src_name or '').name
    return f'{prefix}/{photo_id}_{basename}'


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--start-id', type=int, default=0)
        parser.add_argument('--user-id', type=int, default=0)
        parser.add_argument('--prefix', type=str, default='baby_album/legacy')
        parser.add_argument('--overwrite', action='store_true')
        parser.add_argument('--log-every', type=int, default=1)
        parser.add_argument('--process-variants', action='store_true')
        parser.add_argument('--variants-only', action='store_true')

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            raise CommandError('USE_S3_MEDIA 未开启，无法迁移到 MinIO')

        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        if not bucket or not endpoint or not access_key or not secret_key:
            raise CommandError('MinIO/S3 配置不完整（bucket/endpoint/key/secret）')

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            raise CommandError('MEDIA_ROOT 未配置')
        media_root_path = Path(media_root)

        dry_run = bool(options['dry_run'])
        limit = int(options['limit'] or 0)
        start_id = int(options['start_id'] or 0)
        user_id = int(options['user_id'] or 0)
        prefix = (options['prefix'] or 'baby_album/legacy').strip().strip('/')
        overwrite = bool(options['overwrite'])
        log_every = int(options['log_every'] or 0)
        process_variants = bool(options['process_variants'])
        variants_only = bool(options['variants_only'])
        if log_every < 0:
            log_every = 0

        s3 = _get_s3_client()

        qs = AlbumPhoto.objects.select_related('album', 'album__user').order_by('id')
        if start_id > 0:
            qs = qs.filter(id__gte=start_id)
        if user_id > 0:
            qs = qs.filter(album__user_id=user_id)
        if limit > 0:
            qs = qs[:limit]

        total = qs.count()
        migrated = 0
        skipped = 0
        failed = 0

        self.stdout.write(f'total={total} dry_run={dry_run} bucket={bucket} prefix={prefix}')

        processed = 0
        for photo in qs.iterator(chunk_size=200):
            processed += 1
            if not photo.image or not photo.image.name:
                skipped += 1
                continue

            src_name = str(photo.image.name)
            if src_name.startswith('http://') or src_name.startswith('https://'):
                skipped += 1
                continue

            if variants_only:
                if not process_variants or dry_run:
                    migrated += 1
                    continue
                tmp_dir = tempfile.mkdtemp(prefix='album_media_')
                tmp_path = str(Path(tmp_dir) / Path(src_name).name)
                try:
                    s3.download_file(bucket, src_name, tmp_path)
                    if photo.is_video:
                        _ensure_video_streams(photo, tmp_path, s3=s3, bucket=bucket)
                    else:
                        _ensure_image_variants(photo, tmp_path, s3=s3, bucket=bucket)
                    migrated += 1
                except Exception as e:
                    failed += 1
                    self.stderr.write(f'failed variants id={photo.id} key={src_name} err={e}')
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                continue

            if src_name.startswith(f'{prefix}/'):
                migrated += 1
                continue

            local_path = (media_root_path / src_name).resolve()
            if not local_path.exists():
                skipped += 1
                continue

            if local_path.is_dir():
                skipped += 1
                continue

            dest_key = _build_dest_key(prefix, photo.id, src_name)
            local_size = local_path.stat().st_size

            if log_every and (processed == 1 or processed % log_every == 0):
                self.stdout.write(f'[{processed}/{total}] id={photo.id} size={local_size} src={src_name} dest={dest_key}')

            existing = _head_object(s3, bucket, dest_key)
            if existing and not overwrite:
                existing_size = existing.get('ContentLength')
                if isinstance(existing_size, int) and existing_size == local_size:
                    if not dry_run:
                        photo.image.name = dest_key
                        photo.save(update_fields=['image'])
                    migrated += 1
                    continue

            content_type, _ = mimetypes.guess_type(local_path.name)
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            try:
                if not dry_run:
                    with local_path.open('rb') as f:
                        if extra_args:
                            s3.upload_fileobj(f, bucket, dest_key, ExtraArgs=extra_args)
                        else:
                            s3.upload_fileobj(f, bucket, dest_key)

                    head = _head_object(s3, bucket, dest_key)
                    if not head:
                        raise RuntimeError('upload ok but head_object failed')
                    remote_size = head.get('ContentLength')
                    if isinstance(remote_size, int) and remote_size != local_size:
                        raise RuntimeError(f'size mismatch local={local_size} remote={remote_size}')

                    photo.image.name = dest_key
                    photo.save(update_fields=['image'])

                migrated += 1
            except Exception as e:
                failed += 1
                self.stderr.write(f'failed id={photo.id} src={src_name} err={e}')

            if process_variants and not dry_run:
                tmp_dir = tempfile.mkdtemp(prefix='album_media_')
                tmp_path = str(Path(tmp_dir) / Path(dest_key).name)
                try:
                    s3.download_file(bucket, dest_key, tmp_path)
                    if photo.is_video:
                        _ensure_video_streams(photo, tmp_path, s3=s3, bucket=bucket)
                    else:
                        _ensure_image_variants(photo, tmp_path, s3=s3, bucket=bucket)
                except Exception as e:
                    self.stderr.write(f'failed variants id={photo.id} key={dest_key} err={e}')
                finally:
                    shutil.rmtree(tmp_dir, ignore_errors=True)

        self.stdout.write(f'migrated={migrated} skipped={skipped} failed={failed}')
