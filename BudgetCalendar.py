import calendar
import os
from datetime import datetime, timedelta, date
import pickle
import random

PROFILE = False

cwd = os.getcwd()

def myconverter(o):
    if isinstance(o, datetime):
        return o.__str__()

class savings_goal():
    def __init__(self, name: str = "", start= datetime.now(), end= datetime.now()+ timedelta(days=1),balance: int = 0, goal: int = 100):
        self.name = name
        self.start = start.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%b %d, %Y')
        self.end = end.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%b %d, %Y')
        self.balance = balance
        self.goal = goal

    def __str__(self):
        return f'Your "{self.name}" goal from {self.start} -> {self.end} is {(self.balance/self.goal)*100:.2f}% complete'

class day_obj:
    paycheck = 1750.5
    def __init__(self, date = datetime.now(), balance: int = 0, loan: int = 0, income: int = 0, bills: int = 0, spending: int = 0, savings_goals: int = 0):
        self.date = date
        self.loan = loan
        self.income = self.paycheck if self.date.day == 1 or self.date.day == 15 else income
        # might be changed later depending on how I want to handle this. Currently is very rigid, does not allow for any flexibility
        self.bills = bills
        self.spending = spending
        self.savings_goals = savings_goals
        self.balance = balance + self.income - self.loan - self.spending - self.bills - self.savings_goals
        self.delta = self.balance - balance

    def __lt__(self, other):
        return self.date < other.date
    
    def __eq__(self, other):
        return self.date == other.date

    def __hash__(self):
        return hash(self.date) 

    def update(self):
        starting_bal = self.balance
        self.balance += self.income - self.loan - self.spending - self.bills - self.savings_goals
        self.delta = self.balance - starting_bal
        return self.delta
               
    def __str__(self):
        """
        really ugly but prints single day in the following format
        # 4/7/2021        Balance: $1747.50
        #                 Spent: $0.00
        #                 Delta: $0.00
        """
        return f"{self.date.month}/{self.date.day}/{self.date.year}  \tBalance: ${self.balance:.2f}\n\t\tSpent: ${self.spending:.2f}\n\t\tDelta: ${self.delta:.2f}\n"

class Month:
    def __init__(self, name: str = "", days: [day_obj] = [], year: int = 2021):
        self.name = name
        self.days = days
        self.year = year

    def __lt__(self, other):
        return self.days[0].date < other.days[0].date
    
    def __eq__(self, other):
        return self.days[0].date == other.days[0].date   

    def preserve_bal(self, start_date: int = 0, to_add: int = 0):
        """
        Only useful on adjusting historic entries
        Example: If 3 days ago you remember you spent x dollars, you would need to update 
        the following days by adjusting +- x amount from the following days balances
        """
        try:
            for day in self.days[start_date+1::]:
                day.balance += to_add
        except IndexError:
            print(f"Index {start_date} out of range {len(self.days)}")

def build_month(month = datetime.now().month, year = datetime.now().year) -> Month:
    dates = []
    total_Days_in_month = datetime.now()
    if total_Days_in_month.month > month and month > 0 and month <13:
        if total_Days_in_month.year >= year:
            total_Days_in_month = calendar.monthrange(year,month)[1]
    elif total_Days_in_month.month == month:
        total_Days_in_month = total_Days_in_month.day
    else:
        return 
    for i in range(1,total_Days_in_month+1):
        that_day = date(year, month, i)
        dates.append(day_obj(date=that_day))
    return Month(name = calendar.month_name[dates[0].date.month], days = dates, year = year)

def month_propegator(month) -> None:
    try:
        for index, day in enumerate(month.days):
            if day.delta != 0:
                month.preserve_bal(index ,day.delta)
    except IndexError:
        print('Everything is already up to date')
    except AttributeError:
        print('Future dates are locked until I figure out how to handle them.')

def snapshot(m):
    try:
        print(f'Snapshot of the last 3 days of {m.name}.')
        for day in m.days[-3::]:
            print(day)
    except AttributeError:
        pass # Future dates are locked until I figure out how to handle them
    except IndexError:
        print('Cannot print the snapshot as there have not been enough days in this month yet.')

def save(m):
    print(f'Saving {m.name} of {m.days[0].date.year} to file.')
    save_dir = os.getcwd() + f"\\MonthObjects\\{m.name[0:3]}-{m.days[0].date.year}.pickle"
    with open(save_dir, 'wb') as f:
        pickle.dump(m, f)
        f.close()
        
def retrieve_month(m):
    """
    this should be called before making a new month
    First look for a month pickle, then try to load it, otherwise create a new month
    """
    try:
        search_dir = os.getcwd() + f"\\MonthObjects\\{m.name[0:3]}-{m.days[0].date.year}.pickle"
        with open(search_dir, 'wb') as f:
            month = pickle.load(m, f)
            f.close()
            return month
    except:
        pass
    pass

def interact_with_single_day(date_to_edit, curr_month):
    if date_to_edit.isnumeric:
        date_to_edit = int(date_to_edit)
        if date_to_edit >= 1 and date_to_edit <= len(curr_month.days):
            try:
                print(f'\n{curr_month.days[date_to_edit-1]}')
            except AttributeError:
                print('Future dates are locked until I figure out how to handle them. [curr_month.days[date_to_edit-1]]')
            except IndexError:
                print('Cannot print this date as this day has not happened.')    
        else:
            print('That date is invalid, please try a different date.\n')

def main():
    # should first see if the curr month file exists to load instead of making it from scratch each time
    quit_loop = False
    curr_month = build_month()
    month_propegator(curr_month)

    while not quit_loop:
        month = input('What month would you like to view? Enter the month number (ex. Feb -> 2, April -> 4, Dec -> 12) ')
        if month.isnumeric:
            month = int(month)
            if month > 0 and month < 13:
                curr_month = build_month(month = month)
                month_propegator(curr_month)
                same_month = True
                while same_month:
                    if curr_month:
                        date_to_edit = input(f'What day would you like to look at? [1-{len(curr_month.days)}] ')
                        interact_with_single_day(date_to_edit, curr_month)
                        same_month = False if 'n' in input('Stay on this month? (y/n) ') else True
                    else: same_month = False

                if curr_month:
                    save(curr_month)

        quit_loop = input('Keep going? ')
        quit_loop = True if 'n'in quit_loop else False
        
if __name__ == '__main__':
    if PROFILE:
        import cProfile
        cProfile.run('main()', 'output.dat')

        import pstats
        from pstats import SortKey
        
        with open('output_time.txt','w') as f:
            p = pstats.Stats('output.dat', stream=f)
            p.sort_stats("time").print_stats()

        with open('output_calls.txt','w') as f:
            p = pstats.Stats('output.dat', stream=f)
            p.sort_stats("calls").print_stats()

    else:
        main()
        tt = savings_goal(name="hi")
        print(tt)