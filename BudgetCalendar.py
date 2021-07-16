from datetime import date
import string

from savingsGoal import SavingsGoal
from monthObject import Month, month_propegator, build_month, interact_with_single_day, snapshot
from fileIO import save, load

# class etc():
#     def __init__(self, name: str = "", amount: float = 0.0):
#         self.name = name
#         self.amount = amount

def main():
    quit_loop = False

    while not quit_loop:
        month = input('What month would you like to view? Enter the month number (ex. Feb -> 2, April -> 4, Dec -> 12) ')
        if month.isnumeric():
            month = int(month)
            if month > 0 and month < 13:
                same_month = True
                date_to_load = date(year=2021, month=month,day=1)
                curr_month: Month = load(date_to_load)
                
                if not curr_month:  # If the file could not be loaded, the month does not exist. Make the month
                    curr_month = build_month(month=month)
                    month_propegator(curr_month)
                
                while same_month: # keep looking at different dates in the same month to avoid constant read/writes
                    if curr_month:
                        date_to_edit = input(f'What day would you like to look at? [1-{len(curr_month.days)}] ')
                        interact_with_single_day(date_to_edit, curr_month)
                        same_month = False if 'n' in input('Stay on this month? (y/n) ') else True
                    else: same_month = False
            
                if curr_month: # if the month object exists, then save it to file
                    save(curr_month)
            else: print('Please pick a valid month.\n')
        else:
            print(f"'{month}' is not a valid number 1-12. Please try again.")
        quit_loop = input('Continue? (y/n) ')
        quit_loop = True if 'n'in quit_loop else False










if __name__ == '__main__':
    PROFILE = False

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
