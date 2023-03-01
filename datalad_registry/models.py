import click
from flask.cli import with_appcontext
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()


class URL(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    url = db.Column(db.Text, nullable=False, unique=True)
    ds_id = db.Column(db.Text, nullable=True)
    annex_uuid = db.Column(db.Text)
    annex_key_count = db.Column(db.Integer)
    annexed_files_in_wt_count = db.Column(db.Integer)
    annexed_files_in_wt_size = db.Column(db.BigInteger)
    info_ts = db.Column(db.DateTime(timezone=True))
    update_announced = db.Column(db.Boolean, default=False, nullable=False)
    head = db.Column(db.Text)
    head_describe = db.Column(db.Text)
    branches = db.Column(db.Text)
    tags = db.Column(db.Text)
    git_objects_kb = db.Column(db.BigInteger)
    #: Whether initial data has been collected for this URL
    processed = db.Column(db.Boolean, default=False, nullable=False)

    meta_data = db.relationship("URLMetadata", backref="url")

    def __repr__(self) -> str:
        return f"<URL(url={self.url!r}, ds_id={self.ds_id!r})>"


class URLMetadata(db.Model):  # type: ignore
    """
    Model for dataset level metadata of a dataset at a specific URL.
    """

    id = db.Column(db.Integer, primary_key=True, nullable=False)

    # The head_describe of the dataset at the associated URL at the time of extraction
    dataset_describe = db.Column(db.String(60), nullable=False)

    dataset_version = db.Column(db.String(60), nullable=False)
    extractor_name = db.Column(db.String(100), nullable=False)
    extractor_version = db.Column(db.String(60), nullable=False)
    extraction_parameter = db.Column(db.JSON, nullable=False)

    extracted_metadata = db.Column(db.JSON, nullable=False)

    # The ID of the associated URL
    url_id = db.Column(db.Integer, db.ForeignKey("url.id"), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<URLMetadata(url={self.url.url!r}, extractor={self.extractor_name!r})> "
        )


@click.command("init-db")
@with_appcontext
def init_db_command() -> None:
    db.create_all()
