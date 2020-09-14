import base64
from enum import IntEnum


class InvalidURL(Exception):
    pass


def url_decode(url):
    try:
        return base64.urlsafe_b64decode(url.encode()).decode()
    except (base64.binascii.Error, UnicodeDecodeError):
        raise InvalidURL


def url_encode(url):
    return base64.urlsafe_b64encode(url.encode()).decode()


class TokenStatus(IntEnum):
    REQUESTED = 0
    STAGED = 1
    VERIFIED = 2
    FAILED = 3
    NOTNEEDED = 4
