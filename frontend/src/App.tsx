import './App.css'
import MapComponent from './components/Map'
import { Alert, Box, Button } from '@mui/material'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { MapFloatingControls } from './components/map/MapFloatingControls'
import { MapLayerDetailsDialog } from './components/map/MapLayerDetailsDialog'
import { MapInterpretationDialog } from './components/map/MapInterpretationDialog'
import { SuitabilityLegend } from './components/map/SuitabilityLegend'
import { InspectionHud } from './components/InspectionHud'
import { type Model, getFeatureBandNames } from './types/model'
import type { CatalogProject, ProjectSummary } from './types/project'
import type { PointInspection } from './types/pointInspection'
import { fetchModelCatalog } from './api/catalog'
import { fetchProjectCatalog } from './api/projects'
import { postExplainabilityWarmup } from './api/explainabilityWarmup'
import { fetchPointInspection } from './api/inspectPoint'
import { Navbar } from './components/Navbar'
import { useAuth } from './auth/useAuth'
import { layerDisplayName } from './utils/layerDisplay'

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
    opts.push({ id: LEGACY_PROJECT_ID, name: 'Stand-alone layers' })
  }
  return opts
}

function modelsForProject(projectId: string, models: Model[]): Model[] {
  if (projectId === LEGACY_PROJECT_ID) {
    return models.filter((m) => !m.project_id)
  }
  return models.filter((m) => m.project_id === projectId)
}

function projectIdForModel(m: Model): string {
  return m.project_id ?? LEGACY_PROJECT_ID
}

function App() {
  const { user, getIdToken } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [projects, setProjects] = useState<CatalogProject[]>([])
  const [models, setModels] = useState<Model[]>([])
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedModelId, setSelectedModelId] = useState('')
  const [opacity, setOpacity] = useState(70)
  const [layerVisible, setLayerVisible] = useState(true)
  const [inspectCoords, setInspectCoords] = useState<{ lng: number; lat: number } | null>(
    null,
  )
  const [inspection, setInspection] = useState<PointInspection | null>(null)
  const [inspectLoading, setInspectLoading] = useState(false)
  const [inspectError, setInspectError] = useState<string | null>(null)
  const [hudOpen, setHudOpen] = useState(false)
  const inspectAbortRef = useRef<AbortController | null>(null)
  const [catalogReady, setCatalogReady] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)
  const [mapInfoOpen, setMapInfoOpen] = useState(false)
  const [layerDetailsOpen, setLayerDetailsOpen] = useState(false)

  const retryLoadCatalog = useCallback(() => {
    setReloadNonce((n) => n + 1)
  }, [])

  const toggleLayerVisible = useCallback(() => {
    setLayerVisible((v) => !v)
  }, [])

  useEffect(() => {
    // Keyboard shortcut: "V" toggles the active layer's visibility while
    // focus is not in an input, textarea, or contenteditable surface. Matches
    // the quick-compare workflow (flick raster on/off vs. the basemap).
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'v' && e.key !== 'V') return
      if (e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return
      const target = e.target as HTMLElement | null
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return
      }
      setLayerVisible((v) => !v)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

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
          setLoadError('Couldn’t load map layers. Check your connection, or try again in a moment.')
        }
      } finally {
        if (!cancelled) setCatalogReady(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [user, getIdToken, reloadNonce])

  const projectOptions = useMemo(
    () => buildProjectOptions(projects, models),
    [projects, models],
  )

  const selectedModel = useMemo(
    () => models.find((m) => m.id === selectedModelId) ?? null,
    [models, selectedModelId],
  )

  useEffect(() => {
    if (!catalogReady || !selectedModelId) return
    const ac = new AbortController()
    let cancelled = false
    ;(async () => {
      const token = user ? await getIdToken(true).catch(() => null) : null
      if (cancelled) return
      await postExplainabilityWarmup(selectedModelId, ac.signal, { token }).catch(() => {})
    })()
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [catalogReady, selectedModelId, user, getIdToken])

  const selectedProjectId = useMemo(() => {
    if (!selectedModel) return ''
    return projectIdForModel(selectedModel)
  }, [selectedModel])

  const selectedProjectLabel = useMemo(() => {
    if (!selectedModel) return ''
    if (!selectedModel.project_id) return 'Stand-alone layer'
    const p = projects.find((x) => x.id === selectedModel.project_id)
    return p?.name ?? selectedModel.project_id
  }, [selectedModel, projects])

  useEffect(() => {
    if (!catalogReady) return
    const pu = searchParams.get('project')
    const mu = searchParams.get('model')
    const opts = projectOptions

    let modelId = ''
    let derivedProjectId = ''

    if (mu) {
      const m = models.find((x) => x.id === mu)
      if (m) {
        modelId = m.id
        derivedProjectId = projectIdForModel(m)
      }
    }
    if (!modelId) {
      if (pu && opts.some((o) => o.id === pu)) {
        const filtered = modelsForProject(pu, models)
        const first = filtered[0]
        if (first) {
          modelId = first.id
          derivedProjectId = projectIdForModel(first)
        }
      } else if (models.length > 0) {
        const first = models[0]
        modelId = first.id
        derivedProjectId = projectIdForModel(first)
      }
    }

    setSelectedModelId(modelId)
    if (modelId && derivedProjectId && (pu !== derivedProjectId || mu !== modelId)) {
      setSearchParams({ project: derivedProjectId, model: modelId }, { replace: true })
    }
  }, [catalogReady, searchParams, projectOptions, models, setSearchParams])

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

  const onModelChange = useCallback(
    (modelId: string) => {
      clearInspection()
      if (!modelId) setLayerDetailsOpen(false)
      // Always re-show the raster when switching to a new layer — stale
      // visibility across different species is almost never what the user
      // wants.
      setLayerVisible(true)
      setSelectedModelId(modelId)
      const m = models.find((x) => x.id === modelId)
      if (m) {
        const pid = projectIdForModel(m)
        setSearchParams({ project: pid, model: modelId }, { replace: true })
      }
    },
    [clearInspection, models, setSearchParams],
  )

  const closeHud = useCallback(() => {
    clearInspection()
  }, [clearInspection])

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
      <Box
        component="main"
        sx={{
          flex: 1,
          minHeight: 0,
          minWidth: 0,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Absolute-fill wrapper so the MapLibre canvas has an explicit size. */}
        <Box sx={{ position: 'absolute', inset: 0 }}>
          <MapComponent
            opacity={opacity / 100}
            visible={layerVisible}
            model={selectedModel}
            onInspect={selectedModel && !loadError ? handleInspect : undefined}
          />
        </Box>

        <MapFloatingControls
          models={models}
          selectedModelId={selectedModelId}
          onModelChange={onModelChange}
          onOpenMapInfoDialog={() => setMapInfoOpen(true)}
          onOpenLayerDetailsDialog={() => setLayerDetailsOpen(true)}
          opacity={opacity}
          onOpacityChange={setOpacity}
          layerVisible={layerVisible}
          onToggleLayerVisible={toggleLayerVisible}
          loading={!catalogReady}
          errored={Boolean(loadError)}
        />

        {selectedModel && !loadError && layerVisible && (
          <Box
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              zIndex: 999,
              pointerEvents: 'auto',
            }}
          >
            <SuitabilityLegend />
          </Box>
        )}

        {loadError && (
          <Alert
            severity="error"
            variant="outlined"
            sx={{
              position: 'absolute',
              top: 16,
              right: 16,
              zIndex: 1001,
              maxWidth: 360,
              bgcolor: 'background.paper',
              boxShadow: 2,
            }}
            action={
              <Button color="inherit" size="small" onClick={retryLoadCatalog}>
                Retry
              </Button>
            }
          >
            {loadError}
          </Alert>
        )}

        {hudOpen && selectedModel && !loadError && (
          <InspectionHud
            onClose={closeHud}
            modelLabel={layerDisplayName(selectedModel)}
            lng={inspectCoords?.lng ?? null}
            lat={inspectCoords?.lat ?? null}
            inspection={inspection}
            loading={inspectLoading}
            error={inspectError}
            technicalDetails={{
              modelId: selectedModel.id,
              projectId: selectedModel.project_id,
              driverFeatureBandNames: getFeatureBandNames(selectedModel),
            }}
          />
        )}
      </Box>

      <MapInterpretationDialog open={mapInfoOpen} onClose={() => setMapInfoOpen(false)} />
      <MapLayerDetailsDialog
        open={layerDetailsOpen}
        onClose={() => setLayerDetailsOpen(false)}
        model={selectedModel}
        projectSummary={projectSummary}
        selectedProjectLabel={selectedProjectLabel}
      />
    </div>
  )
}

export default App
