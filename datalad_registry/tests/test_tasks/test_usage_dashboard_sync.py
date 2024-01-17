import json

import pytest
import responses

from datalad_registry.blueprints.api import DATASET_URLS_PATH
from datalad_registry.models import RepoUrl, db
from datalad_registry.tasks import usage_dashboard_sync
from datalad_registry.tasks.utils.usage_dashboard import DASHBOARD_COLLECTION_URL


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
                            "status": "active"
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
                "https://gin.g-node.org/AIDAqc_datasets/117_m_RT_Vr",
            },
        ),
        (
            """
                    {
                        "github": [],
                        "osf": [],
                        "gin": []
                    }""",
            {
                "https://github.com/1104HARI/s3cmd.git",
                "https://gin.g-node.org/AIDAqc_datasets/7_m_RT_Bo",
                "http://db/example.git",
            },
            set(),
        ),
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
                            "status": "active"
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
            set(),
            {
                "https://github.com/1104HARI/fail2ban.git",
                "https://github.com/1104HARI/s3cmd.git",
                "https://gin.g-node.org/AIDAqc_datasets/117_m_RT_Vr",
                "https://gin.g-node.org/AIDAqc_datasets/7_m_RT_Bo",
            },
        ),
    ],
)
@pytest.mark.parametrize("post_resp_status_code", [201, 202, 400])
@responses.activate
def test_usage_dashboard_sync(
    dashboard_collection: str,
    registered_repos: set[str],
    expected_submitted_repos: set[str],
    post_resp_status_code,
    flask_app,
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
    # Mock the response from the datalad-usage-dashboard
    responses.get(DASHBOARD_COLLECTION_URL, json=json.loads(dashboard_collection))

    # Insert the registered repos to the database
    with flask_app.app_context():
        db.session.add_all(RepoUrl(url=url) for url in registered_repos)
        db.session.commit()

    # Mock the response from POSTing to the DataLad-Registry instance
    responses.post(
        flask_app.config["DATALAD_REGISTRY_WEB_API_URL"] + f"/{DATASET_URLS_PATH}",
        status=post_resp_status_code,
    )

    sync_result = usage_dashboard_sync()

    if post_resp_status_code == 201:
        assert sync_result["failed_submissions_count"] == 0
        assert sync_result["update_requested_repos_count"] == 0
        assert sync_result["newly_registered_repos_count"] == len(
            expected_submitted_repos
        )
        assert sync_result["failed_submissions"] == []
        assert sync_result["update_requested_repos"] == []
        assert set(sync_result["newly_registered_repos"]) == expected_submitted_repos
    elif post_resp_status_code == 202:
        assert sync_result["failed_submissions_count"] == 0
        assert sync_result["update_requested_repos_count"] == len(
            expected_submitted_repos
        )
        assert sync_result["newly_registered_repos_count"] == 0
        assert sync_result["failed_submissions"] == []
        assert set(sync_result["update_requested_repos"]) == expected_submitted_repos
        assert sync_result["newly_registered_repos"] == []
    else:
        assert sync_result["failed_submissions_count"] == len(expected_submitted_repos)
        assert sync_result["update_requested_repos_count"] == 0
        assert sync_result["newly_registered_repos_count"] == 0

        failed_submissions = sync_result["failed_submissions"]
        assert all(
            submission["status_code"] == post_resp_status_code
            for submission in failed_submissions
        )
        assert (
            set(submission["url"] for submission in failed_submissions)
            == expected_submitted_repos
        )

        assert sync_result["update_requested_repos"] == []
        assert sync_result["newly_registered_repos"] == []
