import argparse
import calendar
import sys
from datetime import datetime

from cal import Calendar
from issuetracker import IssueTracker
from report import print_weekly_summary


def main():

    (
        str_date_from,
        str_date_to,
        calendar_name,
        is_dryrun,
        is_weeklyreport,
        _,
        list_calendars,
        list_week,
    ) = parse_cmd_arguments()

    if list_calendars:
        Calendar.get_calendars()
        sys.exit()

    if list_week:
        Calendar(calendar_name).get_week_entries()
        sys.exit()

    date_from = datetime.strptime(str_date_from, '%d-%m-%Y')
    date_to = datetime.strptime(str_date_to, '%d-%m-%Y')

    calendar_entries = Calendar(calendar_name).get_entries(date_from, date_to)

    if is_weeklyreport:
        print_weekly_summary(calendar_entries)

    if not is_dryrun:
        IssueTracker().add_worklog(calendar_entries)


def parse_cmd_arguments():
    today = datetime.today()
    first_dom = 1
    last_dom = calendar.monthrange(today.year, today.month)[1]

    # python coordinador.py --from 31-01-2023 --dryrun
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        '--from',
        dest='datefrom',
        default=datetime.today().replace(day=first_dom).strftime('%d-%m-%Y'),
    )
    arg_parser.add_argument(
        '--to', dest='dateto', default=datetime.today().replace(day=last_dom).strftime('%d-%m-%Y')
    )
    arg_parser.add_argument('--calendar', dest='calendar_name', default='Jira')
    arg_parser.add_argument('--dryrun', action='store_true')
    arg_parser.add_argument('--weeklyreport', action='store_true')
    arg_parser.add_argument('--listcalendars', action='store_true', dest='list_calendars')
    arg_parser.add_argument('--listweek', action='store_true', dest='list_week')
    arg_parser.add_argument('positionals', nargs='*')

    args = arg_parser.parse_args()

    return (
        args.datefrom,
        args.dateto,
        args.calendar_name,
        args.dryrun,
        args.weeklyreport,
        args.positionals,
        args.list_calendars,
        args.list_week,
    )


if __name__ == '__main__':
    main()
