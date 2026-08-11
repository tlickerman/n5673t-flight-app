"""
Live weather pull from aviationweather.gov (no API key required).
Used to auto-fill the "Current Conditions" section of the Takeoff Data Sheet.
"""

import requests

BASE_URL = "https://aviationweather.gov/api/data"
TIMEOUT_SECONDS = 8

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


import re
from datetime import datetime, timedelta, timezone as dt_timezone

TAF_WIND_RE = re.compile(r"^(?P<dir>\d{3}|VRB)(?P<spd>\d{2,3})(G(?P<gust>\d{2,3}))?KT$")
TAF_VIS_RE = re.compile(r"^(?P<frac>M?\d+(/\d+)?|P6)SM$")
TAF_SKY_RE = re.compile(r"^(FEW|SCT|BKN|OVC|VV)(\d{3})$")
TAF_FM_RE = re.compile(r"^FM(?P<day>\d{2})(?P<hour>\d{2})(?P<min>\d{2})$")
TAF_TIME_RANGE_RE = re.compile(r"^(?P<d1>\d{2})(?P<h1>\d{2})/(?P<d2>\d{2})(?P<h2>\d{2})$")
TAF_PROB_RE = re.compile(r"^PROB(\d{2})$")


def _taf_day_hour_to_dt(day, hour, minute, ref_dt):
    """Resolve a TAF DDHH(MM) token to a full UTC datetime using ref_dt (the
    TAF issuance time) for month/year context, handling month rollover."""
    day, hour, minute = int(day), int(hour), int(minute or 0)
    year, month = ref_dt.year, ref_dt.month
    try:
        candidate = datetime(year, month, day, hour % 24, minute, tzinfo=dt_timezone.utc)
    except ValueError:
        return None
    if hour == 24:
        candidate += timedelta(hours=24)
    # If the day number is much earlier than the issuance day, the TAF
    # period has rolled into the next month.
    if day < ref_dt.day - 5:
        if month == 12:
            candidate = candidate.replace(year=year + 1, month=1)
        else:
            candidate = candidate.replace(month=month + 1)
    return candidate


def _decode_taf_fields(tokens):
    """Pull wind/visibility/sky/weather out of a list of TAF tokens."""
    fields = {"wind": None, "visibility": None, "sky": [], "weather": None}
    wx_tokens = []
    for tok in tokens:
        m = TAF_WIND_RE.match(tok)
        if m:
            gust = f", gusting {m.group('gust')} kt" if m.group("gust") else ""
            direction = "variable" if m.group("dir") == "VRB" else f"{m.group('dir')}\u00b0"
            fields["wind"] = f"{direction} at {m.group('spd')} kt{gust}"
            continue
        m = TAF_VIS_RE.match(tok)
        if m:
            frac = m.group("frac")
            fields["visibility"] = "6+ SM" if frac == "P6" else f"{frac} SM"
            continue
        m = TAF_SKY_RE.match(tok)
        if m:
            cover, base = m.group(1), int(m.group(2)) * 100
            fields["sky"].append(f"{CLOUD_COVER.get(cover, cover)} at {base} ft")
            continue
        if tok in ("SKC", "CLR", "NSW"):
            fields["sky"].append(CLOUD_COVER.get(tok, tok))
            continue
        # Leftover tokens (weather phenomena codes like -RA, BR, etc.)
        if re.match(r"^[+-]?[A-Z]{2,6}$", tok) and tok not in ("KT", "SM"):
            wx_tokens.append(tok)
    if wx_tokens:
        fields["weather"] = _decode_wx_string(" ".join(wx_tokens))
    return fields


def parse_taf_periods(raw_taf):
    """
    Parse a raw TAF string into a list of period dicts:
    {type: 'base'|'tempo'|'becmg'|'prob', start, end, probability, fields}
    Best-effort parser covering FM/TEMPO/BECMG/PROBnn groups, which covers
    the vast majority of U.S. TAFs. Returns [] if the TAF can't be parsed.
    """
    if not raw_taf:
        return []
    tokens = raw_taf.replace("\n", " ").split()
    if not tokens or tokens[0] != "TAF":
        return []

    # Find issuance time (DDHHMMZ) and overall valid period (DDHH/DDHH)
    issuance = next((t for t in tokens if re.match(r"^\d{6}Z$", t)), None)
    valid_range = next((t for t in tokens if TAF_TIME_RANGE_RE.match(t)), None)
    if not issuance or not valid_range:
        return []

    now = datetime.now(dt_timezone.utc)
    ref_dt = now.replace(day=int(issuance[:2]), hour=int(issuance[2:4]),
                          minute=int(issuance[4:6]), second=0, microsecond=0)

    m = TAF_TIME_RANGE_RE.match(valid_range)
    period_start = _taf_day_hour_to_dt(m.group("d1"), m.group("h1"), 0, ref_dt)
    period_end = _taf_day_hour_to_dt(m.group("d2"), m.group("h2"), 0, ref_dt)
    if not period_start or not period_end:
        return []

    # Split remaining tokens (after the valid_range token) into groups,
    # each starting at a FM/TEMPO/BECMG/PROBnn keyword.
    start_idx = tokens.index(valid_range) + 1
    body = tokens[start_idx:]

    groups = []  # (type, header_tokens, condition_tokens)
    current_type = "base"
    current_header = []
    current_tokens = []

    def flush():
        if current_tokens or current_header or current_type == "base":
            groups.append((current_type, current_header, current_tokens))

    i = 0
    while i < len(body):
        tok = body[i]
        if TAF_FM_RE.match(tok):
            flush()
            current_type, current_header, current_tokens = "fm", [tok], []
        elif tok == "TEMPO":
            flush()
            current_type, current_header, current_tokens = "tempo", [tok], []
        elif tok == "BECMG":
            flush()
            current_type, current_header, current_tokens = "becmg", [tok], []
        elif TAF_PROB_RE.match(tok):
            flush()
            current_type, current_header, current_tokens = "prob", [tok], []
        else:
            if current_type in ("tempo", "becmg", "prob") and TAF_TIME_RANGE_RE.match(tok) and len(current_header) == 1:
                current_header.append(tok)
            else:
                current_tokens.append(tok)
        i += 1
    flush()

    periods = []
    base_start = period_start
    base_segments_raw = [g for g in groups if g[0] in ("base", "fm")]

    for idx, (gtype, header, cond_tokens) in enumerate(base_segments_raw):
        if gtype == "fm":
            m = TAF_FM_RE.match(header[0])
            seg_start = _taf_day_hour_to_dt(m.group("day"), m.group("hour"), m.group("min"), ref_dt)
        else:
            seg_start = period_start
        seg_end = period_end
        if idx + 1 < len(base_segments_raw):
            nxt_type, nxt_header, _ = base_segments_raw[idx + 1]
            if nxt_type == "fm":
                m2 = TAF_FM_RE.match(nxt_header[0])
                seg_end = _taf_day_hour_to_dt(m2.group("day"), m2.group("hour"), m2.group("min"), ref_dt)
        if seg_start:
            periods.append({
                "type": "base", "start": seg_start, "end": seg_end,
                "probability": None, "fields": _decode_taf_fields(cond_tokens),
            })

    for gtype, header, cond_tokens in groups:
        if gtype not in ("tempo", "becmg", "prob"):
            continue
        prob_pct = None
        time_tok = None
        if gtype == "prob":
            prob_match = TAF_PROB_RE.match(header[0])
            prob_pct = prob_match.group(1) if prob_match else None
            time_tok = header[1] if len(header) > 1 else None
        else:
            time_tok = header[1] if len(header) > 1 else None
        if not time_tok:
            continue
        m3 = TAF_TIME_RANGE_RE.match(time_tok)
        if not m3:
            continue
        seg_start = _taf_day_hour_to_dt(m3.group("d1"), m3.group("h1"), 0, ref_dt)
        seg_end = _taf_day_hour_to_dt(m3.group("d2"), m3.group("h2"), 0, ref_dt)
        if seg_start and seg_end:
            periods.append({
                "type": gtype, "start": seg_start, "end": seg_end,
                "probability": prob_pct, "fields": _decode_taf_fields(cond_tokens),
            })

    return periods


def get_taf_conditions_for_time(raw_taf, target_dt_utc):
    """
    Given a raw TAF and a target UTC datetime, return the applicable base
    conditions plus any overlapping TEMPO/BECMG/PROB conditions. Returns
    None if the TAF can't be parsed or the target time is outside the
    TAF's valid period.
    """
    periods = parse_taf_periods(raw_taf)
    if not periods:
        return None

    base = None
    overlays = []
    for p in periods:
        if p["start"] and p["end"] and p["start"] <= target_dt_utc < p["end"]:
            if p["type"] == "base":
                base = p
            else:
                overlays.append(p)

    if base is None:
        return None

    result = {
        "wind": base["fields"]["wind"],
        "visibility": base["fields"]["visibility"],
        "sky": "; ".join(base["fields"]["sky"]) if base["fields"]["sky"] else None,
        "weather": base["fields"]["weather"],
        "notes": [],
    }
    for ov in overlays:
        label = {"tempo": "TEMPO", "becmg": "BECMG", "prob": f"PROB{ov['probability']}"}.get(ov["type"], ov["type"].upper())
        parts = []
        if ov["fields"]["wind"]:
            parts.append(f"wind {ov['fields']['wind']}")
        if ov["fields"]["visibility"]:
            parts.append(f"vis {ov['fields']['visibility']}")
        if ov["fields"]["sky"]:
            parts.append(f"sky {'; '.join(ov['fields']['sky'])}")
        if ov["fields"]["weather"]:
            parts.append(ov["fields"]["weather"])
        if parts:
            result["notes"].append(f"{label}: {', '.join(parts)}")

    return result


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
