"""Resolve environmental COG paths without FastAPI dependencies."""


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
