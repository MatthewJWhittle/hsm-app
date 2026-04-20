"""Cloud Run worker — Cloud Tasks POST /internal/worker/run."""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Header, Request
from google.cloud import firestore
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from hsm_core.catalog_collections import PROJECTS_COLLECTION_ID
from hsm_core.catalog_write import upsert_project
from hsm_core.firestore_io import snapshot_to_document_dict
from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.env_background_sample import (
    sanitize_exception_for_client,
    write_project_explainability_background_parquet,
)
from hsm_core.explainability_job_preflight import (
    ExplainabilityJobPreflightError,
    validate_catalog_project_for_explainability_sample,
)
from hsm_core.job_error_codes import JobErrorCode
from hsm_core.jobs import (
    JobDocument,
    explainability_sample_rows_for_job,
    fail_job,
    get_job,
    try_claim_job_for_execution,
    update_job_status,
)
from hsm_core.schemas_project import CatalogProject
from hsm_core.settings import WorkerSettings
from hsm_core.storage import EXPLAINABILITY_BACKGROUND_FILENAME, build_object_storage

logger = logging.getLogger(__name__)


class TaskPayload(BaseModel):
    job_id: str = Field(..., min_length=1)
    kind: str | None = Field(
        default=None,
        description="Optional echo of kind; routing uses Firestore job document after claim.",
    )


def _load_project(client: firestore.Client, project_id: str) -> CatalogProject | None:
    snap = client.collection(PROJECTS_COLLECTION_ID).document(project_id).get()
    if not snap.exists:
        return None
    return CatalogProject.model_validate(snapshot_to_document_dict(snap))


def _verify_worker_internal_secret(settings: WorkerSettings, header_value: str | None) -> None:
    expected = settings.worker_internal_secret
    if not expected:
        return
    got = header_value or ""
    if len(got) != len(expected) or not secrets.compare_digest(
        got.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(status_code=403, detail="Forbidden")


def _run_explainability_after_claim(
    settings: WorkerSettings,
    client: firestore.Client,
    job: JobDocument,
) -> None:
    job_id = job.job_id
    project_id = job.project_id
    if not project_id:
        fail_job(
            client,
            job_id,
            code=JobErrorCode.MISSING_PROJECT,
            message="job has no project_id",
        )
        return

    project = _load_project(client, project_id)
    if project is None:
        fail_job(
            client,
            job_id,
            code=JobErrorCode.PROJECT_NOT_FOUND,
            message="project not found in Firestore",
        )
        return

    try:
        validate_catalog_project_for_explainability_sample(project)
    except ExplainabilityJobPreflightError as e:
        fail_job(client, job_id, code=e.code, message=e.message)
        return

    artifact_root = project.driver_artifact_root
    cog_path = project.driver_cog_path
    band_defs = project.environmental_band_definitions
    n_samples = explainability_sample_rows_for_job(
        job, settings_default=settings.env_background_sample_rows
    )
    storage = build_object_storage(settings)
    artifact_read = ArtifactReadRuntime(settings)

    try:
        write_project_explainability_background_parquet(
            storage,
            settings,
            project_id,
            artifact_root,
            cog_path,
            band_defs,
            n_samples,
            artifact_read,
        )
    except Exception as e:
        logger.exception("explainability_background_failed job_id=%s", job_id)
        fail_job(
            client,
            job_id,
            code=JobErrorCode.EXPLAINABILITY_BACKGROUND_FAILED,
            message=sanitize_exception_for_client(e),
        )
        return

    now = datetime.now(UTC).isoformat()
    updated = project.model_copy(
        update={
            "explainability_background_path": EXPLAINABILITY_BACKGROUND_FILENAME,
            "explainability_background_sample_rows": n_samples,
            "explainability_background_generated_at": now,
            "updated_at": now,
        }
    )
    try:
        upsert_project(settings, updated)
    except Exception as e:
        logger.exception("catalog_save_failed job_id=%s", job_id)
        fail_job(
            client,
            job_id,
            code=JobErrorCode.CATALOG_SAVE_FAILED,
            message=sanitize_exception_for_client(e),
        )
        return

    update_job_status(client, job_id, status="succeeded")
    logger.info("worker_job_ok job_id=%s project_id=%s", job_id, project_id)


WorkerJobHandler = Callable[[WorkerSettings, firestore.Client, JobDocument], None]

JOB_HANDLERS: dict[str, WorkerJobHandler] = {
    "explainability_background_sample": _run_explainability_after_claim,
}


def _dispatch_after_claim(settings: WorkerSettings, job_id: str, body_kind: str | None) -> None:
    client = firestore.Client(project=settings.google_cloud_project)
    stale_after = (
        settings.worker_http_deadline_seconds + settings.worker_stale_running_grace_seconds
    )
    claimed = try_claim_job_for_execution(
        client, job_id, stale_running_after_seconds=stale_after
    )
    if claimed is None:
        existing = get_job(client, job_id)
        if existing and existing.status in ("succeeded", "failed"):
            logger.info("worker_job_skip job_id=%s status=%s", job_id, existing.status)
            return
        if existing and existing.status == "running":
            logger.info(
                "worker_job_skip job_id=%s status=running (lease still fresh)",
                job_id,
            )
            return
        raise RuntimeError("job not found or could not be claimed")

    if body_kind is not None and body_kind != claimed.kind:
        logger.warning(
            "worker_task_kind_mismatch job_id=%s body_kind=%s doc_kind=%s",
            job_id,
            body_kind,
            claimed.kind,
        )

    kind = claimed.kind
    handler = JOB_HANDLERS.get(kind)
    if handler is None:
        fail_job(
            client,
            job_id,
            code=JobErrorCode.UNKNOWN_KIND,
            message=f"unsupported job kind {kind!r}",
        )
        return
    handler(settings, client, claimed)


def create_app(settings: WorkerSettings | None = None) -> FastAPI:
    settings = settings or WorkerSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        yield

    app = FastAPI(
        title="HSM Worker",
        lifespan=lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/internal/worker/run")
    async def run_task(
        request: Request,
        payload: TaskPayload,
        x_hsm_worker_secret: str | None = Header(default=None, alias="X-HSM-Worker-Secret"),
    ):
        s: WorkerSettings = request.app.state.settings
        _verify_worker_internal_secret(s, x_hsm_worker_secret)
        try:
            await run_in_threadpool(_dispatch_after_claim, s, payload.job_id, payload.kind)
        except HTTPException:
            raise
        except Exception:
            logger.exception("worker_task_failed job_id=%s", payload.job_id)
            raise HTTPException(status_code=500, detail="worker task failed") from None
        return {"ok": True}

    return app


app = create_app()
