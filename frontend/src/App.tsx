import './App.css'
import MapComponent from './components/Map'
import { useEffect, useMemo, useState } from 'react'
import { MapControlPanel } from './components/map/MapControlPanel'
import type { Model } from './types/model'
import { apiBase } from './utils/apiBase'

function App() {
  const [models, setModels] = useState<Model[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedModelId, setSelectedModelId] = useState('')
  const [opacity, setOpacity] = useState(70)

  useEffect(() => {
    const base = apiBase()
    fetch(`${base}/models`)
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText || String(r.status))
        return r.json() as Promise<Model[]>
      })
      .then((list) => {
        setModels(list)
        setLoadError(null)
      })
      .catch(() => {
        setModels([])
        setLoadError('Could not load model catalog. Is the API running?')
      })
  }, [])

  useEffect(() => {
    if (!selectedModelId && models.length > 0) {
      setSelectedModelId(models[0].id)
    }
  }, [models, selectedModelId])

  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  return (
    <div className="app-container">
      <MapControlPanel
        models={models}
        selectedModelId={selectedModelId}
        opacity={opacity}
        onModelChange={setSelectedModelId}
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
      <MapComponent opacity={opacity / 100} model={selectedModel} />
    </div>
  )
}

export default App
