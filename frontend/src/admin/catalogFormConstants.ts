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
