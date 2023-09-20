from datetime import datetime, timedelta, timezone
from enum import auto
import json
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from datalad import api as dl
from datalad.api import Dataset
from datalad.distribution.dataset import require_dataset
from datalad.support.exceptions import IncompleteResultsError
from datalad.utils import rmtree as rm_ds_tree
from flask import current_app
from pydantic import StrictInt, StrictStr, parse_obj_as, validate_arguments
from sqlalchemy import and_, case, not_, or_, select

from datalad_registry.com_models import MetaExtractResult
from datalad_registry.models import RepoUrl, URLMetadata, db
from datalad_registry.utils import StrEnum
from datalad_registry.utils.datalad_tls import (
    clone,
    get_origin_annex_key_count,
    get_origin_annex_uuid,
    get_origin_branches,
    get_wt_annexed_file_info,
)

from .utils import allocate_ds_path, update_ds_clone, validate_url_is_processed

lgr = get_task_logger(__name__)


class ExtractMetaStatus(StrEnum):
    SUCCEEDED = auto()
    ABORTED = auto()
    SKIPPED = auto()
    NO_RECORD = auto()


class ProcessUrlStatus(StrEnum):
    SUCCEEDED = auto()
    NO_RECORD = auto()


class ChkUrlStatus(StrEnum):
    SUCCEEDED = auto()
    ABORTED = auto()
    SKIPPED = auto()


def _update_dataset_url_info(dataset_url: RepoUrl, ds: Dataset) -> None:
    """
    Update a given RepoUrl object with the information of a given dataset

    Note: The timestamp regarding the update of this information, `last_update_dt`,
          is to be updated as well.

    :param dataset_url: The RepoUrl object to be updated
    :param ds: A dataset object representing an up-to-date clone of the dataset
               in the local cache. Note: The caller of this function is responsible for
               ensuring the clone of the dataset in cache is up-to-date.
    """

    dataset_url.ds_id = ds.id

    dataset_url.annex_uuid = (
        str(annex_uuid)
        if (annex_uuid := get_origin_annex_uuid(ds)) is not None
        else None
    )

    dataset_url.annex_key_count = get_origin_annex_key_count(ds)

    if (wt_annexed_file_info := get_wt_annexed_file_info(ds)) is not None:
        dataset_url.annexed_files_in_wt_count = wt_annexed_file_info.count
        dataset_url.annexed_files_in_wt_size = wt_annexed_file_info.size
    else:
        dataset_url.annexed_files_in_wt_count = None
        dataset_url.annexed_files_in_wt_size = None

    dataset_url.head = ds.repo.get_hexsha("origin/HEAD")
    dataset_url.head_describe = ds.repo.describe("origin/HEAD", tags=True, always=True)

    dataset_url.branches = get_origin_branches(ds)

    dataset_url.tags = json.dumps(ds.repo.get_tags())

    dataset_url.git_objects_kb = (
        ds.repo.count_objects["size"] + ds.repo.count_objects["size-pack"]
    )

    dataset_url.last_update_dt = datetime.now(timezone.utc)


# Map of extractors to their respective required files
#     The required files are specified relative to the root of the dataset
_EXTRACTOR_REQUIRED_FILES = {
    "metalad_studyminimeta": [".studyminimeta.yaml"],
    "datacite_gin": ["datacite.yml"],
    "bids_dataset": ["dataset_description.json"],
}


@shared_task
def log_error(request, exc, traceback) -> None:
    """
    An error handler for logging errors in tasks
    :param request: The request in fulfilling which the error/exception has occurred
    :param exc: The exception that has occurred
    :param traceback: The traceback of the exception
    """
    lgr.error("%s\n%r\n%s\n", request, exc, traceback)


# `acks_late` is set. Make sure this task is always idempotent
@shared_task(acks_late=True)
@validate_arguments
def extract_ds_meta(ds_url_id: StrictInt, extractor: StrictStr) -> ExtractMetaStatus:
    """
    Extract dataset level metadata from a dataset

    :param ds_url_id: The ID (primary key) of the RepoUrl of the dataset in the database
    :param extractor: The name of the extractor to use
    :return: `ExtractMetaStatus.SUCCEEDED` if the extraction has produced
                 valid metadata. In this case, the metadata has been recorded to
                 the database upon return.
             `ExtractMetaStatus.ABORTED` if the extraction has been aborted due to some
                 required files not being present in the dataset. For example,
                 `.studyminimeta.yaml` is not present in the dataset for running
                 the studyminimeta extractor.
             `ExtractMetaStatus.SKIPPED` if the extraction has been skipped because the
                 metadata to be extracted is already present in the database,
                 as identified by the extractor name, RepoUrl, and dataset version.
             `ExtractMetaStatus.NO_RECORD` if there is no RepoUrl in the database with
                the specified ID. (This task can be initiated with the argument of a
                supposed ID of a RepoUrl that doesn't identify any RepoUrl in
                the database at the time of the execution of this task because
                the RepoUrl has been deleted from the database.)
    :raise: ValueError if the RepoUrl of the specified ID does not exist or has not
                been processed yet.
            RuntimeError if the extraction has produced no valid metadata.

    """

    # Get the RepoUrl from the database by ID with a read/share lock
    url = (
        db.session.execute(
            select(RepoUrl).filter_by(id=ds_url_id).with_for_update(read=True)
        )
        .scalars()
        .one_or_none()
    )

    if url is None:
        # === there is no RepoUrl in the database with the specified ID ===
        return ExtractMetaStatus.NO_RECORD

    validate_url_is_processed(url)

    # Absolute path of the dataset clone in cache
    cache_path_abs = (
        current_app.config["DATALAD_REGISTRY_DATASET_CACHE"] / url.cache_path
    )

    # Check for missing of required files
    if extractor in _EXTRACTOR_REQUIRED_FILES:
        for required_file_path in (
            cache_path_abs / f for f in _EXTRACTOR_REQUIRED_FILES[extractor]
        ):
            if not required_file_path.is_file():
                # A required file is missing. Abort the extraction
                return ExtractMetaStatus.ABORTED

    # Check if the metadata to be extracted is already present in the database
    for data in url.metadata_:  # type: ignore
        if extractor == data.extractor_name:
            # Get the current version of the dataset as it exists in the local cache
            ds_version = require_dataset(
                cache_path_abs, check_installed=True
            ).repo.get_hexsha()

            if ds_version == data.dataset_version:
                # The metadata to be extracted is already present in the database
                return ExtractMetaStatus.SKIPPED
            else:
                # metadata can be extracted for a new version of the dataset

                db.session.delete(data)  # delete the old metadata from the database
                break

    results = parse_obj_as(
        list[MetaExtractResult],
        dl.meta_extract(
            extractor,
            dataset=cache_path_abs,
            result_renderer="disabled",
            on_failure="stop",
        ),
    )

    if len(results) == 0:
        lgr.debug(
            "Extractor %s did not produce any metadata for %s", extractor, url.url
        )
        raise RuntimeError(
            f"Extractor {extractor} did not produce any metadata for {url.url}"
        )

    produced_valid_result = False
    for res in results:
        if res.status != "ok":
            lgr.debug(
                "A result of extractor %s for %s is not 'ok'."
                "It will not be recorded to the database",
                extractor,
                url.url,
            )
        else:
            # Record the metadata to the database
            metadata_record = res.metadata_record
            url_metadata = URLMetadata(
                dataset_describe=url.head_describe,
                dataset_version=metadata_record.dataset_version,
                extractor_name=metadata_record.extractor_name,
                extractor_version=metadata_record.extractor_version,
                extraction_parameter=metadata_record.extraction_parameter,
                extracted_metadata=metadata_record.extracted_metadata,
                url=url,
            )
            db.session.add(url_metadata)

            produced_valid_result = True

    if produced_valid_result:
        db.session.commit()
        return ExtractMetaStatus.SUCCEEDED
    else:
        raise RuntimeError(
            f"Extractor {extractor} did not produce any valid metadata for {url.url}"
        )


@shared_task(
    acks_late=True,  # `acks_late` is set. Make sure this task is always idempotent
    autoretry_for=(IncompleteResultsError,),
    max_retries=4,
    retry_backoff=100,
)
@validate_arguments
def process_dataset_url(dataset_url_id: StrictInt) -> ProcessUrlStatus:
    """
    Process a RepoUrl

    :param dataset_url_id: The ID (primary key) of the RepoUrl in the database

    note:: This function clones the dataset at the specified URL to a new local
           cache directory and extracts information from the cloned copy of the dataset
           to populate the cells of the given RepoUrl row in the RepoUrl table. If both
           the cloning and extraction of information are successful,
           the `processed` cell of the given RepoUrl row will be set to `True`,
           the other cells of the row will be populated with the up-to-date
           information, and if the RepoUrl has been processed previously, the old
           cache directory established by the previous processing will be removed.
           Otherwise, no cell of the given RepoUrl row will be changed,
           and the local cache will be restored to its previous state
           (by deleting the new cache directory for the cloning of the dataset).

    Note: If there is no RepoUrl in the database with the specified ID, this task simply
          returns `ProcessUrlStatus.NO_RECORD` without doing anything else.
          (This task can be initiated with an argument, a supposed ID of a RepoUrl,
          that doesn't identify any RepoUrl in the database at the time of the execution
          of this task because the RepoUrl has been deleted from the database.)
    """

    # Get the RepoUrl from the database by ID
    dataset_url: Optional[RepoUrl] = (
        db.session.execute(
            select(RepoUrl).filter_by(id=dataset_url_id).with_for_update()
        )
        .scalars()
        .one_or_none()
    )

    if dataset_url is None:
        # === there is no RepoUrl in the database with the specified ID ===
        return ProcessUrlStatus.NO_RECORD

    old_cache_path_absolute = dataset_url.cache_path_absolute

    # Allocate a new path in the local cache for cloning the dataset
    # at the specified URL
    ds_path_relative = allocate_ds_path()

    ds_path_absolute = (
        current_app.config["DATALAD_REGISTRY_DATASET_CACHE"] / ds_path_relative
    )

    # Create a directory at the newly allocated path
    ds_path_absolute.mkdir(parents=True, exist_ok=False)

    try:
        # Clone the dataset at the specified URL to the newly created directory
        ds = clone(
            source=dataset_url.url,
            path=ds_path_absolute,
            on_failure="stop",
            result_renderer="disabled",
        )

        # Extract information from the cloned copy of the dataset
        _update_dataset_url_info(dataset_url, ds)

        dataset_url.processed = True
        dataset_url.cache_path = str(ds_path_relative)

        # Commit the updated RepoUrl object to the database
        db.session.commit()

    except Exception as e:
        # Delete the newly created directory for cloning the dataset
        rm_ds_tree(ds_path_absolute)

        raise e

    else:
        if old_cache_path_absolute is not None:
            # Delete the directory for the old local dataset clone
            rm_ds_tree(old_cache_path_absolute)

        return ProcessUrlStatus.SUCCEEDED


@shared_task
@validate_arguments
def mark_for_chk(url_id: StrictInt) -> None:
    """
    Mark a dataset url for check for update with a timestamp as the value of
    `chk_req_dt` of the `RepoUrl` object representing the URL

    :param url_id: The ID (primary key) of the `RepoUrl` object representing the URL
    """

    # Select and lock the dataset url to be marked for update check
    url: Optional[RepoUrl] = (
        db.session.execute(select(RepoUrl).filter_by(id=url_id).with_for_update())
        .scalars()
        .one_or_none()
    )

    # Note: It is possible that there is no `RepoUrl` record with the given ID
    #       (possibly due to deletion).
    #       So do something only if there is such a record
    if url is not None and url.processed and url.chk_req_dt is None:
        # The dataset url has been processed and there is no unhandled request
        # for check for update of the dataset at the URL
        url.chk_req_dt = datetime.now(timezone.utc)
        db.session.commit()


@shared_task
def url_chk_dispatcher():
    """
    A task intended to be run periodically by Celery Beat to initiate
    checking of dataset urls for potential update
    """

    max_failed_chks = current_app.config["DATALAD_REGISTRY_MAX_FAILED_CHKS_PER_URL"]
    min_chk_interval = timedelta(
        seconds=current_app.config["DATALAD_REGISTRY_MIN_CHK_INTERVAL_PER_URL"]
    )
    # todo: make this configurable
    #   This is determined by the `rate_limit` of the `chk_url` task and how frequently
    #   the `url_chk_dispatcher` task is run
    max_chks_to_dispatch = 10
    chk_url_task_expiration = 60.0  # todo: make this configurable
    repeat_cutoff_dt = datetime.now(timezone.utc) - min_chk_interval

    relevant_action_dt = case(
        (RepoUrl.last_chk_dt.is_not(None), RepoUrl.last_chk_dt),
        else_=RepoUrl.last_update_dt,
    )

    # Condition for not yet checked urls
    not_chked_cond = or_(
        RepoUrl.last_chk_dt.is_(None),
        RepoUrl.last_chk_dt < RepoUrl.chk_req_dt,
    )

    # Condition for requested but not yet checked urls
    requested_not_chked_cond = and_(RepoUrl.chk_req_dt.is_not(None), not_chked_cond)

    # Condition for requested and already checked urls
    requested_chked_cond = and_(RepoUrl.chk_req_dt.is_not(None), not_(not_chked_cond))

    # Select and lock all dataset urls to be checked
    result: tuple[int, Optional[datetime]] = db.session.execute(
        select(RepoUrl.id, RepoUrl.last_chk_dt)
        .filter(
            and_(
                RepoUrl.processed,
                RepoUrl.n_failed_chks <= max_failed_chks,
                or_(
                    and_(
                        RepoUrl.chk_req_dt.is_not(None),  # requested to be checked
                        or_(
                            # The ones that have not been checked since the request
                            not_chked_cond,
                            # The ones that have been checked since the request but
                            # the last check is old enough
                            RepoUrl.last_chk_dt <= repeat_cutoff_dt,
                        ),
                    ),
                    and_(
                        RepoUrl.chk_req_dt.is_(None),  # not requested to be checked
                        relevant_action_dt <= repeat_cutoff_dt,
                    ),
                ),
            )
        )
        .with_for_update(skip_locked=True)  # Skipping already locked rows
        .order_by(
            case(
                (
                    requested_not_chked_cond,
                    1,
                ),
                (
                    requested_chked_cond,
                    2,
                ),
                else_=3,
            ),
            case(
                (
                    requested_not_chked_cond,
                    RepoUrl.chk_req_dt,
                ),
                (
                    requested_chked_cond,
                    RepoUrl.last_chk_dt,
                ),
                else_=relevant_action_dt,
            ),
        )
        .limit(max_chks_to_dispatch)
    ).all()

    for id_, last_chk_dt in result:
        chk_url_to_update.apply_async(
            (id_, last_chk_dt), expires=chk_url_task_expiration
        )


@shared_task(rate_limit="10/m")
@validate_arguments
def chk_url_to_update(
    url_id: StrictInt, initial_last_chk_dt: Optional[datetime]
) -> ChkUrlStatus:
    """
    Check a dataset url for potential update

    If an update is available, update the clone of the dataset at the url in the local
    cache and update the corresponding RepoUrl object in the database.

    :param url_id: The id (primary key) of the dataset url, represented by a `RepoUrl`,
                   in the database
    :param initial_last_chk_dt: The value of `last_chk_dt` of the `RepoUrl`
                                when this check was initiated.
    :raise: ValueError if the RepoUrl of the specified ID does not exist or has not
            been processed yet.
    """

    # Select and lock the RepoUrl identified by the given ID if it is not locked
    # by another transaction
    url = (
        db.session.execute(
            select(RepoUrl).filter_by(id=url_id).with_for_update(skip_locked=True)
        )
        .scalars()
        .one_or_none()
    )

    if url is None:
        # ===
        # There is no RepoUrl in the database with the specified ID, possibly due to
        # deletion, or the RepoUrl identified by the given ID is currently locked.
        # ===
        return ChkUrlStatus.ABORTED

    # ===
    # At this point, the RepoUrl identified by the given ID is obtained and exclusively
    # locked by the current transaction
    # ===

    validate_url_is_processed(url)

    if url.last_chk_dt != initial_last_chk_dt:
        # The RepoUrl has been checked by another process since this check was initiated
        # Skip this check
        return ChkUrlStatus.SKIPPED

    # ===
    # The RepoUrl has not been checked by any other process
    # since this check was initiated
    # ===

    try:
        # Check and potentially update the dataset clone
        ds_clone_path_relative, is_new_clone = update_ds_clone(url)
    except Exception as e:
        lgr.info(
            "Check to update the clone of the dataset at the given URL, %s failed."
            "This is the %s-th consecutive failures in checking for update",
            url.url,
            url.n_failed_chks + 1,
            exc_info=True,
        )

        url.n_failed_chks += 1

        raise e
    else:
        ds_clone = require_dataset(
            (
                current_app.config["DATALAD_REGISTRY_DATASET_CACHE"]
                / ds_clone_path_relative
            ),
            check_installed=True,
            purpose="updating dataset info in database",
        )

        _update_dataset_url_info(url, ds_clone)

        if is_new_clone:
            # Remove old clone
            rm_ds_tree(url.cache_path)

            # Update the cache path to the path of the new clone
            url.cache_path = str(ds_clone_path_relative)

        # Initiate extraction of metadata of the up-to-date dataset
        for extractor in current_app.config["DATALAD_REGISTRY_METADATA_EXTRACTORS"]:
            extract_ds_meta.apply_async((url.id, extractor), link_error=log_error.s())

        url.n_failed_chks = 0
        url.chk_req_dt = None
    finally:
        url.last_chk_dt = datetime.now(timezone.utc)
        db.session.commit()

    return ChkUrlStatus.SUCCEEDED
