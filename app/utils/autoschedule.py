from datetime import datetime, time, timedelta
from ortools.sat.python import cp_model


def generate_week_schedule(movies, screens, start_date, theatre_start, theatre_end, buffer=15):

    model = cp_model.CpModel()

    def to_minutes(t: time):
        return t.hour * 60 + t.minute

    theatre_start_m = to_minutes(theatre_start)
    theatre_end_m = to_minutes(theatre_end)
    total_minutes = theatre_end_m - theatre_start_m

    schedule_vars = {}
    all_vars = []

    # 7-day schedule
    for day_offset in range(7):
        date = start_date + timedelta(days=day_offset)
        for screen in screens:
            screen_id = screen["id"]

            for movie in movies:
                movie_id = movie["id"]
                duration = movie["duration"]

                # Start time variable (minutes from theatre_start)
                start_var = model.NewIntVar(0, total_minutes - duration, f"start_{day_offset}_{screen_id}_{movie_id}")
                show_var = (day_offset, screen_id, movie_id, start_var, duration)
                schedule_vars[(day_offset, screen_id, movie_id)] = start_var
                all_vars.append(show_var)

    # Constraints: no overlaps per screen per day
    for day_offset in range(7):
        for screen in screens:
            screen_id = screen["id"]
            shows = [(movie["id"], movie["duration"], schedule_vars[(day_offset, screen_id, movie["id"])]) for movie in movies]

            for i in range(len(shows)):
                for j in range(i + 1, len(shows)):
                    mi, di, vi = shows[i]
                    mj, dj, vj = shows[j]

                    model.Add(vj >= vi + di + buffer).OnlyEnforceIf(model.NewBoolVar(f"after_{i}_{j}_{day_offset}_{screen_id}"))
                    model.Add(vi >= vj + dj + buffer).OnlyEnforceIf(model.NewBoolVar(f"before_{i}_{j}_{day_offset}_{screen_id}"))

    # Objective: maximize screen utilization
    utilization = []
    for (day_offset, screen_id, movie_id), start_var in schedule_vars.items():
        duration = next(m["duration"] for m in movies if m["id"] == movie_id)
        utilization.append(duration)
    model.Maximize(sum(utilization))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10
    solver.Solve(model)

    # Build final schedule
    final_schedule = []
    for (day_offset, screen_id, movie_id), start_var in schedule_vars.items():
        start_min = solver.Value(start_var)
        start_h, start_m = divmod(start_min + theatre_start_m, 60)
        end_min = start_min + next(m["duration"] for m in movies if m["id"] == movie_id)
        end_h, end_m = divmod(end_min + theatre_start_m, 60)

        final_schedule.append({
            "date": str(start_date + timedelta(days=day_offset)),
            "screen_id": screen_id,
            "movie_id": movie_id,
            "start": f"{start_h:02d}:{start_m:02d}",
            "end": f"{end_h:02d}:{end_m:02d}"
        })

    return final_schedule
