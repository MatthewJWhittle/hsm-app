"""OpenAPI ``openapi_extra`` for admin multipart model routes (manual form parsing)."""

from __future__ import annotations

# Suitability COG must be EPSG:3857 tiled GeoTIFF — see docs/data-models.md and README.
_CO_DESC = (
    "Suitability COG (GeoTIFF). Must be a tiled Cloud Optimized GeoTIFF in "
    "EPSG:3857 (Web Mercator), not e.g. EPSG:27700 — reproject before upload."
)
_META_DESC = (
    "Model metadata: preferred as a multipart part with Content-Type application/json "
    "(JSON object); a plain string field with JSON text is also accepted."
)

OPENAPI_POST_MODELS: dict = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["project_id", "species", "activity", "file"],
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Existing catalog project id (UUID).",
                        },
                        "species": {"type": "string"},
                        "activity": {"type": "string"},
                        "file": {
                            "type": "string",
                            "format": "binary",
                            "description": _CO_DESC,
                        },
                        "metadata": {
                            "description": _META_DESC,
                        },
                        "serialized_model_file": {
                            "type": "string",
                            "format": "binary",
                            "description": "Optional sklearn pipeline pickle for explainability.",
                        },
                    },
                }
            }
        }
    }
}

OPENAPI_PUT_MODEL: dict = {
    "requestBody": {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Change catalog project; must exist.",
                        },
                        "species": {"type": "string"},
                        "activity": {"type": "string"},
                        "file": {
                            "type": "string",
                            "format": "binary",
                            "description": _CO_DESC,
                        },
                        "metadata": {"description": _META_DESC},
                        "serialized_model_file": {
                            "type": "string",
                            "format": "binary",
                        },
                    },
                }
            }
        }
    }
}
