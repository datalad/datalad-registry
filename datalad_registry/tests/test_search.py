import pytest

from ..search import parser


def test_search_errors():
    with pytest.raises(ValueError):
        parser.parse("unknown_field:example")


@pytest.mark.parametrize(
    "query",
    [
        "example",
        "example OR another",
        "example AND another",
        "another example", # should be identical result to above AND
        "example AND NOT another",
        "example AND (another OR test)",
        "example AND (another OR test) AND NOT (example OR another)",
        "example AND (another OR test) AND NOT (example OR another) AND another",
        "metadata[ex1,ex2]:\"specific data\"",
        r"""((jim AND NOT haxby AND "important\" paper") OR ds_id:"^000[3-9]..$" OR url:"example.com") AND metadata:non""",
        r"""((jim AND NOT haxby AND "important\" paper") OR ds_id:"^000[3-9]..$" OR url:"example.com") AND metadata:non AND metadata[ex1,ex2]:"specific data" AND metadata[extractor2]:data""",
],
)
def test_search_complex_smoke(query):
    r = parser.parse(query)
    print(f"QUERY {query}: {r}")