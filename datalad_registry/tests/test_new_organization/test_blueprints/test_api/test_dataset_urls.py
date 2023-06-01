from datetime import datetime

import pytest

from datalad_registry.blueprints.api.dataset_urls import DatasetURLRespModel
from datalad_registry.models import URL, db


@pytest.fixture
def populate_with_2_dataset_urls(flask_app):
    """
    Populate the url table with 2 URLs, at position 1 and 3.
    """

    dataset_url1 = URL(url="https://example.com")
    dataset_url2 = URL(url="https://docs.datalad.org")
    dataset_url3 = URL(url="/foo/bar")

    with flask_app.app_context():
        for url in [dataset_url1, dataset_url2, dataset_url3]:
            db.session.add(url)
        db.session.commit()

        db.session.delete(dataset_url2)
        db.session.commit()


@pytest.fixture
def populate_with_dataset_urls(flask_app):
    """
    Populate the url table with a list of URLs.
    """

    urls = [
        URL(
            url="https://www.example.com",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7b",
            head_describe="1234",
            annex_key_count=20,
            annexed_files_in_wt_count=200,
            annexed_files_in_wt_size=1000,
            git_objects_kb=110,
            info_ts=datetime(2008, 7, 18, 18, 34, 32),
            processed=True,
            cache_path="8c8/fff/e01f2142d88690d92144b00af0",
        ),
        URL(
            url="http://www.datalad.org",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7c",
            head_describe="1234",
            annex_key_count=40,
            annexed_files_in_wt_count=100,
            annexed_files_in_wt_size=400,
            git_objects_kb=1100,
            info_ts=datetime(2009, 6, 18, 18, 34, 32),
            processed=True,
            cache_path="72e/cd9/cc10534e2a9f551e32119e0e60",
        ),
        URL(
            url="https://handbook.datalad.org",
            ds_id="2a0b7b7b-a984-4c4a-844c-be3132291a7c",
            head_describe="1234",
            annex_key_count=90,
            annexed_files_in_wt_count=490,
            annexed_files_in_wt_size=1000_000,
            git_objects_kb=4000,
            info_ts=datetime(2004, 6, 18, 18, 34, 32),
            processed=True,
            cache_path="72e/4e5/4184da47e282c02ae7e568ba74",
        ),
        URL(
            url="https://www.dandiarchive.org",
            processed=False,
            cache_path="a/b/c",
        ),
    ]

    with flask_app.app_context():
        for url in urls:
            db.session.add(url)
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

    @pytest.mark.usefixtures("populate_with_2_dataset_urls")
    @pytest.mark.parametrize(
        "request_json_body", [{"url": "https://example.com"}, {"url": "/foo/bar"}]
    )
    def test_resubmission(self, flask_client, request_json_body):
        """
        Test resubmitting URLs that already exist in the database
        """
        resp = flask_client.post("/api/v2/dataset-urls", json=request_json_body)
        assert resp.status_code == 409


class TestDatasetURLs:
    @pytest.mark.parametrize(
        "query_params",
        [
            {"url": "www.example.com"},
            {"ds_id": "34"},
            {"min_annex_key_count": "ab"},
            {"max_annex_key_count": "bc"},
            {"min_annexed_files_in_wt_count": "cd"},
            {"max_annexed_files_in_wt_count": "def"},
            {"min_annexed_files_in_wt_size": "efg"},
            {"max_annexed_files_in_wt_size": "hij"},
            {"earliest_last_update": "jkl"},
            {"latest_last_update": "klm"},
            {"min_git_objects_kb": "lmn"},
            {"max_git_objects_kb": "mno"},
            {"processed": "nop"},
        ],
    )
    def test_invalid_query_params(self, flask_client, query_params):
        resp = flask_client.get("/api/v2/dataset-urls", query_string=query_params)
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "query_params",
        [
            {"url": "https://www.example.com"},
            {"ds_id": "2a0b7b7b-a984-4c4a-844c-be3132291d7b"},
            {"min_annex_key_count": "1"},
            {"max_annex_key_count": 2},
            {"min_annexed_files_in_wt_count": 200},
            {"max_annexed_files_in_wt_count": "40"},
            {"min_annexed_files_in_wt_size": 33},
            {"max_annexed_files_in_wt_size": 21},
            {"earliest_last_update": 656409661000},
            {"latest_last_update": "2001-03-22T01:22:34"},
            {"min_git_objects_kb": 40},
            {"max_git_objects_kb": "100"},
            {"processed": True},
        ],
    )
    def test_valid_query_params(self, flask_client, query_params):
        resp = flask_client.get("/api/v2/dataset-urls", query_string=query_params)
        assert resp.status_code == 200

    @pytest.mark.usefixtures("populate_with_dataset_urls")
    @pytest.mark.parametrize(
        "query_params, expected_output",
        [
            (
                {},
                {
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                },
            ),
            ({"url": "https://www.example.com"}, {"https://www.example.com"}),
            (
                {"ds_id": "2a0b7b7b-a984-4c4a-844c-be3132291d7c"},
                {"http://www.datalad.org"},
            ),
            (
                {"min_annex_key_count": "39"},
                {"http://www.datalad.org", "https://handbook.datalad.org"},
            ),
            (
                {"min_annex_key_count": "39", "max_annex_key_count": 40},
                {"http://www.datalad.org"},
            ),
            (
                {
                    "min_annexed_files_in_wt_count": 190,
                    "max_annexed_files_in_wt_count": 500,
                },
                {"https://www.example.com", "https://handbook.datalad.org"},
            ),
            ({"min_annexed_files_in_wt_size": 1000_001}, set()),
            ({"max_annexed_files_in_wt_size": 500}, {"http://www.datalad.org"}),
            (
                {"max_annexed_files_in_wt_size": 2000},
                {"https://www.example.com", "http://www.datalad.org"},
            ),
            (
                {
                    "min_annexed_files_in_wt_size": 300,
                    "max_annexed_files_in_wt_size": 2200,
                },
                {"https://www.example.com", "http://www.datalad.org"},
            ),
            (
                {"earliest_last_update": "2001-03-22T01:22:34"},
                {
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                },
            ),
            (
                {
                    "earliest_last_update": "2007-03-22T01:22:34",
                    "latest_last_update": "2009-03-22T01:22:34",
                },
                {"https://www.example.com"},
            ),
            (
                {"min_git_objects_kb": 1000, "max_git_objects_kb": 2000},
                {"http://www.datalad.org"},
            ),
            (
                {"processed": True},
                {
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                },
            ),
            ({"processed": False}, {"https://www.dandiarchive.org"}),
            (
                {"min_annex_key_count": "39", "max_annexed_files_in_wt_size": 2200},
                {"http://www.datalad.org"},
            ),
            # === filtered by cache_path ===
            (
                {"cache_path": "8c8/fff/e01f2142d88690d92144b00af0"},
                {"https://www.example.com"},
            ),
            (
                {"cache_path": "8c8/fff/e01f2142d88690d92144b00af0/"},
                {"https://www.example.com"},
            ),
            (
                {"cache_path": "8c8/fff/e01f2142d88690d92144b00af0//"},
                {"https://www.example.com"},
            ),
            (
                {"cache_path": "/a/c/8c8/fff/e01f2142d88690d92144b00af0"},
                {"https://www.example.com"},
            ),
            (
                {"cache_path": "/8c8/fff/e01f2142d88690d92144b00af0"},
                {"https://www.example.com"},
            ),
            (
                {"cache_path": "a/c/8c8/fff/e01f2142d88690d92144b00af0"},
                set(),
            ),
            (
                {"cache_path": "72e/4e5/4184da47e282c02ae7e568ba74"},
                {"https://handbook.datalad.org"},
            ),
            (
                {"cache_path": "a/b/c"},
                {"https://www.dandiarchive.org"},
            ),
        ],
    )
    def test_filter(self, flask_client, query_params, expected_output):
        resp = flask_client.get("/api/v2/dataset-urls", query_string=query_params)
        assert resp.status_code == 200

        resp_json_body: list = resp.json

        assert {i["url"] for i in resp_json_body} == expected_output


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
