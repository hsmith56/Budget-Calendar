from datetime import datetime, timedelta

class SavingsGoal():
    """
    Savings goal objects get a name, startdate, enddate, and a goal balance.
    Stored in a day object in a list of SavingsGoal objects.
    """

    def __init__(self, name: str = "", start= datetime.now(), end= datetime.now()+ timedelta(days=1),balance: float = 0, goal: int = 100):
        self.name = name
        self.start = start.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%b %d, %Y')
        self.end = end.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%b %d, %Y')
        self.balance = balance
        self.goal = goal

    def __str__(self):
        return f'Your "{self.name}" goal from {self.start} -> {self.end} is {(self.balance/self.goal)*100:.2f}% complete.'

    # TODO Check for completion
    # TODO Display time to complete
    # TODO Make immutable after completion ?