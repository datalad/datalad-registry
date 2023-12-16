# This file is for defining the API endpoints related to dataset URls

from json import loads
import operator
from pathlib import Path

from celery import group
from flask import current_app, url_for
from flask_openapi3 import APIBlueprint, Tag
from psycopg2.errors import UniqueViolation
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import BinaryExpression

from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import (
    extract_ds_meta,
    log_error,
    mark_for_chk,
    process_dataset_url,
)
from datalad_registry.utils.flask_tools import json_resp_from_str

from .models import (
    DatasetURLPage,
    DatasetURLRespBaseModel,
    DatasetURLRespModel,
    DatasetURLSubmitModel,
    MetadataReturnOption,
    OrderKey,
    PathParams,
    QueryParams,
)
from .. import API_URL_PREFIX, COMMON_API_RESPONSES, HTTPExceptionResp
from ..url_metadata.models import URLMetadataRef
from ..utils import disable_in_read_only_mode

_ORDER_KEY_TO_SQLA_ATTR = {
    OrderKey.url: RepoUrl.url,
    OrderKey.annex_key_count: RepoUrl.annex_key_count,
    OrderKey.annexed_files_in_wt_count: RepoUrl.annexed_files_in_wt_count,
    OrderKey.annexed_files_in_wt_size: RepoUrl.annexed_files_in_wt_size,
    OrderKey.last_update: RepoUrl.last_update_dt,
    OrderKey.git_objects_kb: RepoUrl.git_objects_kb,
}

bp = APIBlueprint(
    "dataset_urls_api",
    __name__,
    url_prefix=f"{API_URL_PREFIX}/dataset-urls",
    abp_tags=[Tag(name="Dataset URLs", description="API endpoints for dataset URLs")],
    abp_responses=COMMON_API_RESPONSES,
)


@bp.post(
    "",
    responses={
        "201": DatasetURLRespModel,
        "202": DatasetURLRespModel,
        "405": HTTPExceptionResp,  # Occurs only when the server is in read-only mode
    },
)
@disable_in_read_only_mode
def declare_dataset_url(body: DatasetURLSubmitModel):
    """
    Handle the submission of a dataset URL, adding a new one or updating an existing one

    If the submitted URL does not exist in the database,
      * create a new RepoUrl to represent it in the database
      * initiate Celery tasks to process the RepoUrl
        and extract metadata from the dataset at the URL
      * return the newly created representation of the URL in the database
        in the response (with a 201 status code).
        Note: This newly created representation, most likely, will not contain
              the results of the initiated Celery tasks, as they will need more time
              to complete.

    If the submitted URL already exists in the database,
      * flag the representation of the URL in the database to be updated
        if the URL has been initially processed by the system. Do nothing otherwise
        as the URL will be processed by the system the first time.
      * return the current representation of the URL in the database in the response
        (with a 202 status code)
    """
    url_as_str = str(body.url)

    repo_url_row = db.session.execute(
        db.select(RepoUrl).filter_by(url=url_as_str)
    ).one_or_none()
    if repo_url_row is None:
        # == The URL requested to be created does not exist in the database ==

        repo_url_to_add = RepoUrl(url=url_as_str)

        max_url_uniqueness_failures = 10
        url_uniqueness_failure_count = 0
        while url_uniqueness_failure_count < max_url_uniqueness_failures:
            db.session.add(repo_url_to_add)

            try:
                db.session.commit()
            except IntegrityError as e:
                if isinstance(e.orig, UniqueViolation):
                    url_uniqueness_failure_count += 1

                    # The URL has been added to the database by another request
                    # while the current request is being processed.
                    # Rollback the session and obtain the representation
                    # of the URL in the database
                    db.session.rollback()
                    repo_url_added_by_another = (
                        db.session.execute(db.select(RepoUrl).filter_by(url=url_as_str))
                        .scalars()
                        .one_or_none()
                    )

                    if repo_url_added_by_another is not None:
                        # ===
                        # The representation of the URL that is added by another request
                        # is successfully obtained from the database.
                        # ===
                        repo_url_to_resp = repo_url_added_by_another
                        break
                    else:
                        # ===
                        # The representation of the URL that is added by another request
                        # no longer exists in the database
                        # ===
                        continue
                else:
                    raise
            else:
                # Initiate celery tasks to process the RepoUrl
                # and extract metadata from the corresponding dataset
                url_processing = process_dataset_url.signature(
                    (repo_url_to_add.id,), link_error=log_error.s()
                )
                meta_extractions = [
                    extract_ds_meta.signature(
                        (repo_url_to_add.id, extractor),
                        immutable=True,
                        link_error=log_error.s(),
                    )
                    for extractor in current_app.config[
                        "DATALAD_REGISTRY_METADATA_EXTRACTORS"
                    ]
                ]
                (url_processing | group(meta_extractions)).apply_async()
                repo_url_to_resp = repo_url_to_add
                break
        else:
            raise RuntimeError(f"Failed to add the URL, {url_as_str}, to the database.")

        return json_resp_from_str(
            DatasetURLRespModel.from_orm(repo_url_to_resp).json(exclude_none=True),
            status=201,
        )

    else:
        # == The URL requested to be created already exists in the database ==

        repo_url = repo_url_row[0]

        # Build the response from the current representation of the URL in the DB
        resp_model = DatasetURLRespModel.from_orm(repo_url).json(exclude_none=True)

        if repo_url.processed and repo_url.chk_req_dt is None:
            # === The dataset url has been processed and there is no unhandled request
            # for check for update of the dataset at the URL ===
            mark_for_chk.delay(repo_url.id)

        return json_resp_from_str(resp_model, status=202)


@bp.get("", responses={"200": DatasetURLPage})
def dataset_urls(query: QueryParams):
    """
    Get all dataset URLs that satisfy the constraints imposed by the query parameters.
    """

    def append_constraint(
        db_model_column, op, qry, qry_spec_transform=(lambda x: x)
    ) -> None:
        """
        Append a filter constraint corresponding to a given query parameter value
        to the list of filter constraints.

        :param db_model_column: The SQLAlchemy model column to build the constraint with
        :param op: The operator to build the constraint with
        :param qry: The query parameter value
        :param qry_spec_transform: The transformation to apply to the query parameter
                                   value in to build the constraint. Defaults to the
                                   identity function.
        """
        if qry is not None:
            constraints.append(op(db_model_column, qry_spec_transform(qry)))

    def cache_path_trans(cache_path: Path) -> str:
        """
        Transform a cache path to its string representation.
        If the cache path is absolute, only the last three components of the path
        are used in the string representation.
        """
        if cache_path.is_absolute():
            cache_path = Path(*(cache_path.parts[-3:]))
        return str(cache_path)

    # ==== Gathering constraints from query parameters ====

    constraints: list[BinaryExpression] = []

    append_constrain_arg_lst = [
        (RepoUrl.url, operator.eq, query.url, str),
        (RepoUrl.ds_id, operator.eq, query.ds_id, str),
        (RepoUrl.annex_key_count, operator.ge, query.min_annex_key_count),
        (RepoUrl.annex_key_count, operator.le, query.max_annex_key_count),
        (
            RepoUrl.annexed_files_in_wt_count,
            operator.ge,
            query.min_annexed_files_in_wt_count,
        ),
        (
            RepoUrl.annexed_files_in_wt_count,
            operator.le,
            query.max_annexed_files_in_wt_count,
        ),
        (
            RepoUrl.annexed_files_in_wt_size,
            operator.ge,
            query.min_annexed_files_in_wt_size,
        ),
        (
            RepoUrl.annexed_files_in_wt_size,
            operator.le,
            query.max_annexed_files_in_wt_size,
        ),
        (RepoUrl.last_update_dt, operator.ge, query.earliest_last_update),
        (RepoUrl.last_update_dt, operator.le, query.latest_last_update),
        (RepoUrl.git_objects_kb, operator.ge, query.min_git_objects_kb),
        (RepoUrl.git_objects_kb, operator.le, query.max_git_objects_kb),
        (RepoUrl.processed, operator.eq, query.processed),
        (RepoUrl.cache_path, operator.eq, query.cache_path, cache_path_trans),
    ]

    for args in append_constrain_arg_lst:
        append_constraint(*args)

    # ==== Gathering constraints from query parameters ends ====

    ep = ".dataset_urls"  # Endpoint of `dataset_urls`
    base_qry = loads(query.json(exclude={"page"}, exclude_none=True))

    max_per_page = 100  # The overriding limit to `per_page` provided by the requester
    pagination = db.paginate(
        db.select(RepoUrl)
        .filter(and_(True, *constraints))
        .order_by(
            getattr(
                _ORDER_KEY_TO_SQLA_ATTR[query.order_by], query.order_dir.value
            )().nulls_last()
        ),
        page=query.page,
        per_page=query.per_page,
        max_per_page=max_per_page,
    )
    orm_ds_urls = pagination.items
    cur_pg_num = pagination.page
    last_pg_num = pagination.pages

    if query.return_metadata is None:
        # === No metadata should be returned ===

        # noinspection PyArgumentList
        ds_urls = [
            DatasetURLRespModel(
                **DatasetURLRespBaseModel.from_orm(i).dict(), metadata_=None
            )
            for i in orm_ds_urls
        ]

    elif query.return_metadata is MetadataReturnOption.reference:
        # === Metadata should be returned by reference ===

        # noinspection PyArgumentList
        ds_urls = [
            DatasetURLRespModel(
                **DatasetURLRespBaseModel.from_orm(i).dict(),
                metadata_=[
                    URLMetadataRef(
                        extractor_name=j.extractor_name,
                        link=url_for(
                            "url_metadata_api.url_metadata", url_metadata_id=j.id
                        ),
                    )
                    for j in i.metadata_
                ],
            )
            for i in orm_ds_urls
        ]

    else:
        # === Metadata should be returned by content ===

        ds_urls = orm_ds_urls

    assert pagination.total is not None

    page = DatasetURLPage(
        total=pagination.total,
        cur_pg_num=cur_pg_num,
        prev_pg=url_for(ep, **base_qry, page=pagination.prev_num)
        if pagination.has_prev
        else None,
        next_pg=url_for(ep, **base_qry, page=pagination.next_num)
        if pagination.has_next
        else None,
        first_pg=url_for(ep, **base_qry, page=1),
        last_pg=url_for(ep, **base_qry, page=last_pg_num),
        dataset_urls=ds_urls,
    )

    return json_resp_from_str(page.json(exclude_none=True))


@bp.get("/<int:id>", responses={"200": DatasetURLRespModel})
def dataset_url(path: PathParams):
    """
    Get a dataset URL by ID.
    """
    ds_url = DatasetURLRespModel.from_orm(db.get_or_404(RepoUrl, path.id))
    return json_resp_from_str(ds_url.json(exclude_none=True))
