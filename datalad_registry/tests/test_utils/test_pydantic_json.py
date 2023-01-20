from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel, validate_arguments
import pytest

from datalad_registry.utils.pydantic_json import (
    pydantic_model_dumps,
    pydantic_model_loads,
)

# ==== Test for handling standard types =======================================
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
def test_standard_types(test_input, expected_output):
    assert pydantic_model_loads(pydantic_model_dumps(test_input)) == expected_output


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
    assert (
        process_func(pydantic_model_loads(pydantic_model_dumps(test_input)))
        == expected_output
    )


# ==== Test for handling unsupported types ====================================
@dataclass
class DataclassUser:
    id: int
    name = "Jane Doe"


def test_unsupported_types():
    with pytest.raises(TypeError):
        pydantic_model_dumps(DataclassUser(id=1))
