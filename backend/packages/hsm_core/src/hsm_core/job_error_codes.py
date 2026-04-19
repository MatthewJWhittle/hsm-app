"""Stable ``error_code`` values stored on Firestore job documents (API + worker)."""

from __future__ import annotations

from enum import StrEnum


class JobErrorCode(StrEnum):
    ENQUEUE_FAILED = "ENQUEUE_FAILED"
    NEVER_DISPATCHED = "NEVER_DISPATCHED"
    LOCAL_WORKER_DISPATCH_FAILED = "LOCAL_WORKER_DISPATCH_FAILED"

    UNKNOWN_KIND = "UNKNOWN_KIND"
    MISSING_PROJECT = "MISSING_PROJECT"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"

    ENV_COG_REQUIRED = "ENV_COG_REQUIRED"
    BAND_DEFINITIONS_MISSING = "BAND_DEFINITIONS_MISSING"
    ENV_COG_PATH_INVALID = "ENV_COG_PATH_INVALID"
    ENV_COG_NOT_ON_DISK = "ENV_COG_NOT_ON_DISK"

    EXPLAINABILITY_BACKGROUND_FAILED = "EXPLAINABILITY_BACKGROUND_FAILED"
    CATALOG_SAVE_FAILED = "CATALOG_SAVE_FAILED"


def job_error_code_str(code: JobErrorCode | str) -> str:
    return code.value if isinstance(code, JobErrorCode) else code
