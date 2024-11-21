import datetime
from typing import List

import pytz
from colorama import Back, Fore, Style, init
from jira import JIRA, JIRAError

from claimer import config
from claimer.cal import CalendarEntry, ClaimStatus


class IssueTracker:
    def __init__(self):
        init()
        self.jira = self._get_jira_connection(
            config.jira_server, config.jira_user, config.jira_pass
        )

    @staticmethod
    def _get_jira_connection(jira_server, jira_user, jira_pass):
        options = {'server': jira_server}

        return JIRA(options=options, basic_auth=(jira_user, jira_pass))

    def add_worklog(self, entries_calendar: List[CalendarEntry]):
        for entry in entries_calendar:
            self.add_entry(entry)
            entry.print_summary()

    def add_entry(self, entry):
        if not entry.issue_id:
            entry.claim_status = ClaimStatus.ERROR
            return

        try:
            if self.is_entry_already_claimed(entry):
                entry.claim_status = ClaimStatus.SKIP
                return

            self.jira.add_worklog(
                issue=entry.issue_id,
                timeSpentSeconds=entry.duration_in_seconds,
                comment=entry.description,
                started=entry.start.astimezone(pytz.UTC),
                user=self.jira.current_user(),
            )
            entry.claim_status = ClaimStatus.ADD

        except JIRAError as exc:
            entry.claim_status = ClaimStatus.ERROR

            if exc.status_code == '400':
                print(Back.RED + Fore.WHITE + 'JIRA: Sin permisos' + Style.RESET_ALL)
            else:
                print(Back.RED + Fore.WHITE + 'JIRA: Error desconocido' + Style.RESET_ALL)
        except Exception as exc:
            print(Back.RED + Fore.WHITE + 'JIRA: Error' + str(exc) + Style.RESET_ALL)
            entry.claim_status = ClaimStatus.ERROR

    def is_entry_already_claimed(self, entry) -> bool:
        try:
            worklogs = self.jira.worklogs(entry.issue_id)
        except JIRAError:
            print(
                Fore.RED
                + f'ERROR: Invalid JIRA code {entry.issue_id} : from {entry.description}'
                + Style.RESET_ALL
            )
            raise

        worklogs_starts = []
        for worklog in [
            worklog.started
            for worklog in worklogs
            if hasattr(worklog.author, 'emailAddress')
            and worklog.author.emailAddress == config.jira_user
        ]:
            worklogs_starts.append(datetime.datetime.strptime(worklog, '%Y-%m-%dT%H:%M:%S.000%z'))

        return entry.start in worklogs_starts
