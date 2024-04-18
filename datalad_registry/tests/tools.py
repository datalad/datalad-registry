# This file contains helper functions for testing purposes

from flask import Flask

from datalad_registry.models import RepoUrl, db


def populate_with_dataset_urls(urls: list[RepoUrl], flask_app: Flask) -> list[str]:
    """
    Populate the `repo_url` table with a list of RepoUrl objects

    :param urls: The list of RepoUrl objects to populate
    :param flask_app: The Flask app instance which provides the context for
                      database access
    :return: The list of URLs, expressed in `str`, that were added to the database
    """

    with flask_app.app_context():
        db.session.add_all(urls)
        db.session.commit()

        return [url.url for url in urls]
