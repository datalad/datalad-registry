import base64
from enum import IntEnum


def url_decode(url):
    return base64.urlsafe_b64decode(url.encode()).decode()


def url_encode(url):
    return base64.urlsafe_b64encode(url.encode()).decode()


class TokenStatus(IntEnum):
    REQUESTED = 0
    STAGED = 1
    VERIFIED = 2
    FAILED = 3
    NOTNEEDED = 4
