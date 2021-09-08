from setuptools import setup

setup(
    entry_points={
        "datalad.extensions": ["registry=datalad_registry_client:command_suite"],
    },
)
