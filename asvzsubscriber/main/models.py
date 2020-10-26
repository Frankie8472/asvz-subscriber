from django.contrib.auth.models import User
from django.db import models
from django.db.models import DateTimeField, CharField, URLField, BooleanField, OneToOneField


# Create your models here.
class ASVZEvent(models.Model):
    user: CharField = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    url: URLField = models.URLField()
    sport_name: CharField = models.CharField(max_length=100)
    title: CharField = models.CharField(max_length=100)
    location: CharField = models.CharField(max_length=100)
    event_start_date: DateTimeField = models.DateTimeField()
    register_start_date: DateTimeField = models.DateTimeField()
    niveau_short_name: CharField = models.CharField(max_length=100)

    class Meta:
        unique_together = ("user", "url")

    def __str__(self):
        return f"{self.user.__str__()} - {self.url[-6:]}"


class BearerToken(models.Model):
    user: OneToOneField = models.OneToOneField(User, on_delete=models.CASCADE)
    bearerToken: CharField = models.CharField(max_length=4000)
    valid_until: DateTimeField = models.DateTimeField()
    is_updating: BooleanField = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.__str__()} - {self.valid_until.__str__()[:16]}"
