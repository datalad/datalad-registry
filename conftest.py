import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--devserver",
        action="store_true",
        default=False,
        help="Run tests that depend on Flask development server",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--devserver"):
        return

    skip_devserver = pytest.mark.skip(reason="--devserver option not specified")
    for item in items:
        if "devserver" in item.keywords:
            item.add_marker(skip_devserver)
