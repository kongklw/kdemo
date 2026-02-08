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