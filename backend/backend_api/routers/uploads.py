"""Admin upload session routes (init/complete/status)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from datetime import timedelta
from typing import Annotated

import google.auth
import google.auth.transport.requests
from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import storage

from backend_api.auth_deps import require_admin_claims
from backend_api.deps.settings_dep import get_settings
from backend_api.schemas_upload import (
    UploadCompleteBody,
    UploadInitBody,
    UploadSession,
    UploadSessionResponse,
    to_upload_session_response,
)
from backend_api.settings import Settings
from backend_api.upload_session_transitions import complete_upload_transition
from backend_api.upload_sessions import get_upload_session, upsert_upload_session

router = APIRouter()
logger = logging.getLogger(__name__)

_ADMIN_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid bearer token"},
    status.HTTP_403_FORBIDDEN: {"description": "Valid token but admin claim not set"},
    status.HTTP_404_NOT_FOUND: {"description": "Upload session not found"},
    status.HTTP_409_CONFLICT: {"description": "Upload session state transition conflict"},
    status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Firestore read/write failure"},
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _looks_like_signing_capability_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "private key" in msg
        or "sign credentials" in msg
        or "could not automatically determine credentials" in msg
    )


def _mint_signed_upload_url(
    *,
    settings: Settings,
    bucket_name: str,
    object_path: str,
    content_type: str | None,
) -> str:
    """Create a temporary V4 signed URL for direct object upload."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_path)
    kwargs = {
        "version": "v4",
        "expiration": timedelta(hours=1),
        "method": "PUT",
        "content_type": content_type or "application/octet-stream",
    }
    try:
        return blob.generate_signed_url(**kwargs)
    except Exception as direct_err:
        if not _looks_like_signing_capability_error(direct_err):
            raise
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        signer_email = settings.gcs_signed_url_service_account or getattr(
            credentials, "service_account_email", None
        )
        if not signer_email or signer_email == "default":
            raise RuntimeError(
                "runtime credentials cannot sign directly; set "
                "GCS_SIGNED_URL_SERVICE_ACCOUNT to a signer service account email"
            ) from direct_err
        if credentials is None:
            raise RuntimeError(
                "storage client has no credentials available for IAM signed URL fallback"
            ) from direct_err
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        access_token = getattr(credentials, "token", None)
        if not access_token:
            raise RuntimeError(
                "could not refresh access token for IAM signed URL fallback"
            ) from direct_err
        try:
            return blob.generate_signed_url(
                **kwargs,
                service_account_email=signer_email,
                access_token=access_token,
            )
        except Exception as iam_err:
            raise RuntimeError(
                "signed URL generation failed for both direct and IAM fallback paths; "
                "ensure signer IAM permission (iam.serviceAccounts.signBlob/TokenCreator) "
                "and a valid signer service account"
            ) from iam_err


@router.post(
    "/uploads/init",
    response_model=UploadSessionResponse,
    status_code=201,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Create an upload session for direct object storage upload",
)
async def post_upload_init(
    body: UploadInitBody,
    settings: Annotated[Settings, Depends(get_settings)],
    claims: Annotated[dict, Depends(require_admin_claims)],
):
    """
    Create and persist a new upload session.

    PR1 stores lifecycle state only. Signed/resumable URL minting is added in later work,
    so ``upload_url`` is currently null.
    """
    if settings.storage_backend.strip().lower() != "gcs":
        raise HTTPException(
            status_code=503,
            detail="Upload sessions currently require STORAGE_BACKEND=gcs",
        )
    if not settings.gcs_bucket:
        raise HTTPException(
            status_code=503,
            detail="GCS_BUCKET is required for upload sessions",
        )

    upload_id = str(uuid.uuid4())
    safe_name = Path(body.filename).name or "upload.bin"
    now = _now_iso()
    object_path = f"uploads/{upload_id}/{safe_name}"
    session = UploadSession(
        id=upload_id,
        project_id=body.project_id,
        filename=safe_name,
        content_type=body.content_type,
        requested_size_bytes=body.size_bytes,
        status="pending",
        stage="upload",
        gcs_bucket=settings.gcs_bucket,
        object_path=object_path,
        created_by_uid=str(claims.get("uid", "unknown")),
        created_at=now,
        updated_at=now,
    )
    try:
        upload_url = _mint_signed_upload_url(
            settings=settings,
            bucket_name=settings.gcs_bucket,
            object_path=object_path,
            content_type=body.content_type,
        )
    except Exception as e:
        logger.exception(
            "Failed to mint upload signed URL",
            extra={
                "bucket": settings.gcs_bucket,
                "object_path": object_path,
            },
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "could not create upload URL: signing configuration unavailable. "
                "check runtime signer identity and IAM permissions"
            ),
        ) from e

    try:
        upsert_upload_session(settings, session)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not create upload session: {e}",
        ) from e
    return to_upload_session_response(session, upload_url=upload_url)


@router.get(
    "/uploads/{upload_id}",
    response_model=UploadSessionResponse,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Get upload session status",
)
async def get_upload_status(
    upload_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
):
    try:
        session = get_upload_session(settings, upload_id)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not read upload session: {e}",
        ) from e
    if session is None:
        raise HTTPException(status_code=404, detail="upload session not found")
    return to_upload_session_response(session, upload_url=None)


@router.post(
    "/uploads/{upload_id}/complete",
    response_model=UploadSessionResponse,
    tags=["admin"],
    responses=_ADMIN_RESPONSES,
    summary="Mark upload session complete and advance lifecycle",
)
async def post_upload_complete(
    upload_id: str,
    body: UploadCompleteBody,
    settings: Annotated[Settings, Depends(get_settings)],
    _claims: Annotated[dict, Depends(require_admin_claims)],
):
    """
    Mark session as uploaded once client upload finishes.

    PR1 only performs status transition persistence. Validation/derivation jobs are added later.
    """
    try:
        existing = get_upload_session(settings, upload_id)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not read upload session: {e}",
        ) from e
    if existing is None:
        raise HTTPException(status_code=404, detail="upload session not found")

    try:
        updated = complete_upload_transition(
            existing,
            size_bytes=body.size_bytes,
            checksum_sha256=body.checksum_sha256,
            now_iso=_now_iso(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        ) from e
    try:
        upsert_upload_session(settings, updated)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"could not update upload session: {e}",
        ) from e
    return to_upload_session_response(updated, upload_url=None)
