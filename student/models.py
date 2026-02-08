from django.db import models
from users.models import User


# Create your models here.
class Student(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'MALE'
        FEMALE = 'F', 'FEMALE'
        OTHERS = 'O', "OTHERS"

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=20)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
