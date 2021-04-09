import calendar
import os
from datetime import datetime, timedelta, date
import json
import random

def myconverter(o):
    if isinstance(o, datetime):
        return o.__str__()

class day_obj:
    def __init__(self, date = datetime.now(), balance: int = 0, loan: int = 0, income: int = 0, bills: int = 0, spending: int = 0, savings_goals: int = 0):
        self.date = date # maybe make this a datetime obj instead???
        self.loan = loan
        self.income = 1747.50 if self.date.day == 1 or self.date.day == 15 else income
        self.bills = bills
        self.spending = spending
        self.savings_goals = savings_goals
        self.balance = balance + self.income - self.loan - self.spending - self.bills

    def __lt__(self, other):
        return self.date < other.date
    
    def __eq__(self, other):
        return self.date == other.date

    def __hash__(self):
        return hash(self.date)

    def update(self):
        delta = self.balance
        self.balance += self.income - self.loan - self.spending - self.bills
        return self.balance - delta
               
    def __repr__(self):
        return "{0}/{1}/{2} - Balance: ${3}".format(self.date.month,self.date.day,self.date.year,self.balance)

class Month:
    def __init__(self, name: str = "", days: [day_obj] = [], year: int = 2021):
        self.name = name
        self.days = days
        self.year = year

    def save(self, filepath):
        for day in self.days:
            jsonStr = json.dumps(day.__dict__, default = myconverter)
            print(jsonStr)

    def __lt__(self, other):
        return self.days[0].date < other.days[0].date
    
    def __eq__(self, other):
        return self.days[0].date == other.days[0].date   

    def preserve_bal(self, start_date: int = 0, to_add: int = 0):
        # Only useful on adjusting historic entries
        # Example: If 3 days ago you remember you spent x dollars, you would need to update 
        # the following days by deducting x amount from the following days balances

        try:
            for day in self.days[start_date+1::]:
                day.balance += to_add
        except IndexError:
            print(f"Index {start_date} out of range {len(self.days)}")

def build_month(month = datetime.now().month, year = datetime.now().year) -> [day_obj]:
    dates = []
    now = datetime.now()
    if now.month > month and month > 0 and month <13:
        if now.year >= year:
            now = calendar.monthrange(year,month)[1]
    else:
        now = now.day
    for i in range(1,now+1):
        that_day = date(year, month, i)
        dates.append(day_obj(date=that_day))
    return dates

dates = build_month(month = 2, year=2020)
curr_month = Month(name=calendar.month_name[3], days=dates, year = datetime.now().year)

preserve_index = 0
curr_month.preserve_bal(preserve_index ,curr_month.days[preserve_index].balance)
for day in curr_month.days:
     print(day)



# curr_month.days[3].bills += 1000
# delta = curr_month.days[3].update()
# preserve_index = 3
# curr_month.preserve_bal(preserve_index , delta)
# print("\n\n")
# for day in curr_month.days:
#     print(day)

# curr_month.days[5].income += 750.5
# delta = curr_month.days[5].update()
# preserve_index = 5
# curr_month.preserve_bal(preserve_index , delta)
# print("\n\n")
# for day in curr_month.days:
#     print(day)


# # print("Day {}, no sign of covid ceasing".format(date.day_of_year))
# print(date.date.year)
#date.save('random.csv')
#print(date.time_delta)


# dates1 = set()
# while len(dates1) != 4:
#     dates1.add(date_info(time_delta = random.randint(0,7)))

# dates2 = set()
# while len(dates2) != 4:
#     dates2.add(date_info(time_delta = random.randint(30,37)))

# month1 = Month(name="Fake Month", days=list(dates1))
# month2 = Month(name="Fake Month", days=list(dates2))
# month1.days.sort()
# month2.days.sort()
# #month.save("")
# print(month1 > month2)

# curr_month = Month(name=calendar.month_name[4], days=[], year = datetime.now().year)
# print(curr_month.name, curr_month.year)
# curr_month.days.append(date_info(time_delta = 7))
# curr_month.days.append(date_info(time_delta = -6))
# for day in curr_month.days:
#     print(day)


"""

print(calendar.month(year, month))
print(calendar.weekday(year=year, month=month, day=day))
days_in_the_year = (dt.date(year, month, day) - dt.date(year,1,1)).days + 1
print("{1}/{2}/{0}".format(year, month, day))

def __init__(self, year: int = dt.date.today().year, month: int =dt.date.today().month, day: int = dt.date.today().day, day_of_year: int = 0):
        self.year = year
        self.month = month
        self.day = day
        self.day_of_year = (dt.date(self.year, self.month, self.day) - dt.date(self.year,1,1)).days + 1
        # init day then look for date in some state file maintaining stats
        self.balance = 0.0

"""