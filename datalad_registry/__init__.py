import sys

from celery import Celery

if sys.version_info[:2] < (3, 8):
    from importlib_metadata import version
else:
    from importlib.metadata import version

__version__ = version("datalad-registry")

celery = Celery("datalad_registry")
