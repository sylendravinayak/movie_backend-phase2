from datetime import datetime, timedelta, time,date
from model import Show, Movie
def generate_day_slots(open_time, close_time, duration, buffer_minutes):
    slots = []
    cur = datetime.combine(date.today(), open_time)
    end = datetime.combine(date.today(), close_time)

    while cur + duration <= end:
        slots.append(cur.time())
        cur += duration + timedelta(minutes=buffer_minutes)

    return slots

def is_prime_slot(t):

    if isinstance(t, datetime):
        t = t.time()

    return time(18,0) <= t <= time(22,0)


