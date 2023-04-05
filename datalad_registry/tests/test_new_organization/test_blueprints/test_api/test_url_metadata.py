import pytest

from datalad_registry.com_models import URLMetadataModel


@pytest.fixture
def populate_with_metadata(flask_app):
    from datalad_registry.models import URL, URLMetadata, db

    url = URL(url="https://example.com")
    url_metadata = URLMetadata(
        dataset_describe="abc",
        dataset_version="cde",
        extractor_name="complete-imagination",
        extractor_version="0.1.0",
        extraction_parameter={"a": 1, "b": 2},
        extracted_metadata={"brave": "new world", "apple": "1984"},
        url=url,
    )

    with flask_app.app_context():
        db.session.add(url)
        db.session.add(url_metadata)
        db.session.commit()


class TestURLMetadata:
    @pytest.mark.parametrize("url_metadata_id", [1, 2, 3, 60, 71, 100])
    def test_not_found(self, flask_client, url_metadata_id):
        with flask_client:
            resp = flask_client.get(f"/api/v2/url-metadata/{url_metadata_id}")
            assert resp.status_code == 404

    @pytest.mark.usefixtures("populate_with_metadata")
    def test_found(self, flask_client):
        resp = flask_client.get("/api/v2/url-metadata/1")

        assert resp.status_code == 200

        returned_metadata = URLMetadataModel.parse_obj(resp.json)
        expected_metadata = URLMetadataModel(
            dataset_describe="abc",
            dataset_version="cde",
            extractor_name="complete-imagination",
            extractor_version="0.1.0",
            extraction_parameter={"a": 1, "b": 2},
            extracted_metadata={"brave": "new world", "apple": "1984"},
        )

        assert returned_metadata == expected_metadata
