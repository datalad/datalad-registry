# This script is for populating the metadata of each URL found in the database.
# The population is executed in the context of the Flask application of
# datalad-registry. Thus, one should run this script in an environment that is suitable
# for running datalad-registry. Additionally, this script invokes the Celery worker in
# datalad-registry to do the metadata extraction. Therefore, one should ensure that
# the Celery worker is running before running this script.


from pathlib import Path

from datalad_registry.factory import create_app
from datalad_registry.models import URL, db
from datalad_registry.tasks import extract_meta
from datalad_registry.utils.url_encoder import url_encode

flask_app = create_app()


cache_dir = Path(flask_app.config["DATALAD_REGISTRY_DATASET_CACHE"])

with flask_app.app_context():
    urls = db.session.execute(db.select(URL)).scalars().all()
    print(f"Found {len(urls)} URLs.")

    for url in urls:
        if url.ds_id is not None:
            # Reconstruct the path of the dataset of the URL at the local cache
            ds_path = cache_dir / url.ds_id[:3] / url_encode(url.url)

            url_id = url.id
            ds_path_str = str(ds_path)

            for extractor in flask_app.config["DATALAD_REGISTRY_METADATA_EXTRACTORS"]:
                extract_meta.delay(url_id, ds_path_str, extractor)
        else:
            print(
                f"Warning: {url.url} has no dataset ID in the database.\n"
                f"    Therefore, no metadata can be extracted "
                f"for the dataset at the URL."
            )
