from datetime import datetime

import click


def get_default_from() -> str:
    """Returns first day of current month"""
    first_dom = 1

    return datetime.today().replace(day=first_dom).strftime('%d-%m-%Y')


def get_default_to() -> str:
    """Returns today"""
    return datetime.today().strftime('%d-%m-%Y')


def validate_date(*args) -> datetime:
    value = args[2]
    date_fmt = '%d-%m-%Y'
    try:
        return datetime.strptime(value, date_fmt)
    except ValueError as exc:
        raise click.BadParameter(f"format must be '{date_fmt}'") from exc
