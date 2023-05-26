def test_register():
    """
    Test that `registry_get_urls` is registered with DataLad
    """
    import datalad.api as ds

    assert hasattr(ds, "registry_get_urls")
