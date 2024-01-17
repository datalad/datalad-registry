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

        # noinspection PyTypeChecker
        config = BaseConfig(
            DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
            DATALAD_REGISTRY_WEB_API_URL="http://web/api",
            CELERY_BROKER_URL="redis://localhost",
            CELERY_RESULT_BACKEND="redis://localhost",
            SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
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

        with pytest.raises(ValidationError, match="Path must be absolute"):
            # noinspection PyTypeChecker
            BaseConfig(
                DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
            )

    @pytest.mark.parametrize(
        "dispatch_cycle_length, usage_dashboard_sync_cycle_length, "
        "broker_url, result_backend, expected_broker_url ",
        [
            (
                None,
                "400",
                "redis://localhost",
                "redis://127.0.0.1",
                "redis://localhost",
            ),
            ("10", None, "redis://broker", "redis://new", "redis://broker"),
            (
                "400.0",
                "3600.0",
                '["redis://localhost", "redis://broker"]',
                "redis://127.0.0.1",
                ["redis://localhost", "redis://broker"],
            ),
        ],
    )
    def test_celery(
        self,
        dispatch_cycle_length,
        usage_dashboard_sync_cycle_length,
        broker_url,
        result_backend,
        expected_broker_url,
        monkeypatch,
    ):
        expected_dispatch_cycle_length = (
            float(dispatch_cycle_length) if dispatch_cycle_length is not None else 60.0
        )
        expected_usage_dashboard_sync_cycle_length = (
            float(usage_dashboard_sync_cycle_length)
            if usage_dashboard_sync_cycle_length is not None
            else 60.0 * 60 * 24
        )
        expected_beat_schedule = {
            "url-check-dispatcher": {
                "task": "datalad_registry.tasks.url_chk_dispatcher",
                "schedule": expected_dispatch_cycle_length,
                "options": {"expires": expected_dispatch_cycle_length},
            },
            "usage-dashboard-sync": {
                "task": "datalad_registry.tasks.usage_dashboard_sync",
                "schedule": expected_usage_dashboard_sync_cycle_length,
                "options": {"expires": expected_usage_dashboard_sync_cycle_length},
            },
        }

        if dispatch_cycle_length is not None:
            monkeypatch.setenv(
                "DATALAD_REGISTRY_DISPATCH_CYCLE_LENGTH", dispatch_cycle_length
            )
        if usage_dashboard_sync_cycle_length is not None:
            monkeypatch.setenv(
                "DATALAD_REGISTRY_USAGE_DASHBOARD_SYNC_CYCLE_LENGTH",
                usage_dashboard_sync_cycle_length,
            )
        monkeypatch.setenv("CELERY_BROKER_URL", broker_url)
        monkeypatch.setenv("CELERY_RESULT_BACKEND", result_backend)

        # noinspection PyTypeChecker
        assert BaseConfig(
            DATALAD_REGISTRY_OPERATION_MODE=OperationMode.PRODUCTION,
            DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
            DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
            DATALAD_REGISTRY_WEB_API_URL="http://web/api",
            SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
        ).CELERY == dict(
            broker_url=expected_broker_url,
            result_backend=result_backend,
            beat_schedule=expected_beat_schedule,
            task_ignore_result=True,
            worker_max_tasks_per_child=1000,
            worker_max_memory_per_child=500_000,  # 500 MB
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
            DATALAD_REGISTRY_WEB_API_URL="http://web/api",
            CELERY_BROKER_URL="redis://localhost",
            CELERY_RESULT_BACKEND="redis://localhost",
            SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
        )
        assert config.DATALAD_REGISTRY_OPERATION_MODE is OperationMode(operation_mode)

        # Initialize the config with both init kwargs and environment variables
        with monkeypatch.context() as m:
            m.setenv("DATALAD_REGISTRY_OPERATION_MODE", operation_mode)
            config = config_cls(
                DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                DATALAD_REGISTRY_WEB_API_URL="http://web/api",
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
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
        with pytest.raises(ValidationError, match="DATALAD_REGISTRY_OPERATION_MODE"):
            config_cls(
                DATALAD_REGISTRY_OPERATION_MODE=OperationMode(operation_mode),
                DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                DATALAD_REGISTRY_WEB_API_URL="http://web/api",
                CELERY_BROKER_URL="redis://localhost",
                CELERY_RESULT_BACKEND="redis://localhost",
                SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
            )

        # Initialize the config with both init kwargs and environment variables
        with monkeypatch.context() as m:
            m.setenv("DATALAD_REGISTRY_OPERATION_MODE", operation_mode)
            with pytest.raises(
                ValidationError, match="DATALAD_REGISTRY_OPERATION_MODE"
            ):
                config_cls(
                    DATALAD_REGISTRY_INSTANCE_PATH=Path("/a/b"),
                    DATALAD_REGISTRY_DATASET_CACHE=Path("/a/b"),
                    DATALAD_REGISTRY_WEB_API_URL="http://web/api",
                    CELERY_BROKER_URL="redis://localhost",
                    CELERY_RESULT_BACKEND="redis://localhost",
                    SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://usr:pd@db:5432/dbn",
                )


class TestCompileConfigFromEnv:
    @pytest.mark.parametrize(
        (
            "op_mode",
            "instance_path",
            "cache_path",
            "web_api_url",
            "broker_url",
            "result_backend",
            "sa_db_uri",
            "config_cls",
        ),
        [
            (
                "PRODUCTION",
                "/a/b",
                "/c/d",
                "http://web:5000/api/v2",
                "redis://localhost",
                "redis://localhost",
                "postgresql+psycopg2://user:pd@db:5432/dbn",
                ProductionConfig,
            ),
            (
                "DEVELOPMENT",
                "/a",
                "/",
                "http://web/api/v2",
                "redis://localhost",
                "redis://localhost",
                "postgresql+psycopg2://usr:passd@db:5432/dbn",
                DevelopmentConfig,
            ),
            (
                "TESTING",
                "/a/b/c",
                "/c/d/",
                "http://web",
                "redis://localhost",
                "redis://localhost",
                "postgresql+psycopg2://usr:pd@db:5432/db_name",
                _TestingConfig,
            ),
            (
                "READ_ONLY",
                "/ab",
                "/cd",
                "https://web:5000/api/v2",
                "redis://localhost",
                "redis://localhost",
                "postgresql+psycopg2://usr:pd@db:1111/dbn",
                ReadOnlyConfig,
            ),
        ],
    )
    def test_valid_env(
        self,
        op_mode,
        instance_path,
        cache_path,
        web_api_url,
        broker_url,
        result_backend,
        sa_db_uri,
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
        monkeypatch.setenv("DATALAD_REGISTRY_WEB_API_URL", web_api_url)
        monkeypatch.setenv("CELERY_BROKER_URL", broker_url)
        monkeypatch.setenv("CELERY_RESULT_BACKEND", result_backend)
        monkeypatch.setenv("SQLALCHEMY_DATABASE_URI", sa_db_uri)

        config = compile_config_from_env()

        assert config.DATALAD_REGISTRY_OPERATION_MODE is OperationMode(op_mode)
        assert config.DATALAD_REGISTRY_INSTANCE_PATH == Path(instance_path)
        assert config.DATALAD_REGISTRY_DATASET_CACHE == Path(cache_path)
        assert str(config.DATALAD_REGISTRY_WEB_API_URL) == web_api_url
        assert config.CELERY_BROKER_URL == broker_url
        assert config.CELERY_RESULT_BACKEND == result_backend
        assert config.SQLALCHEMY_DATABASE_URI == sa_db_uri
        assert isinstance(config, config_cls)

    def test_invalid_op_mode(self, monkeypatch):
        """
        Test the case that the operation mode fetched from the environment is one
        that is not valid, one that is not mapped to a config class.
        """
        monkeypatch.setenv("DATALAD_REGISTRY_OPERATION_MODE", "DEVELOPMENT")

        class MockOperationModeToConfigCls:
            # noinspection PyMethodMayBeStatic
            def get(self, *_args, **_kwargs):
                return None

        from datalad_registry import conf

        monkeypatch.setattr(
            conf, "OPERATION_MODE_TO_CONFIG_CLS", MockOperationModeToConfigCls()
        )

        with pytest.raises(ValueError, match="Unexpected operation mode"):
            compile_config_from_env()
