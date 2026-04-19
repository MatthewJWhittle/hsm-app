"""Resolve environmental COG paths without FastAPI dependencies."""

from __future__ import annotations

from pathlib import Path


def environmental_cog_readable_for_sampling(abs_path: str) -> bool:
    """True if sampling can read the COG (local file exists or cloud URI)."""
    if abs_path.startswith("gs://"):
        return True
    return Path(abs_path).is_file()


def resolve_env_cog_path_from_parts(
    artifact_root: str | None, driver_cog_path: str | None
) -> str | None:
    """Absolute path from storage root + relative COG path."""
    if not artifact_root or not driver_cog_path:
        return None
    root = artifact_root.rstrip("/")
    rel = driver_cog_path.strip()
    if rel.startswith("/"):
        return rel
    return f"{root}/{rel}"
