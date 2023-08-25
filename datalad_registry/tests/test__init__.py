from pathlib import Path

from celery import Celery
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import pytest

import datalad_registry
from datalad_registry import create_app
from datalad_registry.conf import BaseConfig, OperationMode


class TestCreateApp:
    @pytest.mark.parametrize(
        ("op_mode", "instance_path", "cache_path", "broker_url", "result_backend"),
        [
            ("PRODUCTION", "/a/b", "/c/d", "redis://localhost", "redis://localhost"),
            ("DEVELOPMENT", "/a", "/", "redis://localhost", "redis://localhost"),
            ("TESTING", "/a/b/c", "/c/d/", "redis://localhost", "redis://localhost"),
            ("READ_ONLY", "/ab", "/cd", "redis://localhost", "redis://localhost"),
        ],
    )
    def test_configuration(
        self,
        op_mode,
        instance_path,
        cache_path,
        broker_url,
        result_backend,
        monkeypatch,
    ):
        """
        Verify configuration is correctly passed to the Flask app and the Celery app
        """

        default_beat_schedule = {
            "url-check-dispatcher": {
                "task": "datalad_registry.tasks.url_chk_dispatcher",
                "schedule": 60.0,
            }
        }

        default_metadata_extractors = [
            "metalad_core",
            "metalad_studyminimeta",
            "datacite_gin",
            "bids_dataset",
        ]

        def mock_compile_config_from_env(*_args, **_kwargs):
            # noinspection PyTypeChecker
            return BaseConfig(
                DATALAD_REGISTRY_OPERATION_MODE=op_mode,
                DATALAD_REGISTRY_INSTANCE_PATH=instance_path,
                DATALAD_REGISTRY_DATASET_CACHE=cache_path,
                CELERY_BROKER_URL=broker_url,
                CELERY_RESULT_BACKEND=result_backend,
                SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
            )

        def dummy_func(*_args, **_kwargs) -> None:
            return None

        # Monkeypatch `compile_config_from_env` to control the "input" configuration
        monkeypatch.setattr(
            datalad_registry, "compile_config_from_env", mock_compile_config_from_env
        )

        # Disable `Path.mkdir()` to skip the instance path creation
        monkeypatch.setattr(Path, "mkdir", dummy_func)

        # Disable `SQLAlchemy.init_app()` to skip the database integration
        monkeypatch.setattr(SQLAlchemy, "init_app", dummy_func)

        # Disable `Migrate.init_app()` to skip the database migration integration
        monkeypatch.setattr(Migrate, "init_app", dummy_func)

        # Verify the loading of configuration to the Flask app
        flask_app = create_app()
        assert flask_app.config["DATALAD_REGISTRY_OPERATION_MODE"] is OperationMode(
            op_mode
        )
        assert flask_app.config["DATALAD_REGISTRY_INSTANCE_PATH"] == Path(instance_path)
        assert flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"] == Path(cache_path)
        assert flask_app.config["DATALAD_REGISTRY_MIN_CHK_INTERVAL_PER_URL"] == 3600
        assert flask_app.config["DATALAD_REGISTRY_MAX_FAILED_CHKS_PER_URL"] == 10
        assert flask_app.config["DATALAD_REGISTRY_MAX_URL_CHKS_IN_PROGRESS"] == 10
        assert (
            flask_app.config["DATALAD_REGISTRY_METADATA_EXTRACTORS"]
            == default_metadata_extractors
        )
        assert flask_app.config["CELERY_BROKER_URL"] == broker_url
        assert flask_app.config["CELERY_RESULT_BACKEND"] == result_backend
        assert flask_app.config["CELERY_BEAT_SCHEDULE"] == default_beat_schedule
        assert flask_app.config["CELERY"] == {
            "broker_url": broker_url,
            "result_backend": result_backend,
            "beat_schedule": default_beat_schedule,
            "task_ignore_result": True,
            "worker_max_tasks_per_child": 1000,
            "worker_max_memory_per_child": 500_000,  # 500 MB
        }
        assert (
            flask_app.config["SQLALCHEMY_DATABASE_URI"]
            == "postgresql+psycopg2://usr:pd@db:5432/dbn"
        )
        assert flask_app.config["TESTING"] is False

        # Verify the loading of configuration to the Celery app
        celery_app: Celery = flask_app.extensions["celery"]
        assert celery_app.conf["broker_url"] == broker_url
        assert celery_app.conf["result_backend"] == result_backend
        assert celery_app.conf["beat_schedule"] == default_beat_schedule
        assert celery_app.conf["task_ignore_result"] is True
