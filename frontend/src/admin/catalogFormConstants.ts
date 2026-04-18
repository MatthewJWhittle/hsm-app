/** Shared copy for admin project / layer forms. */

export const FIELD_HELP = {
  species: 'Shown in the layer list and map legend.',
  activity: 'Together with species, identifies this layer (e.g. roosting, in flight).',
  suitabilityCog:
    'Cloud-optimized GeoTIFF in Web Mercator (EPSG:3857). Rasters in other CRS (e.g. EPSG:27700) must be reprojected first — see docs/data-models.md.',
} as const

export const COG_REQUIREMENTS_INFO =
  'Upload a GeoTIFF in COG format, in Web Mercator (EPSG:3857). Other CRS (e.g. UK EPSG:27700) are rejected — reproject with gdalwarp or rio before upload. The server checks tiling, CRS, and size.'

export const DRIVER_COG_INFO =
  'Optional: one shared environmental raster for this project (several bands in one file). Same format rules as suitability uploads. You can add or replace it later when editing the project.'

/** Shown next to the canonical storage filename so uploads feel “real” after replace. */
export const DRIVER_COG_STORAGE_NOTE =
  'The server always stores this raster as environmental_cog.tif under the project folder; your original filename is shown for reference.'

export const COG_REPLACE_HINT =
  'Optional replacement file with the same rules. Leave empty to keep the current upload.'

export const EXPLAINABILITY_HELP = {
  toggle:
    'When enabled, map clicks can show which environmental variables increase or decrease suitability at that point (requires matching project environmental raster and band indices).',
  featureNames:
    'Comma-separated names in the same order as environmental band indices. Must match the columns your trained model expects.',
  bandLabels:
    'Optional friendly labels for the raw values list (same order as bands). Leave empty to use feature names.',
  modelFile: 'Pickled scikit-learn estimator (e.g. .pkl) saved with the same feature order.',
  backgroundNote:
    'The reference sample for explanations is generated from the project’s environmental COG using the admin “Regenerate reference sample” action (shared by all layers in the project).',
} as const
