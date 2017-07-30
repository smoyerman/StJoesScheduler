from django.http import Http404 
import calendar
import numpy as np
from django.template import Template, Context
from django.shortcuts import render, redirect
from myproject import Config
import scheduler.models as smodels
import datetime

# Function to advance and pull back months by 1
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

# Takes in a given month and returns the resident schedule for that month
def returnResidentSchedule(month, year):
    resSchedule = []
    c = calendar.Calendar(calendar.SUNDAY)
    cal = np.array(c.monthdayscalendar(year,month))
    nextMonth, nextYear, lastMonth, lastYear = moveMonths(month,year)
    cal2 = np.array(calendar.Calendar(calendar.SUNDAY).monthdayscalendar(lastYear,lastMonth))
    for j,week in enumerate(cal):
        weekly = []
        for i,day in enumerate(week):
            if day:
                d = smodels.Day.objects.get(date__month=month, date__year=year, date__day=day)
                weekly.append([day,[(res.lname + ": PGY" + str(res.year), smodels.Service.objects.get(month=month,year=year,res=res)) for res in d.residents.all().order_by('-year')],[]])
            else:
                if j == 0:
                    try:
                        d = smodels.Day.objects.get(date__month=lastMonth, date__year=lastYear, date__day=cal2[-1,i])
                        weekly.append([0,[(res.lname + ": PGY" + str(res.year), smodels.Service.objects.get(month=month,year=year,res=res)) for res in d.residents.all().    order_by('-year')],[]])
                    except:
                        weekly.append([0,[],[]])
                else:
                    weekly.append([0,[],[]])
        resSchedule.append(weekly)
    return resSchedule

def updateResDays(s):
    for res in s.residents:
        resmodel = smodels.Resident.objects.get(id=res.resNo)
        resmodel.noCallDays += res.noCallDays
        resmodel.save()

def checkStart(month,year):
    if month >= 7:
        return str(year) + "-07-01"
    else:
        return str(year-1) + "-07-01" 

# Checks number of PTO days requested so far (rough) and if there are any PTO conflicts. 
def checkPTOconflicts(month, year):
    # check total PTO per resident up till this point
    nextMonth = month + 1
    nextYear = year
    if nextMonth > 12:
        nextYear = year + 1
        nextMonth = nextMonth % 12
    warningDayCount = []
    for res in Resident.objects.all():
        daysToDate = len(res.PTO.filter(date__range=[checkStart(month,year), str(nextYear) + "-" + str(nextMonth) + "-01"]))
        if daysToDate > 15:
            warningDayCount.append((res,daysToDate))
    # Check same service requested
    services = smodels.Service.objects.filter(month = month)
    noServices = max([service.onservice for service in services])
    for i in range(noServices):
        resOn = []
        for service in services.filter(onservice = i):
            resOn.append(service.res)
        dates = []
        for res in resOn:
            dates.extend(res.PTO.all())

# Function for homepage - redirects to schedule of current month
def homepage(request):
    now = datetime.datetime.now()
    if now.year == 2017 and now.month == 7:
        return redirect('/schedule/2017/8/')
    return redirect('/schedule/'+str(now.year)+'/'+str(now.month))

# Main function to generate scheduling page
def generate_schedule(request,year,month):
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
        nextMonth, nextYear, lastMonth, lastYear = moveMonths(month,year)
        daysOff = smodels.DayOff.objects.filter(date__month=month, date__year = year)
        if days:
            resSchedule = returnResidentSchedule(month, year)
            for day in daysOff:
                for week in resSchedule:
                    for d in week:
                        if d[0] == day.date.day:
                            d[2] = [r.lname for r in day.resident_set.all()]
                            break
            nextMonth, nextYear, lastMonth, lastYear = moveMonths(month,year)
            templateVars = { "schedule" : resSchedule,
                             "monthName" : calendar.month_name[month],
                             "year": year,
                             "nextYear": nextYear,
                             "nextMonth": nextMonth,
                             "lastMonth": lastMonth,
                             "lastYear": lastYear}
            return render(request,"calendar.html",templateVars)
        # Arrange residents in a meaningful way
        s = Config.DBScheduler(year, month)
        success = s.scheduleMonth()
        
    #updateResDays(s)
    resSchedule = returnResidentSchedule(month, year)
    for day in daysOff:
        for week in resSchedule:
            for d in week:
                if d[0] == day.date.day:
                    d[2] = [r.lname for r in day.resident_set.all()]
                    break
    templateVars = { "schedule" : resSchedule,
                     "monthName" : s.monthName,
                     "year": year,
                     "nextYear": nextYear,
                     "nextMonth": nextMonth,
                     "lastMonth": lastMonth,
                     "lastYear": lastYear}

    return render(request,"calendar.html",templateVars)

