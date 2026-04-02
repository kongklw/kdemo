from django.db import models
from users.models import User
import os
import uuid

# Create your models here.
# Define user directory path
def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = '{}.{}'.format(uuid.uuid4().hex[:10], ext)
    return os.path.join("files", filename)

class File(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    file = models.FileField(upload_to=user_directory_path, null=True)
    upload_method = models.CharField(max_length=20, verbose_name="Upload Method")
    created_at = models.DateTimeField(auto_now_add=True)


class MediaAsset(models.Model):
    class Status(models.TextChoices):
        INIT = 'init', 'init'
        UPLOADED = 'uploaded', 'uploaded'
        BOUND = 'bound', 'bound'
        DELETED = 'deleted', 'deleted'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    bucket = models.CharField(max_length=128)
    object_key = models.CharField(max_length=1024)
    original_name = models.CharField(max_length=255, blank=True, null=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    size_bytes = models.BigIntegerField(blank=True, null=True)
    etag = models.CharField(max_length=255, blank=True, null=True)
    is_video = models.BooleanField(default=False)
    purpose = models.CharField(max_length=64)
    ref_type = models.CharField(max_length=64, blank=True, null=True)
    ref_id = models.BigIntegerField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INIT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
