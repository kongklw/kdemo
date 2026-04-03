from __future__ import annotations

import mimetypes
from pathlib import Path

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from baby.models import BabyInfo, GrowthRecord, BabyExpense
from fileUpload.models import File


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


def _upload_one(s3, bucket: str, local_path: Path, key: str, overwrite: bool) -> tuple[bool, str]:
    local_size = local_path.stat().st_size
    existing = _head_object(s3, bucket, key)
    if existing and not overwrite:
        existing_size = existing.get('ContentLength')
        if isinstance(existing_size, int) and existing_size == local_size:
            return False, 'exists'

    content_type, _ = mimetypes.guess_type(str(local_path))
    extra_args = {'ContentType': content_type} if content_type else None
    with local_path.open('rb') as f:
        if extra_args:
            s3.upload_fileobj(f, bucket, key, ExtraArgs=extra_args)
        else:
            s3.upload_fileobj(f, bucket, key)
    return True, 'uploaded'

def _extract_media_key(raw: str) -> str:
    if raw is None:
        return ''
    raw = str(raw).strip()
    if not raw:
        return ''
    if raw.startswith('data:image/'):
        return ''

    normalized = raw.replace('\\', '/')
    if '/media/' in normalized:
        normalized = normalized.split('/media/', 1)[1]

    return normalized.lstrip('/')


def _iter_expense_keys(qs):
    seen = set()
    for exp in qs.iterator(chunk_size=200):
        key = _extract_media_key(getattr(exp, 'image_url', None))
        if not key:
            continue
        if key.startswith('http://') or key.startswith('https://'):
            continue
        if key in seen:
            continue
        seen.add(key)
        yield exp.id, key


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--overwrite', action='store_true')
        parser.add_argument('--target', type=str, default='all')
        parser.add_argument('--log-every', type=int, default=50)

    def handle(self, *args, **options):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            raise CommandError('USE_S3_MEDIA 未开启，无法同步到 MinIO')

        bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        endpoint = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        if not bucket or not endpoint or not access_key or not secret_key:
            raise CommandError('S3 configuration incomplete')

        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if not media_root:
            raise CommandError('MEDIA_ROOT not set')
        media_root_path = Path(media_root)

        dry_run = bool(options['dry_run'])
        limit = int(options['limit'] or 0)
        overwrite = bool(options['overwrite'])
        target = str(options['target'] or 'all').strip().lower()
        log_every = int(options['log_every'] or 0)
        if log_every < 0:
            log_every = 0

        s3 = _get_s3_client()

        targets: list[tuple[str, object, str, str]] = []
        if target in ['all', 'baby_info', 'babyinfo']:
            targets.append(('baby_info', BabyInfo.objects.order_by('id'), 'image', 'id'))
        if target in ['all', 'growth', 'growth_record', 'growthrecord']:
            targets.append(('growth_record', GrowthRecord.objects.order_by('id'), 'photo', 'id'))
        if target in ['all', 'files', 'uploaded_files', 'fileupload']:
            targets.append(('uploaded_files', File.objects.order_by('id'), 'file', 'id'))
        if target in ['all', 'expense', 'expenses']:
            targets.append(('expense', BabyExpense.objects.order_by('id'), 'image_url', 'id'))

        if not targets:
            raise CommandError('target 无效，可选: all/baby_info/growth_record/files/expense')

        for label, qs, field_name, pk_name in targets:
            if label != 'expense':
                if limit > 0:
                    qs = qs[:limit]
                total = qs.count()
            else:
                total = qs.count() if limit <= 0 else min(limit, qs.count())
            processed = 0
            uploaded = 0
            skipped = 0
            failed = 0

            self.stdout.write(f'target={label} total={total} dry_run={dry_run} bucket={bucket}')

            if label == 'expense':
                it = _iter_expense_keys(qs if limit <= 0 else qs[:limit])
                for exp_id, key in it:
                    processed += 1
                    local_path = (media_root_path / key).resolve()
                    if not local_path.exists() or local_path.is_dir():
                        skipped += 1
                        continue

                    if log_every and (processed == 1 or processed % log_every == 0):
                        self.stdout.write(f'[{processed}/{total}] {label} id={exp_id} key={key}')

                    try:
                        if not dry_run:
                            did_upload, _ = _upload_one(s3, bucket, local_path, key, overwrite=overwrite)
                            if did_upload:
                                uploaded += 1
                            else:
                                skipped += 1
                        else:
                            uploaded += 1
                    except Exception as e:
                        failed += 1
                        self.stderr.write(f'failed target={label} id={exp_id} key={key} err={e}')
            else:
                for obj in qs.iterator(chunk_size=200):
                    processed += 1
                    file_field = getattr(obj, field_name, None)
                    src_name = getattr(file_field, 'name', None) if file_field else None
                    if not src_name:
                        skipped += 1
                        continue

                    key = str(src_name).replace('\\', '/').lstrip('/')
                    local_path = (media_root_path / key).resolve()
                    if not local_path.exists() or local_path.is_dir():
                        skipped += 1
                        continue

                    if log_every and (processed == 1 or processed % log_every == 0):
                        pk_val = getattr(obj, pk_name, None)
                        self.stdout.write(f'[{processed}/{total}] {label} {pk_name}={pk_val} key={key}')

                    try:
                        if not dry_run:
                            did_upload, _ = _upload_one(s3, bucket, local_path, key, overwrite=overwrite)
                            if did_upload:
                                uploaded += 1
                            else:
                                skipped += 1
                        else:
                            uploaded += 1
                    except Exception as e:
                        failed += 1
                        pk_val = getattr(obj, pk_name, None)
                        self.stderr.write(f'failed target={label} {pk_name}={pk_val} key={key} err={e}')

            self.stdout.write(f'target={label} uploaded={uploaded} skipped={skipped} failed={failed}')
