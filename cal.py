import datetime
import os.path
import pickle
import re

import dateutil.parser
from colorama import Fore, Style, init
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]

JIRA_PATTERN_NAME = re.compile('^([A-Z][A-Z0-9]+[-][0-9]+): ?(.*)')

init()

class Calendar:

    def __init__(self, calendar_name):
        self.__service = None
        self.__calendar = None
        self.calendar_name = calendar_name

    @property
    def service(self) -> discovery.Resource:
        if not self.__service:
            self.__service = self._get_service()

        return self.__service

    @property
    def calendar(self):
        if not self.__calendar:
            self.__calendar = self._get_calendar_from_name(self.calendar_name)

        return self.__calendar

    @property
    def calendar_id(self) -> str:
        return self.calendar['id']

    def _get_calendar_from_name(self, calendar_name):
        calendarlist = self.service.calendarList().list().execute()
        ic = list(filter(lambda x: x['summary'] == calendar_name, [c for c in calendarlist['items']]))

        if not ic:
            raise Exception(f"[ERROR] Calendar {calendar_name} not found!")

        return ic[0]

    @staticmethod
    def _get_service() -> discovery.Resource:
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

    def get_entries(self, date_from, date_to=None):  # list(CalendarEntry)
        raw_entries = self._get_raw_entries(date_from, date_to)

        entries = []

        for raw_entry in raw_entries:
            calendar_entry = CalendarEntry(**raw_entry)

            if calendar_entry:
                entries.append(calendar_entry)

        return entries

    def _get_raw_entries(self, date_from, date_to=None, num_entries=1000):
        print(f'JIRAS from {date_from}')
        params = {
            'calendarId': self.calendar_id,
            'timeMin': date_from.isoformat() + 'Z',
            'maxResults': num_entries,
            'singleEvents': True,
            'orderBy': 'startTime',
        }

        if date_to:
            params['timeMax'] = (date_to + datetime.timedelta(days=1)).isoformat() + 'Z'

        entries_result = self.service.events().list(**params).execute()

        entries = entries_result.get('items', [])

        if not entries:
            raise Exception('No JIRA entries found.')

        return entries

    def update_event_status(self, entries):
        for entry in entries:
            if entry.claim_status != 2:
                # No change in claim status
                continue

            entry.summary = '✅ ' + entry.summary
            self.service.events().update(
                calendarId=self.calendar_id, eventId=entry['id'], body=entry
            ).execute()

    @classmethod
    def get_calendars(cls):
        service = cls._get_service()
        calendarlist = service.calendarList().list().execute()

        for calendar in calendarlist['items']:
            print(f"{calendar['summary']:<30} {calendar['id']:>30}")


    def get_week_entries(self):
        now = datetime.datetime.now()
        monday = now - datetime.timedelta(days=now.weekday())
        next_monday = monday + datetime.timedelta(days=7)
        entries = self.get_entries(date_from=monday, date_to=next_monday)
        # Print entries

        for entry in entries:
            entry.print_summary()


class CalendarEntry:

    def __init__(self, **kwargs):
        self.entry = kwargs
        self.load_input(**kwargs)

    def load_input(self, **entry):
        self.entry_id = entry['id']
        self.summary = entry['summary']
        self.start_str = entry['start'].get('dateTime', entry['start'].get('date'))
        self.end_str = entry['end'].get('dateTime')
        self.start = datetime.datetime.fromisoformat(self.start_str[0:-1])
        self.end = datetime.datetime.fromisoformat(self.end_str[0:-1])
        self.start_jira = self.start.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        self.end_jira = self.end.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        self.description = None
        self.issue_id = None
        self.claim_status = -1

        if 'summary' not in entry:
            return

        jira_match = JIRA_PATTERN_NAME.search(entry['summary'])

        if not jira_match:
            print(f"ERROR! Invalid entry: {entry['summary']}")

            return

        self.description = jira_match.group(2).strip()
        self.issue_id = jira_match.group(1)

    @property
    def duration_in_hours(self):
        return self.duration_in_seconds / 3600.0

    @property
    def duration_in_seconds(self):
        return (self.end - self.start).seconds

    def print_summary(self):
        fore = ''
        status = None

        if self.claim_status == 0:
            status = "ERROR"
            fore = Fore.RED
        elif self.claim_status == 1:
            status = "SKIP"
            fore = Fore.YELLOW
        elif self.claim_status == 2:
            status = "ADD"
            fore = Fore.GREEN

        print(fore + f'{status + ": " if status else ""}[{self.issue_id}] hours={self.duration_in_hours}, description={self.description}, started={self.start_str}' + Style.RESET_ALL)

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value
        self.entry['summary'] = self._summary
