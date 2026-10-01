# DisasterShield — Earth Engine Disaster Risk & Emergency Routing

A full-stack disaster risk assessment and emergency route identification web application.

## What is real / live?

- **Google Earth Engine**: live satellite/terrain-derived risk analysis on the server.
- **OpenStreetMap**: live basemap through Leaflet.
- **OSRM**: live road routing using OpenStreetMap road data.
- **Google Maps**: "Open in Google Maps" handoff for the selected route.
- **No fake map geometry** is used.

> Important: OpenStreetMap data is free/open, but the public OSM tile server is community-funded and has usage rules. For a classroom/demo deployment with normal interactive use, attribution and normal caching requirements apply. For production/high traffic, use an OSM-derived tile provider or host your own tiles.

## Risk model

The included Earth Engine endpoint computes a demonstrator risk index from:

1. **JRC Global Surface Water** occurrence — persistent water/flood susceptibility signal.
2. **SRTM elevation/slope** — terrain exposure.
3. **Sentinel-2 surface reflectance** — recent NDVI/vegetation condition.
4. **Rainfall hook** — optional CHIRPS precipitation can be added/weighted in `risk_service.py`.

This is a **screening/decision-support index**, not an official emergency warning or engineering-grade hazard model. The weights are intentionally visible in the UI.

## Architecture

Browser
  -> FastAPI
      -> Google Earth Engine
  -> OSRM public routing service
  -> OpenStreetMap tiles
  -> Google Maps URL for navigation

## 1. Earth Engine setup

You need a Google Cloud / Earth Engine-enabled account or project.

Install the Python Earth Engine API:

```bash
pip install -r backend/requirements.txt
```

Authenticate locally:

```bash
earthengine authenticate
```

For a deployed server, use a service account / workload identity rather than putting credentials in the frontend.

Set:

```env
EE_PROJECT=your-earth-engine-project-id
```

If using a service-account key for a simple local/server demo:

```env
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
```

Do NOT commit that JSON file.

## 2. Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS

uvicorn main:app --reload --port 8000
```

Test:

- http://localhost:8000/health
- http://localhost:8000/docs

## 3. Frontend

The frontend is plain HTML/CSS/JS, so no build step is required.

Run it from a local web server:

```bash
cd frontend
python -m http.server 5173
```

Open:

http://localhost:5173

The frontend expects the API at `http://localhost:8000`.

## 4. Routing

The default routing service is OSRM:

`https://router.project-osrm.org`

It is suitable for a demonstration, but it is a public service with capacity/usage limitations. For a production deployment, use your own OSRM/Valhalla instance or a provider with a suitable SLA.

## 5. Google Maps

The app does not embed the paid Google Maps JavaScript SDK. Instead it creates a Google Maps Directions URL for the selected emergency route:

`https://www.google.com/maps/dir/?api=1&origin=...&destination=...`

This gives the presenter an actual Google Maps navigation handoff without exposing a Google Maps API key.

If your project specifically requires an embedded Google Maps map, enable Maps JavaScript API in Google Cloud, configure billing/quotas, and replace the Leaflet map component.

## Demo flow

1. Open the site.
2. Search for a location or click the map.
3. Select a disaster type.
4. Click **Assess risk with Earth Engine**.
5. The server requests real Earth Engine statistics for the selected area.
6. Choose an emergency destination.
7. Click **Find safest route**.
8. The app requests a real road route from OSRM.
9. The route is drawn on the map and its distance/time are shown.
10. Click **Open in Google Maps** to continue navigation.

## Suggested presentation storyline

Problem:
- During disasters, responders need a quick spatial picture of hazard exposure and an accessible route.

Solution:
- Earth observation + terrain data identifies risk hotspots.
- OpenStreetMap provides the road network.
- OSRM identifies a road route.
- Google Maps provides the final navigation handoff.

Future production upgrades:
- Weather/radar nowcasts.
- Flood depth models and river networks.
- Official disaster authority feeds.
- Hospitals, shelters and fire stations from authoritative datasets.
- Multi-vehicle routing.
- Road closure feeds.
- Offline responder mode.
- Historical event validation and model calibration.
