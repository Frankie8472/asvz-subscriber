from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class ASVZEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    sport_name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    event_start_date = models.DateTimeField()
    register_start_date = models.DateTimeField()
    url = models.URLField()

    class Meta:
        unique_together = ("user", "url")

    def __str__(self):
        return f"{self.user.__str__()} - {self.url[-6:]}"
