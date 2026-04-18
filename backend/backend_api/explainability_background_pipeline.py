"""Regenerate explainability background Parquet from a project's environmental COG."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from backend_api.api_errors import validation_error
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_project
from backend_api.env_background_sample import (
    sanitize_exception_for_client,
    write_project_explainability_background_parquet,
)
from backend_api.project_manifest import resolve_env_cog_path_from_parts
from backend_api.schemas_project import CatalogProject
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage
from backend_api.routers.catalog_upload_utils import reload_catalog_threaded


async def regenerate_explainability_background_pipeline(
    request: Request,
    settings: Settings,
    storage: ObjectStorage,
    catalog: CatalogService,
    project_id: str,
    sample_rows: int | None,
) -> CatalogProject:
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    band_defs = existing.environmental_band_definitions

    if not artifact_root or not cog_path:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_REQUIRED",
                "project has no environmental COG; upload one first",
            ),
        )
    if not band_defs:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "BAND_DEFINITIONS_MISSING",
                "project has no environmental band definitions; save band names first",
            ),
        )

    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_PATH_INVALID",
                "cannot resolve environmental COG path",
            ),
        )
    if not abs_path.startswith("gs://") and not Path(abs_path).is_file():
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "ENV_COG_NOT_ON_DISK",
                "environmental COG not found on server",
            ),
        )

    n_samples = (
        sample_rows
        if sample_rows is not None
        else settings.env_background_sample_rows
    )

    def _bg() -> None:
        write_project_explainability_background_parquet(
            storage,
            settings,
            project_id,
            artifact_root,
            cog_path,
            band_defs,
            n_samples,
        )

    try:
        await run_in_threadpool(_bg)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "EXPLAINABILITY_BACKGROUND_FAILED",
                "could not build explainability background sample from COG",
                context={"cause": sanitize_exception_for_client(e)},
            ),
        ) from e

    now = datetime.now(UTC).isoformat()
    project = existing.model_copy(
        update={
            "explainability_background_path": EXPLAINABILITY_BACKGROUND_FILENAME,
            "explainability_background_sample_rows": n_samples,
            "explainability_background_generated_at": now,
            "updated_at": now,
        }
    )

    def _persist() -> None:
        upsert_project(settings, project)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=validation_error(
                "CATALOG_SAVE_FAILED",
                f"could not save catalog: {e}",
            ),
        ) from e

    await reload_catalog_threaded(request)
    return project
