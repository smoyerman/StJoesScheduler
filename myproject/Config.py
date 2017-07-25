from enum import Enum
import operator
from itertools import chain
import numpy as np
import calendar
import random
import os
import scheduler.models as smodels
import datetime

# Services
class Service(Enum):
    TRAUMA = 1
    HPB_TRANSPLANT = 2
    VASCULAR = 3
    COLORECTAL = 4
    BREAST = 5
    GS_GOLD = 6
    GS_BLUE = 7
    GS_ORANGE = 8
    PLASTICS = 9
    PCH = 10
    THORACIC = 11
    ANIR = 12
    CRITCARE = 13
    HARDING = 14
    OTHER = 15

# Types of resident
class Type(Enum):
    JUNIOR = 1
    SENIOR = 2

# Call Mapping
class TakesCall:
    allCall = [1,3,4,5,6,7,8,12,13,14]
    allCallJr = [1,2,3,4,5,6,7,8,12,13,14]
    allCallnoT = [3,4,5,6,7,8,12,13,14]
    jrCall = [2]
    trauma = 1
    services =  { "Trauma":1, "Hepatobiliary / Transplant":2,
                  "Vascular":3, "Colorectal":4,
                  "Breast":5, "Gen Surg - Gold":6,
                  "Gen Surg - Blue":7, "Gen Surg - Orange":8,
                  "Plastics":9, "PCH":10,
                  "Thoracic":11, "Anesthesia / IR":12,
                  "Critical Care":13, "Harding":15, "Other":14 }

    mapServices = {1: Service.TRAUMA,
                   2: Service.HPB_TRANSPLANT,
                   3: Service.VASCULAR,
                   4: Service.COLORECTAL,
                   5: Service.BREAST,
                   6: Service.GS_GOLD,
                   7: Service.GS_BLUE,
                   8: Service.GS_ORANGE,
                   9: Service.PLASTICS,
                   10:Service.PCH,
                   11:Service.THORACIC,
                   12:Service.ANIR,
                   13:Service.CRITCARE,
                   14:Service.HARDING,
                   15:Service.OTHER }

# Resident Class
class Resident():

    def __init__(self, service, year, no):
        self.resNo = no
        self.noCallDays = 0
        self.callDays = []
        self.service = service
        self.year = year
        self.type = Type.JUNIOR
        self.PTO = []  # Dyanmically filled
        if year >= 3:
            self.type = Type.SENIOR

# New resident for database style structure
class DBResident():

    def __init__(self, assignment, month):
        self.resNo = assignment.res.id
        self.noCallDays = 0 
        self.weekendCallDays = 0
        self.callDays = []
        self.service = TakesCall.mapServices[assignment.onservice]
        self.year = assignment.res.year
        self.type = Type.JUNIOR if assignment.res.resType=="Junior" else Type.SENIOR
        PTOdates = assignment.res.PTO.filter(date__month=month)
        days = []
        for DO in PTOdates:
            days.append(DO.date.day)
        self.PTO = days

class DBScheduler():

    def __init__(self, year, month):
        self.month = month
        self.year = year
        self.c = calendar.Calendar(calendar.SUNDAY)
        self.calendar = np.array(self.c.monthdayscalendar(year,month))
        self.monthName = calendar.month_name[month]
        self.daysInMonth = np.max(self.calendar)
        self.callAssignments = dict()
        for d in range(1, self.daysInMonth+1):
            self.callAssignments[d] = []
            #dy = smodels.Day.objects.get_or_create(date=datetime.date(year=year, month=month, day=d))
            dy = smodels.Day(date=datetime.date(year=year, month=month, day=d))
            dy.save()
        self.hasSenior = np.zeros(self.daysInMonth+1)
        self.hasJunior = np.zeros(self.daysInMonth+1)

    # Schedule a month of call
    def scheduleMonth(self):
        self.tc = TakesCall
        assignments = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCall)
        othAss = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.jrCall).filter(res__resType="Junior")
        self.allAssignments = list(chain(assignments,othAss))
        self.daysPerMonthSr = dict()
        self.daysPerMonthJr = dict()
        for a in smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCall).filter(res__resType="Senior"): 
            self.daysPerMonthSr[a.res.id] = 0
        for a in smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCallJr).filter(res__resType="Junior"): 
            self.daysPerMonthJr[a.res.id] = 0
        self.placeTraumaSeniors()
        self.placeWeekendSeniors()
        success = self.placeSeniors()
        self.tryFitSrs()
        self.placeJuniors()
        return True

    # Function to add a senior to the call schedule for the month
    def addSr(self, sr, day):
        self.callAssignments[day].append(sr)
        sr.noCallDays += 1
        sr.save()
        self.hasSenior[day] = 1
        self.daysPerMonthSr[sr.id] += 1
        dy = smodels.Day.objects.get(date=datetime.date(month=self.month, year=self.year, day=day))
        dy.residents.add(sr)

    # Check same service on same weekend
    def checkSameService(self,res,day):
        services = []
        for r in day.residents.all():
            services.append(r.service_set.get(month=self.month, year=self.year).onservice)
        # If Friday
        if day.date.day in self.calendar[:,5]:
            try:
                dayp2 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=2))
                for r in dayp2.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
            try:
                dayp1 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=1))
                for r in dayp1.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
        # If Saturday
        if day.date.day in self.calendar[:,6]:
            try:
                dayp1 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=1))
                for r in dayp1.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
            try:
                daym1 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-1))
                for r in daym1.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
        # If Sunday
        if day.date.day in self.calendar[:,0]:
            try:
                daym1 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-1))
                for r in daym1.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
            try:
                daym2 = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-2))
                for r in daym2.residents.all():
                    services.append(r.service_set.get(month=self.month, year=self.year).onservice)
            except:
                pass
        if res.service_set.get(month=self.month, year=self.year).onservice in services:
            return False
        return True

    def checkQ3(self, res, day):
        Q2Residents = []
        # Look 2 days back
        try:
            twoBack = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-2))
            for r in twoBack.residents.all():
                Q2Residents.append(r)
        except:
            pass
        try:
            oneBack = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-1))
            for r in oneBack.residents.all():
                Q2Residents.append(r)
        except:
            pass
        try:
            twoF = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=2))
            for r in twoF.residents.all():
                Q2Residents.append(r)
        except:
            pass
        try:
            oneF = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=1))
            for r in oneF.residents.all():
                Q2Residents.append(r)
        except:
            pass
        if res in Q2Residents:
            return False
        return True
        

    # Check back to back weekends
    def checkB2BWeekends(self, res, day):
        wkndResidents = []
        # Friday
        if day.date.day in self.calendar[:,5]:
            try:
                lastFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-7))
                for r in lastFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-6))
                for r in lastSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-5))
                for r in lastSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=7))
                for r in nextFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=8))
                for r in nextSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=9))
                for r in nextSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
        # Saturday
        if day.date.day in self.calendar[:,6]:
            try:
                lastFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-8))
                for r in lastFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-7))
                for r in lastSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-6))
                for r in lastSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=6))
                for r in nextFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=7))
                for r in nextSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=8))
                for r in nextSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
        # Sunday
        if day.date.day in self.calendar[:,0]:
            try:
                lastFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-9))
                for r in lastFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-8))
                for r in lastSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                lastSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=-7))
                for r in lastSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextFri = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=5))
                for r in nextFri.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSat = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=6))
                for r in nextSat.residents.all():
                    wkndResidents.append(r)
            except:
                pass
            try:
                nextSun = smodels.Day.objects.get(date=datetime.date(self.year,self.month,day.date.day) + datetime.timedelta(days=7))
                for r in nextSun.residents.all():
                    wkndResidents.append(r)
            except:
                pass
        if res in wkndResidents:
            return False
        return True

    # Function to check against PTO
    def checkPTO(self, res, day):
        PTOdates = [d.date for d in res.PTO.filter(date__month=self.month)] 
        if day in PTOdates:
            return False
        return True

    # Function to check rules
    def checkRules(self, res, day):
        dy = smodels.Day.objects.get(date=datetime.date(month=self.month, year=self.year, day=day))
        checkSS = self.checkSameService(res, dy)
        checkB2B = self.checkB2BWeekends(res, dy)
        checkQ3 = self.checkQ3(res, dy)
        checkPTO = self.checkPTO(res, datetime.date(month=self.month, year=self.year, day=day))
        if checkSS and checkB2B and checkQ3 and checkPTO:
            return True
        return False

    # Function to try to place the juniors
    def placeJuniors(self):
        jrCall = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCallJr).filter(res__resType="Junior")
        jrCallRes = [serv.res for serv in jrCall]
        random.shuffle(srCallRes)


    # Function to place the rest of the seniors
    def placeSeniors(self):
        srCall = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCallnoT).filter(res__resType="Senior")
        srCallRes = [serv.res for serv in srCall]
        random.shuffle(srCallRes)
        resNo = 0
        for i in range(1,self.daysInMonth+1):
            if not self.hasSenior[i]:
                resNo = resNo % len(srCallRes)
                if self.checkRules(srCallRes[resNo], i) and (self.daysPerMonthSr[srCallRes[resNo].id] < 4):
                    self.addSr(srCallRes[resNo], i)
                    resNo += 1
                else:
                    swappage = 0
                    while (not self.checkRules(srCallRes[resNo], i)) or (self.daysPerMonthSr[srCallRes[resNo].id] >= 4):
                        if swappage == len(srCallRes):
                            return False
                        srCallRes[resNo],srCallRes[(resNo+swappage) % len(srCallRes)] = srCallRes[(resNo+swappage) % len(srCallRes)], srCallRes[resNo]
                        swappage += 1
                    self.addSr(srCallRes[resNo], i)
                    resNo += 1
        return True

    # Function to place weekend seniors
    def placeWeekendSeniors(self):
        srCallWknd = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCallnoT).filter(res__resType="Senior")
        srCallWkndRes = [serv.res for serv in srCallWknd]
        thirdFourth = [res for res in srCallWkndRes if res.year in [3,4]]
        fifth = [res for res in srCallWkndRes if res.year == 5]
        random.shuffle(thirdFourth)
        random.shuffle(fifth)
        thirdFourth.extend(fifth)
        frisatArr = np.reshape(self.calendar[:,5:],-1)
        # Start with Friday
        i = 0
        for day in frisatArr:
            if day > 0 and (not self.hasSenior[day]):
                i = i % len(thirdFourth)
                if self.checkRules(thirdFourth[i], day):
                    self.addSr(thirdFourth[i], day)
                    thirdFourth[i].noWkndCallDays += 1
                    thirdFourth[i].save()
                else:
                    thirdFourth[i], thirdFourth[(i+1) % len(thirdFourth)] = thirdFourth[(i+1) % len(thirdFourth)], thirdFourth[i] 
                    self.addSr(thirdFourth[i], day)
                    thirdFourth[i].noWkndCallDays += 1
                    thirdFourth[i].save()
                i += 1
        
    # If there are any days without seniors, try very hard to place them
    def tryFitSrs(self):
        srCallWknd = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCall).filter(res__resType="Senior")
        srCallWkndRes = [serv.res for serv in srCallWknd]
        for i in range(1,self.daysInMonth+1):
            if not self.hasSenior[i]:
                sorted_days = sorted(self.daysPerMonthSr.items(), key=operator.itemgetter(1))
                for resid, days in sorted_days:
                    if self.checkRules(smodels.Resident.objects.get(id=resid),i):
                        self.addSr(smodels.Resident.objects.get(id=resid), i)
                        break

    # Find trauma seniors and place them on call
    def placeTraumaSeniors(self):
        traumaSrServ = smodels.Service.objects.filter(month=self.month, year=self.year, onservice=self.tc.trauma).filter(res__resType="Senior")
        traumaSrs = [serv.res for serv in traumaSrServ]
        if len(traumaSrs) == 1:
            for i in self.calendar[:,0]:
                if i > 0:
                    self.addSr(traumaSrs[0], i)
        elif len(traumaSrs) >= 2:
            ctr = 1
            for i in self.calendar[:,0]:
                if i > 0:
                    self.addSr(traumaSrs[ctr % len(traumaSrs)], i)
                    ctr += 1
                if i-1 > 0:
                    self.addSr(traumaSrs[ctr % len(traumaSrs)], i-1)
                    if len(traumaSrs) > 2:
                        ctr += 1

class Scheduler():

    def __init__(self, year, month):
        self.residents = []
        self.month = month
        self.year = year
        c = calendar.Calendar(calendar.SUNDAY)
        self.calendar = np.array(c.monthdayscalendar(year,month))
        self.monthName = calendar.month_name[month]
        self.daysInMonth = np.max(self.calendar)
        self.callAssignments = dict()
        for d in range(1, self.daysInMonth+1):
            self.callAssignments[d] = []
        self.hasSenior = np.zeros(self.daysInMonth+1)
        self.hasJunior = np.zeros(self.daysInMonth+1)

    def scheduleMonth(self, allAssignments):
        for assignment in allAssignments:
            self.addDBResident(assignment)
        self.unRavelResidents()
        # Put seniors on Trauma
        self.getTraumaSeniors()
        self.assignTraumaSeniors()
        self.assignWeekendSeniors()

        # Place the seniors everywhere
        self.placeSeniors()
        success = self.completeSeniors()
        if not success:
            return success

        # Place all the juniors
        self.placeWeekendJuniors()
        success = self.placeJuniors()
        if not success:
            return success

        self.add3rdDayJuniors()
        return True

    # Add a resident to the residents array in the Scheduler object
    def addResident(self, res):
        self.residents.append(res)

    def addDBResident(self, assignment):
        res = DBResident(assignment, self.month)
        self.residents.append(res)

    # Unravel all the reaidents into tracking arrays, this will help parse and debug
    def unRavelResidents(self):
        self.Services = []
        self.CallCounts = []
        self.Years = []
        self.Types = []
        for res in self.residents:
            self.Services.append(res.service)
            self.Years.append(res.year)
            self.Types.append(res.type)
            self.CallCounts.append(res.noCallDays)
        self.Services = np.array(self.Services)
        self.CallCounts = np.array(self.CallCounts)
        self.Years = np.array(self.Years)
        self.Types = np.array(self.Types)

    # Get the indices of the trauma seniors
    def getTraumaSeniors(self):
        self.TS = np.where((self.Services == Service.TRAUMA) & (self.Types == Type.SENIOR))[0]

    # Assign the senior(s) on Trauma to the call schedule
    def assignTraumaSeniors(self):
        if len(self.TS) == 1:
            for i in self.calendar[:,0]:
                if i > 0:
                    self.addCallDay(i,self.TS[0])
                    self.hasSenior[i] = 1
        elif len(self.TS) == 2:
            ctr = 1
            for i in self.calendar[:,0]:
                if i > 0:
                    self.addCallDay(i, self.TS[ctr % len(self.TS)])
                    self.hasSenior[i] = 1
                    ctr += 1
                if i-1 > 0:
                    self.addCallDay(i-1, self.TS[ctr % len(self.TS)])
                    self.hasSenior[i-1] = 1
                    if len(self.TS) > 2:
                        ctr += 1

    # Adding a call day to a person's schedule - track everywhere
    def addCallDay(self, day, resident):
        self.callAssignments[day].append(self.residents[resident])
        self.residents[resident].noCallDays += 1
        self.residents[resident].callDays.append(day)
        self.CallCounts[resident] += 1

    # Quick print of call schedule to the command line
    def printCallSchedule(self):
        #for key, item in self.callAssignments.items():
        #    for res in item:
        #        print(str(key) + ":\t" + str((res.resNo, res.service.name, res.year)))
        print("Call Counts: ", self.CallCounts)

    # Find juniors with less days and give them thirds
    def add3rdDayJuniors(self):
        self.Juniors = np.where(self.Types == Type.JUNIOR)[0]
        for jr in self.Juniors:
            while (self.residents[jr].noCallDays < 4):
                day = random.randint(1,self.daysInMonth)
                if len(self.callAssignments[day]) < 3:
                    if self.checkRulesJr(jr, day):
                        self.addCallDay(day,jr)

    # Function to place the juniors in a smart way on the weekend
    def placeWeekendJuniors(self):
        self.Juniors = np.where(self.Types == Type.JUNIOR)[0]
        for row in self.calendar[:,5:]:
            for i in row:
                if i > 0:
                    sameService = np.where(self.Services[self.Juniors] == self.callAssignments[i][0].service)[0]
                    if len(sameService) > 0:
                        if i+7 <= self.daysInMonth and self.checkRulesJr(self.Juniors[sameService[0]], i+7):
                            self.addCallDay(i+7,self.Juniors[sameService[0]])
                            self.hasJunior[i+7] += 1
    
    # First step is to assign seniors to the weekends
    def assignWeekendSeniors(self):
        self.Seniors = np.where((self.Types == Type.SENIOR) & (self.Services != Service.TRAUMA))[0]
        weekendSeniors = []
        youngerSeniors = np.where(((self.Years == 3) | (self.Years == 4)) & (self.Services != Service.TRAUMA))[0]
        thirdAndfourth  = len(youngerSeniors)
        pull = random.randint(0,thirdAndfourth-1)
        # Assign Fridays
        for i in self.calendar[:,5]:
            if not i == 0:
                if not self.hasSenior[i]:
                    if self.checkRules(youngerSeniors[pull], i):
                        self.addCallDay(i,youngerSeniors[pull])
                        self.hasSenior[i] = 1
                        weekendSeniors.append(pull)
                        pull += 1
                        pull = pull % thirdAndfourth
        for i in self.calendar[:,6]:
            if not i == 0:
                if not self.hasSenior[i]:
                    if self.checkRules(youngerSeniors[pull], i):
                        if i>1 and (not self.callAssignments[i-1][0].service == self.Services[pull]):
                            self.addCallDay(i,youngerSeniors[pull])
                            self.hasSenior[i] = 1
                            weekendSeniors.append(pull)
                            pull += 1
                            pull = pull % thirdAndfourth

    # Function to place seniors in remaining days, giving preference to older
    def placeSeniors(self):
        self.Seniors = np.where((self.Types == Type.SENIOR) & (self.Services != Service.TRAUMA))[0]
        noSrsInPool = np.sum(self.Types == Type.SENIOR)
        noCallDaysRemaining = np.sum(self.hasSenior == 0)
        daysPerSenior = noCallDaysRemaining / float(noSrsInPool)
        random.shuffle(self.Seniors)
        j = 0
        for i in range(1,self.daysInMonth+1):
            if not self.hasSenior[i]:
                # assign next senior here
                if self.CallCounts[self.Seniors[j]] <= daysPerSenior:
                        if self.checkRules(self.Seniors[j], i):
                            self.addCallDay(i,self.Seniors[j])
                            self.hasSenior[i] = 1
                j += 1
                if j == len(self.Seniors):
                    random.shuffle(self.Seniors)
                    j = j % len(self.Seniors)

    # Check if call schedule is full then add seniors as necessary
    def completeSeniors(self):
        j = 0
        self.Seniors = np.where((self.Types == Type.SENIOR) & (self.Services != Service.TRAUMA))[0]
        for i in range(1,self.daysInMonth+1):
            if not self.hasSenior[i]:
                lowest = np.argmin(self.CallCounts[self.Seniors])
                if self.checkRules(self.Seniors[lowest], i):
                    self.addCallDay(i,self.Seniors[lowest])
                    self.hasSenior[i] = 1
                else:
                    numTries = 0
                    unFilled = True
                    while(unFilled):
                        if self.checkRules(self.Seniors[j], i):
                            self.addCallDay(i,self.Seniors[j])
                            self.hasSenior[i] = 1
                            unFilled = False
                            j += 1
                        else:
                            j += 1
                            numTries += 1
                        j = j % len(self.Seniors)
                        if numTries > len(self.Seniors):
                            return False
        return True

    # Place the juniors into the call pool
    def placeJuniors(self):
        j = 0
        self.Juniors = np.where(self.Types == Type.JUNIOR)[0]
        for i in range(1,self.daysInMonth+1):
            if not self.hasJunior[i]:
                lowest = np.argmin(self.CallCounts[self.Juniors])
                if self.checkRulesJr(self.Juniors[lowest], i):
                    self.addCallDay(i,self.Juniors[lowest])
                    self.hasJunior[i] = 1
                else:
                    numTries = 0
                    unFilled = True
                    while(unFilled):
                        if self.checkRulesJr(self.Juniors[j], i):
                            self.addCallDay(i,self.Juniors[j])
                            self.hasJunior[i] = 1
                            unFilled = False
                            j += 1
                        else:
                            j += 1
                            numTries += 1
                        j = j % len(self.Juniors)
                        if numTries > len(self.Juniors):
                            return False
        return True
                    
    # Check all the rules to see if a person can be put on this day
    def checkRulesJr(self, jrInd, day):
        jr = self.residents[jrInd]
        if self.check48hours(jr,day) and self.checkBacktoBackWeekends(jr,day) and self.checkPTO(jr, day) and self.checkMatchingSenior(jr,day) and self.checkWeekend(jr,day):
            return True
        else:
            return False

    # Rule to check that junior isn't on the same service as their senior
    def checkMatchingSenior(self, jr, day):
        if self.callAssignments[day][0].service == jr.service:
            return False
        return True

    # Rule to check that junior isn't on the same weekend service as their senior
    def checkWeekend(self, jr, day):
        services = []
        if day in self.calendar[:,5]: # Friday
            try:
                services.append(self.callAssignments[day+1][0].service)
            except:
                pass
            try: 
                services.append(self.callAssignments[day+2][0].service)
            except:
                pass
            if jr.service in services:
                return False
        if day in self.calendar[:,6]: # Saturday
            try:
                services.append(self.callAssignments[day+1][0].service)
            except:
                pass
            try: 
                services.append(self.callAssignments[day-1][0].service)
            except:
                pass
            if jr.service in services:
                return False
        if day in self.calendar[:,0]: # Sunday
            try:
                services.append(self.callAssignments[day-2][0].service)
            except:
                pass
            try: 
                services.append(self.callAssignments[day-1][0].service)
            except:
                pass
            if jr.service in services:
                return False
        return True 
            
    # Check all the rules to see if a person can be put on this day
    def checkRules(self, srInd, day):
        sr = self.residents[srInd]
        if self.check48hours(sr,day) and self.checkBacktoBackWeekends(sr,day) and self.checkPTO(sr,day) and self.checkWeekend(sr,day):
            return True
        else:
            return False

    # Check if on consecutive weekends, return True if everything is ok, return False if putting 2 weekends in a row
    # TODO: this could have some roll-over problems if I'm not keeping track of the last month...
    def checkBacktoBackWeekends(self, sr, day):
        if (day in self.calendar[:,0]): # Sunday
            if day - 7 > 0:
                if sr in self.callAssignments[day-7]: 
                    return False
            if day - 8 > 0:
                if sr in self.callAssignments[day-8]:
                    return False
            if day - 9 > 0:
                if sr in self.callAssignments[day-9]:
                    return False
            if day + 7 <= self.daysInMonth:
                if sr in self.callAssignments[day+7]: 
                    return False
            if day + 6 <= self.daysInMonth:
                if sr in self.callAssignments[day+6]:
                    return False
            if day + 5 <= self.daysInMonth:
                if sr in self.callAssignments[day+5]:
                    return False
        elif (day in self.calendar[:,6]): # Saturday
            if day - 6 > 0:
                if sr in self.callAssignments[day-6]: 
                    return False
            if day - 7 > 0:
                if sr in self.callAssignments[day-7]: 
                    return False
            if day - 8 > 0:
                if sr in self.callAssignments[day-8]: 
                    return False
            if day + 7 <= self.daysInMonth:
                if sr in self.callAssignments[day+7]: 
                    return False
            if day + 6 <= self.daysInMonth:
                if sr in self.callAssignments[day+6]:
                    return False
            if day + 8 <= self.daysInMonth:
                if sr in self.callAssignments[day+8]:
                    return False
        elif (day in self.calendar[:,5]): # Friday
            if day - 5 > 0:
                if sr in self.callAssignments[day-5]:
                    return False
            if day - 6 > 0:
                if sr in self.callAssignments[day-6]:
                    return False
            if day - 7 > 0:
                if sr in self.callAssignments[day-7]:
                    return False
            if day + 7 <= self.daysInMonth:
                if sr in self.callAssignments[day+7]: 
                    return False
            if day + 8 <= self.daysInMonth:
                if sr in self.callAssignments[day+8]:
                    return False
            if day + 9 <= self.daysInMonth:
                if sr in self.callAssignments[day+9]:
                    return False
        return True

    # Check if giving them their PTO - can add this in later, easy
    def checkPTO(self, sr, day):
        if day in sr.PTO:
            return False
        return True

    # Check if there's at least 48 hours between calls
    def check48hours(self, sr, day):
        if day <= 2:
            lastMonth = self.month - 1
            lastYear = self.year
            if lastMonth < 1:
                lastMonth = 12
                lastYear -= 1
            wkdy,noDays = calendar.monthrange(lastYear, lastMonth)
            if day == 1:
                try:
                    dayAgo = smodels.Day.objects.get(date=datetime.date(month=lastMonth,year=lastYear,day=noDays))
                    twoDaysAgo = smodels.Day.objects.get(date=datetime.date(month=lastMonth,year=lastYear,day=noDays-1))
                    resids = [res.id for res in dayAgo.residents.all()]
                    resid2 = [res.id for res in twoDaysAgo.residents.all()]
                    if (sr.resNo in resids) or (sr.resNo in resid2):
                        return False
                except:
                    pass
            if day == 2:
                try:
                    dayAgo = smodels.Day.objects.get(date=datetime.date(month=lastMonth,year=lastYear,day=noDays))
                    resids = [res.id for res in dayAgo.residents.all()]
                    if sr.resNo in resids:
                        return False
                except:
                    pass
        if day >= 2:
            if (sr in self.callAssignments[day-1]):
                return False
        if day >= 3:
            if (sr in self.callAssignments[day-2]):
                return False
        if day <= self.daysInMonth - 1:
            if (sr in self.callAssignments[day + 1]):
                return False
        if day <= self.daysInMonth - 2:
            if (sr in self.callAssignments[day + 2]):
                return False
        return True

    # Return residents in a nice way for rendering them to html
    def returnResidents(self):
        resSchedule = []
        for week in self.calendar:
            weekly = []
            for day in week:
                if day:
                    item = self.callAssignments[day]
                    weekly.append([day,[res.service.name + ": PGY" + str(res.year) for res in item]])
                else:
                    weekly.append([0,[]])
            resSchedule.append(weekly)
        return resSchedule

