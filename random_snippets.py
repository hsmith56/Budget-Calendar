
# dates = build_month(month = 2, year=2020)

# preserve_index = 0
# curr_month.preserve_bal(preserve_index ,curr_month.days[preserve_index].balance)
# for day in curr_month.days[-3::]:
#      print(day)  

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