import ee
import math
from datetime import datetime, timedelta

def _safe_number(value, default=0.0):
    try:
        if value is None:
            return default
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return default
        return value
    except Exception:
        return default


def _normalize(value, low, high):
    if high == low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def assess_risk(lat: float, lon: float, radius_m: int, hazard: str):
    """
    Real Earth Engine analysis.

    The output is intentionally a transparent screening index:
      flood/water persistence + low terrain + low vegetation condition.

    It is NOT an official emergency warning.
    """
    point = ee.Geometry.Point([lon, lat])
    area = point.buffer(radius_m)

    # 1) JRC Global Surface Water: historical occurrence (%)
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
    water_stats = water.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=area,
        scale=30,
        maxPixels=1e8,
        bestEffort=True,
    ).getInfo()
    water_occurrence = _safe_number(water_stats.get("occurrence"))

    # 2) SRTM terrain
    dem = ee.Image("USGS/SRTMGL1_003")
    terrain = ee.Terrain.products(dem)
    elevation_stats = dem.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=area,
        scale=30,
        maxPixels=1e8,
        bestEffort=True,
    ).getInfo()
    slope_stats = terrain.select("slope").reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=area,
        scale=30,
        maxPixels=1e8,
        bestEffort=True,
    ).getInfo()

    elevation = _safe_number(elevation_stats.get("elevation"))
    slope = _safe_number(slope_stats.get("slope"))

    # 3) Sentinel-2 recent NDVI.
    end = datetime.utcnow()
    start = end - timedelta(days=60)

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(area)
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 40))
    )

    count = s2.size().getInfo()

    if count:
        def add_ndvi(image):
            ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
            return image.addBands(ndvi)

        ndvi = s2.map(add_ndvi).select("NDVI").median()
        ndvi_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
            scale=20,
            maxPixels=1e8,
            bestEffort=True,
        ).getInfo()
        ndvi_value = _safe_number(ndvi_stats.get("NDVI"))
    else:
        ndvi_value = 0.35

    # Transparent scoring:
    # high persistent water = higher flood exposure
    # lower slope = somewhat higher flood exposure
    # low NDVI = higher surface-stress signal
    water_score = _normalize(water_occurrence, 0, 100)
    low_slope_score = 1 - _normalize(slope, 0, 20)
    vegetation_stress = 1 - _normalize(ndvi_value, -0.1, 0.8)

    if hazard.lower() == "flood":
        score = 100 * (0.55 * water_score + 0.30 * low_slope_score + 0.15 * vegetation_stress)
    elif hazard.lower() == "landslide":
        slope_score = _normalize(slope, 5, 35)
        score = 100 * (0.55 * slope_score + 0.20 * vegetation_stress + 0.25 * (1 - water_score))
    else:
        # Generic exposure screening for other selectable hazards.
        score = 100 * (0.40 * water_score + 0.30 * low_slope_score + 0.30 * vegetation_stress)

    score = max(0, min(100, score))

    if score < 30:
        level = "Low"
    elif score < 60:
        level = "Moderate"
    elif score < 80:
        level = "High"
    else:
        level = "Critical"

    return {
        "hazard": hazard,
        "score": round(score, 1),
        "level": level,
        "location": {"lat": lat, "lon": lon},
        "radius_m": radius_m,
        "metrics": {
            "water_occurrence_pct": round(water_occurrence, 1),
            "mean_elevation_m": round(elevation, 1),
            "mean_slope_deg": round(slope, 1),
            "recent_ndvi": round(ndvi_value, 3),
            "sentinel2_images_used": int(count),
        },
        "method": [
            "JRC Global Surface Water occurrence",
            "SRTM elevation and slope",
            "Sentinel-2 SR Harmonized recent median NDVI",
        ],
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "warning": "Screening/decision-support index only; not an official warning or engineering assessment."
    }
