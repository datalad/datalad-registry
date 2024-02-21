import pytest

from datalad_registry.models import RepoUrl, URLMetadata, db

from ..search import parser


def test_search_errors():
    with pytest.raises(ValueError):
        parser.parse("unknown_field:example")


@pytest.fixture
def populate_with_url_metadata_for_search(
    populate_with_dataset_urls,  # noqa: U100 (unused argument)
    flask_app,
):
    """
    Populate the url_metadata table with a list of metadata
    """
    metadata_lst = [
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_core",
            extractor_version="0.14.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(meta1="meta3value", meta2="meta4value"),
            url_id=1,
        ),
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_studyminimeta",
            extractor_version="0.1.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(c=3, d=4),
            url_id=1,
        ),
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_core",
            extractor_version="0.14.0",
            extraction_parameter=dict(a=1, b=2),
            extracted_metadata=dict(meta1="meta1value", meta2="meta2value"),
            url_id=2,
        ),
    ]

    with flask_app.app_context():
        for metadata in metadata_lst:
            db.session.add(metadata)
        db.session.commit()


@pytest.mark.usefixtures("populate_with_url_metadata_for_search")
@pytest.mark.parametrize(
    "query, expected",
    [
        # based purely on url field
        ("example", [1]),
        ("example OR handbook", [1, 3]),
        # case insensitive
        ("Example OR handBook", [1, 3]),
        ("example AND handbook", []),
        ("datalad OR handbook", [2, 3]),
        ("datalad AND handbook", [3]),
        ("handbook datalad", [3]),  # should be identical result to above AND
        ("handbook url:datalad", [3]),
        ("handbook ds_id:datalad", []),
        ("handbook OR ds_id:datalad", [3]),
        ("url:handbook OR ds_id:datalad", [3]),
        ("url:handbook OR ds_id:844c", [1, 2, 3]),
        ("(url:handbook OR metadata[metalad_core]:meta1value) AND ds_id:844c", [2, 3]),
        ("(url:handbook OR metadata[metalad_core]:meta3value) AND ds_id:844C", [1, 3]),
        ("(url:handbook OR metadata[metalad_core]:value) AND ds_id:844c", [1, 2, 3]),
        ("meta2value", [2]),
        ('metadata:"value"', [1, 2]),
        ('metadata[metalad_studyminimeta]:"value"', []),
        # ATM only exact match for extractor
        ('metadata[metalad]:"value"', []),
        ('metadata[metalad_core]:"value"', [1, 2]),
        # OR among multiple listed, ok to have unknown
        ('metadata[metalad_core,metalad_studyminimeta,unknown]:"value"', [1, 2]),
        # Prototypical query for which we do not have full support yet, e.g.
        # regex matching :~
        #  (r"""((jim AND NOT haxby AND "important\" paper") OR ds_id:~"^000[3-9]..$"
        #   OR url:"example.com") AND metadata:non AND metadata[ex1,ex2]:"specific data"
        #   AND metadata[extractor2]:data""", []),
        # Find datasets with the last
        #  (metadata[bids_dataset][Authors][-1]:haxby ...)
    ],
)
def test_search_complex_smoke(flask_app, query, expected):
    r = parser.parse(query)
    # print(f"QUERY {query}: {r}")
    with flask_app.app_context():
        result = db.session.query(RepoUrl).filter(r)
        hits = [_.id for _ in result.all()]
        # print(expected, hits)
        assert hits == expected
