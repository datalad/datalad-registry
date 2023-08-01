from pathlib import Path

from pydantic import ValidationError
import pytest

from datalad_registry.conf import (
    BaseConfig,
    DevelopmentConfig,
    OperationMode,
    ProductionConfig,
    ReadOnlyConfig,
)
from datalad_registry.conf import (
    TestingConfig as _TestingConfig,  # Requires name transformation because of pytest
)
from datalad_registry.conf import compile_config_from_env


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

    @pytest.mark.parametrize(
        "broker_url, result_backend, task_ignore_result, expected_broker_url",
        [
            ("redis://localhost", "redis://127.0.0.1", "True", "redis://localhost"),
            ("redis://broker", "redis://new", "1", "redis://broker"),
            (
                '["redis://localhost", "redis://broker"]',
                "redis://127.0.0.1",
                "True",
                ["redis://localhost", "redis://broker"],
            ),
        ],
    )
    def test_celery(
        self,
        broker_url,
        result_backend,
        task_ignore_result,
        expected_broker_url,
        monkeypatch,
    ):
        monkeypatch.setenv("CELERY_BROKER_URL", broker_url)
        monkeypatch.setenv("CELERY_RESULT_BACKEND", result_backend)
        monkeypatch.setenv("CELERY_TASK_IGNORE_RESULT", task_ignore_result)

        assert BaseConfig(
            DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
            DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
            DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
        ).CELERY == dict(
            broker_url=expected_broker_url,
            result_backend=result_backend,
            task_ignore_result=True,
        )


class TestUpperLevelConfigs:
    @pytest.mark.parametrize(
        "config_cls, operation_mode",
        [
            (ProductionConfig, "PRODUCTION"),
            (DevelopmentConfig, "DEVELOPMENT"),
            (_TestingConfig, "TESTING"),
            (ReadOnlyConfig, "READ_ONLY"),
        ],
    )
    def test_operation_mode_restriction_met(
        self, config_cls, operation_mode, monkeypatch
    ):
        # Initialize the config with init kwargs alone
        config = config_cls(
            DATALAD_REGISTRY_OPERATION_MODE=OperationMode(operation_mode),
            DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
            DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
            CELERY_BROKER_URL="redis://localhost",
            CELERY_RESULT_BACKEND="redis://localhost",
            CELERY_TASK_IGNORE_RESULT=True,
        )
        assert config.DATALAD_REGISTRY_OPERATION_MODE is OperationMode(operation_mode)

        # Initialize the config with both init kwargs and environment variables
        with monkeypatch.context() as m:
            m.setenv("DATALAD_REGISTRY_OPERATION_MODE", operation_mode)
            config = config_cls(
                DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                CELERY_TASK_IGNORE_RESULT=True,
            )
        assert config.DATALAD_REGISTRY_OPERATION_MODE is OperationMode(operation_mode)

    @pytest.mark.parametrize(
        "config_cls, operation_mode",
        [
            (ProductionConfig, "DEVELOPMENT"),
            (DevelopmentConfig, "PRODUCTION"),
            (_TestingConfig, "READ_ONLY"),
            (ReadOnlyConfig, "TESTING"),
        ],
    )
    def test_operation_mode_restriction_not_met(
        self, config_cls, operation_mode, monkeypatch
    ):
        # Initialize the config with init kwargs alone
        with pytest.raises(ValidationError):
            config_cls(
                DATALAD_REGISTRY_OPERATION_MODE=OperationMode(operation_mode),
                DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                CELERY_TASK_IGNORE_RESULT=True,
            )

        # Initialize the config with both init kwargs and environment variables
        with monkeypatch.context() as m:
            m.setenv("DATALAD_REGISTRY_OPERATION_MODE", operation_mode)
            with pytest.raises(ValidationError):
                config_cls(
                    DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                    DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                    CELERY_BROKER_URL="redis://localhost",
                    CELERY_RESULT_BACKEND="redis://localhost",
                    CELERY_TASK_IGNORE_RESULT=True,
                )


class TestCompileConfigFromEnv:
    @pytest.mark.parametrize(
        (
            "op_mode",
            "instance_path",
            "cache_path",
            "broker_url",
            "result_backend",
            "task_ignore_result",
            "config_cls",
        ),
        [
            (
                "PRODUCTION",
                "/a/b",
                "/c/d",
                "redis://localhost",
                "redis://localhost",
                "True",
                ProductionConfig,
            ),
            (
                "DEVELOPMENT",
                "/a",
                "/",
                "redis://localhost",
                "redis://localhost",
                "1",
                DevelopmentConfig,
            ),
            (
                "TESTING",
                "/a/b/c",
                "/c/d/",
                "redis://localhost",
                "redis://localhost",
                "Yes",
                _TestingConfig,
            ),
            (
                "READ_ONLY",
                "/ab",
                "/cd",
                "redis://localhost",
                "redis://localhost",
                "True",
                ReadOnlyConfig,
            ),
        ],
    )
    def test_valid_env(
        self,
        op_mode,
        instance_path,
        cache_path,
        broker_url,
        result_backend,
        task_ignore_result,
        config_cls,
        monkeypatch,
    ):
        """
        Test the case that the environment contains all the required variables
        with valid values
        """

        monkeypatch.setenv("DATALAD_REGISTRY_OPERATION_MODE", op_mode)
        monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", instance_path)
        monkeypatch.setenv("DATALAD_REGISTRY_DATASET_CACHE", cache_path)
        monkeypatch.setenv("CELERY_BROKER_URL", broker_url)
        monkeypatch.setenv("CELERY_RESULT_BACKEND", result_backend)
        monkeypatch.setenv("CELERY_TASK_IGNORE_RESULT", task_ignore_result)

        config = compile_config_from_env()

        assert config.DATALAD_REGISTRY_OPERATION_MODE == OperationMode(op_mode)
        assert config.DATALAD_REGISTRY_INSTANCE_PATH == Path(instance_path)
        assert config.DATALAD_REGISTRY_DATASET_CACHE == Path(cache_path)
        assert config.CELERY_BROKER_URL == broker_url
        assert config.CELERY_RESULT_BACKEND == result_backend
        assert config.CELERY_TASK_IGNORE_RESULT
        assert isinstance(config, config_cls)

    def test_invalid_op_mode(self, monkeypatch):
        """
        Test the case that the operation mode fetched from the environment is one
        that is not valid, one that is not mapped to a config class.
        """
        monkeypatch.setenv("DATALAD_REGISTRY_OPERATION_MODE", "DEVELOPMENT")
        monkeypatch.setenv("DATALAD_REGISTRY_INSTANCE_PATH", "/a/b")
        monkeypatch.setenv("DATALAD_REGISTRY_DATASET_CACHE", "/c/d")
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost")
        monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://localhost")
        monkeypatch.setenv("CELERY_TASK_IGNORE_RESULT", "True")

        class MockOperationModeToConfigCls:
            # noinspection PyMethodMayBeStatic
            def get(self, *_args, **_kwargs):
                return None

        from datalad_registry import conf

        monkeypatch.setattr(
            conf, "operation_mode_to_config_cls", MockOperationModeToConfigCls()
        )

        with pytest.raises(ValueError):
            compile_config_from_env()
