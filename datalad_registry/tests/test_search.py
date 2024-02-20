import pytest

from ..search import parser


def test_search_errors():
    with pytest.assert_raises(ValueError):
        parser.parse("unknown_field:example")


def test_search_complex():
    query = r"""((jim AND NOT haxby AND "important\" paper") OR ds_id:~"^000[3-9]..$" OR url:"example.com") AND metadata:non AND metadata[ex1,ex2]:"specific data" AND metadata[extractor2]:data"""
    r = parser.parse(query)
    print(r)