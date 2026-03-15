import './App.css'
import MapComponent from './components/Map'
import { useEffect, useMemo, useState } from 'react'
import { MapControlPanel } from './components/map/MapControlPanel'

function App() {
  const [selectedSpecies, setSelectedSpecies] = useState('')
  const [selectedActivity, setSelectedActivity] = useState('')
  const [opacity, setOpacity] = useState(70)
  const [speciesOptions, setSpeciesOptions] = useState<string[]>([])
  const [activityOptionsAll, setActivityOptionsAll] = useState<string[]>([])
  const [items, setItems] = useState<Array<{ species: string; activity: string; cog_path: string }>>([])
  const [cogPath, setCogPath] = useState('')

  // Fetch available options (species, activities)
  useEffect(() => {
    fetch('http://localhost:8000/hsm/options')
      .then((r) => r.json())
      .then((data) => {
        setSpeciesOptions(data.species ?? [])
        setActivityOptionsAll(data.activities ?? [])
        setItems(data.items ?? [])
      })
      .catch(() => {
        setSpeciesOptions([])
        setActivityOptionsAll([])
        setItems([])
      })
  }, [])

  useEffect(() => {
    if (!selectedSpecies && speciesOptions.length > 0) {
      setSelectedSpecies(speciesOptions[0])
    }
  }, [speciesOptions, selectedSpecies])

  // Compute per-species activity options from items
  const activityOptions = useMemo(() => {
    if (!selectedSpecies) return []
    const set = new Set<string>()
    for (const it of items) if (it.species === selectedSpecies) set.add(it.activity)
    const arr = Array.from(set)
    return arr.length > 0 ? arr : activityOptionsAll
  }, [items, activityOptionsAll, selectedSpecies])

  useEffect(() => {
    if ((!selectedActivity || !activityOptions.includes(selectedActivity)) && activityOptions.length > 0) {
      setSelectedActivity(activityOptions[0])
    }
  }, [activityOptions, selectedActivity])

  // Fetch the cog url for the selected species/activity
  useEffect(() => {
    if (!selectedSpecies || !selectedActivity) return
    const url = new URL('http://localhost:8000/hsm/url')
    url.searchParams.set('species', selectedSpecies)
    url.searchParams.set('activity', selectedActivity)
    fetch(url.toString())
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((data) => setCogPath(data.cog_path ?? ''))
      .catch(() => setCogPath(''))
  }, [selectedSpecies, selectedActivity])

  return (
    <div className="app-container">
      <MapControlPanel
        selectedSpecies={selectedSpecies}
        selectedActivity={selectedActivity}
        opacity={opacity}
        onSpeciesChange={setSelectedSpecies}
        onActivityChange={setSelectedActivity}
        onOpacityChange={setOpacity}
        speciesOptions={speciesOptions}
        activityOptions={activityOptions}
      />
      <MapComponent opacity={opacity / 100} cogPath={cogPath} />
    </div>
  )
}

export default App
