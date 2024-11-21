import datetime
import os.path
import pickle
import re
from enum import Enum
from typing import List

import pytz
from colorama import Fore, Style, init
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery

from claimer.config import CONFIG_DIR

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
]

JIRA_PATTERN_NAME = re.compile('^([A-Z][A-Z0-9]+[-][0-9]+): ?(.*)')

init()

CLAIM_OK = '✅ '
CLAIM_NOK = '❌ '


class ClaimStatus(Enum):
    UNKNOWN = 0
    ERROR = 1
    SKIP = 2
    ADD = 3


FORE_COLOR_STATUS_MAPPING = {
    ClaimStatus.ERROR: Fore.RED,
    ClaimStatus.SKIP: Fore.YELLOW,
    ClaimStatus.ADD: Fore.GREEN,
}


class CalendarEntry:
    def __init__(self, service, calendar_id, **kwargs):
        self.service = service
        self.calendar_id = calendar_id
        self.entry = kwargs
        self.load_input(**kwargs)
        self.load_status(**kwargs)

    def load_input(self, **entry):
        self.entry_id = entry['id']
        self.summary = entry.get('summary', '')
        self.start_str = entry['start'].get('dateTime', entry['start'].get('date'))
        self.end_str = entry['end'].get('dateTime')
        self.start = pytz.UTC.localize(datetime.datetime.fromisoformat(self.start_str[:-1]))
        self.end = pytz.UTC.localize(datetime.datetime.fromisoformat(self.end_str[0:-1]))
        self.description = None
        self.issue_id = None

    def load_status(self, **entry):
        summary = entry['summary']

        self._claim_status = ClaimStatus.UNKNOWN

        if summary.startswith(CLAIM_OK):
            self._claim_status = ClaimStatus.ADD
            summary = summary.replace(CLAIM_OK, '')
        if summary.startswith(CLAIM_NOK):
            summary = summary.replace(CLAIM_NOK, '')

        jira_match = JIRA_PATTERN_NAME.search(summary)

        if not jira_match:
            # Invalid entry
            self.description = summary

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
        fore_color = Style.RESET_ALL
        status = None

        if self.claim_status != ClaimStatus.UNKNOWN:
            fore_color = FORE_COLOR_STATUS_MAPPING[self.claim_status]
            status = self.claim_status.name

        print(
            fore_color
            + f'{status: <6}'
            + f'[ {str(self.issue_id): <14}] '
            + f'{str(self.description)[0:50]: >50} | '
            + f'{self.start.strftime("%Y-%m-%dT%H:%M")} | '
            + f'{self.duration_in_hours: <4}h'
            + Style.RESET_ALL
        )

    @property
    def summary(self):
        return self._summary

    @summary.setter
    def summary(self, value):
        self._summary = value
        self.entry['summary'] = self._summary

    @property
    def claim_status(self):
        return self._claim_status

    @claim_status.setter
    def claim_status(self, value):
        if self._claim_status == value:
            # No change in claim status
            return

        self._claim_status = value
        update_summary = False

        if self._claim_status in (
            ClaimStatus.ADD,
            ClaimStatus.SKIP,
        ) and not self.summary.startswith(CLAIM_OK):
            # TODO gestionar de otra forma
            self.summary = self.summary.replace(CLAIM_NOK, '')
            self.summary = CLAIM_OK + self.summary
            update_summary = True
        elif self._claim_status == ClaimStatus.ERROR and not self.summary.startswith(CLAIM_NOK):
            self.summary = CLAIM_NOK + self.summary
            update_summary = True

        if update_summary:
            self.service.events().update(
                calendarId=self.calendar_id, eventId=self.entry_id, body=self.entry
            ).execute()


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
        ic = list(
            filter(lambda x: x['summary'] == calendar_name, [c for c in calendarlist['items']])
        )

        if not ic:
            raise Exception(f'[ERROR] Calendar {calendar_name} not found!')

        return ic[0]

    @staticmethod
    def _get_service() -> discovery.Resource:
        """The file token.pickle stores the user's access and refresh
        tokens, and is created automatically when the authorization flow
        completes for the first time.
        """
        creds = None

        token_file_path = os.path.join(CONFIG_DIR, 'token.pickle')

        if os.path.exists(token_file_path):
            with open(token_file_path, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let
        # the user log in.

        credentials_file_path = os.path.join(CONFIG_DIR, 'credentials.json')

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open(token_file_path, 'wb') as token:
                pickle.dump(creds, token)

        service = discovery.build('calendar', 'v3', credentials=creds)

        return service

    def get_entries(self, date_from, date_to=None) -> List[CalendarEntry]:
        raw_entries = self._get_raw_entries(date_from, date_to)

        entries = []

        for raw_entry in raw_entries:
            calendar_entry = CalendarEntry(self.service, self.calendar_id, **raw_entry)

            if calendar_entry:
                entries.append(calendar_entry)

        return entries

    def _get_raw_entries(self, date_from, date_to=None, num_entries=1000):
        print(f'JIRAS from {date_from} to {date_to}')
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
