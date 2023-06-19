from typing import Optional

from bs4 import BeautifulSoup
import pytest


class TestOverView:
    @pytest.mark.usefixtures("populate_with_dataset_urls")
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

    @pytest.mark.usefixtures("populate_with_dataset_urls")
    @pytest.mark.parametrize(
        "filter_by, expected_results",
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
        ],
    )
    def test_filter(
        self, filter_by: Optional[str], expected_results: list[str], flask_client
    ):
        """
        Test for the filtering of dataset URLs in the overview page
        """

        resp = flask_client.get("/overview/", query_string={"filter": filter_by})

        soup = BeautifulSoup(resp.text, "html.parser")

        url_list = [row.td.a.string for row in soup.body.table.find_all("tr")[1:]]

        assert url_list == expected_results

    def test_pagination(self):
        pass

    def test_metadata(self):
        """
        Test for the present of metadata in the overview page
        """
        pass
