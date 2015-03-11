from flask import Flask
from flask import render_template
import requests
from requests.exceptions import ConnectionError
import datetime

from settings import API_KEY

app = Flask(__name__)

CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/startupedmonton.com_1hv08457agfled5c5doo9evhk4%40group.calendar.google.com/events?key={}".format(
    API_KEY)
CALENDAR_CACHED = None
EVENTS_CACHED = None


def cache_calendar(calendar_url):
    """Attempt to connect to the calendar and fetch the JSON provided."""
    try:
        global CALENDAR_CACHED
        CALENDAR_CACHED = requests.get(calendar_url).json()
    except ConnectionError:
        return False
    return CALENDAR_CACHED


def get_calendar(calendar_url):
    """Return cache or set a new cache on the calendar for today"""
    return cache_calendar(calendar_url)
    # return CALENDAR_CACHED or cache_calendar(calendar_url)


def get_calendar_today(CALENDAR_URL):
    cal = get_calendar(CALENDAR_URL)
    today = datetime.datetime.now().date()
    events = []
    for event_iter, event in enumerate(cal['items']):
        if 'start' in event and 'dateTime' in event['start']:
            event_start_time = convert_from_iso(event['start']['dateTime']).date()
            if today == event_start_time:
                events.append(event)
    global EVENTS_CACHED
    EVENTS_CACHED = events
    return events


def convert_from_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S-06:00")


def find_event_property(properties, value, events):
    for event in events:
        if event[properties] == value:
            return True
    return False


def compare_events(events_prev, events_new):
    for event in events_prev:
        if not find_event_property('start', event['start'], events_new) or \
                not find_event_property('end', event['end'], events_new) or \
                not find_event_property('summary', event['summary'], events_new) or \
                not find_event_property('location', event['location'], events_new) or \
                not find_event_property('description', event['description'], events_new):
            return False
    return True


@app.template_filter('str_hour')
def str_hour_to_hour(s):
    # TODO: Fix the -06:00 time zone offset
    if s:
        d = convert_from_iso(s)
        return datetime.datetime.strftime(d, "%I:%M %p").lstrip('0').strip(" ")
    else:
        return s


@app.route('/')
def index():
    events = get_calendar_today(CALENDAR_URL)
    return render_template('index.html', events=events)


@app.route('/events/')
def events():
    temp_cache = EVENTS_CACHED
    events = get_calendar_today(CALENDAR_URL)

    if temp_cache is None or compare_events(temp_cache, events):
        print "NO CHANGE IN EVENTS!"
        return "false"

    print "CHANGE DETECTED IN EVENTS!"
    return render_template('events.html', events=events)


if __name__ == '__main__':
    app.debug = True
    app.run()
