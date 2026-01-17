from collections import Counter

def compute_trend(date_series):
    if not date_series or len(date_series) < 2:
        return 1.0

    counts = Counter(date_series)

    ordered = sorted(counts.items())
    values = [v for _, v in ordered]

    if len(values) < 2:
        return 1.0

    delta = values[-1] - values[0]

    if delta > 2:
        return 1.2
    elif delta > 0:
        return 1.1
    elif delta < -2:
        return 0.8
    elif delta < 0:
        return 0.9
    else:
        return 1.0



def seasonality_factor(date):
    if date.weekday() in [5, 6]:
        return 1.3
    return 1.0


def forecast_from_trend(blended, season):
    base_capacity = 3   # your business constant
    return round(max(base_capacity * blended * season, 1))



