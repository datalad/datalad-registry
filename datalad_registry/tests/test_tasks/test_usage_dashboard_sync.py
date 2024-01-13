import pytest


# Use fixture `flask_app` to ensure that the Celery app is initialized,
# and the db and the cache are clean
@pytest.mark.usefixtures("flask_app")
@pytest.mark.parametrize(
    ("dashboard_collection", "registered_repos", "expected_submitted_repos"),
    [
        (
            """
                {
                    "github": [
                        {
                            "id": 728117155,
                            "name": "1104HARI/fail2ban",
                            "url": "https://github.com/1104HARI/fail2ban",
                            "stars": 0,
                            "dataset": false,
                            "run": true,
                            "container_run": false,
                            "status": "active"
                        },
                        {
                            "id": 728117263,
                            "name": "1104HARI/s3cmd",
                            "url": "https://github.com/1104HARI/s3cmd",
                            "stars": 0,
                            "dataset": false,
                            "run": true,
                            "container_run": false,
                            "status": "active"
                        },
                        {
                            "id": 271283042,
                            "name": "314eter/recoll",
                            "url": "https://github.com/314eter/recoll",
                            "stars": 30,
                            "dataset": false,
                            "run": true,
                            "container_run": false,
                            "status": "gone"
                        }
                    ],
                    "osf": [
                        {
                            "url": "https://osf.io/4cdw3/",
                            "id": "4cdw3",
                            "name": "3am-complex-orientation-phantoms",
                            "status": "active"
                        },
                        {
                            "url": "https://osf.io/u5w4j/",
                            "id": "u5w4j",
                            "name": "AOMICPIOP2DemoDataset",
                            "status": "active"
                        }
                    ],
                    "gin": [
                        {
                            "id": 10064,
                            "name": "AIDAqc_datasets/117_m_RT_Vr",
                            "url": "https://gin.g-node.org/AIDAqc_datasets/117_m_RT_Vr",
                            "stars": 0,
                            "status": "gone"
                        },
                        {
                            "id": 10158,
                            "name": "AIDAqc_datasets/7_m_RT_Bo",
                            "url": "https://gin.g-node.org/AIDAqc_datasets/7_m_RT_Bo",
                            "stars": 0,
                            "status": "active"
                        }
                    ]
                }
                """,
            {
                "https://github.com/1104HARI/s3cmd.git",
                "https://gin.g-node.org/AIDAqc_datasets/7_m_RT_Bo",
                "http://db/example.git",
            },
            {
                "https://github.com/1104HARI/fail2ban.git",
                "https://github.com/314eter/recoll.git",
                "https://gin.g-node.org/AIDAqc_datasets/117_m_RT_Vr",
            },
        ),
    ],
)
def test_usage_dashboard_sync(
    dashboard_collection: str,
    registered_repos: set[str],
    expected_submitted_repos: set[str],
    monkeypatch,
):
    """
    Test running the Celery task `usage_dashboard_sync`

    :param dashboard_collection: The JSON string representing the collection
                                 of git repos in the usage dashboard
    :param registered_repos: The set of repos, represented in their respective
                             clone URL, that are already registered in the
                             Datalad-Registry instance.
    :param expected_submitted_repos: The set of repos, represented in their respective
                                     clone URL, that are expected to be submitted to the
                                     DataLad-Registry instance for registration

    """
    pass
