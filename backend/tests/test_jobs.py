"""Tests for generic job schemas and Firestore helpers (Phase 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from backend_api.jobs import (
    JOBS_COLLECTION_ID,
    JOB_IDEMPOTENCY_COLLECTION_ID,
    _claim_job_in_transaction,
    complete_job_failure,
    complete_job_success,
    create_job,
    get_job,
)
from backend_api.schemas_job import (
    Job,
    JobError,
    JobInputEnvironmentalCogReplace,
    JobKind,
    JobStatus,
    parse_job_input_payload,
    validate_job_input,
)
from backend_api.job_handlers.registry import get_job_handler
from backend_api.settings import Settings


def test_job_handler_registry_has_all_kinds():
    for k in JobKind:
        assert get_job_handler(k) is not None


def test_parse_job_input_payload_typed_union():
    p = parse_job_input_payload(
        JobKind.ENVIRONMENTAL_COG_REPLACE,
        {"project_id": "proj-1", "upload_session_id": "upload-1"},
    )
    assert isinstance(p, JobInputEnvironmentalCogReplace)
    assert p.project_id == "proj-1"


def test_validate_job_input_environmental_ok():
    out = validate_job_input(
        JobKind.ENVIRONMENTAL_COG_REPLACE,
        {"project_id": "proj-1", "upload_session_id": "upload-1"},
    )
    assert out["project_id"] == "proj-1"
    assert out["upload_session_id"] == "upload-1"
    assert out.get("environmental_band_definitions") is None


def test_validate_job_input_environmental_rejects_empty():
    with pytest.raises(ValidationError):
        validate_job_input(
            JobKind.ENVIRONMENTAL_COG_REPLACE,
            {"project_id": "", "upload_session_id": "u"},
        )


def test_validate_job_input_project_create_ok():
    out = validate_job_input(
        JobKind.PROJECT_CREATE_WITH_ENV_UPLOAD,
        {
            "project_id": "p1",
            "name": "N",
            "visibility": "public",
            "upload_session_id": "u1",
            "allowed_uids_json": "[]",
        },
    )
    assert out["project_id"] == "p1"
    assert out["upload_session_id"] == "u1"


def test_validate_job_input_model_create_ok():
    out = validate_job_input(
        JobKind.MODEL_CREATE_WITH_UPLOAD,
        {
            "model_id": "m1",
            "project_id": "p1",
            "species": "s",
            "activity": "a",
            "upload_session_id": "u1",
        },
    )
    assert out["model_id"] == "m1"


def test_validate_job_input_model_replace_ok():
    out = validate_job_input(
        JobKind.MODEL_REPLACE_SUITABILITY_COG,
        {
            "model_id": "m1",
            "upload_session_id": "u1",
            "species": "s",
            "activity": "a",
            "project_id": "p1",
        },
    )
    assert out["model_id"] == "m1"


def test_validate_job_input_explainability_bg_ok():
    out = validate_job_input(
        JobKind.EXPLAINABILITY_BACKGROUND_REGENERATE,
        {"project_id": "p1", "sample_rows": 100},
    )
    assert out["project_id"] == "p1"
    assert out["sample_rows"] == 100


def test_validate_job_input_unknown_kind():
    class _Unsupported:
        pass

    with pytest.raises(ValueError, match="unsupported job kind"):
        validate_job_input(_Unsupported(), {})  # type: ignore[arg-type]


def test_job_model_json_roundtrip():
    job = Job(
        id="j1",
        kind=JobKind.ENVIRONMENTAL_COG_REPLACE,
        status=JobStatus.QUEUED,
        input={"project_id": "p", "upload_session_id": "u"},
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    data = job.model_dump(mode="json")
    assert data["kind"] == "environmental_cog_replace"
    assert data["status"] == "queued"


def test_claim_job_in_transaction_claims_queued():
    snap = MagicMock()
    snap.exists = True
    snap.to_dict.return_value = {
        "kind": JobKind.ENVIRONMENTAL_COG_REPLACE.value,
        "status": JobStatus.QUEUED.value,
        "input": {"project_id": "p", "upload_session_id": "u"},
        "created_at": "t0",
        "updated_at": "t0",
    }
    doc_ref = MagicMock()
    doc_ref.get.return_value = snap
    transaction = MagicMock()

    out = _claim_job_in_transaction(transaction, doc_ref, "job-abc")

    assert out is not None
    assert out.id == "job-abc"
    assert out.status == JobStatus.RUNNING
    transaction.update.assert_called_once()
    call_kw = transaction.update.call_args[0][1]
    assert call_kw["status"] == JobStatus.RUNNING.value
    assert "started_at" in call_kw


def test_claim_job_in_transaction_skips_non_queued():
    snap = MagicMock()
    snap.exists = True
    snap.to_dict.return_value = {"status": JobStatus.RUNNING.value}
    doc_ref = MagicMock()
    doc_ref.get.return_value = snap
    assert _claim_job_in_transaction(MagicMock(), doc_ref, "j") is None


class _FakeSnapshot:
    def __init__(self, exists: bool, data: dict | None = None) -> None:
        self.exists = exists
        self._data = data or {}

    def to_dict(self) -> dict:
        return dict(self._data)


class _FakeDocRef:
    def __init__(self, doc_id: str, store: dict[str, dict]) -> None:
        self.id = doc_id
        self._store = store

    def get(self, transaction=None) -> _FakeSnapshot:
        if self.id not in self._store:
            return _FakeSnapshot(False)
        return _FakeSnapshot(True, dict(self._store[self.id]))

    def set(self, data: dict) -> None:
        self._store[self.id] = dict(data)

    def update(self, data: dict) -> None:
        cur = dict(self._store.get(self.id, {}))
        for k, v in data.items():
            from google.cloud import firestore as fs

            if v is fs.DELETE_FIELD:
                cur.pop(k, None)
            else:
                cur[k] = v
        self._store[self.id] = cur


class _FakeCollection:
    def __init__(self, name: str, db: dict[str, dict[str, dict]]) -> None:
        self._name = name
        self._db = db

    def document(self, doc_id: str) -> _FakeDocRef:
        if self._name not in self._db:
            self._db[self._name] = {}
        return _FakeDocRef(doc_id, self._db[self._name])


class _FakeTransaction:
    """Minimal write batch so transactional create_job tests avoid real RPCs."""

    def set(self, doc_ref: _FakeDocRef, data: dict, merge: bool = False) -> None:
        doc_ref.set(data)


class _FakeFirestoreClient:
    def __init__(self) -> None:
        self._db: dict[str, dict[str, dict]] = {}

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(name, self._db)

    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction()


def _passthrough_transactional(fn):
    """Run the wrapped function once (no begin/commit); use with fake Firestore."""

    class _Inner:
        def __call__(self, transaction, *args, **kwargs):
            return fn(transaction, *args, **kwargs)

    return _Inner()


def test_create_job_and_get_roundtrip():
    fake = _FakeFirestoreClient()
    settings = Settings(google_cloud_project="test-project")
    with patch("backend_api.jobs.firestore.Client", return_value=fake):
        job = create_job(
            settings,
            kind=JobKind.ENVIRONMENTAL_COG_REPLACE,
            input={"project_id": "p1", "upload_session_id": "u1"},
            created_by_uid="admin-1",
        )
        assert job.status == JobStatus.QUEUED
        assert job.created_by_uid == "admin-1"
        loaded = get_job(settings, job.id)
        assert loaded is not None
        assert loaded.kind == JobKind.ENVIRONMENTAL_COG_REPLACE
        assert loaded.input["project_id"] == "p1"
        assert loaded.input["upload_session_id"] == "u1"
        assert JOBS_COLLECTION_ID in fake._db
        assert job.id in fake._db[JOBS_COLLECTION_ID]


def test_create_job_idempotency_returns_same_job():
    fake = _FakeFirestoreClient()
    settings = Settings(google_cloud_project="test-project")
    with (
        patch("backend_api.jobs.firestore.Client", return_value=fake),
        patch(
            "backend_api.jobs.firestore.transactional",
            _passthrough_transactional,
        ),
    ):
        a = create_job(
            settings,
            kind=JobKind.ENVIRONMENTAL_COG_REPLACE,
            input={"project_id": "p1", "upload_session_id": "u1"},
            idempotency_key="key-1",
        )
        b = create_job(
            settings,
            kind=JobKind.ENVIRONMENTAL_COG_REPLACE,
            input={"project_id": "p1", "upload_session_id": "u1"},
            idempotency_key="key-1",
        )
        assert a.id == b.id
        assert JOB_IDEMPOTENCY_COLLECTION_ID in fake._db


def test_complete_job_success_and_failure():
    fake = _FakeFirestoreClient()
    settings = Settings(google_cloud_project="test-project")
    job_id = "job-1"
    now = datetime.now(UTC).isoformat()
    fake._db[JOBS_COLLECTION_ID] = {
        job_id: {
            "kind": JobKind.ENVIRONMENTAL_COG_REPLACE.value,
            "status": JobStatus.RUNNING.value,
            "input": {"project_id": "p", "upload_session_id": "u"},
            "created_at": now,
            "updated_at": now,
            "started_at": now,
            "error": {"code": "X", "message": "old"},
        }
    }
    with patch("backend_api.jobs.firestore.Client", return_value=fake):
        complete_job_success(settings, job_id)
        doc = fake._db[JOBS_COLLECTION_ID][job_id]
        assert doc["status"] == JobStatus.SUCCEEDED.value
        assert "error" not in doc

    fake._db[JOBS_COLLECTION_ID][job_id] = {
        "kind": JobKind.ENVIRONMENTAL_COG_REPLACE.value,
        "status": JobStatus.RUNNING.value,
        "input": {"project_id": "p", "upload_session_id": "u"},
        "created_at": now,
        "updated_at": now,
    }
    with patch("backend_api.jobs.firestore.Client", return_value=fake):
        complete_job_failure(
            settings,
            job_id,
            JobError(code="TEST", message="failed", detail="d"),
        )
        doc = fake._db[JOBS_COLLECTION_ID][job_id]
        assert doc["status"] == JobStatus.FAILED.value
        assert doc["error"]["code"] == "TEST"
