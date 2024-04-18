from typing import Optional

from bs4 import BeautifulSoup
import pytest
from yarl import URL as YURL


class TestOverView:
    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize(
        "sort_by, expected_order",
        [
            (
                None,
                [
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "keys-asc",
                [
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "keys-desc",
                [
                    "https://handbook.datalad.org",
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "update-asc",
                [
                    "https://handbook.datalad.org",
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "update-desc",
                [
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "url-asc",
                [
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                    "https://www.example.com",
                ],
            ),
            (
                "url-desc",
                [
                    "https://www.example.com",
                    "https://www.dandiarchive.org",
                    "https://handbook.datalad.org",
                    "http://www.datalad.org",
                ],
            ),
            (
                "annexed_files_in_wt_count-asc",
                [
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "annexed_files_in_wt_count-desc",
                [
                    "https://handbook.datalad.org",
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "annexed_files_in_wt_size-asc",
                [
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "annexed_files_in_wt_size-desc",
                [
                    "https://handbook.datalad.org",
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "git_objects_kb-asc",
                [
                    "https://www.example.com",
                    "http://www.datalad.org",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            (
                "git_objects_kb-desc",
                [
                    "https://handbook.datalad.org",
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://www.dandiarchive.org",
                ],
            ),
        ],
    )
    def test_sorting(
        self, sort_by: Optional[str], expected_order: list[str], flask_client
    ):
        """
        Test for the sorting of dataset URLs in the overview page
        """
        resp = flask_client.get("/overview/", query_string={"sort": sort_by})

        soup = BeautifulSoup(resp.text, "html.parser")

        url_list = [row.td.a.string for row in soup.body.table.find_all("tr")[1:]]

        assert url_list == expected_order

    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize(
        "search_query, expected_results",
        [
            (
                None,
                [
                    "http://www.datalad.org",
                    "https://www.example.com",
                    "https://handbook.datalad.org",
                    "https://www.dandiarchive.org",
                ],
            ),
            ("exa", ["https://www.example.com"]),
            # we support advanced search language now
            (
                "example OR handbook",
                ["https://www.example.com", "https://handbook.datalad.org"],
            ),
            ("datalad AND handbook", ["https://handbook.datalad.org"]),
        ],
    )
    def test_search_with_valid_query(
        self, search_query: Optional[str], expected_results: list[str], flask_client
    ):
        """
        Test searching with a valid query
        """

        resp = flask_client.get("/overview/", query_string={"query": search_query})

        soup = BeautifulSoup(resp.text, "html.parser")

        url_list = [row.td.a.string for row in soup.body.table.find_all("tr")[1:]]

        assert url_list == expected_results

    @pytest.mark.usefixtures("populate_with_std_ds_urls")
    @pytest.mark.parametrize(
        "search_query, err_msg_prefix",
        [
            ("unknown_field:example", "Unknown field: 'unknown_field'. Known are:"),
            ("", "Query string cannot be empty"),
            ("  \t \n", "Query string cannot contain only whitespace"),
            (" ", "Query string cannot contain only whitespace"),
            ("     ", "Query string cannot contain only whitespace"),
            ("  \t \n \t   ", "Query string cannot contain only whitespace"),
        ],
    )
    def test_search_with_invalid_query(
        self, search_query: str, err_msg_prefix: str, flask_client
    ):
        """
        Test searching with an invalid query
        """

        resp = flask_client.get("/overview/", query_string={"query": search_query})

        soup = BeautifulSoup(resp.text, "html.parser")

        assert (error_span := soup.find("span", class_="error"))
        assert error_span.text.startswith(f"ERROR: {err_msg_prefix}")

    def test_pagination(self, populate_with_std_ds_urls, flask_client):
        """
        Test pagination in Web UI
        """

        # For storing all URLs obtained from all pages
        ds_urls: set[str] = set()

        # === Get the first page ===
        resp = flask_client.get("/overview/", query_string={"per_page": 2})

        # noinspection DuplicatedCode
        assert resp.status_code == 200

        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all dataset URLs from the first page
        page_ds_urls = [row.td.a.string for row in soup.body.table.find_all("tr")[1:]]
        assert len(page_ds_urls) == 2

        # Store all dataset URLs from the first page
        for url in page_ds_urls:
            ds_urls.add(url)

        pagination_element = soup.find("div", {"class": "pagination"})
        page_1_element = pagination_element.strong
        page_2_element = pagination_element.a
        page_2_link = YURL(page_2_element["href"])

        assert page_1_element.string == "1"
        assert page_2_element.string == "2"
        assert page_2_link.path == "/overview/"
        assert len(page_2_link.query) == 3
        assert page_2_link.query["page"] == "2"
        assert page_2_link.query["per_page"] == "2"
        assert page_2_link.query["sort"] == "update-desc"

        # === Get the second page ===
        resp = flask_client.get(str(page_2_link))

        # noinspection DuplicatedCode
        assert resp.status_code == 200

        soup = BeautifulSoup(resp.text, "html.parser")

        # Get all dataset URLs from the second page
        page_ds_urls = [row.td.a.string for row in soup.body.table.find_all("tr")[1:]]
        assert len(page_ds_urls) == 2

        # Store all dataset URLs from the second page
        for url in page_ds_urls:
            ds_urls.add(url)

        pagination_element = soup.find("div", {"class": "pagination"})
        page_1_element = pagination_element.a
        page_2_element = pagination_element.strong
        page_1_link = YURL(page_1_element["href"])

        assert page_1_element.string == "1"
        assert page_2_element.string == "2"
        assert page_1_link.path == "/overview/"
        assert len(page_1_link.query) == 3
        assert page_1_link.query["page"] == "1"
        assert page_1_link.query["per_page"] == "2"
        assert page_1_link.query["sort"] == "update-desc"

        assert ds_urls == set(populate_with_std_ds_urls)

    @pytest.mark.usefixtures("populate_with_url_metadata")
    def test_metadata(self, flask_client):
        """
        Test for the present of metadata in the overview page
        """
        resp = flask_client.get("/overview/")

        soup = BeautifulSoup(resp.text, "html.parser")

        metadata_map = {
            row.td.a.string: {
                link.string.strip() for link in row.find_all("td")[-1].find_all("a")
            }
            for row in soup.body.table.find_all("tr")[1:]
        }

        assert metadata_map == {
            "https://www.example.com": {"metalad_core", "metalad_studyminimeta"},
            "http://www.datalad.org": set(),
            "https://handbook.datalad.org": {"metalad_core"},
            "https://www.dandiarchive.org": set(),
        }
