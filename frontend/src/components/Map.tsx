import Map, { Layer, Source } from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useMemo, useRef } from 'react'
import type { Model } from '../types/model'
import { resolveSuitabilityPath } from '../utils/cogPath'
import { titilerBase } from '../utils/apiBase'

interface MapComponentProps {
  model: Model | null
  opacity?: number
}

function MapComponent({ opacity = 0.5, model = null }: MapComponentProps) {
  const mapRef = useRef(null)

  const tileUrl = useMemo(() => {
    if (!model) return ''
    const absPath = resolveSuitabilityPath(model)
    const pathForFileUrl = absPath.replace(/^\/+/, '')
    const urlParam = `file:///${pathForFileUrl}`
    const searchParams = new URLSearchParams({
      url: urlParam,
      colormap_name: 'viridis',
      rescale: '0,1',
    })
    const base = titilerBase().replace(/\/$/, '')
    return `${base}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?${searchParams.toString()}`
  }, [model])

  const rasterLayer = {
    id: 'hsm-raster',
    type: 'raster' as const,
    source: 'hsm-source',
    paint: {
      'raster-opacity': opacity,
    },
  }

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: -1.9487,
        latitude: 53.900293,
        zoom: 8,
      }}
      style={{ width: '100%', height: '100%' }}
      mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    >
      {model && tileUrl && (
        <Source
          id="hsm-source"
          type="raster"
          minzoom={1}
          maxzoom={15}
          tiles={[tileUrl]}
          tileSize={256}
        >
          <Layer {...rasterLayer} />
        </Source>
      )}
    </Map>
  )
}

export default MapComponent
