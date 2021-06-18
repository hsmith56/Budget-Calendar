
#  Budget-Calendar  

##  TODO
### Need to clarify what daily spending is tracking.
- Is it tracking total spent on that day?
- Is it tracking misc spending?
- Is it tracking some categories but not all?

- [x] Confirm that correct values are propegated through month
- [x] Need a good way to carry over balance from 1st of month to last of month
- [x] more efficient methods of propegating balance forward
- [ ] Move Savings goals into seperate class
	- [ ] Savings goals should be persistent across months from start date to finish date
	- [ ] Savings goals should be customizable with start/end date, name, auto deposit on specific day
- [ ] Modify handling of paychecks (Do I set paycheck balance at first of month or as I get them?)
- [ ] Better input handler/input handler function\
      

####  Random.csv will eventually be replaced with a dir of month json objects to avoid loading the entirety of every month into memory. Will look at how costly that would be, would not assume too much but python is already heavy so if I can put lighten some of the burden then why not.