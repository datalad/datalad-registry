from datalad_registry import celery
from datalad_registry.factory import create_app, setup_celery

app = create_app()

# todo: This is most likely to be unnecessary. It can even be problematic.
#       Within create_app() above, it is already run.
setup_celery(app, celery)
