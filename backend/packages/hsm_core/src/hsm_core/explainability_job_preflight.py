"""Shared checks before enqueueing or running explainability background sampling."""

from __future__ import annotations

from hsm_core.env_cog_paths import (
    environmental_cog_readable_for_sampling,
    resolve_env_cog_path_from_parts,
)
from hsm_core.job_error_codes import JobErrorCode
from hsm_core.schemas_project import CatalogProject


class ExplainabilityJobPreflightError(Exception):
    """Project cannot run explainability background sampling (same semantics API vs worker)."""

    def __init__(self, code: JobErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def validate_catalog_project_for_explainability_sample(project: CatalogProject) -> None:
    """Raise :class:`ExplainabilityJobPreflightError` when prerequisites are not met."""
    artifact_root = project.driver_artifact_root
    cog_path = project.driver_cog_path
    band_defs = project.environmental_band_definitions

    if not artifact_root or not cog_path:
        raise ExplainabilityJobPreflightError(
            JobErrorCode.ENV_COG_REQUIRED,
            "project has no environmental COG; upload one first",
        )
    if not band_defs:
        raise ExplainabilityJobPreflightError(
            JobErrorCode.BAND_DEFINITIONS_MISSING,
            "project has no environmental band definitions; save band names first",
        )

    abs_path = resolve_env_cog_path_from_parts(artifact_root, cog_path)
    if not abs_path:
        raise ExplainabilityJobPreflightError(
            JobErrorCode.ENV_COG_PATH_INVALID,
            "cannot resolve environmental COG path",
        )
    if not environmental_cog_readable_for_sampling(abs_path):
        raise ExplainabilityJobPreflightError(
            JobErrorCode.ENV_COG_NOT_ON_DISK,
            "environmental COG not found on server",
        )
