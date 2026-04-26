import Map, {
  Layer,
  Source,
  type MapMouseEvent,
  type MapRef,
  type MapSourceDataEvent,
} from 'react-map-gl/maplibre'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef } from 'react'
import { COLORMAP_NAME, SUITABILITY_RESCALE_MAX, SUITABILITY_RESCALE_MIN } from '../map/suitabilityScale'
import type { Model } from '../types/model'
import { resolveSuitabilityPath, titilerRasterUrlParam } from '../utils/cogPath'
import { titilerBase } from '../utils/apiBase'
import { fetchRasterBounds } from '../api/rasterBounds'

export interface MapPlaceTarget {
  id: string
  center: {
    lng: number
    lat: number
  }
  bbox?: [number, number, number, number] | null
}

interface MapComponentProps {
  model: Model | null
  opacity?: number
  /** When false, the raster source is not rendered (no tile fetches). */
  visible?: boolean
  /** Place-search target selected by the user. */
  placeTarget?: MapPlaceTarget | null
  /** When set, map clicks sample suitability at the clicked (lng, lat). */
  onInspect?: (lng: number, lat: number) => void
  onLayerLoadingChange?: (loading: boolean) => void
  onMapHover?: (point: { x: number; y: number }) => void
  onMapLeave?: () => void
}

function MapComponent({
  opacity = 0.5,
  model = null,
  visible = true,
  placeTarget = null,
  onInspect,
  onLayerLoadingChange,
  onMapHover,
  onMapLeave,
}: MapComponentProps) {
  const mapRef = useRef<MapRef | null>(null)
  const fittedModelIdRef = useRef<string | null>(null)
  const hasUserMovedMapRef = useRef(false)
  const programmaticFitRef = useRef(false)
  const fitTimerRef = useRef<number | null>(null)

  const tileUrl = useMemo(() => {
    if (!model) return ''
    const absPath = resolveSuitabilityPath(model)
    const searchParams = new URLSearchParams({
      url: titilerRasterUrlParam(absPath),
      colormap_name: COLORMAP_NAME,
      rescale: `${SUITABILITY_RESCALE_MIN},${SUITABILITY_RESCALE_MAX}`,
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

  useEffect(() => {
    return () => {
      if (fitTimerRef.current !== null) window.clearTimeout(fitTimerRef.current)
    }
  }, [])

  useEffect(() => {
    onLayerLoadingChange?.(Boolean(model && visible && tileUrl))
    return () => onLayerLoadingChange?.(false)
  }, [model, onLayerLoadingChange, tileUrl, visible])

  useEffect(() => {
    if (!model || !visible) return
    if (hasUserMovedMapRef.current) return
    if (fittedModelIdRef.current === model.id) return

    const ac = new AbortController()
    let cancelled = false

    fetchRasterBounds(model, ac.signal)
      .then((bounds) => {
        if (cancelled || hasUserMovedMapRef.current) return
        const map = mapRef.current
        if (!map) return

        fittedModelIdRef.current = model.id
        programmaticFitRef.current = true
        if (fitTimerRef.current !== null) window.clearTimeout(fitTimerRef.current)
        map.fitBounds(bounds, {
          padding: 72,
          duration: 700,
          maxZoom: 11,
        })
        fitTimerRef.current = window.setTimeout(() => {
          programmaticFitRef.current = false
          fitTimerRef.current = null
        }, 800)
      })
      .catch((error: unknown) => {
        if (cancelled) return
        if (error instanceof Error && error.name === 'AbortError') return
        console.warn('Could not fit map to raster bounds', error)
      })

    return () => {
      cancelled = true
      ac.abort()
    }
  }, [model, visible])

  useEffect(() => {
    if (!placeTarget) return
    const map = mapRef.current
    if (!map) return

    hasUserMovedMapRef.current = true
    programmaticFitRef.current = true
    if (fitTimerRef.current !== null) window.clearTimeout(fitTimerRef.current)

    const bbox = placeTarget.bbox
    if (bbox) {
      const [west, south, east, north] = bbox
      map.fitBounds(
        [
          [west, south],
          [east, north],
        ],
        {
          padding: 72,
          duration: 700,
          maxZoom: 14,
        },
      )
    } else {
      map.flyTo({
        center: [placeTarget.center.lng, placeTarget.center.lat],
        zoom: 13,
        duration: 700,
      })
    }

    fitTimerRef.current = window.setTimeout(() => {
      programmaticFitRef.current = false
      fitTimerRef.current = null
    }, 800)
  }, [placeTarget])

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
      onMoveStart={() => {
        if (!programmaticFitRef.current) {
          hasUserMovedMapRef.current = true
        }
      }}
      onSourceData={(e: MapSourceDataEvent) => {
        if (e.sourceId !== 'hsm-source') return
        onLayerLoadingChange?.(!e.isSourceLoaded)
      }}
      onClick={(e) => {
        const { lng, lat } = e.lngLat
        onInspect?.(lng, lat)
      }}
      onMouseMove={(e: MapMouseEvent) => {
        onMapHover?.(e.point)
      }}
      onMouseLeave={onMapLeave}
    >
      {model && tileUrl && visible && (
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
