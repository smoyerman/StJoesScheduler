from django.http import Http404 
from django.template import Template, Context
from django.shortcuts import render_to_response
from myproject import Config
import scheduler.models as smodels
from itertools import chain

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

def generate_schedule(request,year,month):
    tc = Config.TakesCall
    success = False
    while (not success):
        try:
            year = int(year)
            month = int(month)
        except:
            raise Http404()
        if not 1 <= month <= 12:
            raise Http404()
        s = Config.Scheduler(year, month)
        assignments = smodels.Service.objects.filter(month=month, year=year, onservice__in=tc.allCall)
        othAss = smodels.Service.objects.filter(month=month, year=year, onservice__in=tc.jrCall)
        allAssignments = list(chain(assignments,othAss))
        # Arrange residents in a meaningful way
        for assignment in allAssignments:
            s.addDBResident(assignment)
        s.unRavelResidents()

        # Put seniors on Trauma
        s.getTraumaSeniors()
        s.assignTraumaSeniors()
        s.assignWeekendSeniors()

        # Place the seniors everywhere
        s.placeSeniors()
        s.completeSeniors()

        # Place all the juniors
        s.placeWeekendJuniors()
        success = s.placeJuniors()

    resSchedule = s.returnResidents()
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
