import calendar
import sys
from datetime import datetime

import click

from claimer.cal import Calendar
from claimer.issuetracker import IssueTracker
from claimer.report import print_weekly_summary


def get_default_from():
    first_dom = 1

    return datetime.today().replace(day=first_dom).strftime('%d-%m-%Y')


def get_default_to():
    today = datetime.today()
    last_dom = calendar.monthrange(today.year, today.month)[1]

    return datetime.today().replace(day=last_dom).strftime('%d-%m-%Y')


def validate_date(*args):
    value = args[2]
    date_fmt = '%d-%m-%Y'
    try:
        return datetime.strptime(value, date_fmt)
    except ValueError as exc:
        raise click.BadParameter(f"format must be '{date_fmt}'") from exc


@click.command()
@click.option(
    '--from-date', help='Date from.', required=False, show_default=True, default=get_default_from,
    callback=validate_date
)
@click.option(
    '--to-date', help='Date to.', required=False, show_default=True, default=get_default_to,
    callback=validate_date
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

    from_date = datetime.strptime(from_date, '%d-%m-%Y')
    to_date = datetime.strptime(to_date, '%d-%m-%Y')

    calendar_entries = Calendar(calendar_name).get_entries(from_date, to_date)

    if weeklyreport:
        print_weekly_summary(calendar_entries)

    if not dryrun:
        IssueTracker().add_worklog(calendar_entries)
