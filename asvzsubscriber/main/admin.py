from django.contrib import admin
from .models import ASVZEvent, ASVZUser

# Register your models here.
admin.site.register(ASVZUser)
admin.site.register(ASVZEvent)

