from django.db import models
from django.conf import settings

# Requested day off by resident
class DayOff(models.Model):
    date = models.DateField(verbose_name="PTO Date")
    def __str__(self):
        return u'%s %s, %s' % (self.date.strftime("%B"), self.date.day, self.date.year)

# Resident centric database 
class Resident(models.Model):
    YEAR_RES_CHOICES = (
            (1, 'PGY1'),
            (2, 'PGY2'),
            (3, 'PGY3'),
            (4, 'PGY4'),
            (5, 'PGY5'),
    )
    fname = models.CharField(max_length=50, verbose_name="First Name", blank=True)
    lname = models.CharField(max_length=50, verbose_name="Last Name", blank=True)
    name = models.CharField(max_length=50, verbose_name="Resident Name", blank=True)
    year = models.IntegerField(choices = YEAR_RES_CHOICES, verbose_name="Year of Service")
    PTO = models.ManyToManyField(DayOff, verbose_name="PTO Requested Days", blank=True)
    noCallDays = models.IntegerField(default=0, verbose_name="Number of Call Days")
    noWkndCallDays = models.IntegerField(default=0,verbose_name="Number of Weekend Call Days")
    resType = models.CharField(max_length=16, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    # Auto write junior or senior
    def save(self, *args, **kwargs):
        self.resType = "Senior" if self.year >= 3 else "Junior"
        super(Resident, self).save(*args, **kwargs)

    def __str__(self):
        return u'%s, %s - PGY%s' % (self.lname, self.fname, self.year)

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
            (13,"Critical Care"), (14, "Harding"), (15,"Other"),
    )
    YEAR_CHOICES = (
            (2017, 2017), (2018, 2018), (2019, 2019),
    )
    month = models.IntegerField(choices = MONTH_CHOICES, verbose_name="Month of Year") 
    year = models.IntegerField(choices = YEAR_CHOICES, verbose_name="Year")
    onservice = models.IntegerField(choices = SERVICE_CHOICES, verbose_name ="Service")
    res = models.ForeignKey(Resident, verbose_name="Resident on Service")
    callDays = models.IntegerField(default=0, verbose_name="Call Days This Month")
    callDaysYTD = models.IntegerField(default=0, verbose_name="Call Days YTD")
    wkndcallDays = models.IntegerField(default=0, verbose_name="Weekend Call Days This Month")
    wkndcallDaysTYD = models.IntegerField(default=0, verbose_name="Weekend Call Days YTD")

    def __str__(self):
        return u'%s %s' % (self.month, self.onservice)

# Individual day of call schedule - this is all we need for schedule storing!
class Day(models.Model):
    date = models.DateField(verbose_name="On Call Day")
    residents = models.ManyToManyField(Resident, verbose_name="Residents on Call", blank=True) 

    def get_residents(self):
        return "\n".join([r.lname for r in self.residents.all()])
