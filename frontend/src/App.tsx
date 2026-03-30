import './App.css'
import MapComponent from './components/Map'
import { Box } from '@mui/material'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MapControlPanel, type ProjectSummary } from './components/map/MapControlPanel'
import { InspectionHud } from './components/InspectionHud'
import type { Model } from './types/model'
import type { CatalogProject } from './types/project'
import type { PointInspection } from './types/pointInspection'
import { fetchModelCatalog } from './api/catalog'
import { fetchProjectCatalog } from './api/projects'
import { fetchPointInspection } from './api/inspectPoint'
import { Navbar } from './components/Navbar'
import { useAuth } from './auth/useAuth'

const LEGACY_PROJECT_ID = '__legacy__'

function buildProjectOptions(
  projects: CatalogProject[],
  models: Model[],
): { id: string; name: string }[] {
  const opts = projects
    .filter((p) => p.status === 'active')
    .map((p) => ({ id: p.id, name: p.name }))
  const hasLegacy = models.some((m) => !m.project_id)
  if (hasLegacy) {
    opts.push({ id: LEGACY_PROJECT_ID, name: 'Legacy (no project)' })
  }
  return opts
}

function modelsForProject(projectId: string, models: Model[]): Model[] {
  if (projectId === LEGACY_PROJECT_ID) {
    return models.filter((m) => !m.project_id)
  }
  return models.filter((m) => m.project_id === projectId)
}

function App() {
  const { user, getIdToken } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [projects, setProjects] = useState<CatalogProject[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedProjectId, setSelectedProjectId] = useState('')
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
  const [catalogReady, setCatalogReady] = useState(false)

  useEffect(() => {
    let cancelled = false
    setCatalogReady(false)
    ;(async () => {
      try {
        const token = user ? await getIdToken(true).catch(() => null) : null
        if (cancelled) return
        const [plist, mlist] = await Promise.all([
          fetchProjectCatalog({ token }),
          fetchModelCatalog({ token }),
        ])
        if (cancelled) return
        setProjects(plist)
        setModels(mlist)
        setLoadError(null)
      } catch {
        if (!cancelled) {
          setProjects([])
          setModels([])
          setLoadError('Could not load catalog. Is the API running?')
        }
      } finally {
        if (!cancelled) setCatalogReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user, getIdToken])

  const projectOptions = useMemo(
    () => buildProjectOptions(projects, models),
    [projects, models],
  )

  useEffect(() => {
    if (!catalogReady) return
    const opts = projectOptions
    const pu = searchParams.get('project')
    const mu = searchParams.get('model')
    const defaultProject = opts[0]?.id ?? ''
    const projectId =
      pu && opts.some((o) => o.id === pu) ? pu : defaultProject
    const filtered = modelsForProject(projectId, models)
    const defaultModel = filtered[0]?.id ?? ''
    const modelId =
      mu && filtered.some((m) => m.id === mu) ? mu : defaultModel

    setSelectedProjectId(projectId)
    setSelectedModelId(modelId)
    if (projectId && modelId && (pu !== projectId || mu !== modelId)) {
      setSearchParams({ project: projectId, model: modelId }, { replace: true })
    }
  }, [catalogReady, searchParams, projectOptions, models, setSearchParams])

  const filteredModels = useMemo(
    () => modelsForProject(selectedProjectId, models),
    [selectedProjectId, models],
  )

  const projectSummary = useMemo((): ProjectSummary => {
    if (!selectedProjectId) return null
    if (selectedProjectId === LEGACY_PROJECT_ID) {
      return {
        isLegacy: true,
        visibility: 'public',
        hasEnvironmentalCog: false,
      }
    }
    const p = projects.find((x) => x.id === selectedProjectId)
    if (!p) return null
    return {
      isLegacy: false,
      visibility: p.visibility,
      hasEnvironmentalCog: Boolean(p.driver_cog_path),
    }
  }, [selectedProjectId, projects])

  const clearInspection = useCallback(() => {
    inspectAbortRef.current?.abort()
    inspectAbortRef.current = null
    setInspection(null)
    setInspectError(null)
    setInspectCoords(null)
    setInspectLoading(false)
    setHudOpen(false)
  }, [])

  const onProjectChange = useCallback(
    (projectId: string) => {
      clearInspection()
      setSelectedProjectId(projectId)
      const next = modelsForProject(projectId, models)
      const nextId = next[0]?.id ?? ''
      setSelectedModelId(nextId)
      if (projectId && nextId) {
        setSearchParams({ project: projectId, model: nextId }, { replace: true })
      }
    },
    [clearInspection, models, setSearchParams],
  )

  const onModelChange = useCallback(
    (modelId: string) => {
      clearInspection()
      setSelectedModelId(modelId)
      if (selectedProjectId && modelId) {
        setSearchParams({ project: selectedProjectId, model: modelId }, { replace: true })
      }
    },
    [clearInspection, selectedProjectId, setSearchParams],
  )

  const closeHud = useCallback(() => {
    clearInspection()
  }, [clearInspection])

  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  const handleInspect = useCallback(
    async (lng: number, lat: number) => {
      if (!selectedModel) return
      inspectAbortRef.current?.abort()
      const ac = new AbortController()
      inspectAbortRef.current = ac

      setHudOpen(true)
      setInspectCoords({ lng, lat })
      setInspectLoading(true)
      setInspectError(null)

      const token = user ? await getIdToken(true).catch(() => null) : null

      fetchPointInspection(selectedModel.id, lng, lat, ac.signal, { token })
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
    [selectedModel, user, getIdToken],
  )

  return (
    <div className="app-container">
      <Navbar />
      <div className="app-main">
        <MapControlPanel
          projectOptions={projectOptions}
          selectedProjectId={selectedProjectId}
          onProjectChange={onProjectChange}
          models={filteredModels}
          selectedModelId={selectedModelId}
          opacity={opacity}
          onModelChange={onModelChange}
          onOpacityChange={setOpacity}
          projectSummary={projectSummary}
        />
        <Box
          sx={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
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
              technicalDetails={{
                modelId: selectedModel.id,
                projectId: selectedModel.project_id,
                driverBandIndices: selectedModel.driver_band_indices,
              }}
            />
          )}
          <Box sx={{ flex: 1, minHeight: 0, minWidth: 0, position: 'relative' }}>
            <MapComponent
              opacity={opacity / 100}
              model={selectedModel}
              onInspect={selectedModel && !loadError ? handleInspect : undefined}
            />
          </Box>
        </Box>
      </div>
    </div>
  )
}

export default App
