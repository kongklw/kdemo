from django.db import models

# Create your models here.

class SportModels(models.Model):

    name = models.CharField(max_length=100,unique=True,verbose_name="sport name")
    country = models.CharField(max_length=100,verbose_name="origin country")
    popularity = models.IntegerField(null=True,default=None)

    class Meta:
        db_table = "tb_sports"
        verbose_name = "sports"
        verbose_name_plural = verbose_name