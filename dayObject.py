from datetime import datetime
from savingsGoal import SavingsGoal
from typing import Type
from functools import total_ordering

@total_ordering
class DayObject:

    def __init__(self, date = datetime.now(), balance: float = 0.0, loan: float = 0.0, income: float = 0.0, bills: float = 0.0, etc: float = 0.0, savings_goals: Type[SavingsGoal] = []):
        self.date = date
        self.loan = loan
        self.income = income
        self.bills = bills
        self.etc = etc
        self.savings_goals = savings_goals
        self.balance = balance + self.income - self.loan - self.etc - self.bills - sum([goal.balance for goal in self.savings_goals])
        self.delta = self.balance - balance
        self.starting_bal = self.balance

    def __lt__(self, other):
        return self.date < other.date
    
    def __eq__(self, other):
        return self.date == other.date

    def __hash__(self):
        return hash(self.date) 

    def get_savings_balance(self):
        """Return the total balance of all savings goal objects in a day."""
        return sum([goal.balance for goal in self.savings_goals])

    def update(self):
        """Update the day's balance and return the amount changed by."""
        starting_balance = self.balance
        self.balance += self.income - self.loan - self.etc - self.bills - self.get_savings_balance() - self.delta
        change_in_balance = self.balance - starting_balance
        self.delta += change_in_balance
        return change_in_balance
               
    def __str__(self):
        """
        really ugly but prints single day in the following format
        # 4/7/2021        Balance: $1747.50
        #                 Spent: $0.00
        #                 Delta: $0.00
        """
        return f"{self.date.month}/{self.date.day}/{self.date.year}  \tBalance: ${self.balance:.2f}\n\t\tSpent: ${self.etc:.2f}\n\t\tDelta: ${self.delta:.2f}\n"