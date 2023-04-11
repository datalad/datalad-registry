import pytest

from datalad_registry.blueprints.api.dataset_urls import DatasetURLRespModel


@pytest.fixture
def populate_with_2_dataset_urls(flask_app):
    """
    Populate the url table with 2 URLs, at position 1 and 3.
    """
    from datalad_registry.models import URL, db

    dataset_url1 = URL(url="https://example.com")
    dataset_url2 = URL(url="https://www.google.com")
    dataset_url3 = URL(url="/foo/bar")

    with flask_app.app_context():
        for url in [dataset_url1, dataset_url2, dataset_url3]:
            db.session.add(url)
        db.session.commit()

        db.session.delete(dataset_url2)
        db.session.commit()


class TestCreateDatasetURL:
    def test_without_body(self, flask_client):
        resp = flask_client.post("/api/v2/dataset-urls")
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "request_json_body",
        [
            {},
            {"url": ""},
            {"url": "hehe"},
            {"url": "haha/hehe"},
            {"url": "www.example.com"},
        ],
    )
    def test_invalid_body(self, flask_client, request_json_body):
        resp = flask_client.post("/api/v2/dataset-urls", json=request_json_body)
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "request_json_body",
        [{"url": "https://example.com"}, {"url": "/hehe"}, {"url": "/haha/hehe"}],
    )
    def test_valid_body(self, flask_client, request_json_body):
        resp = flask_client.post("/api/v2/dataset-urls", json=request_json_body)
        assert resp.status_code == 201

        resp_json_body = resp.json

        # Ensure the keys of the JSON body of the response are the field names of
        # DatasetURLRespModel
        model_field_names = set(
            DatasetURLRespModel.schema(by_alias=False)["properties"]
        )
        resp_json_body_keys = set(resp_json_body)
        assert resp_json_body_keys == model_field_names

        # Ensure the `processed` field is the default value of False
        assert not resp_json_body["processed"]


class TestDatasetURLs:
    pass


@pytest.mark.usefixtures("populate_with_2_dataset_urls")
class TestDatasetURL:
    @pytest.mark.parametrize("dataset_url_id", [-100, -1, 0, 2, 60, 71, 100])
    def test_invalid_id(self, flask_client, dataset_url_id):
        resp = flask_client.get(f"/api/v2/dataset-urls/{dataset_url_id}")
        assert resp.status_code == 404

    @pytest.mark.parametrize(
        "dataset_url_id, url", [(1, "https://example.com"), (3, "/foo/bar")]
    )
    def test_valid_id(self, flask_client, dataset_url_id, url):
        resp = flask_client.get(f"/api/v2/dataset-urls/{dataset_url_id}")
        assert resp.status_code == 200

        resp_json_body = resp.json

        # Ensure the keys of the JSON body of the response are the field names of
        # DatasetURLRespModel
        model_field_names = set(
            DatasetURLRespModel.schema(by_alias=False)["properties"]
        )
        resp_json_body_keys = set(resp_json_body)
        assert resp_json_body_keys == model_field_names

        # Ensure the correct URL is fetched
        assert resp_json_body["url"] == url
