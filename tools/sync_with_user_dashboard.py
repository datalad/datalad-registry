# This script initiates the Celery task, `datalad_registry.tasks.usage_dashboard_sync`
# on demand. Thus, can be used to ensure that the active repositories listed in
# datalad-usage-dashboard is are registered in datalad-registry on demand.


from datalad_registry import create_app
from datalad_registry.tasks import usage_dashboard_sync

# Set up the Datalad-Registry Celery app through creating the Datalad-Registry Flask app
create_app()

# Trigger a `usage_dashboard_sync` task to be executed by a Celery worker
usage_dashboard_sync.delay()
