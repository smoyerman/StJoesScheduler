from django.http import Http404 
from django.template import Template, Context
from django.shortcuts import render_to_response
from myproject import Config
import scheduler.models as smodels
from itertools import chain
import datetime

monthRes = [
    # First
    (Config.Service.GS_GOLD, 1),
    (Config.Service.TRAUMA, 1),
    (Config.Service.GS_BLUE, 1),
    (Config.Service.COLORECTAL, 1),
    (Config.Service.BREAST, 1),
    (Config.Service.GS_ORANGE, 1),
    # Second
    (Config.Service.HPB_TRANSPLANT, 2),
    # Third
    (Config.Service.TRAUMA, 3),
    (Config.Service.GS_GOLD, 3),
    (Config.Service.GS_BLUE, 3),
    # Fourth
    (Config.Service.HPB_TRANSPLANT, 4),
    (Config.Service.VASCULAR, 4),
    (Config.Service.COLORECTAL, 4),
    # Fifth
    (Config.Service.GS_GOLD, 5),
    (Config.Service.GS_BLUE, 5),
    (Config.Service.GS_ORANGE, 5),
    #(Config.Service.TRAUMA, 5),
]

def moveMonths(month,year):
    nextMonth = month + 1
    nextYear = year
    if nextMonth > 12:
        nextMonth = 1
        nextYear += 1
    lastMonth = month - 1
    lastYear = year
    if lastMonth == 0:
        lastMonth = 12
        lastYear -= 1
    return nextMonth, nextYear, lastMonth, lastYear


def returnResidentSchedule(month, year, s):
    resSchedule = []
    for week in s.calendar:
        weekly = []
        for day in week:
            if day:
                d = smodels.Day.objects.get(date__month=month, date__year=year, date__day=day)
                weekly.append([day,[(res.lname + ": PGY" + str(res.year), smodels.Service.objects.get(month=month,year=year,res=res)) for res in d.residents.all()]])
            else:
                weekly.append([0,[]])
        resSchedule.append(weekly)
    return resSchedule


def generate_schedule(request,year,month):
    tc = Config.TakesCall
    success = False
    yearmo = int(year + month)
    while (not success):
        try:
            year = int(year)
            month = int(month)
        except:
            raise Http404()
        if not 1 <= month <= 12:
            raise Http404()
        if yearmo < 20178:
            raise Http404()
        # Check for pre-generated
        days = smodels.Day.objects.filter(date__month=month, date__year=year)
        s = Config.Scheduler(year, month)
        if days:
            success = True
            resSchedule = returnResidentSchedule(month, year, s)
            nextMonth, nextYear, lastMonth, lastYear = moveMonths(month,year)
            templateVars = { "schedule" : resSchedule,
                             "monthName" : s.monthName,
                             "year": year,
                             "nextYear": nextYear,
                             "nextMonth": nextMonth,
                             "lastMonth": lastMonth,
                             "lastYear": lastYear}
            return render_to_response("calendar.html",templateVars)
        assignments = smodels.Service.objects.filter(month=month, year=year, onservice__in=tc.allCall)
        othAss = smodels.Service.objects.filter(month=month, year=year, onservice__in=tc.jrCall).filter(res__resType="Junior")
        allAssignments = list(chain(assignments,othAss))
        # Arrange residents in a meaningful way
        success = s.scheduleMonth(allAssignments)
        
        # Save this schedule
        for i in range(1,s.daysInMonth+1):
            d = datetime.date(day=i, month=month, year=year)
            dy = smodels.Day(date=d)
            dy.save()
            for res in s.callAssignments[i]:
                r = smodels.Resident.objects.get(id=res.resNo)
                dy.residents.add(r)

    resSchedule = returnResidentSchedule(month, year, s)
    nextMonth, nextYear, lastMonth, lastYear = moveMonths(month,year)
    templateVars = { "schedule" : resSchedule,
                     "monthName" : s.monthName,
                     "year": year,
                     "nextYear": nextYear,
                     "nextMonth": nextMonth,
                     "lastMonth": lastMonth,
                     "lastYear": lastYear}

    return render_to_response("calendar.html",templateVars)
#    return HttpResponse("Hello world")
