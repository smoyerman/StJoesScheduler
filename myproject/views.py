from django.http import Http404 
import calendar
import numpy as np
from django.template import Template, Context
from django.shortcuts import render, redirect
from myproject import Config
import scheduler.models as smodels
import datetime
from django.contrib.auth.models import User
from django.http import HttpResponse

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

# Check start of month day
def checkStart(month,year):
    if month >= 7:
        return str(year) + "-07-01"
    else:
        return str(year-1) + "-07-01" 

# Checks number of PTO days requested so far (rough)
def checkPTOcounts(month, year):
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

# Checks if there are any PTO conflicts requested
def checkPTOConflicts(month, year):
    # Check same service requested
    services = smodels.Service.objects.filter(month = month)
    noServices = max([service.onservice for service in services])
    daysInMonth = calendar.monthrange(year, month)[1]
    badDays = []
    for i in range(noServices):
        resOn = []
        for service in services.filter(onservice = i):
            resOn.append(service.res)
        dayTracker = [[] for i in range(daysInMonth)]
        if len(resOn) > 1:
            for res in resOn:
                for day in res.PTO.filter(date__month=month,date__year=year):
                    dayTracker[day.date.day-1].append(res)
            for i,d in enumerate(dayTracker):
                if len(d) >= 2:
                    badDays.append((i+1,d,service))
    badDays.sort(key=lambda tup: tup[0])
    return badDays

# Function for homepage - redirects to schedule of current month
def homepage(request):
    now = datetime.datetime.now()
    if now.year == 2017 and now.month == 7:
        return redirect('/schedule/2017/8/')
    return redirect('/schedule/'+str(now.year)+'/'+str(now.month))

# Function to check on number of call days per resident - weekend and weekday
def callDayChecker():
    ResDict = {}
    # Order this query by PGY year and list PGY level - add months in call pool
    for res in smodels.Resident.objects.all():
        ResDict[res.name] = [0,0]
    for day in smodels.Day.objects.all():
        for res in day.residents.all():
            if day.date.weekday() < 4:
                ResDict[res.name][0] += 1
            else:
                ResDict[res.name][1] += 1
    return ResDict

def see_call_day_count(request):
    ResDict = callDayChecker()
    templateVars = {"ResDict": ResDict}
    return render(request, "CallCount.html", templateVars)

# Function to update PTO requests
def update_pto(request,year,month):
    if request.user.is_authenticated():
        try:
            user = request.user
            r = smodels.Resident.objects.get(user=user)
        except:
            return HttpResponse('Unauthorized', status=401)
    else:
        return HttpResponse('Unauthorized', status=401)
    yearmo = int(year + month)
    try:
        year = int(year)
        month = int(month)
    except:
        raise Http404()
    if not yearmo == 201711:
        raise Http404()
    month2, year2, month0, year0 = moveMonths(month,year)
    month3, year3, month1, year1 = moveMonths(month2,year2)
    month4, year4, month2, year2 = moveMonths(month3,year3)
    month5, year5, month3, year3 = moveMonths(month4,year4)
    months = [month0, month1, month2, month3, month4, month5]
    years = [year0, year1, year2, year3, year4, year5]
    monthNames = [calendar.month_name[month] for month in months]
    c = calendar.Calendar(calendar.SUNDAY)
    cal1 = np.array(c.monthdayscalendar(year1,month1))
    cal2 = np.array(c.monthdayscalendar(year2,month2))
    cal3 = np.array(c.monthdayscalendar(year3,month3))
    cal4 = np.array(c.monthdayscalendar(year4,month4))
    cals = [None, cal1, cal2, cal3, cal4]
    days = []
    for year,month in zip(years[1:],months[1:]):
        days.append(r.PTO.filter(date__month = month, date__year = year)) 
    PTODays = []
    for y,m in zip(years,[None, month1, month2, month3, month4]):
        if m:
            PTODays.append([d.date.day for d in r.PTO.filter(date__month=m,date__year=y)])
        else:
            PTODays.append([])
    ymnamescals = zip(years, months, monthNames, cals, PTODays)
    templateVars = { "ymnamescals" : ymnamescals}
    return render(request,"PTO.html",templateVars)

# Function to request a day of PTO from the calendar page
def request_day(request, userid, year, month, day):
    dayoff = smodels.DayOff.objects.get(date = datetime.date(int(year), int(month), int(day))) 
    user = User.objects.get(id = int(userid))
    resident = smodels.Resident.objects.get(user = user)
    resident.PTO.add(dayoff)
    resident.save()

# Function to remove  aday of PTO from the calendar page
def remove_day(request, userid, year, month, day):
    dayoff = smodels.DayOff.objects.get(date = datetime.date(int(year), int(month), int(day))) 
    user = User.objects.get(id = int(userid))
    resident = smodels.Resident.objects.get(user = user)
    resident.PTO.remove(dayoff)
    resident.save()

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
        PTOConflictDays = checkPTOConflicts(month, year)
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
                             "lastYear": lastYear,
                             "PTOConflictDays": PTOConflictDays}
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
                     "lastYear": lastYear,
                     "PTOConflictDays": PTOConflictDays}

    return render(request,"calendar.html",templateVars)

