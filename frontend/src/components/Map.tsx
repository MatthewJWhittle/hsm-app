import Map, { Layer, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useRef } from 'react';

interface MapComponentProps {
  opacity?: number;
}

function MapComponent({ opacity = 0.5 }: MapComponentProps) {
  const mapRef = useRef(null);

  // Define the raster layer style
  const rasterLayer = {
    id: 'hsm-raster',
    type: 'raster' as const,
    source: 'hsm-source',
    paint: {
      'raster-opacity': opacity
    }
  };

  // construct the tile url
  const rasterFile = "data/Myotis daubentonii_In flight_cog.tif";
  const rasterFileEncoded = encodeURIComponent(rasterFile);
  const params = {
    url: `file:///${rasterFileEncoded}`,
    colormap_name: "viridis",
    rescale: "0,1"
  }
  const queryString = Object.entries(params)  
  .map(([key, value]) => `${key}=${value}`)
  .join('&');
  const tile_url = `http://localhost:8080/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?${queryString}`;

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        longitude: -1.9487000,
        latitude: 53.900293,
        zoom: 8
      }}
      style={{width: "100%", height: "100%"}}
      mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
    >
      <Source
        id="hsm-source"
        type="raster"
        minzoom={1}
        maxzoom={15}
        tiles={[
          tile_url
        ]}
        tileSize={256}
      >
        <Layer {...rasterLayer} />
      </Source>
    </Map>
  );
}
// http://localhost:8080/cog/tiles/WorldMercatorWGS84Quad/{z}/{x}/{y}?url=file:///data/Myotis%20daubentonii_In%20flight_cog.tif&colormap_name=viridis&rescale=0%2C1
// http://localhost:8080/cog/tiles/WorldMercatorWGS84Quad/{z}/{x}/{y}?url=file:///data/Myotis%20daubentonii_In%20flight_cog.tif&colormap_name=viridis&rescale=0,1

export default MapComponent;
