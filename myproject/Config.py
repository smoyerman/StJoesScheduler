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
        self.tryFitJrs()
        return True

    # Function to add a senior to the call schedule for the month
    def addSr(self, sr, day):
        self.callAssignments[day].append(sr)
        #sr.noCallDays += 1
        #sr.save()
        self.hasSenior[day] = 1
        self.daysPerMonthSr[sr.id] += 1
        dy = smodels.Day.objects.get(date=datetime.date(month=self.month, year=self.year, day=day))
        dy.residents.add(sr)

    # Function to add a junior to the call schedule for the month
    def addJr(self, jr, day):
        self.callAssignments[day].append(jr)
        #jr.noCallDays += 1
        #jr.save()
        self.hasJunior[day] = 1
        self.daysPerMonthJr[jr.id] += 1
        dy = smodels.Day.objects.get(date=datetime.date(month=self.month, year=self.year, day=day))
        dy.residents.add(jr)
        #if (day in np.reshape(self.calendar[:,5:],-1)) or (day in self.calendar[:,0]):
        #    jr.noWkndCallDays += 1
        #    jr.save()

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
        random.shuffle(jrCallRes)
        resNo = 0
        for i in range(1, self.daysInMonth+1):
            if not self.hasJunior[i]:
                resNo = resNo % len(jrCallRes)
                if self.checkRules(jrCallRes[resNo], i) and (self.daysPerMonthJr[jrCallRes[resNo].id] < 4):
                    self.addJr(jrCallRes[resNo], i)
                    resNo += 1
                else:
                    swappage = 0
                    while (not self.checkRules(jrCallRes[resNo], i)) or (self.daysPerMonthJr[jrCallRes[resNo].id] >= 4):
                        if swappage == len(jrCallRes):
                            break 
                        jrCallRes[resNo],jrCallRes[(resNo+swappage) % len(jrCallRes)] = jrCallRes[(resNo+swappage) % len(jrCallRes)], jrCallRes[resNo]
                        swappage += 1
                    if swappage < len(jrCallRes):
                        self.addJr(jrCallRes[resNo], i)
                        resNo += 1
        return True

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
                            break
                        srCallRes[resNo],srCallRes[(resNo+swappage) % len(srCallRes)] = srCallRes[(resNo+swappage) % len(srCallRes)], srCallRes[resNo]
                        swappage += 1
                    if swappage < len(srCallRes):
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
                    #thirdFourth[i].noWkndCallDays += 1
                    #thirdFourth[i].save()
                else:
                    thirdFourth[i], thirdFourth[(i+1) % len(thirdFourth)] = thirdFourth[(i+1) % len(thirdFourth)], thirdFourth[i] 
                    self.addSr(thirdFourth[i], day)
                    #thirdFourth[i].noWkndCallDays += 1
                    #thirdFourth[i].save()
                i += 1
        
    # Check jr spots
    def tryFitJrs(self):
        jrCallWknd = smodels.Service.objects.filter(month=self.month, year=self.year, onservice__in=self.tc.allCallJr).filter(res__resType="Junior")
        jrCallWkndRes = [serv.res for serv in jrCallWknd]
        for i in range(1,self.daysInMonth+1):
            if not self.hasJunior[i]:
                sorted_days = sorted(self.daysPerMonthJr.items(), key=operator.itemgetter(1))
                for resid, days in sorted_days:
                    if self.checkRules(smodels.Resident.objects.get(id=resid),i):
                        self.addJr(smodels.Resident.objects.get(id=resid), i)
                        break
        sorted_days = sorted(self.daysPerMonthJr.items(), key=operator.itemgetter(1))
        for resid, days in sorted_days:
            while days < 4:
                trialDay = random.randint(1,self.daysInMonth)
                if self.checkRules(smodels.Resident.objects.get(id=resid),trialDay):
                    numRes = smodels.Day.objects.get(date=datetime.date(self.year,self.month,trialDay)).residents.all()
                    if len(numRes) < 3:
                        self.addJr(smodels.Resident.objects.get(id=resid), trialDay)
                        days += 1

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
            for i in self.calendar[:,6]:
                if i > 0:
                    self.addSr(traumaSrs[0], i)
        elif len(traumaSrs) >= 2:
            ctr = 0
            for i in self.calendar[:,0]:
                if i > 0:
                    self.addSr(traumaSrs[ctr % len(traumaSrs)], i)
                    ctr += 1
                if i-1 > 0:
                    self.addSr(traumaSrs[ctr % len(traumaSrs)], i-1)
                    if len(traumaSrs) > 2:
                        ctr += 1


