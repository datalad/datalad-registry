import logging
import sqlite3

import click
from flask import current_app
from flask import g
from flask.cli import with_appcontext

lgr = logging.getLogger(__name__)


def get_db():
    if "db" not in g:
        database = current_app.config["DATABASE"]
        lgr.debug("Connecting to database %s", database)
        g.db = sqlite3.connect(database, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        lgr.debug("Initializing db with %s", f)
        db.executescript(f.read().decode("utf8"))


@click.command("init-db")
@with_appcontext
def init_db_command():
    init_db()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def read(statement, *values):
    """Execute read-only `statement` parameterized with `values`.

    Return an sqlite3.Cursor.
    """
    return get_db().execute(statement, values)


def write(statement, *values):
    """Execute `statement` parameterized with `values` and commit changes.
    """
    with get_db() as db:
        db.execute(statement, values)
