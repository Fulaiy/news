import time

from datetime import datetime, timedelta
tim = time.time()

t = time.localtime()
# time.struct_time(tm_year=2018, tm_mon=7, tm_mday=15, tm_hour=16, tm_min=26, tm_sec=39, tm_wday=6, tm_yday=196, tm_isdst=0)
# <class 'time.struct_time'>

now_time = "%d-%02d-01"%(t.tm_year,t.tm_mon)
# 2018-07-01
now_time_more = datetime.strptime(now_time,"%Y-%m-%d")
# 2018-07-01 00:00:00

today_time = "%d-%02d-%02d"%(t.tm_year,t.tm_mon,t.tm_mday)
# 2018-07-15 哪天写的就是哪天的日期
today_begin_time = datetime.strptime(today_time,"%Y-%m-%d")
# 2018-07-15 00:00:00


today_begin_time = today_begin_time - timedelta(days=0)
today_end_time = today_begin_time - timedelta(days=-1)

print(tim)

print(t)
print(now_time)
print(today_time)
print(now_time_more)
print(today_begin_time,"------",today_end_time)

