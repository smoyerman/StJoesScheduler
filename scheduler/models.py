from django.db import models

# Requested day off by resident
class DayOff(models.Model):
    date = models.DateField()

# Resident centric database 
class Resident(models.Model):
    YEAR_RES_CHOICES = (
            (1, 'PGY1'),
            (2, 'PGY2'),
            (3, 'PGY3'),
            (4, 'PGY4'),
            (5, 'PGY5'),
    )
    name = models.CharField(max_length=50)
    year = models.IntegerField(choices = YEAR_RES_CHOICES)
    PTO = models.ManyToManyField(DayOff)
    noCallDays = models.IntegerField()
    noWkndCallDays = models.IntegerField()
    resType = models.CharField(max_length=16, blank=True)

    # Auto write junior or senior
    def save(self, *args, **kwargs):
        self.resType = "Senior" if self.year >= 3 else "Junior"
        super(Resident, self).save(*args, **kwargs)

# Service that residents can be on
class Service(models.Model):
    MONTH_CHOICES = (
            (1,"January"),(2,"February"),
            (3,"March"),(4,"April"),
            (5,"May"),(6,"June"),
            (7,"July"),(8,"August"),
            (9,"September"),(10,"October"),
            (11,"November"),(12,"December"),
    )
    SERVICE_CHOICES = (
            (1,"Trauma"),(2,"Hepatobiliary / Transplant"),
            (3,"Vascular"),(4,"Colorectal"),
            (5,"Breast"),(6,"Gen Surg - Gold"),
            (7,"Gen Surg - Blue"),(8,"Gen Surg - Orange"),
            (9,"Plastics"),(10,"PCH"),
            (11,"Thoracic"),(12,"Anesthesia / IR"),
            (13,"Other"),
    )
    month = models.IntegerField(choices = MONTH_CHOICES) 
    onservice = models.IntegerField(choices = SERVICE_CHOICES)
    res = models.ForeignKey(Resident)

# Individual day of call schedule - this is all we need for schedule storing!
class Day(models.Model):
    date = models.DateField()
    residents  = models.ManyToManyField(Resident) 

