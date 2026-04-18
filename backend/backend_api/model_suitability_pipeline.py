"""Model create/update with suitability COG upload (multipart or session)."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile

from backend_api.api_errors import validation_error
from backend_api.catalog_service import CatalogService
from backend_api.catalog_write import upsert_model
from backend_api.cog_validation import CogValidationError
from backend_api.point_explainability import validate_explainability_artifacts_for_model
from backend_api.point_sampling import validate_driver_band_indices_for_model
from backend_api.project_manifest import validate_model_feature_bands_for_admin
from backend_api.routers.catalog_upload_utils import (
    reload_catalog_threaded,
    validate_cog_path_threaded,
)
from backend_api.schemas import Model, ModelAnalysis, ModelMetadata
from backend_api.settings import Settings
from backend_api.schemas_upload import UploadSession
from backend_api.storage import SERIALIZED_MODEL_FILENAME, ObjectStorage
from backend_api.upload_session_ingest import (
    best_effort_fail,
    best_effort_mark,
    download_upload_session_to_tempfile,
    write_upload_file_to_tempfile,
)

logger = logging.getLogger(__name__)


def _cog_validation_422(exc: CogValidationError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=validation_error(exc.code, exc.message, context=exc.context or None),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def merge_serialized_model_upload(
    *,
    storage: ObjectStorage,
    settings: Settings,
    model_id: str,
    metadata: ModelMetadata | None,
    serialized_model_file: StarletteUploadFile | None,
) -> ModelMetadata | None:
    if serialized_model_file is None:
        return metadata
    upload_temp_path = await write_upload_file_to_tempfile(
        serialized_model_file,
        max_bytes=settings.max_upload_bytes,
        suffix=".pkl",
    )
    logger.info("model_serialized_upload_ingest model_id=%s", model_id)
    try:
        upload_size = upload_temp_path.stat().st_size
        if upload_size <= 0:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EMPTY_FILE",
                    "serialized_model_file is empty.",
                    context={"field": "serialized_model_file"},
                ),
            )

        def _write_m() -> None:
            storage.write_model_artifact_from_path(
                model_id, SERIALIZED_MODEL_FILENAME, str(upload_temp_path)
            )

        await run_in_threadpool(_write_m)
    finally:
        upload_temp_path.unlink(missing_ok=True)
    analysis = (metadata.analysis if metadata else None) or ModelAnalysis()
    analysis = analysis.model_copy(update={"serialized_model_path": SERIALIZED_MODEL_FILENAME})
    base = metadata or ModelMetadata()
    return base.model_copy(update={"analysis": analysis})


async def create_model_with_suitability_upload_pipeline(
    request: Request,
    settings: Settings,
    storage: ObjectStorage,
    catalog: CatalogService,
    *,
    model_id: str,
    project_id: str,
    species: str,
    activity: str,
    upload_session_id: str | None,
    file: StarletteUploadFile | None,
    metadata: ModelMetadata | None,
    serialized_model_file: StarletteUploadFile | None,
) -> Model:
    upload_session: UploadSession | None = None
    upload_temp_path = None
    if upload_session_id:
        upload_temp_path, upload_session = await run_in_threadpool(
            download_upload_session_to_tempfile,
            settings,
            upload_session_id,
            purpose="model create",
        )
    elif file is not None:
        upload_temp_path = await write_upload_file_to_tempfile(
            file,
            max_bytes=settings.max_upload_bytes,
        )
    else:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "MISSING_FIELD",
                "file or upload_session_id is required.",
                context={"field": "file"},
            ),
        )

    try:
        upload_size = os.path.getsize(str(upload_temp_path))
        if upload_size <= 0:
            raise HTTPException(
                status_code=422,
                detail=validation_error(
                    "EMPTY_FILE",
                    "file is empty.",
                    context={"field": "file"},
                ),
            )
        if upload_size > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file exceeds max size {settings.max_upload_bytes} bytes",
            )

        upload_session = await run_in_threadpool(
            best_effort_mark,
            settings,
            upload_session,
            status="validating",
            stage="validate",
            context="model-create-validate",
        )
        try:
            await validate_cog_path_threaded(str(upload_temp_path))
        except CogValidationError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="validate",
                error_code=e.code,
                error_message=e.message,
                context="model-create-cog-validate-failed",
            )
            raise _cog_validation_422(e) from e

        def _write() -> tuple[str, str]:
            return storage.write_suitability_cog_from_path(model_id, str(upload_temp_path))

        try:
            artifact_root, suitability_cog_path = await run_in_threadpool(_write)
        except ValueError as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="persist",
                error_code="STORAGE_LAYOUT_INVALID",
                error_message=str(e),
                context="model-create-storage-layout-invalid",
            )
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            await run_in_threadpool(
                best_effort_fail,
                settings,
                upload_session,
                stage="persist",
                error_code="STORAGE_WRITE_FAILED",
                error_message=str(e),
                context="model-create-storage-write-failed",
            )
            raise HTTPException(
                status_code=503,
                detail=f"could not store file: {e}",
            ) from e
    finally:
        if upload_temp_path is not None:
            upload_temp_path.unlink(missing_ok=True)

    meta_in = await merge_serialized_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        metadata=metadata,
        serialized_model_file=serialized_model_file,
    )

    ts = _utc_now_iso()
    model = Model(
        id=model_id,
        project_id=project_id,
        species=species,
        activity=activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        created_at=ts,
        updated_at=ts,
        metadata=meta_in,
    )

    validate_model_feature_bands_for_admin(model, catalog)

    def _validate_and_enrich() -> Model:
        validate_driver_band_indices_for_model(model, catalog)
        validate_explainability_artifacts_for_model(model, catalog)
        return model

    upload_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="deriving",
        stage="derive",
        context="model-create-derive",
    )
    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            upload_session,
            stage="derive",
            error_code="MODEL_VALIDATION",
            error_message=str(e),
            context="model-create-validation-failed",
        )
        raise HTTPException(
            status_code=422,
            detail=validation_error("MODEL_VALIDATION", str(e)),
        ) from e

    def _persist() -> None:
        upsert_model(settings, model)

    upload_session = await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="deriving",
        stage="persist",
        context="model-create-persist",
    )
    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        await run_in_threadpool(
            best_effort_fail,
            settings,
            upload_session,
            stage="persist",
            error_code="CATALOG_SAVE_FAILED",
            error_message=str(e),
            context="model-create-catalog-save",
        )
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    await run_in_threadpool(
        best_effort_mark,
        settings,
        upload_session,
        status="ready",
        stage="done",
        context="model-create-done",
    )

    await reload_catalog_threaded(request)
    return model


async def update_model_pipeline(
    request: Request,
    settings: Settings,
    storage: ObjectStorage,
    catalog: CatalogService,
    existing: Model,
    *,
    species: str,
    activity: str,
    project_id: str,
    metadata: ModelMetadata | None,
    file: StarletteUploadFile | None,
    upload_session_id: str | None,
    serialized_model_file: StarletteUploadFile | None,
) -> Model:
    model_id = existing.id
    artifact_root = existing.artifact_root
    suitability_cog_path = existing.suitability_cog_path

    if file is not None and upload_session_id:
        raise HTTPException(
            status_code=422,
            detail=validation_error(
                "UPLOAD_CONFLICT",
                "provide either multipart file or upload_session_id, not both",
            ),
        )

    if upload_session_id:
        upload_temp_path, _us = await run_in_threadpool(
            download_upload_session_to_tempfile,
            settings,
            upload_session_id,
            purpose="model update",
        )
        try:
            upload_size = os.path.getsize(str(upload_temp_path))
            if upload_size <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "EMPTY_FILE",
                        "file is empty.",
                        context={"field": "file"},
                    ),
                )
            if upload_size > settings.max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"file exceeds max size {settings.max_upload_bytes} bytes",
                )
            await validate_cog_path_threaded(str(upload_temp_path))

            def _write() -> tuple[str, str]:
                return storage.write_suitability_cog_from_path(
                    model_id, str(upload_temp_path)
                )

            try:
                artifact_root, suitability_cog_path = await run_in_threadpool(_write)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"could not store file: {e}",
                ) from e
        finally:
            upload_temp_path.unlink(missing_ok=True)

    elif file is not None:
        upload_temp_path = await write_upload_file_to_tempfile(
            file,
            max_bytes=settings.max_upload_bytes,
        )
        try:
            upload_size = upload_temp_path.stat().st_size
            if upload_size <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=validation_error(
                        "EMPTY_FILE",
                        "file is empty.",
                        context={"field": "file"},
                    ),
                )
            await validate_cog_path_threaded(str(upload_temp_path))

            def _write() -> tuple[str, str]:
                return storage.write_suitability_cog_from_path(
                    model_id, str(upload_temp_path)
                )

            try:
                artifact_root, suitability_cog_path = await run_in_threadpool(_write)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail=f"could not store file: {e}",
                ) from e
        finally:
            upload_temp_path.unlink(missing_ok=True)

    new_metadata = await merge_serialized_model_upload(
        storage=storage,
        settings=settings,
        model_id=model_id,
        metadata=metadata,
        serialized_model_file=serialized_model_file,
    )

    ts = _utc_now_iso()
    created_prev = existing.created_at or ts
    model = Model(
        id=model_id,
        project_id=project_id,
        species=species,
        activity=activity,
        artifact_root=artifact_root,
        suitability_cog_path=suitability_cog_path,
        created_at=created_prev,
        updated_at=ts,
        metadata=new_metadata,
    )

    validate_model_feature_bands_for_admin(model, catalog)

    def _validate_and_enrich() -> Model:
        validate_driver_band_indices_for_model(model, catalog)
        validate_explainability_artifacts_for_model(model, catalog)
        return model

    try:
        model = await run_in_threadpool(_validate_and_enrich)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=validation_error("MODEL_VALIDATION", str(e)),
        ) from e

    def _persist() -> None:
        upsert_model(settings, model)

    try:
        await run_in_threadpool(_persist)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not save catalog: {e}",
        ) from e

    await reload_catalog_threaded(request)
    return model
