"""Cloud Run worker — Cloud Tasks POST /internal/worker/run."""

from __future__ import annotations

import logging
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Header, Request
from google.cloud import firestore
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from hsm_core.catalog_collections import PROJECTS_COLLECTION_ID
from hsm_core.catalog_write import upsert_project
from hsm_core.firestore_io import snapshot_to_document_dict
from hsm_core.env_background_sample import (
    sanitize_exception_for_client,
    write_project_explainability_background_parquet,
)
from hsm_core.env_cog_paths import resolve_env_cog_path_from_parts
from hsm_core.firebase_admin_app import init_firebase_admin
from hsm_core.jobs import JobDocument, get_job, try_claim_job_for_execution, update_job_status
from hsm_core.schemas_project import CatalogProject
from hsm_core.settings import Settings
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


def _environmental_cog_readable_for_sampling(abs_path: str) -> bool:
    if abs_path.startswith("gs://"):
        return True
    from pathlib import Path

    return Path(abs_path).is_file()


def _verify_worker_internal_secret(settings: Settings, header_value: str | None) -> None:
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
    settings: Settings,
    client: firestore.Client,
    job: JobDocument,
) -> None:
    job_id = job.job_id
    project_id = job.project_id
    if not project_id:
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="MISSING_PROJECT",
            error_message="job has no project_id",
        )
        return

    project = _load_project(client, project_id)
    if project is None:
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="PROJECT_NOT_FOUND",
            error_message="project not found in Firestore",
        )
        return

    artifact_root = project.driver_artifact_root
    cog_path = project.driver_cog_path
    band_defs = project.environmental_band_definitions

    if not artifact_root or not cog_path:
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="ENV_COG_REQUIRED",
            error_message="project has no environmental COG",
        )
        return
    if not band_defs:
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="BAND_DEFINITIONS_MISSING",
            error_message="project has no environmental band definitions",
        )
        return

    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="ENV_COG_PATH_INVALID",
            error_message="cannot resolve environmental COG path",
        )
        return
    if not _environmental_cog_readable_for_sampling(abs_path):
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="ENV_COG_NOT_READABLE",
            error_message="environmental COG not readable",
        )
        return

    n_samples = job.sample_rows if job.sample_rows is not None else settings.env_background_sample_rows
    storage = build_object_storage(settings)

    try:
        write_project_explainability_background_parquet(
            storage,
            settings,
            project_id,
            artifact_root,
            cog_path,
            band_defs,
            n_samples,
        )
    except Exception as e:
        logger.exception("explainability_background_failed job_id=%s", job_id)
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="EXPLAINABILITY_BACKGROUND_FAILED",
            error_message=sanitize_exception_for_client(e),
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
        update_job_status(
            client,
            job_id,
            status="failed",
            error_code="CATALOG_SAVE_FAILED",
            error_message=sanitize_exception_for_client(e),
        )
        return

    update_job_status(client, job_id, status="succeeded")
    logger.info("worker_job_ok job_id=%s project_id=%s", job_id, project_id)


def _dispatch_after_claim(settings: Settings, job_id: str, body_kind: str | None) -> None:
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
    if kind == "explainability_background_sample":
        _run_explainability_after_claim(settings, client, claimed)
        return

    update_job_status(
        client,
        job_id,
        status="failed",
        error_code="UNKNOWN_KIND",
        error_message=f"unsupported job kind {kind!r}",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        init_firebase_admin(settings)
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
        s: Settings = request.app.state.settings
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
