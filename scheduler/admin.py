from django.contrib import admin
from .models import Resident, Service, Day

class ResidentAdmin(admin.ModelAdmin):
    list_display = ('lname','fname','year')

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('month','onservice','res')

class DayAdmin(admin.ModelAdmin):
    list_display = ('date', 'get_residents')

# Register your models here.
admin.site.register(Resident, ResidentAdmin)
#admin.site.register(Service, ServiceAdmin)
admin.site.register(Day, DayAdmin)
