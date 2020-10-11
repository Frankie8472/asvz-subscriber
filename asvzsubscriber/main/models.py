from django.contrib.auth.models import User
from django.db import models
from django.db.models import DateTimeField, CharField, URLField, BooleanField


# Create your models here.
class ASVZEvent(models.Model):
    user: CharField = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    sport_name: CharField = models.CharField(max_length=100)
    title: CharField = models.CharField(max_length=100)
    location: CharField = models.CharField(max_length=100)
    event_start_date: DateTimeField = models.DateTimeField()
    register_start_date: DateTimeField = models.DateTimeField()
    url: URLField = models.URLField()
    niveau_short_name: CharField = models.CharField(max_length=100)

    class Meta:
        unique_together = ("user", "url")

    def __str__(self):
        return f"{self.user.__str__()} - {self.url[-6:]}"
