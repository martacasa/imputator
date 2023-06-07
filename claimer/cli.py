import sys
from datetime import datetime

import click

from claimer.cal import Calendar
from claimer.helper import get_default_from, get_default_to, validate_date
from claimer.issuetracker import IssueTracker
from claimer.report import print_weekly_summary


@click.command()
@click.option(
    '--from',
    'from_date',
    help='Date from. Defaults to first day of current month',
    required=False,
    show_default=True,
    default=get_default_from,
    callback=validate_date,
)
@click.option(
    '--to',
    'to_date',
    help='Date to. Defaults to today',
    required=False,
    show_default=True,
    default=get_default_to,
    callback=validate_date,
)
@click.option(
    '--calendar-name',
    help='Google Calendar\'s name.',
    required=False,
    show_default=True,
    default='Jira',
)
@click.option('--dryrun', help='Dry run.', is_flag=True)
@click.option('--weeklyreport', help='Weekly report.', is_flag=True)
@click.option('--listcalendars', help='List calendars.', is_flag=True)
@click.option('--listweek', help='List week.', is_flag=True)
def cli(
    from_date: datetime,
    to_date: datetime,
    calendar_name: str,
    dryrun: bool,
    weeklyreport: bool,
    listcalendars: bool,
    listweek: bool,
):
    if listcalendars:
        Calendar.get_calendars()
        sys.exit()

    if listweek:
        Calendar(calendar_name).get_week_entries()
        sys.exit()

    calendar_entries = Calendar(calendar_name).get_entries(from_date, to_date)

    if weeklyreport:
        print_weekly_summary(calendar_entries)

    if not dryrun:
        IssueTracker().add_worklog(calendar_entries)
