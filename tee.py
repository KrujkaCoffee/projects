import datetime

from project_cust_38 import Cust_prod_calendar as CPC


f = CPC.ProdCalendar('')

month = f.month(datetime.datetime(year=2027, month=3, day=7))
print()