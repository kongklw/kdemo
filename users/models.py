from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    '''
    username
    password
    roles: ['admin'],
    introduction: 'I am a super administrator',
    avatar: 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
    '''
    phone = models.CharField(max_length=11, unique=True, verbose_name="phone number")
    # role_id = models.IntegerField(null=True, blank=True)
    introduction = models.CharField(max_length=100, null=True)
    avatar = models.CharField(max_length=200, null=True)

    class Meta:
        db_table = "tb_users"
        verbose_name = "users"
        verbose_name_plural = verbose_name
