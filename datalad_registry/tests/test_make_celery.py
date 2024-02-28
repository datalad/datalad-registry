import logging

from celery import Celery
import pytest


@pytest.mark.usefixtures("set_test_env")
def test_celery_app_instantiation():
    """
    Test that the Celery app is instantiated correctly.
    """
    from datalad_registry.make_celery import celery_app, flask_app

    assert celery_app is flask_app.extensions["celery"]
    assert isinstance(celery_app, Celery)


class TestSuppressKnownGitProgressReport:
    # Set needed environment to instantiate a flask app in datalad_registry.make_celery
    @pytest.mark.usefixtures("set_test_env")
    @pytest.mark.parametrize(
        "msg, expected_result",
        [
            ("hello", True),
            ("Start receiving objects", True),
            ("Start counting objects", True),
            (
                "Failed to get 'sourcedata/templateflow/tpl-NKI.path', "
                "skipping this submodule",
                True,
            ),
            (
                "Failed to get 'sourcedata/templateflow/tpl-WHS.path', "
                "skipping this submodule",
                True,
            ),
            ("Finished enumerating objects", True),
            ("Finished compressing objects", True),
            ("Resolving deltas:  65% (19502/30003)", False),
            ("Receiving objects:   2% (8943/447132)", False),
            ("Receiving objects:  57% (194348/340960), 9.80 MiB | 9.79 MiB/s", False),
            ("remote: Compressing objects: 100% (111150/111150), done.", False),
            ("remote: Compressing objects:  89% (98924/111150)", False),
            ("Resolving deltas:  90% (27003/30003)", False),
        ],
    )
    def test_filter(self, msg, expected_result):
        """
        Test the filter method of the SuppressKnownGitProgressReport class
        """
        from datalad_registry.make_celery import SuppressKnownGitProgressReport

        record = logging.LogRecord(
            name="logger",
            level=logging.DEBUG,
            pathname="",
            lineno=1,
            msg=msg,
            args=(),
            exc_info=None,
        )

        assert SuppressKnownGitProgressReport().filter(record) is expected_result
