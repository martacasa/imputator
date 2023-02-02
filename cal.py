import datetime
import os.path
import pickle
import re

import dateutil.parser
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]


def get_service():
    """The file token.pickle stores the user's access and refresh
    tokens, and is created automatically when the authorization flow
    completes for the first time.
    """
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let
    # the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = discovery.build('calendar', 'v3', credentials=creds)

    return service


def update_jiras(calendar=None):
    calendar_id = calendar['id'] if calendar else None
    service = get_service()
    # Call the Calendar API
    now = datetime.datetime.utcnow()
    since = now - datetime.timedelta(days=10)
    since_time = since.isoformat() + 'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=since_time,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime',
        )
        .execute()
    )
    events = events_result.get('items', [])

    patron_name = re.compile('^([A-Z][A-Z0-9]+[-][0-9]+)(.*)')

    if not events:
        print('No JIRA events found.')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime')
        event_id = event['id']

        jira_match = patron_name.search(event['summary'])
        if jira_match:
            duration = dateutil.parser.parse(end) - dateutil.parser.parse(start)
            print(
                '#{} {} - {} ({} seconds) | [{}] | {}'.format(
                    event_id,
                    start,
                    end,
                    duration.total_seconds(),
                    jira_match.group(1),
                    jira_match.group(2),
                )
            )
            event['summary'] = '✅ ' + event['summary']
            service.events().update(
                calendarId=calendar_id, eventId=event['id'], body=event
            ).execute()


def get_jiras(date_from, calendar=None):
    calendar_id = calendar['id'] if calendar else None
    if not calendar_id:
        return None

    service = get_service()
    # Call the Calendar API
    date_from_str = str(date_from)
    print(f'JIRAS from {date_from_str}')
    from_datetime = datetime.datetime.combine(date_from, datetime.datetime.min.time())
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=from_datetime.isoformat() + 'Z',
            maxResults=1000,
            singleEvents=True,
            orderBy='startTime',
        )
        .execute()
    )
    events = events_result.get('items', [])

    patron_name = re.compile('^([A-Z][A-Z0-9]+[-][0-9]+)(.*)')

    if not events:
        print('No JIRA events found.')

    jiras = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime')

        if 'summary' not in event:
            continue

        jira_match = patron_name.search(event['summary'])
        if jira_match:
            description = jira_match.group(2)
            issue_id = jira_match.group(1)
            jiras.append(
                {'description': description, 'issue_id': issue_id, 'start': start, 'stop': end}
            )
    return jiras


def get_calendar_from_name(calendar_name):
    service = get_service()
    calendarlist = service.calendarList().list().execute()
    ic = list(filter(lambda x: x['summary'] == calendar_name, [c for c in calendarlist['items']]))
    if not ic:
        return None
    else:
        return ic[0]


def main_get_jiras():
    ic = get_calendar_from_name('Jira')
    print('Jira calendar found with id {}', format(ic['id']))
    jiras = get_jiras(ic, since_days=20)
    print(jiras)
    # update_jiras(ic)


def main_get_calendars():
    service = get_service()
    calendarlist = service.calendarList().list().execute()
    for calendar in calendarlist['items']:
        print(f"{calendar['summary']:<30} {calendar['id']:>30}")


def print_events(events):
    for event in events:
        summary = event['summary']
        start = event['start'].get('date') or event['start'].get('dateTime')
        end = event['end'].get('date') or event['end'].get('dateTime')
        duration = dateutil.parser.parse(end) - dateutil.parser.parse(start)
        duration_h = duration.total_seconds() / 3600
        print(f'{summary:<40} {start:<25} {end:<25} {duration_h:>30}')


def main_get_week_entries(calendar_id):
    now = datetime.datetime.now()
    monday = now - datetime.timedelta(days=now.weekday())
    next_monday = monday + datetime.timedelta(days=7)
    service = get_service()
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=next_monday.isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime',
        )
        .execute()
    )
    events = events_result.get('items', [])
    print_events(events)


if __name__ == '__main__':
    entries = main_get_week_entries('oscar.garcia@makingscience.com')
