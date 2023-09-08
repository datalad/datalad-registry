from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, validate_arguments
import pytest

from datalad_registry.utils.pydantic_json import pydantic_dumps, pydantic_loads

# ==== Test for handling basic types =======================================
d = {"a": 1, "b": 2}
lst = [1, 2, 3]
t = (1, 2, 3)
s = "Hello, world!"
i = 42
f = 3.14
b = True
n = None


@pytest.mark.parametrize(
    "test_input, expected_output",
    [
        (d, d),
        (lst, lst),
        (t, list(t)),
        (s, s),
        (i, i),
        (f, f),
        (b, b),
        (n, n),
    ],
)
def test_basic_types(test_input, expected_output):
    assert pydantic_loads(pydantic_dumps(test_input)) == expected_output


# ===== Test for supported complex standard types ============================
@validate_arguments
def return_datetime(dt: datetime) -> datetime:
    return dt


@validate_arguments
def return_decimal(dec: Decimal) -> Decimal:
    return dec


@validate_arguments
def return_path(pth: Path) -> Path:
    return pth


@validate_arguments
def return_uuid(uid: UUID) -> UUID:
    return uid


@dataclass
class FooData:
    a: int
    b: str


@validate_arguments
def return_foo_data(fd: FooData) -> FooData:
    return fd


@pytest.mark.parametrize(
    "io_put, process_func",
    [
        (
            datetime(
                year=1999,
                month=12,
                day=13,
                hour=11,
                minute=30,
                second=44,
                microsecond=14983,
                tzinfo=timezone.utc,
            ),
            return_datetime,
        ),
        (Decimal("499.543"), return_decimal),
        (Path("/the/middle/path"), return_path),
        (UUID("c55f3251-54eb-4961-be58-0c2d2d24dc24"), return_uuid),
        (FooData(a=1, b="foo"), return_foo_data),
    ],
)
def test_supported_complex_standard_types(io_put, process_func):
    assert process_func(pydantic_loads(pydantic_dumps(io_put))) == io_put


# ==== Test for handling pydantic model types =================================
class User(BaseModel):
    id: int
    name = "Jane Doe"


class Foo(BaseModel):
    count: int
    size: Optional[float] = None


class Bar(BaseModel):
    apple = "x"
    banana = "y"


class Spam(BaseModel):
    foo: Foo
    bars: List[Bar]


user = User(id=1)
spam = Spam(foo=Foo(count=4), bars=[Bar(apple="x1"), Bar(apple="x2")])
user_lst = [user] * 42
spam_lst = [spam] * 6


@validate_arguments
def return_user(u: User) -> User:
    return u


@validate_arguments
def return_spam(spm: Spam) -> Spam:
    return spm


@validate_arguments
def return_list_of_users(user_list: List[User]) -> List[User]:
    return user_list


@validate_arguments
def return_list_of_spams(spam_list: List[Spam]) -> List[Spam]:
    return spam_list


@pytest.mark.parametrize(
    "test_input, expected_output, process_func",
    [
        (user, user, return_user),
        (spam, spam, return_spam),
        (user_lst, user_lst, return_list_of_users),
        (spam_lst, spam_lst, return_list_of_spams),
    ],
)
def test_pydantic_model_types(test_input, expected_output, process_func):
    assert process_func(pydantic_loads(pydantic_dumps(test_input))) == expected_output


# ==== Test for handling unsupported types ====================================


def test_unsupported_types():
    with pytest.raises(TypeError):
        pydantic_dumps(return_datetime)
