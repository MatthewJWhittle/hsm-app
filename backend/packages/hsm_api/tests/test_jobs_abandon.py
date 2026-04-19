"""Stale pending job abandonment (poll-side)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from hsm_core.jobs import JobDocument, try_abandon_stale_pending_job


def _pending_job(created_offset_seconds: float) -> JobDocument:
    created = (datetime.now(UTC) - timedelta(seconds=created_offset_seconds)).isoformat()
    return JobDocument(
        job_id="j1",
        status="pending",
        kind="explainability_background_sample",
        project_id="p1",
        created_by_uid=None,
        created_at=created,
        updated_at=created,
        sample_rows=8,
    )


def test_abandon_skipped_when_disabled():
    job = _pending_job(999_999)
    client = MagicMock()
    out = try_abandon_stale_pending_job(client, job, abandon_after_seconds=None)
    assert out.status == "pending"
    client.transaction.assert_not_called()


def test_abandon_skipped_for_young_pending():
    job = _pending_job(60)
    client = MagicMock()
    out = try_abandon_stale_pending_job(client, job, abandon_after_seconds=3600)
    assert out.status == "pending"
    client.transaction.assert_not_called()


def test_abandon_skipped_for_running():
    job = _pending_job(999_999).model_copy(update={"status": "running"})
    client = MagicMock()
    out = try_abandon_stale_pending_job(client, job, abandon_after_seconds=60)
    assert out.status == "running"
    client.transaction.assert_not_called()
