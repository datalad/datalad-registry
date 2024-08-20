# This script initiates Celery tasks to run the `dandi:files` on each processed repo.

from sqlalchemy import select

from datalad_registry import create_app
from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import extract_ds_meta

flask_app = create_app()

with flask_app.app_context():

    # Get the IDs of the processed repo URLs
    processed_url_ids = (
        db.session.execute(select(RepoUrl.id).filter(RepoUrl.processed)).scalars().all()
    )

    for url_id in processed_url_ids:
        extract_ds_meta.delay(url_id, "dandi:files")
