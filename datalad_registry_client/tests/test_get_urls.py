from datetime import datetime, timezone
from itertools import chain

import datalad.api as dl
from datalad.support.exceptions import IncompleteResultsError
from multidict import MultiDict
import pytest
import requests
from yarl import URL

from datalad_registry.blueprints.api.dataset_urls.models import (
    AnnexDsCollectionStats,
    CollectionStats,
    DataladDsCollectionStats,
    DatasetURLPage,
    DatasetURLRespModel,
    NonAnnexDsCollectionStats,
    StatsSummary,
)
from datalad_registry_client import DEFAULT_BASE_ENDPOINT


class MockResponse:
    """
    Custom class used to mock the response object returned by
    requests' Session.get() method
    """

    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


dataset_url_resp_model_template = dict(
    id=2,
    ds_id="2a0b7b7b-a984-4c4a-844c-be3132291d7b",
    describe="1234",
    annex_key_count=30,
    annexed_files_in_wt_count=45,
    annexed_files_in_wt_size=100,
    last_update=datetime(2008, 7, 18, 18, 34, 32, tzinfo=timezone.utc),
    last_chk_dt=datetime(2004, 6, 18, 18, 33, 7, tzinfo=timezone.utc),
    git_objects_kb=1200,
    processed=True,
    metadata=[],
)

# A dummy `AnnexDsCollectionStats` object
annex_ds_collection_stats = AnnexDsCollectionStats(
    ds_count=101, annexed_files_size=1900, annexed_file_count=42
)
# A dummy `CollectionStats` object
collection_stats = CollectionStats(
    datalad_ds_stats=DataladDsCollectionStats(
        unique_ds_stats=annex_ds_collection_stats, stats=annex_ds_collection_stats
    ),
    pure_annex_ds_stats=annex_ds_collection_stats,
    non_annex_ds_stats=NonAnnexDsCollectionStats(ds_count=40),
    summary=StatsSummary(unique_ds_count=101, ds_count=999),
)


def test_register():
    """
    Test that `registry_get_urls` is registered with DataLad
    """
    import datalad.api as ds

    assert hasattr(ds, "registry_get_urls")


class TestRegistryGetURLs:
    @pytest.mark.parametrize(
        "base_endpoint, endpoint",
        [
            (None, DEFAULT_BASE_ENDPOINT + "/dataset-urls"),
            (
                "http://127.0.0.1:5000/api/v2",
                "http://127.0.0.1:5000/api/v2/dataset-urls",
            ),
            (
                "http://127.0.0.1:5000/api/v2/",
                "http://127.0.0.1:5000/api/v2/dataset-urls",
            ),
            ("http://127.0.0.1:5000/api///", "http://127.0.0.1:5000/api/dataset-urls"),
        ],
    )
    def test_endpoint_construction(self, base_endpoint, endpoint, monkeypatch):
        """
        Verify the correctness of the endpoint construction.
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            requested_endpoint = str(URL(url).with_query({}))
            if requested_endpoint == endpoint:
                # noinspection PyTypeChecker
                return MockResponse(
                    200,
                    DatasetURLPage(
                        total=200,
                        cur_pg_num=1,
                        prev_pg="dummy",
                        next_pg=None,
                        first_pg="dummy",
                        last_pg="dummy",
                        dataset_urls=[
                            DatasetURLRespModel(
                                **dataset_url_resp_model_template,
                                url="https://www.example.com"
                            )
                        ],
                        collection_stats=collection_stats,
                    ).json(exclude_none=True),
                )
            else:
                return MockResponse(404, "Not Found")

        monkeypatch.setattr(requests.Session, "get", mock_get)

        if base_endpoint is not None:
            res = dl.registry_get_urls(cache_path="a/b/c", base_endpoint=base_endpoint)
        else:
            res = dl.registry_get_urls()

        assert len(res) == 1
        assert res[0]["status"] == "ok"

    @pytest.mark.parametrize(
        "cache_path",
        [
            "a/b/c",
            "/a/b/c/",
            "/a/b/c///",
            "8f7/834/cd26484ce78ece48ef811268e2",
            "/8f7/834/cd26484ce78ece48ef811268e2/",
            "/cache/98e/f22/a2d0d240f8a11936e8686ce1ed",
        ],
    )
    def test_query_construction(self, cache_path, monkeypatch):
        """
        Verify the correctness of the query construction
        in requests to the server
        """

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            if URL(url).query == MultiDict(cache_path=cache_path):
                # noinspection PyTypeChecker
                return MockResponse(
                    200,
                    DatasetURLPage(
                        total=100,
                        cur_pg_num=1,
                        prev_pg="dummy",
                        next_pg=None,
                        first_pg="dummy",
                        last_pg="dummy",
                        dataset_urls=[
                            DatasetURLRespModel(
                                **dataset_url_resp_model_template,
                                url="https://www.example.com"
                            )
                        ],
                        collection_stats=collection_stats,
                    ).json(exclude_none=True),
                )
            else:
                return MockResponse(404, "Not Found")

        monkeypatch.setattr(requests.Session, "get", mock_get)

        res = dl.registry_get_urls(cache_path=cache_path)

        assert len(res) == 1
        assert res[0]["status"] == "ok"

    @pytest.mark.parametrize(
        "resp_pgs",
        [
            [["https://www.example.com"]],
            [
                ["https://www.example.com", "https://centerforopenneuroscience.org/"],
                ["https://www.datalad.org/"],
            ],
        ],
    )
    def test_handle_successful_response(self, resp_pgs: list[list[str]], monkeypatch):
        """
        Test handling of a successful response from the server
        """

        def ds_url_pgs():
            total = sum(len(pg) for pg in resp_pgs)

            for i, pg in enumerate(resp_pgs):
                # noinspection PyTypeChecker
                yield DatasetURLPage(
                    total=total,
                    cur_pg_num=i + 1,
                    prev_pg=None if i == 0 else "foo",
                    next_pg=None if i == len(resp_pgs) - 1 else "foo",
                    first_pg="foo",
                    last_pg="bar",
                    dataset_urls=[
                        DatasetURLRespModel(**dataset_url_resp_model_template, url=url)
                        for url in pg
                    ],
                    collection_stats=collection_stats,
                )

        ds_url_pgs_iter = ds_url_pgs()

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            # noinspection PyTypeChecker
            return MockResponse(
                200,
                next(ds_url_pgs_iter).json(exclude_none=True),
            )

        monkeypatch.setattr(requests.Session, "get", mock_get)

        res = dl.registry_get_urls(cache_path="a/b/c")

        assert len(res) == 1
        assert res[0]["status"] == "ok"
        assert str(list(chain(*resp_pgs))) in res[0]["message"]
        assert "error_message" not in res[0]

    @pytest.mark.parametrize(
        "ok_resp_num, ending_status_code, msg_content",
        [
            (0, 400, "Server HTTP response code"),
            (0, 404, "Incorrect target URL"),
            (0, 422, "Unprocessable argument"),
            (0, 500, "Server error"),
            (1, 400, "Server HTTP response code"),
            (2, 404, "Incorrect target URL"),
            (3, 422, "Unprocessable argument"),
            (4, 500, "Server error"),
        ],
    )
    def test_handle_error_response(
        self, ok_resp_num, ending_status_code, msg_content, monkeypatch
    ):
        """
        Test handling of an error response from the server

        :param ok_resp_num: The number of successful responses from the server before
                            the ending error response
        :param ending_status_code: The HTTP status code of the ending error response
                                   from the server
        :param msg_content: Content contained in the message generated by the client
        """

        def mock_responses():
            for i in range(ok_resp_num):
                # noinspection PyTypeChecker
                yield MockResponse(
                    200,
                    DatasetURLPage(
                        total=200,
                        cur_pg_num=i + 1,
                        prev_pg=None if i == 0 else "foo",
                        next_pg="bar",
                        first_pg="dummy",
                        last_pg="dummy",
                        dataset_urls=[
                            DatasetURLRespModel(
                                **dataset_url_resp_model_template,
                                url="https://www.example.com"
                            )
                        ],
                        collection_stats=collection_stats,
                    ).json(exclude_none=True),
                )

        mock_resp_iter = mock_responses()

        # noinspection PyUnusedLocal
        def mock_get(s, url):  # noqa: U100 Unused argument
            try:
                mock_resp = next(mock_resp_iter)
            except StopIteration:
                mock_resp = MockResponse(ending_status_code, "")

            return mock_resp

        monkeypatch.setattr(requests.Session, "get", mock_get)

        with pytest.raises(IncompleteResultsError, match=msg_content) as exc_info:
            dl.registry_get_urls(cache_path="/a/b/c")

        assert len(exc_info.value.failed) == 1
        assert exc_info.value.failed[0]["status"] == "error"
        assert msg_content in exc_info.value.failed[0]["error_message"]
        assert "message" not in exc_info.value.failed[0]
