import trafaret as t
from trafaret import DataError


def _check_return(value, trafaret):
    try:
        return trafaret.check_and_return(value)
    except DataError:
        return None


def is_email(value):
    try:
        t.Email(value)
    except DataError:
        return False
    return True


def to_number(value):
    return _check_return(value, t.ToFloat())
