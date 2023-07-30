from pathlib import Path

from pydantic import ValidationError
import pytest

from datalad_registry.conf import BaseConfig, OperationMode


class TestBaseConfig:
    @pytest.mark.parametrize(
        "instance_path, cache_path", [("/a/b", "/c/d"), ("/", "/e")]
    )
    def test_absolute_paths(self, instance_path: str, cache_path: str, monkeypatch):
        """
        Test instantiation of `BaseConfig` when the environment variables
        `DATALAD_REGISTRY_INSTANCE_PATH` and `DATALAD_REGISTRY_DATASET_CACHE`
        are set to absolute paths
        """
        monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", instance_path)
        monkeypatch.setenv("DATALAD_REGISTRY_DATASET_CACHE", cache_path)

        config = BaseConfig(
            DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
            CELERY_BROKER_URL="redis://localhost",
            CELERY_RESULT_BACKEND="redis://localhost",
            CELERY_TASK_IGNORE_RESULT=True,
        )

        assert config.DATALAD_REGISTRY_INSTANCE_PATH == Path(instance_path)
        assert config.DATALAD_REGISTRY_DATASET_CACHE == Path(cache_path)

    @pytest.mark.parametrize(
        "instance_path, cache_path",
        [
            ("a/b", "/c/d"),
            ("/a/b", "c/d"),
            ("a/b", "c/d"),
            ("a", "/a"),
            ("/b", "b"),
        ],
    )
    def test_relative_paths(self, instance_path: str, cache_path: str, monkeypatch):
        """
        Test instantiation of `BaseConfig` when the environment variable
        `DATALAD_REGISTRY_INSTANCE_PATH` or `DATALAD_REGISTRY_DATASET_CACHE`
        is set to a relative path
        """
        monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", instance_path)
        monkeypatch.setenv("DATALAD_REGISTRY_DATASET_CACHE", cache_path)

        with pytest.raises(ValidationError):
            BaseConfig(
                DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                CELERY_TASK_IGNORE_RESULT=True,
            )
