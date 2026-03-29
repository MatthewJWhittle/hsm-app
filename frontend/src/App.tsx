import './App.css'
import MapComponent from './components/Map'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MapControlPanel } from './components/map/MapControlPanel'
import { InspectionHud } from './components/InspectionHud'
import type { Model } from './types/model'
import type { PointInspection } from './types/pointInspection'
import { fetchModelCatalog } from './api/catalog'
import { fetchPointInspection } from './api/inspectPoint'
import { Navbar } from './components/Navbar'

function App() {
  const [models, setModels] = useState<Model[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedModelId, setSelectedModelId] = useState('')
  const [opacity, setOpacity] = useState(70)
  const [inspectCoords, setInspectCoords] = useState<{ lng: number; lat: number } | null>(
    null,
  )
  const [inspection, setInspection] = useState<PointInspection | null>(null)
  const [inspectLoading, setInspectLoading] = useState(false)
  const [inspectError, setInspectError] = useState<string | null>(null)
  const [hudOpen, setHudOpen] = useState(false)
  const inspectAbortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    fetchModelCatalog()
      .then((list) => {
        setModels(list)
        setLoadError(null)
        setSelectedModelId((prev) => prev || list[0]?.id || '')
      })
      .catch(() => {
        setModels([])
        setLoadError('Could not load model catalog. Is the API running?')
      })
  }, [])

  const clearInspection = useCallback(() => {
    inspectAbortRef.current?.abort()
    inspectAbortRef.current = null
    setInspection(null)
    setInspectError(null)
    setInspectCoords(null)
    setInspectLoading(false)
    setHudOpen(false)
  }, [])

  const onModelChange = useCallback(
    (modelId: string) => {
      clearInspection()
      setSelectedModelId(modelId)
    },
    [clearInspection],
  )

  const closeHud = useCallback(() => {
    clearInspection()
  }, [clearInspection])

  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  const handleInspect = useCallback(
    (lng: number, lat: number) => {
      if (!selectedModel) return
      inspectAbortRef.current?.abort()
      const ac = new AbortController()
      inspectAbortRef.current = ac

      setHudOpen(true)
      setInspectCoords({ lng, lat })
      setInspectLoading(true)
      setInspectError(null)

      fetchPointInspection(selectedModel.id, lng, lat, ac.signal)
        .then(setInspection)
        .catch((e: unknown) => {
          if (e instanceof Error && e.name === 'AbortError') return
          const message = e instanceof Error ? e.message : 'Request failed'
          setInspection(null)
          setInspectError(message)
        })
        .finally(() => {
          if (!ac.signal.aborted) {
            setInspectLoading(false)
          }
        })
    },
    [selectedModel],
  )

  return (
    <div className="app-container">
      <Navbar />
      <div className="app-main">
        <MapControlPanel
          models={models}
          selectedModelId={selectedModelId}
          opacity={opacity}
          onModelChange={onModelChange}
          onOpacityChange={setOpacity}
        />
        {loadError && (
          <div
            role="alert"
            style={{
              position: 'absolute',
              top: 20,
              right: 20,
              zIndex: 1001,
              background: 'rgba(255, 230, 230, 0.95)',
              padding: '12px 16px',
              borderRadius: 8,
              maxWidth: 360,
              fontSize: 14,
            }}
          >
            {loadError}
          </div>
        )}
        {hudOpen && selectedModel && !loadError && (
          <InspectionHud
            onClose={closeHud}
            modelLabel={`${selectedModel.species} — ${selectedModel.activity}`}
            lng={inspectCoords?.lng ?? null}
            lat={inspectCoords?.lat ?? null}
            inspection={inspection}
            loading={inspectLoading}
            error={inspectError}
          />
        )}
        <MapComponent
          opacity={opacity / 100}
          model={selectedModel}
          onInspect={selectedModel && !loadError ? handleInspect : undefined}
        />
      </div>
    </div>
  )
}

export default App
