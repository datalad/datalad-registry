# This file is for removing repo URLs hosted at https://datasets.datalad.org
# and associated metadata from the database

from datalad.utils import rmtree as rm_ds_tree
from sqlalchemy import select

from datalad_registry import create_app
from datalad_registry.models import RepoUrl, db

flask_app = create_app()

with flask_app.app_context():

    # Get all repo URLs that start with https://datasets.datalad.org
    repo_urls = (
        db.session.execute(
            select(RepoUrl).filter(
                RepoUrl.url.startswith("https://datasets.datalad.org")
            )
        )
        .scalars()
        .all()
    )

    print(f"deleting {len(repo_urls)} repo URLs\n")

    # Delete all the repo URLs and associated metadata
    for repo_url in repo_urls:

        # Remove the dataset from the local cache if exists
        cache_path_abs = repo_url.cache_path_abs
        if repo_url.cache_path_abs is not None:
            print(f"deleting {repo_url.cache_path_abs} from cache .. .")
            rm_ds_tree(cache_path_abs)

        # Delete associated metadata
        for md in repo_url.metadata_:
            db.session.delete(md)

        # Delete the repo URL
        db.session.delete(repo_url)

    db.session.commit()

    print("done")
