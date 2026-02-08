from django.db import models
from users.models import User

# Create your models here.

class SportModels(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100, verbose_name="sport name")
    country = models.CharField(max_length=100,verbose_name="origin country")
    popularity = models.IntegerField(null=True,default=None)

    class Meta:
        db_table = "tb_sports"
        verbose_name = "sports"
        verbose_name_plural = verbose_name
        # 确保每个用户的运动名称唯一，而不是全局唯一
        unique_together = ('user', 'name')