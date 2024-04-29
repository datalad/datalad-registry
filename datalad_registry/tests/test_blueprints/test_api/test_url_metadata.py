import pytest

from datalad_registry.blueprints.api.url_metadata import URLMetadataModel
from datalad_registry.models import RepoUrl, URLMetadata, db


@pytest.fixture
def populated_metadata(flask_app) -> list[URLMetadataModel]:
    """
    Populate the database with URLMetadata instances.

    :return: The list of URLMetadataModel instances representing the URLMetadata
             instances is populated to the database.
    """

    url = RepoUrl(url="https://example.com")

    url_metadata_lst = [
        URLMetadata(
            dataset_describe="abc",
            dataset_version="cde",
            extractor_name="complete-imagination",
            extractor_version="0.1.0",
            extraction_parameter={"a": 1, "b": 2},
            extracted_metadata={"brave": "new world", "apple": "1984"},
            url=url,
        ),
        URLMetadata(
            dataset_describe="foo",
            dataset_version="bar",
            extractor_name="baz",
            extractor_version="1.0.0",
            extraction_parameter={"x": 10, "y": 20},
            extracted_metadata=["a", 1, {"year": 1984}],
            url=url,
        ),
    ]

    with flask_app.app_context():
        db.session.add(url)
        db.session.add_all(url_metadata_lst)
        db.session.commit()

        return [
            URLMetadataModel.from_orm(url_metadata) for url_metadata in url_metadata_lst
        ]


class TestURLMetadata:
    @pytest.mark.parametrize("url_metadata_id", [1, 2, 3, 60, 71, 100])
    def test_not_found(self, flask_client, url_metadata_id):
        with flask_client:
            resp = flask_client.get(f"/api/v2/url-metadata/{url_metadata_id}")
            assert resp.status_code == 404

    @pytest.mark.parametrize("url_metadata_id", [1, 2])
    def test_found(self, url_metadata_id, populated_metadata, flask_client):
        resp = flask_client.get(f"/api/v2/url-metadata/{url_metadata_id}")

        assert resp.status_code == 200

        returned_metadata = URLMetadataModel.parse_obj(resp.json)
        expected_metadata = populated_metadata[url_metadata_id - 1]

        assert returned_metadata == expected_metadata
