
import Map from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';


function MapComponent() {
  return (
    <Map
      initialViewState={{
        longitude: -1.9487000,
        latitude: 53.900293,
        zoom: 14
      }}
      style={{width: "100%", height: "100%"}}
      mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    />
  );
}

export default MapComponent;