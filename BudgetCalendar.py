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
        """
        really ugly but prints single day in the following format
        # 4/7/2021        Balance: $1747.50
        #                Spent: $0.00
        """
        return f"{self.date.month}/{self.date.day}/{self.date.year}  \tBalance: ${self.balance:.2f}\n\t\tSpent: ${self.spending:.2f}\n"

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
        """
        Only useful on adjusting historic entries
        Example: If 3 days ago you remember you spent x dollars, you would need to update 
        the following days by deducting x amount from the following days balances
        """
        try:
            for day in self.days[start_date+1::]:
                day.balance += to_add
        except IndexError:
            print(f"Index {start_date} out of range {len(self.days)}")

def build_month(month = datetime.now().month, year = datetime.now().year) -> Month:
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
    return Month(name = calendar.month_name[dates[0].date.month], days = dates, year = datetime.now().year)

def main():
    # should first see if the curr month file exists to load instead of making it from scratch each time
    quit_loop = False
    curr_month = build_month()
    preserve_index = 0
    curr_month.preserve_bal(preserve_index ,curr_month.days[preserve_index].balance)
    print(f'Snapshot of the last 3 days of {curr_month.name}.')
    for day in curr_month.days[-3::]:
        print(day)

    while not quit_loop:
        month = input('What month would you like to view? Enter the month number (ex. Feb -> 2, April -> 4, Dec -> 12) ')
        if month.isnumeric:
            month = int(month)
            if month > 0 and month < 13:
                curr_month = build_month(month=month)
                preserve_index = 0
                curr_month.preserve_bal(preserve_index ,curr_month.days[preserve_index].balance)

                print(f'Snapshot of the last 3 days of {curr_month.name}.')
                for day in curr_month.days[-3::]:
                    print(day)
        quit_loop = input('Keep going? ')
        quit_loop = True if quit_loop == "no" else False
        
if __name__ == '__main__':
    main()
