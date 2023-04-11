# Random Weather Generation

```python
import datetime, time, random, string

def one_station(name):
    # temp pattern
    month_avg = [27,31,44,58,70,79,83,81,74,61,46,32]
    shift = (random.random()-0.5) * 30
    month_avg = [m + shift + (random.random()-0.5) * 5 for m in month_avg]
    
    # rain pattern
    start_rain = [0.1,0.1,0.3,0.5,0.4,0.2,0.2,0.1,0.2,0.2,0.2,0.1]
    shift = (random.random()-0.5) * 0.1
    start_rain = [r + shift + (random.random() - 0.5) * 0.2 for r in start_rain]
    stop_rain = 0.2 + random.random() * 0.2

    # day's state
    today = datetime.date(2000, 1, 1)
    temp = month_avg[0]
    raining = False
    
    # gen weather
    while True:
        # choose temp+rain
        month = today.month - 1
        temp = temp * 0.8 + month_avg[month] * 0.2 + (random.random()-0.5) * 20
        if temp < 32:
            raining=False
        elif raining and random.random() < stop_rain:
            raining = False
        elif not raining and random.random() < start_rain[month]:
            raining = True

        yield (today.strftime("%Y-%m-%d"), name, temp, raining)

        # next day
        today += datetime.timedelta(days=1)
        
def all_stations(count=10, sleep_sec=1):
    assert count <= 26
    stations = []
    for name in string.ascii_uppercase[:count]:
        stations.append(one_station(name))
    while True:
        for station in stations:
            yield next(station)
        time.sleep(sleep_sec)
```