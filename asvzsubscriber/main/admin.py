from django.contrib import admin
from .models import ASVZEvent, ASVZUser, ASVZToken

# Register your models here.
admin.site.register(ASVZUser)
admin.site.register(ASVZToken)
admin.site.register(ASVZEvent)

