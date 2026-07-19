"""
Live weather pull from aviationweather.gov (no API key required).
Used to auto-fill the "Current Conditions" section of the Takeoff Data Sheet.
"""

import requests

BASE_URL = "https://aviationweather.gov/api/data"
TIMEOUT_SECONDS = 8


def get_metar(station_id):
    """Fetch the latest raw + decoded METAR for a station (e.g. 'KPWK')."""
    station_id = (station_id or "").strip().upper()
    if not station_id:
        return {"error": "No station ID provided."}
    try:
        resp = requests.get(
            f"{BASE_URL}/metar",
            params={"ids": station_id, "format": "json", "taf": "false"},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return {"error": f"No METAR found for {station_id}."}
        m = data[0]
        return {
            "station": m.get("icaoId", station_id),
            "raw": m.get("rawOb"),
            "observed": m.get("obsTime"),
            "temp_c": m.get("temp"),
            "dewpoint_c": m.get("dewp"),
            "wind_dir_deg": m.get("wdir"),
            "wind_speed_kt": m.get("wspd"),
            "wind_gust_kt": m.get("wgst"),
            "visibility_sm": m.get("visib"),
            "altimeter_inhg": m.get("altim"),
            "ceiling_ft": _lowest_ceiling(m.get("clouds")),
            "clouds": m.get("clouds"),
            "flight_category": m.get("fltCat"),
            "elevation_m": m.get("elev"),
        }
    except requests.RequestException as e:
        return {"error": f"Weather fetch failed: {e}"}


def get_taf(station_id):
    """Fetch the latest TAF for a station."""
    station_id = (station_id or "").strip().upper()
    if not station_id:
        return {"error": "No station ID provided."}
    try:
        resp = requests.get(
            f"{BASE_URL}/taf",
            params={"ids": station_id, "format": "json"},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return {"error": f"No TAF found for {station_id}."}
        t = data[0]
        return {"station": t.get("icaoId", station_id), "raw": t.get("rawTAF")}
    except requests.RequestException as e:
        return {"error": f"TAF fetch failed: {e}"}


def _lowest_ceiling(clouds):
    if not clouds:
        return None
    ceiling_covers = {"BKN", "OVC"}
    ceilings = [c.get("base") for c in clouds if c.get("cover") in ceiling_covers and c.get("base") is not None]
    return min(ceilings) if ceilings else None


def compute_density_altitude(pressure_altitude_ft, temp_c):
    """ISA standard temp at a given pressure altitude, then DA approximation."""
    try:
        pressure_altitude_ft = float(pressure_altitude_ft)
        temp_c = float(temp_c)
    except (TypeError, ValueError):
        return None
    isa_temp_c = 15 - (2 * (pressure_altitude_ft / 1000))
    da = pressure_altitude_ft + 120 * (temp_c - isa_temp_c)
    return round(da)


def compute_pressure_altitude(field_elevation_ft, altimeter_inhg):
    try:
        field_elevation_ft = float(field_elevation_ft)
        altimeter_inhg = float(altimeter_inhg)
    except (TypeError, ValueError):
        return None
    return round(field_elevation_ft + (29.92 - altimeter_inhg) * 1000)
