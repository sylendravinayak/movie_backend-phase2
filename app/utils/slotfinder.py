from datetime import datetime, timedelta, time

def find_available_slots(existing_shows, movie_duration, operating_start, operating_end, buffer=15):
    """
    existing_shows: list of (start_time, end_time) tuples (datetime.time)
    movie_duration: int (minutes)
    operating_start / end: datetime.time
    buffer: int (minutes)
    """
    shows = sorted(existing_shows, key=lambda x: x[0])
    available_slots = []
    current_time = datetime.combine(datetime.today(), operating_start)

    for start, end in shows:
        start_dt = datetime.combine(datetime.today(), start)
        end_dt = datetime.combine(datetime.today(), end)

        # gap in minutes
        gap = (start_dt - current_time).total_seconds() / 60
        if gap >= movie_duration + buffer:
            available_slots.append((
                current_time.time(),
                start_dt.time()
            ))

        # move current_time beyond this show
        current_time = max(current_time, end_dt + timedelta(minutes=buffer))

    operating_end_dt = datetime.combine(datetime.today(), operating_end)
    gap = (operating_end_dt - current_time).total_seconds() / 60
    if gap >= movie_duration:
        available_slots.append((current_time.time(), operating_end))

    return available_slots
