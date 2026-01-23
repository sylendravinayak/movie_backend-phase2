from faker import Faker
import psycopg2, random, uuid
from datetime import datetime, timedelta, date, time

fake = Faker()

conn = psycopg2.connect(
    dbname="movie_booking",
    user="postgres",
    password="raja807",
    host="localhost",
    port=5432
)
cur = conn.cursor()

# ---------------------------------------------------
# CLEAN LAST 7 DAYS DATA
# ---------------------------------------------------
cur.execute("""
DELETE FROM booked_seats
WHERE booking_id IN (
    SELECT booking_id FROM bookings
    WHERE booking_time >= now() - interval '7 days'
)
""")

cur.execute("""
DELETE FROM bookings
WHERE booking_time >= now() - interval '7 days'
""")
conn.commit()

print("Old last-7-day data cleared")

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

cur.execute("""
SELECT s.show_id, s.movie_id, s.screen_id,
       s.show_date, s.show_time,
       m.rating
FROM shows s
JOIN movies m ON s.movie_id = m.movie_id
""")
shows = cur.fetchall()

cur.execute("SELECT seat_id, screen_id FROM seats")
seats = cur.fetchall()

cur.execute("SELECT user_id FROM users")
users = [u[0] for u in cur.fetchall()]

seat_map = {}
for s in seats:
    seat_map.setdefault(s[1], []).append(s[0])

# ---------------------------------------------------
# WEIGHT SHOWS BY MOVIE POPULARITY
# ---------------------------------------------------

weighted_shows = []
for sh in shows:
    rating = sh[5] or 5
    weight = int(rating * 10)
    weighted_shows.extend([sh] * weight)

# ---------------------------------------------------
# UTILS
# ---------------------------------------------------

def show_datetime(show_date, show_time):
    return datetime.combine(show_date, show_time)

def booking_time_last_week(show_dt):
    start = max(datetime.now() - timedelta(days=7), show_dt - timedelta(days=7))
    end = min(show_dt - timedelta(minutes=30), datetime.now())
    return fake.date_time_between(start_date=start, end_date=end)

def is_seat_taken(seat_id, show_id):
    cur.execute("SELECT 1 FROM booked_seats WHERE seat_id=%s AND show_id=%s LIMIT 1",(seat_id,show_id))
    return cur.fetchone() is not None

# ---------------------------------------------------
# GENERATION
# ---------------------------------------------------

TOTAL_BOOKINGS = 1200
inserted = 0

for _ in range(TOTAL_BOOKINGS):

    show = random.choice(weighted_shows)

    show_id, movie_id, screen_id, sd, st, rating = show
    show_dt = show_datetime(sd, st)

    # weekend boost
    if sd.weekday() >= 5:
        if random.random() > 0.7:
            continue

    booking_time = booking_time_last_week(show_dt)

    status = random.choices(
        ["CONFIRMED","CANCELLED","PENDING"],
        [78,12,10]
    )[0]

    cur.execute("""
    INSERT INTO bookings
    (user_id, show_id, booking_reference, booking_status, booking_time, amount)
    VALUES (%s,%s,%s,%s,%s,%s)
    RETURNING booking_id
    """,(
        random.choice(users),
        show_id,
        uuid.uuid4().hex[:12],
        status,
        booking_time,
        0
    ))

    booking_id = cur.fetchone()[0]

    group = random.choices([1,2,3,4],[60,25,10,5])[0]
    pool = seat_map[screen_id]
    random.shuffle(pool)

    total = 0
    count = 0

    for seat_id in pool:
        if count >= group:
            break
        if is_seat_taken(seat_id, show_id):
            continue

        price = random.choice([150,180,220,250])

        cur.execute("""
        INSERT INTO booked_seats
        (booking_id, seat_id, price, show_id)
        VALUES (%s,%s,%s,%s)
        """,(booking_id,seat_id,price,show_id))

        total += price
        count += 1

    cur.execute("UPDATE bookings SET amount=%s WHERE booking_id=%s",(total,booking_id))

    inserted += 1

conn.commit()
cur.close()
conn.close()

print(f"✅ {inserted} realistic bookings generated for last 7 days")
