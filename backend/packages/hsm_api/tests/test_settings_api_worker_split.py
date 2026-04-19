"""WorkerSettings vs ApiSettings: dispatcher rules apply only to the API model."""

import pytest

from hsm_core.settings import ApiSettings, WorkerSettings


def test_worker_settings_allows_staging_without_cloud_tasks():
    s = WorkerSettings(
        app_env="staging",
        google_cloud_project="p",
        storage_backend="gcs",
        gcs_bucket="b",
    )
    assert s.app_env == "staging"


def test_api_settings_rejects_staging_without_cloud_tasks():
    with pytest.raises(ValueError, match="USE_CLOUD_TASKS"):
        ApiSettings(
            app_env="staging",
            use_cloud_tasks=False,
        )


def test_api_settings_requires_queue_fields_when_cloud_tasks_enabled():
    with pytest.raises(ValueError, match="CLOUD_TASKS_QUEUE"):
        ApiSettings(
            app_env="staging",
            use_cloud_tasks=True,
            cloud_tasks_queue=None,
            cloud_tasks_location="us-central1",
            cloud_tasks_oidc_service_account="sa@x.iam.gserviceaccount.com",
            worker_task_url="https://worker.example/run",
        )
