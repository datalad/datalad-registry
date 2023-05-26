from datalad.tests.utils_pytest import assert_result_count


def test_register():
    """
    Test that `registry_get_urls` is registered with DataLad.
    :return:
    """
    import datalad.api as ds

    assert hasattr(ds, "registry_get_urls")
    assert_result_count(ds.registry_get_urls(), 1, action="registry-get-urls")
