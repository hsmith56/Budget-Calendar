
#  Budget-Calendar  

##  TODO

- [ ] Need a good way to carry over balance from 1st of month to last of month
- [ ] Move Savings goals into seperate class
	- [ ] Savings goals should be persistent across months from start date to finish date
	- [ ] Savings goals should be customizable with start/end date, name, auto deposit on specific day
- [ ] Modify handling of paychecks (Do I set paycheck balance at first of month or as I get them?)  

Whenever I have any change to a specific balance, it should go through all days after it in the same month and deduct the delta from before the change and after the change from the running balance.

IE. \
1/1/2021 - balance 1000\
1/2/2021 - balance 1000\
1/3/2021 - balance 1000\
\
1/1/2021 - balance 1000\
1/2/2021 - balance 1200, income 200, delta = +200\
1/3/2021 - balance = balance + delta 

####  Random.csv will eventually be replaced with a dir of month json objects to avoid loading the entirety of every month into memory. Will look at how costly that would be, would not assume too much but python is already heavy so if I can put lighten some of the burden then why not.