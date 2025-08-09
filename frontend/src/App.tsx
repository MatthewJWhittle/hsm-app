import './App.css'
import MapComponent from './components/Map'
import { useState } from 'react'
import { MapControlPanel } from './components/map/MapControlPanel'

function App() {
  const [selectedSpecies, setSelectedSpecies] = useState('')
  const [selectedActivity, setSelectedActivity] = useState('')
  const [opacity, setOpacity] = useState(70)

  return (
    <div className="app-container">
      <MapControlPanel
        selectedSpecies={selectedSpecies}
        selectedActivity={selectedActivity}
        opacity={opacity}
        onSpeciesChange={setSelectedSpecies}
        onActivityChange={setSelectedActivity}
        onOpacityChange={setOpacity}
      />
      <MapComponent opacity={opacity / 100} />
    </div>
  )
}

export default App
