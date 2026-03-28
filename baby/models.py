from django.db import models
from users.models import User


# Create your models here.

class BabyInfo(models.Model):
    class Gender(models.TextChoices):
        MALE = 'M', 'MALE'
        FEMALE = 'F', 'FEMALE'

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=100)
    birthday = models.DateField(blank=True)
    birth_weight = models.IntegerField()
    birth_height = models.IntegerField()
    gender = models.CharField(max_length=10, choices=Gender, default=Gender.FEMALE)
    birth_week = models.IntegerField(default=40)
    is_sensitive = models.BooleanField(default=False)
    is_only_child = models.BooleanField(default=False)
    image = models.ImageField(upload_to='baby/', null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)


class GrowingBlogModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(null=False, max_length=200)
    content = models.TextField(null=True, blank=True)
    created_time = models.DateField(auto_now_add=True)
    updated_time = models.DateField(auto_now=True)
    number_of_comments = models.IntegerField(default=0)
    number_of_pingbacks = models.IntegerField(default=0)
    rating = models.IntegerField(default=5)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "baby_growing_blog"
        verbose_name = "baby_growing_blog"
        verbose_name_plural = verbose_name


class FeedMilk(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    feed_time = models.DateTimeField(blank=False)
    milk_volume = models.IntegerField()
    time_different = models.DateTimeField(blank=True, null=True)
    
    # Extended fields for detailed records
    feed_type = models.CharField(max_length=20, default='bottle') # breast, breast_bottle, formula
    duration_total = models.IntegerField(default=0) # seconds
    left_duration = models.IntegerField(default=0) # seconds
    right_duration = models.IntegerField(default=0) # seconds
    note = models.TextField(blank=True, null=True)


class SleepLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sleep_time = models.DateTimeField(blank=False)
    status = models.CharField(blank=False, max_length=100)
    describe = models.CharField(max_length=600, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)


class PantsBrandModel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    brand_name = models.CharField(max_length=100)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    class Meta:
        db_table = "baby_pants_brand"
        verbose_name = "baby_pants_brand"
        verbose_name_plural = verbose_name


class BabyDiapers(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    use_date = models.DateTimeField()
    brand = models.CharField(max_length=100)
    tabActiveName = models.CharField(max_length=100, default="peeing")
    is_leaked = models.CharField(max_length=10, default='false')
    peeing_color = models.CharField(max_length=100, null=True, blank=True)
    stool_shape = models.CharField(max_length=200, null=True, blank=True)
    stool_color = models.CharField(max_length=100, null=True, blank=True)
    describe = models.TextField(null=True, blank=True)


class Temperature(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    measure_date = models.DateField(unique=True, null=False)
    temperature = models.CharField(max_length=10, null=False)
    status = models.CharField(max_length=100, null=True, blank=True)


class BabyExpense(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_time = models.DateTimeField(blank=False)
    name = models.CharField(max_length=200, null=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    tag = models.CharField(max_length=100, blank=True, null=True)
    expense_type = models.CharField(max_length=10, default='expense')
    image_url = models.CharField(max_length=500, blank=True, null=True)
    create_time = models.DateField(blank=False, auto_now_add=True)
    update_time = models.DateField(blank=False, auto_now=True)


class BabyAlbum(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Public'
        PRIVATE = 'private', 'Private'
        RELATIVES = 'relatives', 'Relatives'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    happened_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.RELATIVES)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-happened_at']


class AlbumPhoto(models.Model):
    album = models.ForeignKey(BabyAlbum, related_name='photos', on_delete=models.CASCADE)
    image = models.FileField(upload_to='baby_album/')
    is_video = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class GrowthRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    measure_date = models.DateField()
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    head_circumference_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    photo = models.ImageField(upload_to='growth/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-measure_date', '-id']


class VaccineDefinition(models.Model):
    class FeeType(models.TextChoices):
        FREE = 'free', 'FREE'
        PAID = 'paid', 'PAID'

    vaccine_key = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    dose_index = models.IntegerField(default=1)
    dose_total = models.IntegerField(default=1)
    fee_type = models.CharField(max_length=10, choices=FeeType.choices, default=FeeType.FREE)
    description = models.CharField(max_length=500, blank=True, null=True)
    months_offset = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    days_offset = models.IntegerField(default=0)
    price_min = models.IntegerField(blank=True, null=True)
    price_max = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['months_offset', 'days_offset', 'id']


class BabyVaccineRecord(models.Model):
    class FeeType(models.TextChoices):
        FREE = 'free', 'FREE'
        PAID = 'paid', 'PAID'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vaccine_key = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    dose_index = models.IntegerField(default=1)
    dose_total = models.IntegerField(default=1)
    fee_type = models.CharField(max_length=10, choices=FeeType.choices, default=FeeType.FREE)
    description = models.CharField(max_length=500, blank=True, null=True)
    recommend_date = models.DateField()
    done = models.BooleanField(default=False)
    actual_date = models.DateField(blank=True, null=True)
    price_min = models.IntegerField(blank=True, null=True)
    price_max = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'vaccine_key', 'recommend_date')
        ordering = ['recommend_date', 'id']


class ExpenseTag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        verbose_name = "expense_tag"
        verbose_name_plural = verbose_name


class UserAppOrder(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='app_order')
    order = models.JSONField(default=list)  # Stores list of app keys
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s App Order"

class DailyHabit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TodoList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateField(blank=False, auto_now_add=True)
    update_time = models.DateField(blank=False, auto_now=True)
    text = models.CharField(max_length=100, null=False)
    done = models.BooleanField(default=False)
    is_daily = models.BooleanField(default=False)
    icon = models.CharField(max_length=50, blank=True, null=True)


class BabytreeWeeklyInfo(models.Model):
    source = models.CharField(max_length=50, default='babytree')
    stage = models.CharField(max_length=20, default='baby')
    week_index = models.IntegerField(null=True, blank=True)
    age_range_text = models.CharField(max_length=100, blank=True, null=True)
    date_range_text = models.CharField(max_length=100, blank=True, null=True)
    this_week_title = models.CharField(max_length=200, blank=True, null=True)
    this_week_content = models.TextField(blank=True, null=True)
    baby_change_text = models.TextField(blank=True, null=True)
    baby_change_question = models.TextField(blank=True, null=True)
    growth_quicklook = models.JSONField(default=dict, blank=True)
    source_url = models.CharField(max_length=500, blank=True, null=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('source', 'stage', 'week_index', 'age_range_text')


class MenstrualSetting(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cycle_length = models.IntegerField(default=28)
    period_length = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MenstrualLog(models.Model):
    class Mood(models.TextChoices):
        HAPPY = 'happy', 'happy'
        GOOD = 'good', 'good'
        NORMAL = 'normal', 'normal'
        BAD = 'bad', 'bad'
        WORSE = 'worse', 'worse'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    is_period = models.BooleanField(default=False)
    flow_level = models.IntegerField(default=0)
    pain_level = models.IntegerField(default=0)
    had_sex = models.BooleanField(default=False)
    symptoms = models.CharField(max_length=500, blank=True, null=True)
    basal_temp = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mood = models.CharField(max_length=20, choices=Mood.choices, blank=True, null=True)
    habit_eat_on_time = models.BooleanField(default=False)
    habit_water8 = models.BooleanField(default=False)
    habit_fruits = models.BooleanField(default=False)
    habit_exercise = models.BooleanField(default=False)
    habit_poop = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date', '-id']
