from django.db import models
from users.models import User


# Create your models here.

class BabyInfo(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'MALE'
        FEMALE = 'F', 'FEMALE'

    name = models.CharField(max_length=100)
    birthday = models.DateField(blank=True)
    birth_weight = models.IntegerField()
    birth_height = models.IntegerField()
    gender = models.CharField(max_length=10, choices=Gender, default=Gender.FEMALE)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)


class FeedMilk(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feed_time = models.DateTimeField(blank=False)
    milk_volume = models.IntegerField()
    time_different = models.DateTimeField(blank=True, null=True)


class SleepLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sleep_time = models.DateTimeField(blank=False)
    time_different = models.DateTimeField(blank=True)


class BabyDiapers(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    use_date = models.DateTimeField()
    brand = models.CharField(max_length=100)
    is_leaked = models.BooleanField(default=False)


class Temperature(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(unique=True, null=False)
    temperature = models.CharField(max_length=10, null=False)


class BabyExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_time = models.DateField(blank=False)
    amount = models.IntegerField(blank=False)
