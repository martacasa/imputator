import argparse
import re
import sys

import arrow
from colorama import Back
from colorama import Fore
from colorama import init
from colorama import Style
from dateutil import parser
from jira import JIRA
from jira import JIRAError

import config
from cal import get_calendar_from_name
from cal import get_jiras


def print_daily_summary(calendar_entries):
    sorted_entries = sorted(calendar_entries, key=lambda i: i['start'])
    last_day = None
    last_week = None
    l_stop = None
    for calendar_entry in sorted_entries:
        start = arrow.get(calendar_entry['start'])
        stop = arrow.get(calendar_entry['stop'])

        # Check if new week header is needed.
        _, week, _ = start.isocalendar()
        if not last_week or last_week != week:
            # Print new week header
            last_week = week
            print(f"-- Week: {week} ----------------------------------------------")

        # Check if new day header is needed.
        day = start.format("dddd YYYY-MM-DD")
        if not last_day or last_day != day:
            # Print new day header
            last_day = day
            print(f"\t{day}")
            l_stop = None

        t_start = start.format("HH:mm")
        t_stop = stop.format("HH:mm")

        if l_stop and l_stop != t_start:
            # There is a hole
            issue_id = "--- Empty ---"
            print(f'\t\t{l_stop:<5}->{t_start:<5} {issue_id: <15}')

        l_stop = t_stop
        issue_id = calendar_entry['issue_id']
        duration_in_hours = (stop - start).seconds / 3600.0
        print(f'\t\t{t_start:<5}->{t_stop:<5} {issue_id: <15} ... {duration_in_hours:>6} h')


def print_weekly_summary(calendar_entries):
    weeks = {}
    sorted_entries = sorted(calendar_entries, key=lambda i: i['start'])
    for calendar_entry in sorted_entries:
        start = arrow.get(calendar_entry['start'])
        stop = arrow.get(calendar_entry['stop'])
        issue_id = calendar_entry['issue_id']
        duration_in_hours = (stop - start).seconds / 3600.0
        week_number = start.isocalendar()[1]
        if week_number not in weeks:
            weeks[week_number] = {}

        weeks[week_number][issue_id] = (
            duration_in_hours
            if issue_id not in weeks[week_number]
            else weeks[week_number][issue_id] + duration_in_hours
        )

    for week in weeks:
        print(f'Week number {week}')
        print('-------------------------')
        total_time_in_week = 0
        for issue_id in weeks[week]:
            time_spent_in_issue = weeks[week][issue_id]
            total_time_in_week = total_time_in_week + time_spent_in_issue
            print(f'{issue_id: <15} ... {time_spent_in_issue:>6} h')
        print(f'Total time in week {total_time_in_week}')
        print(f'Target time in week {40*.6}')
        print(f'Balance {total_time_in_week - 40*.6}')
        print('')


def main():
    init()
    # print('Argument List:', str(sys.argv))

    srt_date_from, calendar_name, is_dryrun, is_weeklyreport, positionals = parse_cmd_arguments()

    date_from = parser.parse(srt_date_from)

    jira_ms = connect_jira(config.server, config.user_jira, config.pass_jira)

    jira_calendar = get_calendar_from_name(calendar_name)
    entries_calendar = get_jiras(date_from, jira_calendar)

    # print_daily_summary(entries_calendar)
    if is_weeklyreport:
        print_weekly_summary(entries_calendar)

    if not is_dryrun:
        add_jira_worklog(entries_calendar, jira_ms)


def add_jira_worklog(entries_calendar, jira_ms):
    for i in entries_calendar:
        if 'description' not in i or 'issue_id' not in i:
            print(
                ('{} - {} : ' + Back.RED + 'No descripcion' + Style.RESET_ALL).format(
                    i['start'], i['stop']
                )
            )
            continue
        issue_id = re.compile('[0-9A-Z]+-[0-9]+').search(i['issue_id'])

        if issue_id:
            issue_code = issue_id.group(0)
            try:
                jira = jira_ms
                worklogs = jira.worklogs(issue_code)
            except JIRAError as e:
                import ipdb
                ipdb.set_trace()
                print(
                    (Fore.RED + 'ERROR: Jira code {} : from {}' + Style.RESET_ALL).format(
                        issue_code, i['description']
                    )
                )
                continue

            worklogs_starts = []
            try:
                for wl in [
                    wl.started for wl in worklogs if hasattr(wl.author, 'emailAddress') and wl.author.emailAddress == config.user_jira
                ]:
                    worklogs_starts.append(arrow.get(wl))
            except Exception as e:
                import ipdb
                ipdb.set_trace()
                print(
                    (Fore.RED + 'ERROR: Jira code {} : from {}' + Style.RESET_ALL).format(
                        issue_code, i['description']
                    )
                )
                continue

            if not arrow.get(i['start']) in worklogs_starts:
                print(
                    ('ADD: {} - {} : ' + Fore.GREEN + ' {} ' + Style.RESET_ALL).format(
                        i['start'], i['stop'], i['description']
                    )
                )
                issue = issue_code
                duration_in_seconds = (arrow.get(i['stop']) - arrow.get(i['start'])).seconds
                description = i['description'].strip()
                started = arrow.get(i['start'])
                print(
                    'Adding worklog {}, seconds={}, description=[{}] {}, started={}'.format(
                        issue, duration_in_seconds, issue_code, description, started
                    )
                )
                try:
                    jira.add_worklog(
                        issue,
                        None,
                        duration_in_seconds,
                        None,
                        None,
                        None,
                        description,
                        started.to('utc'),
                        jira.current_user(),
                    )
                except JIRAError as e:
                    print(
                        ('ERROR: {} - {} : ' + Fore.RED + '[{}] {} ' + Style.RESET_ALL).format(
                            i['start'], i['stop'], issue_code, i['description']
                        )
                    )
                    if e.status_code == '400':
                        print(Back.RED + Fore.WHITE + 'Sin permisos' + Style.RESET_ALL)
                    else:
                        print(Back.RED + Fore.WHITE + 'Error desconocido' + Style.RESET_ALL)
                    continue
            else:
                print(
                    ('SKIP: {} - {} : ' + Fore.YELLOW + '[{}] {} ' + Style.RESET_ALL).format(
                        i['start'], i['stop'], issue_code, i['description']
                    )
                )

        else:
            print(
                ('{} - {} : ' + Fore.RED + ' {} ' + Style.RESET_ALL).format(
                    i['start'], i['stop'], i['description']
                )
            )


def parse_cmd_arguments():
    p = argparse.ArgumentParser()
    p.add_argument('--from', dest='datefrom', default=None)
    p.add_argument('--calendar', dest='calendar_name', default='Jira')
    p.add_argument('--dryrun', action='store_true')
    p.add_argument('--weeklyreport', action='store_true')
    p.add_argument('positionals', nargs='*')

    args = p.parse_args()
    return args.datefrom, args.calendar_name, args.dryrun, args.weeklyreport, args.positionals


def connect_jira(server, user_jira, pass_jira):
    options = {'server': server}
    return JIRA(options=options, basic_auth=(user_jira, pass_jira))


if __name__ == '__main__':
    main()
