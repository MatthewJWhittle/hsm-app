"""Pydantic models aligned with docs/data-models.md."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelCard(BaseModel):
    """Human-facing model card metadata."""

    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    summary: str | None = None
    spatial_resolution_m: float | None = None
    primary_metric_type: str | None = Field(
        default=None,
        description="Primary quality metric name (e.g. AUC).",
    )
    primary_metric_value: str | None = Field(
        default=None,
        description="Display value for the primary metric (string or number as text).",
    )
    version: str | None = Field(
        default=None,
        description="Optional revision label (e.g. date or run id).",
    )


class ModelAnalysis(BaseModel):
    """Training / inference inputs: band subset, serialized estimator, optional overrides."""

    model_config = ConfigDict(extra="ignore")

    feature_band_names: list[str] | None = Field(
        default=None,
        description=(
            "Ordered machine names matching ``environmental_band_definitions[].name`` on the parent "
            "project (same order as the estimator feature matrix). The server resolves these to band indices."
        ),
    )
    serialized_model_path: str | None = Field(
        default=None,
        description="Path to pickled sklearn estimator relative to artifact_root (e.g. serialized_model.pkl).",
    )
    positive_class_index: int | None = Field(
        default=None,
        ge=0,
        description="Index for predict_proba positive class (default 1 at runtime).",
    )
    driver_cog_path: str | None = Field(
        default=None,
        description="Optional per-model environmental COG override (relative to artifact_root).",
    )


class ModelMetadata(BaseModel):
    """All non-artifact model description: card, custom extras, and analysis inputs."""

    card: ModelCard | None = None
    extras: dict[str, str] | None = None
    analysis: ModelAnalysis | None = None


class Model(BaseModel):
    """One selectable catalog entry (species + activity + COG paths + optional metadata)."""

    id: str = Field(..., description="Stable identifier (slug-safe)")
    project_id: str | None = Field(
        None,
        description="Parent catalog project id; omit only for legacy rows pre-migration",
    )
    species: str
    activity: str
    artifact_root: str = Field(
        ...,
        description="Base path in storage for this model's artifacts",
    )
    suitability_cog_path: str = Field(
        ...,
        description="Path to suitability COG (absolute or relative to artifact_root)",
    )
    created_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when the catalog row was first created (server-set).",
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp of the last catalog update (server-set).",
    )
    metadata: ModelMetadata | None = None

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_model_document(cls, data: Any) -> Any:
        """Map legacy driver fields and old top-level display fields into ``metadata``."""
        if not isinstance(data, dict):
            return data
        if data.get("metadata") is not None:
            data.pop("driver_band_indices", None)
            data.pop("driver_config", None)
        else:
            analysis: dict[str, Any] = {}
            # Legacy driver_band_indices removed — clients must send metadata.analysis.feature_band_names.
            dc = data.get("driver_config")
            if isinstance(dc, dict):
                mp = dc.get("explainability_model_path")
                if isinstance(mp, str) and mp.strip():
                    analysis["serialized_model_path"] = mp.strip()
                pc = dc.get("explainability_positive_class")
                if pc is not None:
                    try:
                        analysis["positive_class_index"] = int(pc)
                    except (TypeError, ValueError):
                        pass
                dcp = dc.get("driver_cog_path")
                if isinstance(dcp, str) and dcp.strip():
                    analysis["driver_cog_path"] = dcp.strip()

            meta: dict[str, Any] = {}
            if analysis:
                meta["analysis"] = analysis
            if meta:
                data["metadata"] = meta
            data.pop("driver_band_indices", None)
            data.pop("driver_config", None)

        legacy_name = data.pop("model_name", None)
        legacy_ver = data.pop("model_version", None)
        if legacy_name is not None or legacy_ver is not None:
            meta = data.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
                data["metadata"] = meta
            card = meta.get("card")
            if not isinstance(card, dict):
                card = {}
                meta["card"] = card
            if isinstance(legacy_name, str) and legacy_name.strip() and not card.get("title"):
                card["title"] = legacy_name.strip()
            if isinstance(legacy_ver, str) and legacy_ver.strip() and not card.get("version"):
                card["version"] = legacy_ver.strip()

        return data


class DriverVariable(BaseModel):
    """One variable’s contribution to suitability at this point (e.g. SHAP-style influence)."""

    name: str
    direction: Literal["increase", "decrease", "neutral"]
    label: str | None = None
    magnitude: float | None = None
    display_name: str | None = Field(
        default=None,
        description="Human-friendly name from catalog (when different from ``name``).",
    )


class RawEnvironmentalValue(BaseModel):
    """Sampled environmental input at the clicked location (secondary detail)."""

    name: str
    value: float
    unit: str | None = None
    description: str | None = Field(
        default=None,
        description="Optional catalog description for this variable.",
    )


class PointInspection(BaseModel):
    """Suitability value, optional influence drivers, and optional raw env values at a location."""

    value: float
    unit: str | None = None
    drivers: list[DriverVariable] = Field(
        default_factory=list,
        description="Ranked variable influence (e.g. SHAP); empty when explainability is not configured.",
    )
    raw_environmental_values: list[RawEnvironmentalValue] | None = Field(
        default=None,
        description="Raw raster values for configured bands at this point (same order as model inputs when aligned).",
    )


class AuthMeResponse(BaseModel):
    """Decoded Firebase ID token fields exposed to the client."""

    uid: str
    email: str | None = None


class AuthTokenRequest(BaseModel):
    """Credentials for Identity Toolkit sign-in (same as Firebase email/password)."""

    email: str
    password: str
    admin_only: bool = Field(
        default=False,
        description=(
            "If true, only return tokens when the user has Firebase custom claim "
            "`admin: true` (else 403)."
        ),
    )


class AuthTokenResponse(BaseModel):
    """Firebase ID token and refresh token from Identity Toolkit."""

    token_type: Literal["Bearer"] = "Bearer"
    id_token: str
    refresh_token: str
    expires_in: str = Field(
        description="Lifetime of the ID token in seconds (string per Identity Toolkit).",
    )
