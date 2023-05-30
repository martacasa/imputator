import calendar
from datetime import datetime


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


