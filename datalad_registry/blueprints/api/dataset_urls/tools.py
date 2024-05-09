from sqlalchemy import (
    CTE,
    Select,
    Subquery,
    TableClause,
    and_,
    column,
    func,
    not_,
    or_,
    select,
    table,
    text,
)

from datalad_registry.models import RepoUrl, db

from .models import (
    AnnexDsCollectionStats,
    CollectionStats,
    DataladDsCollectionStats,
    NonAnnexDsCollectionStats,
    StatsSummary,
)


def cache_result_to_tmp_tb(select_stmt: Select, tb_name: str) -> TableClause:
    """
    Execute the given select statement and cache the result to a temporary table
    with the given name

    :param select_stmt: The given select statement to execute
    :param tb_name: The string to use as the name of the temporary table
    :return: A object representing the temporary table

    Note: The execution of this function requires the Flask app's context
    """
    create_tmp_tb_sql = f"""
        CREATE TEMPORARY TABLE {tb_name} AS
        {select_stmt.compile(bind=db.engine, compile_kwargs={'literal_binds': True})};
    """
    db.session.execute(text(create_tmp_tb_sql))

    return table(
        tb_name,
        *(column(name, c.type) for name, c in select_stmt.selected_columns.items()),
    )


def _get_annex_ds_collection_stats(q: Subquery) -> AnnexDsCollectionStats:
    """
    Get the stats of a collection of datasets that contains only of annex datasets

    :param q: The query that specifies the collection of datasets under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """

    ds_count, annexed_files_size, annexed_file_count = db.session.execute(
        select(
            func.count().label("ds_count"),
            func.sum(q.c.annexed_files_in_wt_size).label("annexed_files_size"),
            func.sum(q.c.annexed_files_in_wt_count).label("annexed_file_count"),
        ).select_from(q)
    ).one()

    return AnnexDsCollectionStats(
        ds_count=ds_count,
        annexed_files_size=annexed_files_size,
        annexed_file_count=annexed_file_count,
    )


def get_unique_dl_ds_collection_stats(base_cte: CTE) -> AnnexDsCollectionStats:
    """
    Get the stats of the subset of the collection of datasets that contains only
    of Datalad datasets, considering datasets with the same `ds_id` as the same
    dataset

    :param base_cte: The base CTE that specified the collection of datasets
        under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """

    grp_by_id_q = (
        select(
            base_cte.c.ds_id,
            func.max(base_cte.c.annexed_files_in_wt_size).label(
                "max_annexed_files_in_wt_size"
            ),
        )
        .group_by(base_cte.c.ds_id)
        .subquery("grp_by_id_q")
    )

    grp_by_id_and_a_f_size_q = (
        select(
            RepoUrl.ds_id,
            RepoUrl.annexed_files_in_wt_size,
            func.max(RepoUrl.annexed_files_in_wt_count).label(
                "annexed_files_in_wt_count"
            ),
        )
        .join(
            grp_by_id_q,
            and_(
                RepoUrl.ds_id == grp_by_id_q.c.ds_id,
                or_(
                    grp_by_id_q.c.max_annexed_files_in_wt_size.is_(None),
                    RepoUrl.annexed_files_in_wt_size
                    == grp_by_id_q.c.max_annexed_files_in_wt_size,
                ),
            ),
        )
        .group_by(RepoUrl.ds_id, RepoUrl.annexed_files_in_wt_size)
        .subquery("grp_by_id_and_a_f_size_q")
    )

    return _get_annex_ds_collection_stats(grp_by_id_and_a_f_size_q)


def get_dl_ds_collection_stats_with_dups(base_cte: CTE) -> AnnexDsCollectionStats:
    """
    Get the stats of the subset of the collection of datasets that contains only
    of Datalad datasets, considering individual repos as a dataset regardless of
    the value of `ds_id`.

    :param base_cte: The base CTE that specified the collection of datasets
                     under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """

    # Select statement for getting all the Datalad datasets
    dl_ds_q = select(base_cte).filter(base_cte.c.ds_id.is_not(None)).subquery("dl_ds_q")

    return _get_annex_ds_collection_stats(dl_ds_q)


def get_dl_ds_collection_stats(base_q: Subquery) -> DataladDsCollectionStats:
    """
    Get the stats of the subset of the collection of datasets that contains only
    of Datalad datasets

    :param base_q: The base query that specified the collection of datasets
                   under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """

    return DataladDsCollectionStats(
        unique_ds_stats=get_unique_dl_ds_collection_stats(base_q),
        stats=get_dl_ds_collection_stats_with_dups(base_q),
    )


def get_pure_annex_ds_collection_stats(base_cte: CTE) -> AnnexDsCollectionStats:
    """
    Get the stats of the subset of the collection of datasets that contains only
    of pure annex datasets, the annex datasets that are not Datalad datasets

    :param base_cte: The base CTE that specified the collection of datasets
                     under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """
    # Select statement for getting all the pure annex datasets
    pure_annex_ds_q = (
        select(base_cte)
        .filter(
            and_(base_cte.c.branches.has_key("git-annex"), base_cte.c.ds_id.is_(None))
        )
        .subquery("pure_annex_ds_q")
    )

    return _get_annex_ds_collection_stats(pure_annex_ds_q)


def get_non_annex_ds_collection_stats(base_q: Subquery) -> NonAnnexDsCollectionStats:
    """
    Get the stats of the subset of the collection of datasets that contains only
    of non-annex datasets

    :param base_q: The base query that specified the collection of datasets
                   under consideration
    :return: The object representing the stats

    Note: The execution of this function requires the Flask app's context
    """
    # Select statement for getting all the non-annex datasets
    non_annex_ds_q = (
        select(base_q)
        .filter(not_(base_q.c.branches.has_key("git-annex")))
        .subquery("non_annex_ds_q")
    )

    return NonAnnexDsCollectionStats(
        ds_count=db.session.execute(
            select(func.count().label("ds_count")).select_from(non_annex_ds_q)
        ).scalar_one()
    )


def get_collection_stats(select_stmt: Select) -> CollectionStats:
    """
    Get the statistics of the collection of dataset URLs specified by the given select
    statement

    :param select_stmt: The given select statement
    :return: The statistics of the collection of dataset URLs

    Note: The execution of this function requires the Flask app's context
    """

    # Cache the result of the select statement to a temporary table
    tmp_tb = cache_result_to_tmp_tb(select_stmt, "tmp_tb")

    # base_q = select_stmt.subquery("base_q")
    base_q = select(tmp_tb).subquery("base_q")

    datalad_ds_stats = get_dl_ds_collection_stats(base_q)

    # Total number of datasets, as individual repos, without any deduplication
    ds_count = db.session.execute(
        select(func.count().label("ds_count")).select_from(base_q)
    ).scalar_one()

    return CollectionStats(
        datalad_ds_stats=datalad_ds_stats,
        pure_annex_ds_stats=get_pure_annex_ds_collection_stats(base_q),
        non_annex_ds_stats=get_non_annex_ds_collection_stats(base_q),
        summary=StatsSummary(
            unique_ds_count=datalad_ds_stats.unique_ds_stats.ds_count, ds_count=ds_count
        ),
    )
