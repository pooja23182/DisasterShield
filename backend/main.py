import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import ee
import httpx

from risk_service import assess_risk

app = FastAPI(
    title="DisasterShield API",
    version="1.0.0",
    description="Google Earth Engine disaster-risk and emergency-routing backend."
)

origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin, "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

EE_PROJECT = os.getenv("EE_PROJECT")

try:
    if EE_PROJECT:
        ee.Initialize(project=EE_PROJECT)
    else:
        ee.Initialize()
except Exception as exc:
    print("Earth Engine initialization warning:", exc)


class Point(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class RiskRequest(BaseModel):
    lat: float
    lon: float
    radius_m: int = Field(2500, ge=500, le=10000)
    hazard: str = "Flood"


class RouteRequest(BaseModel):
    origin: Point
    destination: Point


@app.get("/health")
def health():
    return {"ok": True, "earth_engine_project": EE_PROJECT or "default credentials"}


@app.post("/api/risk")
def risk(req: RiskRequest):
    try:
        return assess_risk(req.lat, req.lon, req.radius_m, req.hazard)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/route")
async def route(req: RouteRequest):
    # OSRM expects lon,lat.
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{req.origin.lon},{req.origin.lat};"
        f"{req.destination.lon},{req.destination.lat}"
        "?overview=full&geometries=geojson&steps=true"
    )

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(status_code=404, detail="No road route found.")

    r = data["routes"][0]
    return {
        "distance_km": round(r["distance"] / 1000, 2),
        "duration_min": round(r["duration"] / 60, 1),
        "geometry": r["geometry"],
        "steps": [
            {
                "instruction": step.get("maneuver", {}).get("type", ""),
                "name": step.get("name", ""),
                "distance_m": round(step.get("distance", 0), 1),
            }
            for leg in r.get("legs", [])
            for step in leg.get("steps", [])
        ],
    }
