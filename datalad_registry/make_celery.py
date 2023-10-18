# This file provides Celery commands access to the Celery app created through
# the factory functions in datalad_registry/__init__.py
import logging

from celery import Celery

from . import create_app


# === Code for suppressing known git progress logs ===
class SuppressKnownGitProgressLogs(logging.Filter):
    # Known git progress log types
    # These types can be found in the definition of
    # `datalad.support.gitrepo.GitProgress`
    known_git_progress_log_types = [
        "Counting objects",
        "Compressing objects",
        "Writing objects",
        "Receiving objects",
        "Resolving deltas",
        "Finding sources",
        "Checking out files",
        "Enumerating objects",
    ]

    known_git_progress_log_contents = [t + ":" for t in known_git_progress_log_types]

    def filter(self, record):
        return all(
            content not in record.getMessage()
            for content in self.known_git_progress_log_contents
        )


# Retrieve a reference to the "datalad.gitrepo" logger
dl_gitrepo_lgr = logging.getLogger("datalad.gitrepo")

# Add a filter to the "datalad.gitrepo" logger to suppress known git progress logs
dl_gitrepo_lgr.addFilter(SuppressKnownGitProgressLogs())
# === End of code for suppressing known git progress logs ===

flask_app = create_app()
celery_app: Celery = flask_app.extensions["celery"]
