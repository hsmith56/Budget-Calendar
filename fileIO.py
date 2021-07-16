import pickle
import os
import calendar
from monthObject import Month

def save(month, *savings_goal):
    try:
        save_dir = os.getcwd() + f"\\MonthObjects\\{month.name[0:3]}-{month.days[0].date.year}.pickle"
        with open(save_dir, 'wb') as to_save:
            pickle.dump(month, to_save)
            print(f'Saving {month.name} of {month.days[0].date.year} to file.')
            to_save.close()

    except FileNotFoundError:
        os.mkdir('MonthObjects')
        save(month)
        
    if savings_goal:
        print(savings_goal[0])
        
def load(m) -> Month:
    """
    [1] input var: 'm' -> datetime object
    This is called before creating a new month, tries to load a month object. 
    First look for a month pickle, then try to load it, otherwise create a new month
    """
    try:
        search_dir = os.getcwd() + f"\\MonthObjects\\{calendar.month_name[m.month][0:3]}-{m.year}.pickle"
        with open(search_dir, 'rb') as to_load:
            month = pickle.load(to_load)
            to_load.close()
            return month
    except FileNotFoundError:
        print(f"failed to open '\\MonthObjects\\{calendar.month_name[m.month][0:3]}-{m.year}.pickle'. This file does not exist.")
    return None