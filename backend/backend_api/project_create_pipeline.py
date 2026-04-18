"""Project create with environmental COG (multipart or upload session)."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from backend_api.api_errors import validation_error
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


def _proj_422(
    code: str, message: str, *, context: dict | None = None
) -> HTTPException:
    return HTTPException(
        status_code=422, detail=validation_error(code, message, context=context)
    )


def _proj_503(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=503, detail=validation_error(code, message)
    )


async def create_project_with_environmental_cog_pipeline(
    request: Request,
    settings: Settings,
    storage: ObjectStorage,
    *,
    project_id: str,
    name: str,
    description: str | None,
    visibility_v: str,
    uids: list[str],
    upload_session_id: str | None,
    file: UploadFile | None,
    environmental_band_definitions: str | None,
    infer_band_definitions: str | None,
) -> CatalogProject:
    """
    Create a new project row with an environmental COG from multipart or upload session.

    Exactly one of ``upload_session_id`` or ``file`` must be set.
    """
    if (upload_session_id is not None) == (file is not None):
        raise _proj_422(
            "UPLOAD_CONFLICT",
            "provide either multipart file or upload_session_id, not both",
        )

    artifact_root: str | None = None
    cog_path: str | None = None
    band_defs: list[EnvironmentalBandDefinition] | None = None
    inference_notes: list[str] | None = None
    uploaded_session = None
    upload_temp_path: Path | None = None
    if upload_session_id:
        upload_temp_path, uploaded_session = await run_in_threadpool(
            download_upload_session_to_tempfile,
            settings,
            upload_session_id,
            purpose="project create",
        )
        logger.info(
            "project_create_ingest_session project_id=%s upload_session_id=%s",
            project_id,
            upload_session_id,
        )
    else:
        upload_temp_path = await write_upload_file_to_tempfile(
            file,  # type: ignore[arg-type]
            max_bytes=settings.max_environmental_upload_bytes,
        )
        logger.info("project_create_ingest_multipart project_id=%s", project_id)

    try:
        upload_size = os.path.getsize(str(upload_temp_path))
        logger.info(
            "project_create_upload_size project_id=%s upload_bytes=%s upload_session_id=%s",
            project_id,
            upload_size,
            uploaded_session.id if uploaded_session else None,
        )
        if upload_size <= 0:
            raise _proj_422("EMPTY_FILE", "empty file")
        if upload_size > settings.max_environmental_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=validation_error(
                    "UPLOAD_TOO_LARGE",
                    f"file exceeds max size {settings.max_environmental_upload_bytes} bytes",
                    context={"max_bytes": settings.max_environmental_upload_bytes},
                ),
            )
        uploaded_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="validating",
            stage="validate",
            context="project-create-validate",
        )
        try:
            logger.info("project_create_validate_start project_id=%s", project_id)
            await validate_cog_path_threaded(str(upload_temp_path))
            logger.info("project_create_validate_ok project_id=%s", project_id)
        except CogValidationError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="validate",
                error_code=e.code,
                error_message=e.message,
                context="project-create-cog-validate-failed",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(e.code, e.message, context=e.context or None),
            ) from e

        def _write() -> tuple[str, str]:
            return storage.write_project_driver_cog_from_path(
                project_id, str(upload_temp_path)
            )

        try:
            artifact_root, cog_path = await run_in_threadpool(_write)
            logger.info(
                "project_create_persist_cog_ok project_id=%s artifact_root=%s",
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
                context="project-create-storage-layout-invalid",
            )
            raise HTTPException(
                status_code=400,
                detail=validation_error("STORAGE_LAYOUT_INVALID", str(e)),
            ) from e
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="persist",
                error_code="STORAGE_WRITE_FAILED",
                error_message=str(e),
                context="project-create-storage-write-failed",
            )
            raise _proj_503("STORAGE_WRITE_FAILED", f"could not store file: {e}") from e

        uploaded_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="deriving",
            stage="derive",
            context="project-create-derive",
        )
        try:
            logger.info("project_create_derive_bands_start project_id=%s", project_id)

            def _defs() -> tuple[list[EnvironmentalBandDefinition], list[str]]:
                return band_definitions_for_upload_path(
                    str(upload_temp_path),
                    environmental_band_definitions,
                    infer_band_definitions=infer_band_definitions_from_form(
                        infer_band_definitions
                    ),
                )

            band_defs, infer_notes = await run_in_threadpool(_defs)
            inference_notes = infer_notes if infer_notes else None
            logger.info(
                "project_create_derive_bands_ok project_id=%s band_count=%s",
                project_id,
                len(band_defs) if band_defs else 0,
            )
        except ValueError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="derive",
                error_code="BAND_DEFINITIONS",
                error_message=str(e),
                context="project-create-band-definitions",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error("BAND_DEFINITIONS", str(e)),
            ) from e
    finally:
        if upload_temp_path is not None:
            upload_temp_path.unlink(missing_ok=True)

    explain_bg_path: str | None = None
    explain_bg_rows: int | None = None
    explain_bg_at: str | None = None
    if band_defs and artifact_root and cog_path:
        try:
            logger.info(
                "project_create_background_start project_id=%s sample_rows=%s",
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
                    band_defs,
                    settings.env_background_sample_rows,
                )

            await run_in_threadpool(_bg)
            explain_bg_path = EXPLAINABILITY_BACKGROUND_FILENAME
            explain_bg_rows = settings.env_background_sample_rows
            logger.info(
                "project_create_background_ok project_id=%s sample_rows=%s",
                project_id,
                explain_bg_rows,
            )
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                uploaded_session,
                stage="derive",
                error_code="EXPLAINABILITY_BACKGROUND_FAILED",
                error_message=str(e),
                context="project-create-explainability-background",
            )
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EXPLAINABILITY_BACKGROUND_FAILED",
                    "could not build explainability background sample from COG",
                    context={"cause": sanitize_exception_for_client(e)},
                ),
            ) from e

    now = datetime.now(UTC).isoformat()
    if explain_bg_path:
        explain_bg_at = now

    project = CatalogProject(
        id=project_id,
        name=name.strip(),
        description=description.strip() if description else None,
        status="active",
        visibility=visibility_v,  # type: ignore[arg-type]
        allowed_uids=uids,
        driver_artifact_root=artifact_root,
        driver_cog_path=cog_path,
        environmental_band_definitions=band_defs,
        band_inference_notes=inference_notes,
        explainability_background_path=explain_bg_path,
        explainability_background_sample_rows=explain_bg_rows,
        explainability_background_generated_at=explain_bg_at,
        created_at=now,
        updated_at=now,
    )

    def _persist() -> None:
        upsert_project(settings, project)

    uploaded_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        uploaded_session,
        status="deriving",
        stage="persist",
        context="project-create-persist",
    )
    try:
        await run_in_threadpool(_persist)
        logger.info("project_create_catalog_save_ok project_id=%s", project_id)
    except Exception as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            uploaded_session,
            stage="persist",
            error_code="CATALOG_SAVE_FAILED",
            error_message=str(e),
            context="project-create-catalog-save",
        )
        raise _proj_503("CATALOG_SAVE_FAILED", f"could not save catalog: {e}") from e

    await reload_catalog_threaded(request)
    if uploaded_session is not None and uploaded_session.status != "ready":
        await run_in_threadpool(
            best_effort_mark,
            settings,
            uploaded_session,
            status="ready",
            stage="done",
            context="project-create-done",
        )
    return project
