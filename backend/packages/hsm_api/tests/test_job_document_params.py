"""Job document ``params`` blob (kind-specific fields)."""

from hsm_core.jobs import (
    JobDocument,
    create_job_document,
    explainability_sample_rows_for_job,
)


def test_create_job_document_sets_params_when_sample_rows_given():
    job = create_job_document(
        kind="explainability_background_sample",
        project_id="p1",
        created_by_uid="u1",
        sample_rows=99,
    )
    assert job.sample_rows == 99
    assert job.params == {"sample_rows": 99}


def test_create_job_document_omits_params_when_sample_rows_unset():
    job = create_job_document(
        kind="explainability_background_sample",
        project_id="p1",
        created_by_uid=None,
        sample_rows=None,
    )
    assert job.sample_rows is None
    assert job.params is None


def test_explainability_sample_rows_prefers_params_over_legacy_field():
    job = JobDocument(
        job_id="j",
        status="pending",
        kind="explainability_background_sample",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        sample_rows=1,
        params={"sample_rows": 42},
    )
    assert explainability_sample_rows_for_job(job, settings_default=256) == 42


def test_explainability_sample_rows_legacy_only():
    job = JobDocument(
        job_id="j",
        status="pending",
        kind="explainability_background_sample",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        sample_rows=7,
    )
    assert explainability_sample_rows_for_job(job, settings_default=256) == 7


def test_explainability_sample_rows_falls_back_to_settings_default():
    job = create_job_document(
        kind="explainability_background_sample",
        project_id="p1",
        created_by_uid=None,
        sample_rows=None,
    )
    assert explainability_sample_rows_for_job(job, settings_default=256) == 256
