"""Sample random pixels from the environmental COG into a Parquet background matrix for SHAP."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow  # noqa: F401 — pandas needs pyarrow for DataFrame.to_parquet(engine="pyarrow")
import rasterio
from rasterio.windows import Window

from backend_api.schemas_project import EnvironmentalBandDefinition
from backend_api.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage


def write_project_explainability_background_parquet(
    storage: ObjectStorage,
    project_id: str,
    artifact_root: str,
    cog_path: str,
    band_defs: list[EnvironmentalBandDefinition],
    n_samples: int,
) -> str:
    """
    Sample pixels from the COG and write ``explainability_background.parquet`` under the project.

    Returns the relative catalog path (fixed filename).
    """
    uri = resolve_env_cog_uri_for_sampling(artifact_root, cog_path)
    tmp_path = sample_background_parquet_to_tempfile(uri, band_defs, n_samples)
    try:
        storage.write_project_artifact_from_path(
            project_id, EXPLAINABILITY_BACKGROUND_FILENAME, str(tmp_path)
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return EXPLAINABILITY_BACKGROUND_FILENAME


def resolve_env_cog_uri_for_sampling(artifact_root: str, cog_rel: str) -> str:
    """
    Path or URI for rasterio to open the environmental COG (local path or ``gs://...``).
    """
    rel = cog_rel.strip()
    if rel.startswith("/"):
        return rel
    root = artifact_root.rstrip("/")
    if root.startswith("gs://"):
        return f"{root}/{rel}"
    return str(Path(root) / rel)


def sample_background_parquet_bytes(
    cog_uri: str,
    band_definitions: list[EnvironmentalBandDefinition],
    n_samples: int,
    *,
    seed: int | None = None,
) -> bytes:
    """
    Randomly sample ``n_samples`` pixels (all bands) into a Parquet file.

    Column names are ``EnvironmentalBandDefinition.name`` sorted by ``index``.
    Skips windows that contain NaN in any band.
    """
    tmp_path = sample_background_parquet_to_tempfile(
        cog_uri, band_definitions, n_samples, seed=seed
    )
    try:
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def sample_background_parquet_to_tempfile(
    cog_uri: str,
    band_definitions: list[EnvironmentalBandDefinition],
    n_samples: int,
    *,
    seed: int | None = None,
) -> Path:
    """Randomly sample pixels and write Parquet directly to a temp file."""
    defs = sorted(band_definitions, key=lambda d: d.index)
    names = [d.name for d in defs]

    rng = np.random.default_rng(seed)
    rows: list[list[float]] = []

    with rasterio.open(cog_uri) as src:
        n_bands = int(src.count)
        if n_bands != len(defs):
            raise ValueError(
                f"band definitions count ({len(defs)}) does not match raster band count ({n_bands})"
            )
        height, width = int(src.height), int(src.width)
        if height < 1 or width < 1:
            raise ValueError("raster has invalid dimensions")

        max_attempts = max(n_samples * 20, n_samples + 100)
        attempts = 0
        while len(rows) < n_samples and attempts < max_attempts:
            attempts += 1
            row = int(rng.integers(0, height))
            col = int(rng.integers(0, width))
            window = Window(col, row, 1, 1)
            data = src.read(window=window)
            if data.shape != (n_bands, 1, 1):
                continue
            vals = data[:, 0, 0].astype(np.float64)
            if not np.all(np.isfinite(vals)):
                continue
            rows.append([float(x) for x in vals])

        if len(rows) < n_samples:
            raise ValueError(
                f"could only sample {len(rows)} valid pixels (try smaller n_samples or check nodata)"
            )

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    df = pd.DataFrame(rows, columns=names)
    df.to_parquet(tmp_path, engine="pyarrow", index=False)
    return tmp_path
