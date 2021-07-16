from dayObject import DayObject
from savingsGoal import SavingsGoal
from typing import Type
from datetime import datetime, date
import calendar

class Month:

    def __init__(self, name: str = "", days: Type[DayObject] = [], year: int = 2021):
        self.name = name
        self.days = days
        self.year = year
        self.stats = {'total_spent':0,'total_loans':0,'total_savings_goals':0,'total_saved':0}

    def __lt__(self, other):
        return self.days[0].date < other.days[0].date
    
    def __eq__(self, other):
        return self.days[0].date == other.days[0].date   

    def preserve_bal(self, start_date: int = 0, to_add: int = 0):
        """
        start_date = index to update from
        to_add = amount to add to the following dates
        Example: If 3 days ago you remember you spent x dollars, you would need to update 
        the following days by adjusting +- x amount from the following days balances
        """
        try:
            for day in self.days[start_date::]:
                day.balance += to_add

        except IndexError:
            print(f"Index {start_date} out of range {len(self.days)}")
    
    def month_stats(self, *start_date, **end_date):
        """
        Returns the months stats in a dictionary
        """
        tot_spent = sum([x.etc for x in self.days])
        tot_saved = sum([x.delta for x in self.days])
        tot_goals = sum([x.get_savings_balance() for x in self.days])
        tot_loans = sum([x.loan for x in self.days])

        self.stats['total_spent'] = f'{tot_spent:.2f}'
        self.stats['total_savings_goals'] = f'{tot_goals:.2f}'
        self.stats['total_loans'] = f'{tot_loans:.2f}'
        self.stats['total_saved'] = f'{tot_saved:.2f}'
        return self.stats

def build_month(month = datetime.now().month, year = datetime.now().year) -> Month:
    """
    Takes in a month int [1-12] and a year int to create that specific month
    The returned month will have the Month name set, an array of all of the days that have happened up to the current day
    Each day will be a default day sequentually added to the month object.
    """
    dates = []
    total_Days_in_month = datetime.now()
    if total_Days_in_month.month >= month and month > 0 and month <13: # Only allow months up to the current month
        if total_Days_in_month.year >= year:
            total_Days_in_month = calendar.monthrange(year,month)[1]
    else:   
        return 
    for i in range(1,total_Days_in_month+1):
        that_day = date(year, month, i)
        dates.append(DayObject(date=that_day))
    return Month(name = calendar.month_name[dates[0].date.month], days = dates, year = year)

def month_propegator(month) -> None:
    """Helper function to mass update a month with the Month.preserve_bal() function."""
    try:
        for index, day in enumerate(month.days):
            if day.delta != 0:
                month.preserve_bal(index, day.delta)
    except IndexError:
        print('Everything is already up to date')
    except AttributeError:
        print('Future dates are locked until I figure out how to handle them.')

def snapshot(m: Month):
    """Prints the last 3 days of the month"""
    try:
        print(f'Snapshot of the last 3 days of {m.name}.')
        for day in m.days[-3::]:
            print(day)

    except AttributeError:
        pass 
    except IndexError:
        print('Cannot print the snapshot as there have not been enough days in this month yet.')


def interact_with_single_day(date_to_edit, curr_month):
    if date_to_edit.isnumeric():
        date_to_edit = int(date_to_edit)
        if date_to_edit >= 1 and date_to_edit <= len(curr_month.days):
            try:
                print(f'\n{curr_month.days[date_to_edit-1]}')
                day = curr_month.days[date_to_edit-1]
                menu_choice = input(f'1. Loan\n2. Savings goals\n3. Income\n4. Etc\n')
                if menu_choice.isnumeric() and int(menu_choice) > 0 and int(menu_choice) < 5:

                    choice = int(menu_choice)
                    if choice == 1:
                        day.loan += 100

                    elif choice ==2:
                        food = SavingsGoal("food", balance=10, goal=100)
                        dog = SavingsGoal("dog", balance=100, goal=101)
                        
                        day.savings_goals.append(food)
                        day.savings_goals.append(dog)
                        
                        #day.savings_goals += 0

                    elif choice == 3:
                        day.income += 100 

                    else:
                        day.etc += 50

                    update_ammount = day.update()
                    curr_month.preserve_bal(start_date = date_to_edit, to_add = update_ammount)

            except AttributeError:
                print('Future dates are locked until I figure out how to handle them. [curr_month.days[date_to_edit-1]]')
            except IndexError:
                print('Cannot print this date as this day has not happened.')   
        else:
            print('That date is invalid, please try a different date.\n')