# This script is for populating the metadata of each RepoUrl found in the database.
# The population is executed in the context of the Flask application of
# datalad-registry. Thus, one should run this script in an environment that is suitable
# for running datalad-registry. Additionally, this script invokes the Celery worker in
# datalad-registry to do the metadata extraction. Therefore, one should ensure that
# the Celery worker is running before running this script.


import click

from datalad_registry import create_app
from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import extract_ds_meta

flask_app = create_app()


@click.command
@click.option(
    "--extractor",
    "-e",
    type=str,
    prompt="Extractor name",
    help="The name of the extractor to use",
)
def populate_url_metadata(extractor: str) -> None:
    with flask_app.app_context():
        urls = db.session.execute(db.select(RepoUrl)).scalars().all()
        print(f"Found {len(urls)} URLs and submitting them for {extractor} extraction.")

        for url in urls:
            if url.processed:
                extract_ds_meta.delay(url.id, extractor)

            else:
                print(
                    f"Warning: {url.url} has not been processed initially "
                    f"(possibly not cloned yet).\n"
                    f"  Therefore, no metadata can be extracted "
                    f"for the dataset at the URL."
                )


if __name__ == "__main__":
    populate_url_metadata()
