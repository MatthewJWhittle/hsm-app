"""Environmental COG replace pipeline (admin route + background worker)."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from backend_api.api_errors import validation_error
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_project
from backend_api.cog_validation import CogValidationError
from backend_api.env_background_sample import (
    sanitize_exception_for_client,
    write_project_explainability_background_parquet,
)
from backend_api.env_cog_bands import (
    band_definitions_for_upload_path,
    infer_band_definitions_from_form,
)
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_path_threaded,
)
from backend_api.schemas_project import CatalogProject, EnvironmentalBandDefinition
from backend_api.schemas_upload import UploadSession
from backend_api.settings import Settings
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage
from backend_api.upload_session_ingest import (
    best_effort_fail,
    best_effort_mark,
    download_upload_session_to_tempfile,
    write_upload_file_to_tempfile,
)

logger = logging.getLogger(__name__)


def _ev_422(
    code: str, message: str, *, context: dict | None = None
) -> HTTPException:
    return HTTPException(
        status_code=422, detail=validation_error(code, message, context=context)
    )


def _upload_error_context(
    *,
    project_id: str,
    phase: str,
    uploaded_session: UploadSession | None,
    extra: dict | None = None,
) -> dict:
    ctx: dict = {
        "project_id": project_id,
        "phase": phase,
        "upload_session_id": uploaded_session.id if uploaded_session is not None else None,
    }
    if extra:
        ctx.update(extra)
    return ctx


async def replace_project_environmental_cogs_pipeline(
    request: Request,
    settings: Settings,
    storage: ObjectStorage,
    catalog: CatalogService,
    project_id: str,
    file: UploadFile | None,
    upload_session_id: str | None,
    environmental_band_definitions: str | None,
    infer_band_definitions: str | None,
) -> CatalogProject:
    """Create/replace a project's active environmental COG (shared sync implementation)."""
    existing = catalog.get_project(project_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="project not found")
    logger.info(
        "project_replace_env_cog_start project_id=%s has_multipart=%s has_session=%s",
        project_id,
        file is not None,
        bool(upload_session_id),
    )

    if file is not None and upload_session_id:
        raise _ev_422(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )
    if file is None and upload_session_id is None:
        raise _ev_422(
            "MISSING_UPLOAD",
            "provide multipart file or upload_session_id",
        )

    artifact_root = existing.driver_artifact_root
    cog_path = existing.driver_cog_path
    new_band_defs: list[EnvironmentalBandDefinition] | None = (
        existing.environmental_band_definitions
    )
    inference_notes: list[str] | None = None

    uploaded_session: UploadSession | None = None
    upload_temp_path: Path | None = None
    if upload_session_id:
        upload_temp_path, uploaded_session = await run_in_threadpool(
            download_upload_session_to_tempfile,
            settings,
            upload_session_id,
            purpose="project update",
        )
        logger.info(
            "project_replace_env_cog_ingest_session project_id=%s upload_session_id=%s",
            project_id,
            upload_session_id,
        )
    elif file is not None:
        upload_temp_path = await write_upload_file_to_tempfile(
            file,
            max_bytes=settings.max_environmental_upload_bytes,
        )
        logger.info("project_replace_env_cog_ingest_multipart project_id=%s", project_id)

    try:
        if upload_temp_path is not None:
            upload_size = os.path.getsize(str(upload_temp_path))
            logger.info(
                "project_replace_env_cog_upload_size project_id=%s upload_bytes=%s upload_session_id=%s",
                project_id,
                upload_size,
                uploaded_session.id if uploaded_session else None,
            )
            if upload_size <= 0:
                raise _ev_422(
                    "EMPTY_FILE",
                    "empty file",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="ingest",
                        uploaded_session=uploaded_session,
                    ),
                )
            if upload_size > settings.max_environmental_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=validation_error(
                        "UPLOAD_TOO_LARGE",
                        f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                        context=_upload_error_context(
                            project_id=project_id,
                            phase="ingest",
                            uploaded_session=uploaded_session,
                            extra={"max_bytes": settings.max_environmental_upload_bytes},
                        ),
                    ),
                )
            uploaded_session = await run_in_threadpool(
                best_effort_mark,
                settings,
                uploaded_session,
                status="validating",
                stage="validate",
                context="project-update-validate",
            )
            try:
                logger.info("project_replace_env_cog_validate_start project_id=%s", project_id)
                await validate_cog_path_threaded(str(upload_temp_path))
                logger.info("project_replace_env_cog_validate_ok project_id=%s", project_id)
            except CogValidationError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="validate",
                    error_code=e.code,
                    error_message=e.message,
                    context="project-update-cog-validate-failed",
                )
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        e.code,
                        e.message,
                        context=_upload_error_context(
                            project_id=project_id,
                            phase="validate",
                            uploaded_session=uploaded_session,
                            extra=e.context or None,
                        ),
                    ),
                ) from e

            def _write() -> tuple[str, str]:
                return storage.write_project_driver_cog_from_path(
                    project_id, str(upload_temp_path)
                )

            try:
                artifact_root, cog_path = await run_in_threadpool(_write)
                logger.info(
                    "project_replace_env_cog_persist_cog_ok project_id=%s artifact_root=%s",
                    project_id,
                    artifact_root,
                )
            except ValueError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="persist",
                    error_code="STORAGE_LAYOUT_INVALID",
                    error_message=str(e),
                    context="project-update-storage-layout-invalid",
                )
                raise HTTPException(
                    status_code=400,
                    detail=validation_error(
                        "STORAGE_LAYOUT_INVALID",
                        str(e),
                        context=_upload_error_context(
                            project_id=project_id,
                            phase="persist",
                            uploaded_session=uploaded_session,
                        ),
                    ),
                ) from e
            except Exception as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="persist",
                    error_code="STORAGE_WRITE_FAILED",
                    error_message=str(e),
                    context="project-update-storage-write-failed",
                )
                raise HTTPException(
                    status_code=503,
                    detail=validation_error(
                        "STORAGE_WRITE_FAILED",
                        f"could not store file: {e}",
                        context=_upload_error_context(
                            project_id=project_id,
                            phase="persist",
                            uploaded_session=uploaded_session,
                        ),
                    ),
                ) from e

            uploaded_session = await run_in_threadpool(
                best_effort_mark,
                settings,
                uploaded_session,
                status="deriving",
                stage="derive",
                context="project-update-derive",
            )
            try:
                logger.info("project_replace_env_cog_derive_bands_start project_id=%s", project_id)

                def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                    return band_definitions_for_upload_path(
                        str(upload_temp_path),
                        environmental_band_definitions,
                        infer_band_definitions=infer_band_definitions_from_form(
                            infer_band_definitions
                        ),
                    )

                new_band_defs, infer_notes = await run_in_threadpool(_defs)
                inference_notes = infer_notes if infer_notes else None
                logger.info(
                    "project_replace_env_cog_derive_bands_ok project_id=%s band_count=%s",
                    project_id,
                    len(new_band_defs) if new_band_defs else 0,
                )
            except ValueError as e:
                await run_in_threadpool(
                    best_effort_fail,
                    settings,
                    uploaded_session,
                    stage="derive",
                    error_code="BAND_DEFINITIONS",
                    error_message=str(e),
                    context="project-update-band-definitions",
                )
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "BAND_DEFINITIONS",
                        str(e),
                        context=_upload_error_context(
                            project_id=project_id,
                            phase="derive",
                            uploaded_session=uploaded_session,
                        ),
                    ),
                ) from e
    finally:
        if upload_temp_path is not None:
            upload_temp_path.unlink(missing_ok=True)

    new_explain_bg_path = existing.explainability_background_path
    new_explain_bg_rows = existing.explainability_background_sample_rows
    new_explain_bg_at = existing.explainability_background_generated_at
    if new_band_defs and artifact_root and cog_path:
        try:
            logger.info(
                "project_replace_env_cog_background_start project_id=%s sample_rows=%s",
                project_id,
                settings.env_background_sample_rows,
            )

            def _bg() -> None:
                write_project_explainability_background_parquet(
                    storage,
                    settings,
                    project_id,
                    artifact_root,
                    cog_path,
                    new_band_defs,
                    settings.env_background_sample_rows,
                )

            await run_in_threadpool(_bg)
            new_explain_bg_path = EXPLAINABILITY_BACKGROUND_FILENAME
            new_explain_bg_rows = settings.env_background_sample_rows
            new_explain_bg_at = datetime.now(UTC).isoformat()
            logger.info(
                "project_replace_env_cog_background_ok project_id=%s sample_rows=%s",
                project_id,
                new_explain_bg_rows,
            )
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="derive",
                error_code="EXPLAINABILITY_BACKGROUND_FAILED",
                error_message=str(e),
                context="project-update-explainability-background",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EXPLAINABILITY_BACKGROUND_FAILED",
                    "could not build explainability background sample from COG",
                    context=_upload_error_context(
                        project_id=project_id,
                        phase="derive",
                        uploaded_session=uploaded_session,
                        extra={"cause": sanitize_exception_for_client(e)},
                    ),
                ),
            ) from e

    now = datetime.now(UTC).isoformat()
    project = existing.model_copy(
        update={
            "driver_artifact_root": artifact_root,
            "driver_cog_path": cog_path,
            "environmental_band_definitions": new_band_defs,
            "band_inference_notes": inference_notes,
            "explainability_background_path": new_explain_bg_path,
            "explainability_background_sample_rows": new_explain_bg_rows,
            "explainability_background_generated_at": new_explain_bg_at,
            "updated_at": now,
        }
    )

    def _persist() -> None:
        upsert_project(settings, project)

    uploaded_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        uploaded_session,
        status="deriving",
        stage="persist",
        context="project-update-persist",
    )
    try:
        await run_in_threadpool(_persist)
        logger.info("project_replace_env_cog_catalog_save_ok project_id=%s", project_id)
    except Exception as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            uploaded_session,
            stage="persist",
            error_code="CATALOG_SAVE_FAILED",
            error_message=str(e),
            context="project-update-catalog-save",
        )
        raise HTTPException(
            status_code=503,
            detail=validation_error(
                "CATALOG_SAVE_FAILED",
                f"could not save catalog: {e}",
                context=_upload_error_context(
                    project_id=project_id,
                    phase="persist",
                    uploaded_session=uploaded_session,
                ),
            ),
        ) from e

    await reload_catalog_threaded(request)
    if uploaded_session is not None and uploaded_session.status != "ready":
        await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="ready",
            stage="done",
            context="project-update-done",
        )
    return project
