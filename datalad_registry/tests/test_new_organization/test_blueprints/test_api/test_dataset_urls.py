from datetime import datetime
from typing import Optional

import pytest
from yarl import URL as YURL

from datalad_registry.blueprints.api.dataset_urls import DatasetURLRespModel
from datalad_registry.blueprints.api.dataset_urls.models import (
    DatasetURLPage,
    MetadataReturnOption,
)
from datalad_registry.blueprints.api.url_metadata.models import (
    URLMetadataModel,
    URLMetadataRef,
)
from datalad_registry.models import URL, URLMetadata, db


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
def populate_with_dataset_urls(flask_app) -> list[str]:
    """
    Populate the url table with a list of URLs.

    Returns: The list of URLs that were added to the database
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

        return [url.url for url in urls]


@pytest.fixture
def populate_with_url_metadata(
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
            extracted_metadata=dict(c=3, d=4),
            url_id=1,
        ),
        URLMetadata(
            dataset_describe="1234",
            dataset_version="1.0.0",
            extractor_name="metalad_studyminimet",
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
            extracted_metadata=dict(c=3, d=4),
            url_id=3,
        ),
    ]

    with flask_app.app_context():
        for metadata in metadata_lst:
            db.session.add(metadata)
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

        # Ensure the response body is valid
        DatasetURLRespModel.parse_raw(resp.text)

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
            {"return_metadata": "all"},
            {"page": 0},
            {"page": -1},
            {"page": -100},
            {"page": "a"},
            {"per_page": 0},
            {"per_page": -1},
            {"per_page": -100},
            {"per_page": "b"},
            {"order_by": "abc"},
            {"order_dir": "def"},
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
            {"return_metadata": None},
            {"return_metadata": MetadataReturnOption.reference.value},
            {"return_metadata": MetadataReturnOption.content.value},
            {"page": 1},
            {"per_page": 10},
            {"per_page": 100},
            {"order_by": "url"},
            {"order_by": "annex_key_count"},
            {"order_by": "annexed_files_in_wt_count"},
            {"order_by": "annexed_files_in_wt_size"},
            {"order_by": "last_update"},
            {"order_by": "git_objects_kb"},
            {"order_dir": "asc"},
            {"order_dir": "desc"},
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

        ds_url_page = DatasetURLPage.parse_raw(resp.text)

        assert {i.url for i in ds_url_page.dataset_urls} == expected_output

    @pytest.mark.usefixtures("populate_with_url_metadata")
    @pytest.mark.parametrize(
        "metadata_ret_opt",
        [
            None,
            MetadataReturnOption.reference,
            MetadataReturnOption.content,
        ],
    )
    def test_metadata_return(self, metadata_ret_opt, flask_client):
        """
        Test the return of metadata as a part of the returned list of dataset urls
        """
        if metadata_ret_opt is None:
            query_string = {}
        else:
            query_string = {"return_metadata": metadata_ret_opt.value}

        resp = flask_client.get("/api/v2/dataset-urls", query_string=query_string)

        assert resp.status_code == 200

        resp_json = resp.json
        ds_url_pg = DatasetURLPage.parse_obj(resp_json)

        if metadata_ret_opt is None:
            # === metadata is not returned ===

            assert all("metadata" not in url for url in resp_json["dataset_urls"])
        else:
            # === metadata is returned ===

            if metadata_ret_opt is MetadataReturnOption.reference:
                metadata_ret_type = URLMetadataRef
            else:
                metadata_ret_type = URLMetadataModel

            for url in ds_url_pg.dataset_urls:
                assert type(url.metadata) is list

                if url.id == 1:
                    assert len(url.metadata) == 2
                elif url.id == 3:
                    assert len(url.metadata) == 1
                else:
                    assert len(url.metadata) == 0

                assert all(type(m) is metadata_ret_type for m in url.metadata)

    def test_pagination(self, populate_with_dataset_urls, flask_client):
        """
        Test the pagination of the results
        """

        # For storing all dataset URL obtained from all pages
        ds_urls: set[str] = set()

        # Get the first page
        resp = flask_client.get("/api/v2/dataset-urls", query_string={"per_page": 2})

        assert resp.status_code == 200

        ds_url_pg = DatasetURLPage.parse_raw(resp.text)

        assert ds_url_pg.total == 4
        assert ds_url_pg.cur_pg_num == 1
        assert ds_url_pg.prev_pg is None
        assert ds_url_pg.next_pg is not None

        next_pg_lk, first_pg_lk, last_pg_lk = (
            YURL(pg)
            for pg in (ds_url_pg.next_pg, ds_url_pg.first_pg, ds_url_pg.last_pg)
        )

        # Check page links
        assert next_pg_lk.query["page"] == "2"
        # noinspection DuplicatedCode
        assert first_pg_lk.query["page"] == "1"
        assert last_pg_lk.query["page"] == "2"
        for pg_lk in (next_pg_lk, first_pg_lk, last_pg_lk):
            assert pg_lk.path == "/api/v2/dataset-urls"

            assert len(pg_lk.query) == 4
            assert pg_lk.query["per_page"] == "2"
            assert pg_lk.query["order_by"] == "last_update"
            assert pg_lk.query["order_dir"] == "desc"

        assert len(ds_url_pg.dataset_urls) == 2

        # Gather Dataset URLs from the first page
        for url in ds_url_pg.dataset_urls:
            ds_urls.add(str(url.url))

        # Get the second page
        resp = flask_client.get(ds_url_pg.next_pg)

        assert resp.status_code == 200

        ds_url_pg = DatasetURLPage.parse_raw(resp.text)

        assert ds_url_pg.total == 4
        assert ds_url_pg.cur_pg_num == 2
        assert ds_url_pg.prev_pg is not None
        assert ds_url_pg.next_pg is None

        prev_pg_lk, first_pg_lk, last_pg_lk = (
            YURL(pg)
            for pg in (ds_url_pg.prev_pg, ds_url_pg.first_pg, ds_url_pg.last_pg)
        )

        # Check page links
        assert prev_pg_lk.query["page"] == "1"
        # noinspection DuplicatedCode
        assert first_pg_lk.query["page"] == "1"
        assert last_pg_lk.query["page"] == "2"
        for pg_lk in (prev_pg_lk, first_pg_lk, last_pg_lk):
            assert pg_lk.path == "/api/v2/dataset-urls"

            assert len(pg_lk.query) == 4
            assert pg_lk.query["per_page"] == "2"
            assert pg_lk.query["order_by"] == "last_update"
            assert pg_lk.query["order_dir"] == "desc"

        assert len(ds_url_pg.dataset_urls) == 2

        # Gather Dataset URLs from the second page
        for url in ds_url_pg.dataset_urls:
            ds_urls.add(str(url.url))

        assert ds_urls == set(populate_with_dataset_urls)

    @pytest.mark.usefixtures("populate_with_dataset_urls")
    @pytest.mark.parametrize(
        "query_params, expected_results_by_id_prefix",
        [
            (
                {
                    "order_by": "url",
                    "order_dir": "asc",
                    "per_page": 2,
                },
                [2, 3, 4, 1],
            ),
            (
                {
                    "order_by": "url",
                    "order_dir": "asc",
                    "per_page": 1,
                },
                [2, 3, 4, 1],
            ),
            (
                {
                    "per_page": 3,
                },
                [2, 1, 3, 4],
            ),
            (
                {
                    "order_by": "git_objects_kb",
                    "order_dir": "desc",
                    "per_page": 1,
                },
                [3, 2, 1, 4],
            ),
            (
                {
                    "order_by": "git_objects_kb",
                    "per_page": 1,
                },
                [3, 2, 1, 4],
            ),
            (
                {
                    "order_by": "annex_key_count",
                    "order_dir": "asc",
                    "per_page": 3,
                },
                [1, 2, 3, 4],
            ),
            (
                {
                    "order_by": "annex_key_count",
                    "order_dir": "asc",
                },
                [1, 2, 3, 4],
            ),
        ],
    )
    def test_ordering(self, query_params, expected_results_by_id_prefix, flask_client):
        """
        Test the ordering of the results
        """
        next_pg: Optional[str] = None
        results_by_id = []

        while True:
            if next_pg is None:
                # Get the first page

                resp = flask_client.get(
                    "/api/v2/dataset-urls", query_string=query_params
                )
            else:
                # Get a subsequent page

                resp = flask_client.get(next_pg)

            assert resp.status_code == 200

            ds_url_pg = DatasetURLPage.parse_raw(resp.text)

            results_by_id.extend(url.id for url in ds_url_pg.dataset_urls)

            if ds_url_pg.next_pg is not None:
                # === There is a subsequent page ===
                next_pg = ds_url_pg.next_pg
            else:
                # === There is no subsequent page ===
                break

        assert (
            results_by_id[: len(expected_results_by_id_prefix)]
            == expected_results_by_id_prefix
        )


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

        # Ensure the response body is valid
        ds_url = DatasetURLRespModel.parse_raw(resp.text)

        # Ensure the correct URL is fetched
        assert str(ds_url.url) == url
