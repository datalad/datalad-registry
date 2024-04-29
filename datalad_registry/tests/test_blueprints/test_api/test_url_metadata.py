import pytest

from datalad_registry.blueprints.api.url_metadata import URLMetadataModel


@pytest.fixture
def populate_with_metadata(flask_app):
    from datalad_registry.models import RepoUrl, URLMetadata, db

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


class TestURLMetadata:
    @pytest.mark.parametrize("url_metadata_id", [1, 2, 3, 60, 71, 100])
    def test_not_found(self, flask_client, url_metadata_id):
        with flask_client:
            resp = flask_client.get(f"/api/v2/url-metadata/{url_metadata_id}")
            assert resp.status_code == 404

    @pytest.mark.usefixtures("populate_with_metadata")
    @pytest.mark.parametrize(
        "url_metadata_id, expected_metadata",
        [
            (
                1,
                URLMetadataModel(
                    dataset_describe="abc",
                    dataset_version="cde",
                    extractor_name="complete-imagination",
                    extractor_version="0.1.0",
                    extraction_parameter={"a": 1, "b": 2},
                    extracted_metadata={"brave": "new world", "apple": "1984"},
                ),
            ),
            (
                2,
                URLMetadataModel(
                    dataset_describe="foo",
                    dataset_version="bar",
                    extractor_name="baz",
                    extractor_version="1.0.0",
                    extraction_parameter={"x": 10, "y": 20},
                    extracted_metadata=["a", 1, {"year": 1984}],
                ),
            ),
        ],
    )
    def test_found(self, url_metadata_id, expected_metadata, flask_client):
        resp = flask_client.get(f"/api/v2/url-metadata/{url_metadata_id}")

        assert resp.status_code == 200

        returned_metadata = URLMetadataModel.parse_obj(resp.json)

        assert returned_metadata == expected_metadata
