from scheduler.models import *
import datetime

def addDayOffOptions(startyr, startmo, startday, endyr):
    date = datetime.date(startyr,startmo,startday)
    day = datetime.timedelta(1)
    # Add days to day off options
    while(date.year < endyr):
        d = DayOff(date=date)
        d.save()
        date += day
