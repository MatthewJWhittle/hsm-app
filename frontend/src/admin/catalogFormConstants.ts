/** Shared copy for admin project / layer forms. */

export const FIELD_HELP = {
  species: 'Appears in the layer list and map.',
  activity: 'Together with species, names the layer (e.g. roosting, foraging).',
  modelName: 'Optional subtitle beyond species and activity.',
  modelVersion: 'Optional label for this revision (e.g. date or version).',
} as const

export const COG_REQUIREMENTS_INFO =
  'Upload a GeoTIFF in COG format, in Web Mercator (EPSG:3857). The server checks format, coordinate system, and file size.'

export const DRIVER_COG_INFO =
  'Optional: one shared environmental raster for this project (several bands in one file). Same format rules as suitability uploads. You can add or replace it later when editing the project.'

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
  backgroundFile:
    'Reference sample as Parquet: rows of training-like values; columns must match feature names (used only to compute explanations).',
} as const
