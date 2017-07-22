from enum import Enum
import numpy as np
import calendar
import random
import os

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
    jrCall = [2]
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
        self.noCallDays = assignment.res.noCallDays
        self.callDays = []
        self.service = TakesCall.mapServices[assignment.onservice]
        self.year = assignment.res.year
        self.type = Type.JUNIOR if assignment.res.resType=="Junior" else Type.SENIOR
        PTOdates = assignment.res.PTO.filter(date__month=month)
        days = []
        for DO in PTOdates:
            days.append(DO.date.day)
        self.PTO = days

class Scheduler():

    def __init__(self, year, month):
        self.residents = []
        self.month = month
        c = calendar.Calendar(calendar.SUNDAY)
        self.calendar = np.array(c.monthdayscalendar(year,month))
        self.monthName = calendar.month_name[month]
        self.daysInMonth = np.max(self.calendar)
        self.callAssignments = dict()
        for d in range(1, self.daysInMonth+1):
            self.callAssignments[d] = []
        self.hasSenior = np.zeros(self.daysInMonth+1)
        self.hasJunior = np.zeros(self.daysInMonth+1)

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
            ctr = 0
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
        thirdAndfourth = np.sum(self.Years[self.Seniors] != 5)
        weekendSeniors = []
        # Assign Fridays
        for i in self.calendar[:,5]:
            if not i == 0:
                pull = random.randint(0,thirdAndfourth-1)
                if not self.hasSenior[i]:
                    if self.checkRules(self.Seniors[pull], i):
                        self.addCallDay(i,self.Seniors[pull])
                        self.hasSenior[i] = 1
                        weekendSeniors.append(self.residents[pull])
                if i+1 <= self.daysInMonth:
                    if not self.hasSenior[i+1]:
                        push = pull + 1
                        push = push % thirdAndfourth
                        if self.checkRules(self.Seniors[push], i+1):
                            if not self.Services[pull] == self.Services[push]:
                                self.addCallDay(i+1,self.Seniors[push])
                                self.hasSenior[i+1] = 1
                                weekendSeniors.append(self.residents[push])
                        pull = push

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
                    unFilled = True
                    while(unFilled):
                        if self.checkRules(self.Seniors[j], i):
                            self.addCallDay(i,self.Seniors[j])
                            self.hasSenior[i] = 1
                            unFilled = False
                            j += 1
                        else:
                            j += 1
                        j = j % len(self.Seniors)

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
        if self.check48hours(jr,day) and self.checkBacktoBackWeekends(jr,day) and self.checkPTO() and self.checkMatchingSenior(jr,day) and self.checkWeekend(jr,day):
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
        if self.check48hours(sr,day) and self.checkBacktoBackWeekends(sr,day) and self.checkPTO() and self.checkWeekend(sr,day):
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
        return True

    # Check if giving them their PTO - can add this in later, easy
    def checkPTO(self):
        return True

    # Check if there's at least 48 hours between calls
    def check48hours(self, sr, day):
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

