"""Offline solar schedule, NOAA fractional-year approximation (minutes accuracy).
Reference: https://gml.noaa.gov/grad/solcalc/solareqns.PDF
UTC timestamps for persistence; zoneinfo handles local dates and DST.
"""
import calendar
import math
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def sun_times(day, latitude, longitude):
    g = 2 * math.pi * (day.timetuple().tm_yday - 1) / (366 if calendar.isleap(day.year) else 365)
    eq = 229.18 * (0.000075 + 0.001868*math.cos(g) - 0.032077*math.sin(g) - 0.014615*math.cos(2*g) - 0.040849*math.sin(2*g))
    dec = 0.006918 - 0.399912*math.cos(g) + 0.070257*math.sin(g) - 0.006758*math.cos(2*g) + 0.000907*math.sin(2*g) - 0.002697*math.cos(3*g) + 0.00148*math.sin(3*g)
    lat = math.radians(latitude)
    cos_h = (math.cos(math.radians(90.833)) / (math.cos(lat)*math.cos(dec)) - math.tan(lat)*math.tan(dec))
    if not -1 <= cos_h <= 1:
        raise ValueError('An diesem Tag gibt es am Standort keinen Sonnenauf- oder -untergang.')
    hour = math.degrees(math.acos(cos_h))
    midnight = datetime.combine(day, time(), timezone.utc)
    return ((midnight + timedelta(minutes=720-4*(longitude+hour)-eq)).timestamp(),
            (midnight + timedelta(minutes=720-4*(longitude-hour)-eq)).timestamp())


def window(day, settings):
    tz = ZoneInfo(settings['timezone'])
    if settings['window'] == 'full':
        return (datetime.combine(day, time(), tz).timestamp(), datetime.combine(day+timedelta(days=1), time(), tz).timestamp())
    sunrise, sunset = sun_times(day, settings['latitude'], settings['longitude'])
    events = {'sunrise': sunrise, 'sunset': sunset}
    start = events[settings['startEvent']] + settings['startOffset']*60
    end = events[settings['endEvent']] + settings['endOffset']*60
    if end <= start:
        raise ValueError('Das Ende muss nach dem Beginn liegen.')
    return start, end
