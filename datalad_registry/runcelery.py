from datalad_registry import celery
from datalad_registry.factory import create_app, setup_celery

app = create_app()
setup_celery(app, celery)
