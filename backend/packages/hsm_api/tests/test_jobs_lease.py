"""Unit tests for Firestore job lease / stale-running helpers."""

from datetime import UTC, datetime, timedelta

from hsm_core.jobs import running_lease_is_stale


def test_running_lease_is_stale_missing_or_bad_updated_at():
    assert running_lease_is_stale(None, stale_after_seconds=60) is True
    assert running_lease_is_stale("", stale_after_seconds=60) is True
    assert running_lease_is_stale("not-a-date", stale_after_seconds=60) is True


def test_running_lease_is_stale_fresh_vs_old():
    now = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    fresh = (now - timedelta(seconds=30)).isoformat()
    old = (now - timedelta(seconds=120)).isoformat()
    assert running_lease_is_stale(fresh, stale_after_seconds=60, now=now) is False
    assert running_lease_is_stale(old, stale_after_seconds=60, now=now) is True
