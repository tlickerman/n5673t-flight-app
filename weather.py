"""
Live weather pull from aviationweather.gov (no API key required).
Used to auto-fill the "Current Conditions" section of the Takeoff Data Sheet.
"""

import requests

BASE_URL = "https://aviationweather.gov/api/data"
TIMEOUT_SECONDS = 8


def get_radar_station(icao_airport_id):
    """
    Map a departure/observation airport to the nearest NWS NEXRAD radar
    station for the regional map. Falls back to KLOT (Chicago) since that's
    home base coverage for KPWK operations.
    """
    airport_to_radar = {
        "KPWK": "KLOT", "KORD": "KLOT", "KMDW": "KLOT", "KDPA": "KLOT",
        "KUGN": "KMKX", "KMKE": "KMKX", "KMSN": "KMKX", "KGRB": "KGRB",
        "KATW": "KGRB", "KEAU": "KMPX", "KMSP": "KMPX", "K3D2": "KGRB",
        "KRFD": "KLOT", "KSGR": "KLOT",
    }
    return airport_to_radar.get((icao_airport_id or "").strip().upper(), "KLOT")


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
            "altimeter_inhg": _hpa_to_inhg(m.get("altim")),
            "ceiling_ft": _lowest_ceiling(m.get("clouds")),
            "clouds": m.get("clouds"),
            "flight_category": m.get("fltCat"),
            "elevation_m": m.get("elev"),
            "wx_string": m.get("wxString"),
            "decoded": _decode_metar(m),
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


WX_CODES = {
    "RA": "rain", "SN": "snow", "DZ": "drizzle", "SG": "snow grains",
    "IC": "ice crystals", "PL": "ice pellets", "GR": "hail", "GS": "small hail",
    "BR": "mist", "FG": "fog", "FU": "smoke", "HZ": "haze", "DU": "dust",
    "SA": "sand", "PY": "spray", "SQ": "squalls", "FC": "funnel cloud",
    "TS": "thunderstorm", "SH": "showers", "VC": "in vicinity",
    "-": "light", "+": "heavy",
}

CLOUD_COVER = {
    "SKC": "sky clear", "CLR": "clear below 12,000 ft", "FEW": "few clouds",
    "SCT": "scattered", "BKN": "broken", "OVC": "overcast", "VV": "obscured sky",
}

FLIGHT_CAT_LABELS = {
    "VFR": "VFR", "MVFR": "Marginal VFR", "IFR": "IFR", "LIFR": "Low IFR",
}


def _compass(deg):
    if deg is None:
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    try:
        return dirs[round(float(deg) / 22.5) % 16]
    except (TypeError, ValueError):
        return ""


def _decode_wx_string(wx):
    if not wx:
        return None
    tokens = wx.split()
    phrases = []
    for tok in tokens:
        intensity = ""
        remainder = tok
        if remainder.startswith(("-", "+")):
            intensity = WX_CODES.get(remainder[0], "")
            remainder = remainder[1:]
        parts = [remainder[i:i + 2] for i in range(0, len(remainder), 2)]
        words = [WX_CODES.get(p, p) for p in parts]
        phrase = " ".join(filter(None, [intensity] + words))
        phrases.append(phrase)
    return ", ".join(phrases)


def _decode_metar(m):
    """Build a plain-English summary from the parsed METAR fields."""
    parts = []

    fltcat = m.get("fltCat")
    if fltcat:
        parts.append(f"Flight category: {FLIGHT_CAT_LABELS.get(fltcat, fltcat)}.")

    wdir, wspd, wgst = m.get("wdir"), m.get("wspd"), m.get("wgst")
    if wspd is not None:
        if wspd == 0:
            parts.append("Winds calm.")
        else:
            dir_txt = "variable" if wdir in (None, "VRB") else f"{_compass(wdir)} ({wdir}\u00b0)"
            gust_txt = f", gusting {wgst} kt" if wgst else ""
            parts.append(f"Wind out of the {dir_txt} at {wspd} kt{gust_txt}.")

    visib = m.get("visib")
    if visib is not None:
        parts.append(f"Visibility {visib} statute miles.")

    wx_decoded = _decode_wx_string(m.get("wxString"))
    if wx_decoded:
        parts.append(f"Weather: {wx_decoded}.")

    clouds = m.get("clouds") or []
    if clouds:
        layer_txt = "; ".join(
            f"{CLOUD_COVER.get(c.get('cover'), c.get('cover'))} at {c.get('base')} ft"
            if c.get("base") is not None else CLOUD_COVER.get(c.get("cover"), c.get("cover"))
            for c in clouds
        )
        parts.append(f"Sky: {layer_txt}.")
    else:
        parts.append("Sky: clear.")

    temp, dewp = m.get("temp"), m.get("dewp")
    if temp is not None:
        parts.append(f"Temperature {temp}\u00b0C, dewpoint {dewp}\u00b0C.")

    return " ".join(parts)


def _hpa_to_inhg(hpa):
    """aviationweather.gov's 'altim' field is in hectopascals, not inHg —
    convert so the displayed value matches the raw METAR's Axxxx group."""
    if hpa is None:
        return None
    try:
        return round(float(hpa) * 0.0295300, 2)
    except (TypeError, ValueError):
        return None


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
