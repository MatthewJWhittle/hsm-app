"""Sample random pixels from the environmental COG into a Parquet background matrix for SHAP."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np
import pandas as pd
import pyarrow  # noqa: F401 — pandas needs pyarrow for DataFrame.to_parquet(engine="pyarrow")
import rasterio

from hsm_core.artifact_read_runtime import ArtifactReadRuntime
from hsm_core.schemas_project import EnvironmentalBandDefinition
from hsm_core.settings import WorkerSettings
from hsm_core.storage import EXPLAINABILITY_BACKGROUND_FILENAME, ObjectStorage

# Cap strata so very large n_samples does not imply tens of thousands of tiny windows.
_MAX_STRATUM_GRID = 32


@dataclass
class _StratumReservoir:
    """Reservoir sample of up to ``k`` rows (feature vectors), uniform over the stream."""

    k: int
    rng: np.random.Generator
    t: int = 0
    rows: list[np.ndarray] | None = None

    def __post_init__(self) -> None:
        if self.rows is None:
            self.rows = []

    def consider(self, feat: np.ndarray) -> None:
        self.t += 1
        ft = np.asarray(feat, dtype=np.float64, order="C")
        if len(self.rows) < self.k:
            self.rows.append(ft.copy())
            return
        j = int(self.rng.integers(0, self.t))
        if j < self.k:
            self.rows[j] = ft.copy()


def _stratum_grid_size(n_samples: int) -> int:
    return max(1, min(_MAX_STRATUM_GRID, int(np.ceil(np.sqrt(n_samples)))))


def _stratum_quotas(n_samples: int, g: int) -> np.ndarray:
    """Integer quotas per stratum, shape (g, g), summing to n_samples."""
    n_strata = g * g
    base = n_samples // n_strata
    rem = n_samples % n_strata
    q = np.full((g, g), base, dtype=np.int32)
    flat = q.ravel()
    flat[:rem] += 1
    return q.reshape(g, g)


def write_project_explainability_background_parquet(
    storage: ObjectStorage,
    settings: WorkerSettings,
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
    uri = resolve_env_cog_uri_for_sampling(settings, artifact_root, cog_path)
    tmp_path = sample_background_parquet_to_tempfile(uri, band_defs, n_samples)
    try:
        storage.write_project_artifact_from_path(
            project_id, EXPLAINABILITY_BACKGROUND_FILENAME, str(tmp_path)
        )
    finally:
        tmp_path.unlink(missing_ok=True)
    return EXPLAINABILITY_BACKGROUND_FILENAME


def resolve_env_cog_uri_for_sampling(
    settings: WorkerSettings, artifact_root: str, cog_rel: str
) -> str:
    """
    Path or URI for rasterio to open the environmental COG.

    For GCS-backed roots, return ``/vsicurl/<signed-https-url>`` so rasterio/GDAL can
    perform cloud-friendly ranged reads without requiring GDAL ``gs://`` auth setup.
    """
    rel = cog_rel.strip()
    if rel.startswith("/"):
        return rel
    root = artifact_root.rstrip("/")
    if root.startswith("gs://"):
        gcs_uri = f"{root}/{rel}"
        return ArtifactReadRuntime(settings).rasterio_open_uri(gcs_uri)
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


def _sample_features_stratified_blocks(
    src: rasterio.io.DatasetReader,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Spatially stratified sample: one reservoir per grid cell (G×G), filled in a single
    pass over internal COG blocks (few large reads instead of many random 1×1 reads).
    """
    n_bands = int(src.count)
    height, width = int(src.height), int(src.width)
    g = _stratum_grid_size(n_samples)
    quotas = _stratum_quotas(n_samples, g)
    row_b = np.array(
        [((sr + 1) * height // g) for sr in range(g)], dtype=np.int64
    )
    col_b = np.array(
        [((sc + 1) * width // g) for sc in range(g)], dtype=np.int64
    )

    reservoirs: dict[tuple[int, int], _StratumReservoir] = {}
    for sr in range(g):
        for sc in range(g):
            q = int(quotas[sr, sc])
            if q > 0:
                reservoirs[(sr, sc)] = _StratumReservoir(q, rng)

    for _, window in src.block_windows(1):
        data = src.read(window=window)
        if data.shape != (n_bands, int(window.height), int(window.width)):
            continue
        valid = np.all(np.isfinite(data), axis=0)
        vr, vc = np.nonzero(valid)
        if vr.size == 0:
            continue
        i0 = int(window.row_off)
        j0 = int(window.col_off)
        vr_g = vr.astype(np.int64) + i0
        vc_g = vc.astype(np.int64) + j0
        sr = np.searchsorted(row_b, vr_g, side="right")
        sc = np.searchsorted(col_b, vc_g, side="right")
        for k in range(vr.size):
            key = (int(sr[k]), int(sc[k]))
            rsv = reservoirs.get(key)
            if rsv is not None:
                rsv.consider(data[:, vr[k], vc[k]])

    collected: list[np.ndarray] = []
    for sr in range(g):
        for sc in range(g):
            if quotas[sr, sc] <= 0:
                continue
            rsv = reservoirs.get((sr, sc))
            if rsv and rsv.rows:
                collected.extend(rsv.rows)

    need = n_samples - len(collected)
    if need > 0:
        backfill = _StratumReservoir(need, rng)
        for _, window in src.block_windows(1):
            data = src.read(window=window)
            valid = np.all(np.isfinite(data), axis=0)
            vr, vc = np.nonzero(valid)
            for k in range(vr.size):
                backfill.consider(data[:, vr[k], vc[k]])
        if len(backfill.rows) < need:
            raise ValueError(
                f"could only sample {len(collected) + len(backfill.rows)} valid pixels "
                f"(try smaller n_samples or check nodata)"
            )
        collected.extend(backfill.rows)

    rng.shuffle(collected)
    return np.stack(collected, axis=0)


def sample_background_parquet_to_tempfile(
    cog_uri: str,
    band_definitions: list[EnvironmentalBandDefinition],
    n_samples: int,
    *,
    seed: int | None = None,
) -> Path:
    """
    Sample pixels and write Parquet directly to a temp file.

    Uses one pass over COG internal blocks with per–grid-cell reservoir sampling
    (spatially spread, minimal random 1×1 reads). A second block pass runs only if
    some strata lack enough valid pixels (e.g. heavy nodata).
    """
    defs = sorted(band_definitions, key=lambda d: d.index)
    names = [d.name for d in defs]

    rng = np.random.default_rng(seed)
    with rasterio.open(cog_uri) as src:
        n_bands = int(src.count)
        if n_bands != len(defs):
            raise ValueError(
                f"band definitions count ({len(defs)}) does not match raster band count ({n_bands})"
            )
        height, width = int(src.height), int(src.width)
        if height < 1 or width < 1:
            raise ValueError("raster has invalid dimensions")

        rows = _sample_features_stratified_blocks(src, n_samples, rng)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    df = pd.DataFrame(rows, columns=names)
    df.to_parquet(tmp_path, engine="pyarrow", index=False)
    return tmp_path


def sanitize_exception_for_client(exc: Exception) -> str:
    """
    Strip URL query strings/tokens from exception text before returning to API clients.
    """
    msg = str(exc)
    # Drop query parameters that may contain signed URL tokens.
    msg = re.sub(r"https?://[^\s?]+[?][^\s]+", "<redacted-url>", msg)
    return msg
