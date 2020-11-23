from enum import IntEnum

import click
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class _TokenStatus(IntEnum):
    REQUESTED = 0
    STAGED = 1
    VERIFIED = 2
    FAILED = 3
    NOTNEEDED = 4


_status_labels = ["token requested",
                  "URL pending verification",
                  "URL verified",
                  "verification failed",
                  "verification not needed"]


class Token(db.Model):

    __tablename__ = "tokens"

    token = db.Column(db.Text, primary_key=True)
    dsid = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    ts = db.Column(db.Integer, nullable=False)

    status = db.Column(db.Integer)
    status_enum = _TokenStatus

    @staticmethod
    def describe_status(status):
        return _status_labels[status]

    def __repr__(self):
        return (f"<Token(token={self.token!r}, "
                f"dsid={self.dsid!r}, url={self.url!r}, "
                f"ts={self.ts}, status={self.status})>")


class URL(db.Model):

    __tablename__ = "urls"

    url = db.Column(db.Text, primary_key=True)
    dsid = db.Column(db.Text, nullable=False)
    info_ts = db.Column(db.Integer)
    update_announced = db.Column(db.Integer)
    head = db.Column(db.Text)
    head_describe = db.Column(db.Text)
    branches = db.Column(db.Text)
    tags = db.Column(db.Text)

    def __repr__(self):
        return f"<URL(url={self.url!r}, dsid={self.dsid!r})>"


@click.command("init-db")
@with_appcontext
def init_db_command():
    db.create_all()
