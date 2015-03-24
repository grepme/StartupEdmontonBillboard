"""
Welcome to the Startup Edmonton Billboard!


---------------
- Quick Start -
---------------
To run:
    python StartupEdmontonBillBoard.py

Open in your browser and go to:
    http://127.0.0.1:5000/

You will need to configure settings.py
You will notice a settings_example.py of all the settings that need configuring.
Rename that file to settings.py

No other options are currently available.
"""

# Common imports
from flask import Flask, render_template
import requests
from requests.exceptions import ConnectionError
import datetime

# Any additional settings
from settings import API_KEY, CALENDAR_ID

app = Flask(__name__)

# Global Calendar URL to get from Google
CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/{}/events".format(CALENDAR_ID)

# Global caching
CALENDAR_CACHED = None
EVENTS_CACHED = None


def cache_calendar_events(calendar_url, params=None):
    """Attempt to connect to the calendar and fetch the JSON provided."""
    try:
        global CALENDAR_CACHED
        CALENDAR_CACHED = requests.get(calendar_url, params=params).json()
    except ConnectionError:
        # Can't connect, are we connected to the internet?
        return False
    return CALENDAR_CACHED


def get_calendar_events(calendar_url, params=None):
    """Ask Google for new events from the calendar"""
    return cache_calendar_events(calendar_url, params=params)
    # return CALENDAR_CACHED or cache_calendar(calendar_url)


def get_calendar_events_today(calendar_url):
    """Get the calendar events from only today. 24 hour span from midnight."""
    # Access the global cache
    global EVENTS_CACHED

    # Construct today and tomorrow datetime objects
    today = datetime.datetime.today()
    tomorrow = today
    tomorrow += datetime.timedelta(days=1)

    # Get the calendar events subjective to time and singleEvents which expands recurring events
    cal = get_calendar_events(calendar_url, params={'key': API_KEY, 'singleEvents': True,
                                                    'timeMax': tomorrow.strftime("%Y-%m-%dT00:00:00-06:00"),
                                                    'timeMin': today.strftime("%Y-%m-%dT00:00:00-06:00"),
    })

    # Specifically, events are held in the items array
    EVENTS_CACHED = cal['items']
    return EVENTS_CACHED


def sort_events_days(events):
    """Sort the event into an array of events by day"""
    # Last event used in the loop
    last_event = datetime.datetime.now()

    # The day we are currently working with
    current_day = datetime.datetime.now()

    # Event days such that each day is its own index in the array of events
    # ie. [[today], [tomorrow], [day after], [etc]]
    event_days = []

    # The list of events for the current day
    day = []
    for i, event in enumerate(events, start=1):
        if convert_from_iso(event['start']['dateTime']).day == last_event.day:
            # This is an event for today
            day.append(event)

            # If this is the last iteration of the loop, we should append our day before breaking
            if i == len(events):
                event_days.append(day)
        else:
            # This event is the start of a new day, so we need to add it.
            event_days.append(day)

            # TODO: Really bad while loop
            # While this event is not the next day, increment the array
            while True:
                # Clear our current day in favour of a new one
                day = []

                # Increment our current day until we find an event that matches it
                current_day = current_day + datetime.timedelta(days=1)
                if current_day.day == convert_from_iso(event['start']['dateTime']).day:
                    day.append(event)
                    break
                else:
                    # This event and all other events are not in this day, so it needs to be blank
                    event_days.append(day)

        # Last event in the loop for comparison against future events
        last_event = convert_from_iso(event['start']['dateTime'])

    # Event days sorted
    return event_days


def get_calendar_events_limit(calendar_url, limit=10, sort=True):
    """Get the calendar events from only today. 24 hour span from midnight."""
    # Access the global cache
    global EVENTS_CACHED

    # Construct today and tomorrow datetime objects
    today = datetime.datetime.today()

    # Get the calendar events subjective to time and singleEvents which expands recurring events
    cal = get_calendar_events(calendar_url, params={'key': API_KEY, 'singleEvents': True,
                                                    'orderBy': 'startTime',
                                                    'timeMin': today.strftime("%Y-%m-%dT00:00:00-06:00"),
                                                    'maxResults': limit})

    # Specifically, events are held in the items array
    EVENTS_CACHED = cal['items']
    if sort:
        return sort_events_days(EVENTS_CACHED)
    else:
        return EVENTS_CACHED


def convert_from_iso(s):
    """Convert from ISO 8601, worst date format, ever...Especially since Google ONLY does this."""
    # TODO: Allow for more timezones than just -6 GMT
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S-06:00")


def find_event_property(properties, value, events):
    """Returns true if a property with a value was found within the events list, else false."""
    for event in events:
        if properties in event and event[properties] == value:
            return True
    return False


def compare_events(events_prev, events_new):
    """Compare two event arrays to determine if they have lost/gained anything significant since last check."""
    # Fields we are interested in monitoring
    fields = ['start', 'end', 'summary', 'location', 'description']

    # The most obvious check is just the length of the previous event list, and the current.
    # If event length has changed, then we need to update.
    if len(events_prev) != len(events_new):
        return False

    # Scan all previous events and compare attributes to current
    for event in events_prev:
        for field in fields:

            # If the field exists in some event, then it likely didn't change
            # TODO: This is invalid if two fields have the same field/value and then one changes.
            if field in event and not find_event_property(field, event[field], events_new):
                # No match found, something has changed.
                return False

    # All checks done, nothing has changed since our last check
    return True


@app.template_filter('str_hour')
def str_hour_to_hour(s):
    """Template filter that converts ISO format to meaningful Hour:Minute A.M/P.M format"""
    # TODO: Fix the -06:00 time zone offset
    if s:
        d = convert_from_iso(s)
        return datetime.datetime.strftime(d, "%I:%M %p").lstrip('0').strip(" ")
    else:
        # Couldn't parse, return original.
        return s


@app.template_filter('str_day')
def str_day(s):
    """Template filter that converts ISO format to meaningful day format"""
    # TODO: Fix the -06:00 time zone offset
    if s:
        d = convert_from_iso(s)
        return datetime.datetime.strftime(d, "%d").strip(" ")
    else:
        # Couldn't parse, return original.
        return s


@app.template_filter('str_day_month')
def str_day_month(s):
    """Template filter that converts ISO format to meaningful month format"""
    # TODO: Fix the -06:00 time zone offset
    if s:
        d = convert_from_iso(s)
        return datetime.datetime.strftime(d, "%B %d|%A").strip("0")
    else:
        # Couldn't parse, return original.
        return s


@app.route('/')
def index():
    """Return the template with the event calendar"""
    # return render_template('index.html', events=get_calendar_events_today(CALENDAR_URL))
    return render_template('index.html', events=get_calendar_events_limit(CALENDAR_URL), events_sorted=True)


@app.route('/events/')
def events():
    """Queries Google and asks for update on calendar"""
    # Compare cache against a new GET request
    temp_cache = EVENTS_CACHED
    # events_new = get_calendar_events_today(CALENDAR_URL)
    events_new = get_calendar_events_limit(CALENDAR_URL, sort=False)

    # If not change is detected, tell the browser to keep it's current content.
    if temp_cache is None or compare_events(temp_cache, events_new):
        return "false"

    # Else, render the partial events template to return to the client.
    return render_template('events_sorted.html', events=sort_events_days(events_new))

# Let's go!
if __name__ == '__main__':
    # Debug always helps
    app.debug = True
    app.run(host="0.0.0.0")
