# This file provides Celery commands access to the Celery app created through
# the factory functions in datalad_registry/__init__.py
import logging
import re

from celery import Celery

from . import create_app


# === Code for suppressing known git progress logs ===
class SuppressKnownGitProgressLogs(logging.Filter):
    # Known git progress log types
    # These types can be found in the definition of
    # `datalad.support.gitrepo.GitProgress`
    known_git_progress_log_types = {
        "Counting objects",
        "Compressing objects",
        "Writing objects",
        "Receiving objects",
        "Resolving deltas",
        "Finding sources",
        "Checking out files",
        "Enumerating objects",
    }

    re_op_absolute = re.compile(r"(?:remote: )?([\w\s]+):\s+\d+.*")
    re_op_relative = re.compile(r"(?:remote: )?([\w\s]+):\s+\d+% \(\d+/\d+\).*")

    def filter(self, record):
        # The following logic is based on the logic in
        # `datalad.support.gitrepo.GitProgress._parse_progress_line`

        msg = record.getMessage()

        match = self.re_op_relative.match(msg)
        if match is None:
            match = self.re_op_absolute.match(msg)

        if match is None:
            # === msg does not match the pattern of a git progress report ===
            return True

        op_name = match.group(1)
        return op_name not in self.known_git_progress_log_types


# Retrieve a reference to the "datalad.gitrepo" logger
dl_gitrepo_lgr = logging.getLogger("datalad.gitrepo")

# Add a filter to the "datalad.gitrepo" logger to suppress known git progress logs
dl_gitrepo_lgr.addFilter(SuppressKnownGitProgressLogs())
# === End of code for suppressing known git progress logs ===

flask_app = create_app()
celery_app: Celery = flask_app.extensions["celery"]
