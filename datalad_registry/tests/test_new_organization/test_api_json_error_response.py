# This file defines tests that ensure all errors in requests to a path
# starting with "/api/" are expressed in a JSON response.

import pytest


class TestAPIJSONErrorResponse:
    @pytest.mark.parametrize(
        "path",
        [
            # Paths that lead to a 404 error because no route matches
            "/api/",
            "/api/haha/world",
            "/api/haha/world/",
            # Paths that lead to a 404 because a 404 error is raised in a view function
            "/api/v1/url-metadata/1",
            "/api/v1/url-metadata/20",
        ],
    )
    def test_404_json_response_in_api_path(self, flask_client, path):
        """
        Test that a 404 error in an API path returns a JSON response
        """
        resp = flask_client.get(path)
        assert resp.status_code == 404
        assert resp.headers["Content-Type"] == "application/json"

        resp_json = resp.get_json()
        assert resp_json["code"] == 404
        assert resp_json["name"] == "Not Found"
        assert "description" in resp_json

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/url-metadata/1",
            "/api/v1/url-metadata/20",
        ],
    )
    def test_405_json_response_in_api_path(self, flask_client, path):
        """
        Test that a 405 error in an API path returns a JSON response
        """
        resp = flask_client.patch(path)
        assert resp.status_code == 405
        assert resp.headers["Content-Type"] == "application/json"

        resp_json = resp.get_json()
        assert resp_json["code"] == 405
        assert resp_json["name"] == "Method Not Allowed"
        assert "description" in resp_json

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/url-metadata/1",
            "/api/v1/url-metadata/33",
            "/api/v1/url-metadata/42",
        ],
    )
    def test_500_json_response_in_api_path(
        self, flask_app, flask_client, monkeypatch, path
    ):
        """
        Test that a 500 error in an API path returns a JSON response
        """
        from datalad_registry.models import db

        # Make sure unhandled exceptions are converted to 500 errors
        if "TESTING" in flask_app.config:
            monkeypatch.setitem(flask_app.config, "TESTING", False)
            flask_app.config["TESTING"] = False
        if "DEBUG" in flask_app.config:
            monkeypatch.setitem(flask_app.config, "DEBUG", False)

        def mock_get_or_404(*args, **kwargs):  # noqa U100 (Unused argument)
            raise RuntimeError("Mocked error")

        monkeypatch.setattr(db, "get_or_404", mock_get_or_404)

        resp = flask_client.get(path)
        assert resp.status_code == 500
        assert resp.headers["Content-Type"] == "application/json"

        resp_json = resp.get_json()
        assert resp_json["code"] == 500
        assert resp_json["name"] == "Internal Server Error"
        assert "description" in resp_json

    @pytest.mark.parametrize("path", ["/api", "/haha/world", "/haha/world/"])
    def test_html_response_in_non_api_path(self, flask_client, path):
        """
        Test that a non-API path returns an HTML response
        """
        resp = flask_client.get(path)
        assert resp.status_code == 404
        assert resp.headers["Content-Type"] == "text/html; charset=utf-8"
