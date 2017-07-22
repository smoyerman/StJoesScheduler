from django.contrib import admin
from .models import Resident, Service

class ResidentAdmin(admin.ModelAdmin):
    list_display = ('lname','fname','year')

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('month','onservice','res')

# Register your models here.
admin.site.register(Resident, ResidentAdmin)
admin.site.register(Service, ServiceAdmin)
