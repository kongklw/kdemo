from datetime import datetime,timedelta
from utils import convert_seconds, convert_string_datetime, convert_string_date

origin = '2024-12-29 00:00:00'

origin_date = datetime.strptime(origin, '%Y-%m-%d %H:%M:%S')
print(type(origin_date), origin_date)

aim = origin_date-timedelta(hours=12)
print(aim)
