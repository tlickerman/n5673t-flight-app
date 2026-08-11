from flask import Flask, render_template, request, jsonify, send_file

import aircraft_constants as AC
import database
import weather
from pdf_generator import generate_pdf
from risk_assessment import score_risk, CATEGORIES
from wb_calculator import calculate_wb

app = Flask(__name__)
database.init_db()

# Bump this on any static asset change (CSS/JS) so iOS home-screen PWAs,
# which cache far more aggressively than a normal Safari tab, are forced
# to fetch the new file instead of silently running stale JS against a
# changed HTML structure.
APP_VERSION = "3"


@app.context_processor
def inject_version():
    return {"app_version": APP_VERSION}


@app.route("/")
def index():
    return render_template(
        "index.html",
        aircraft=AC.AIRCRAFT,
        v_speeds=AC.V_SPEEDS,
        asi_arcs=AC.ASI_ARCS,
        limits={
            "max_takeoff_lb": AC.MAX_TAKEOFF_WEIGHT_LB,
            "max_landing_lb": AC.MAX_LANDING_WEIGHT_LB,
            "fwd_pct_mac": AC.FWD_LIMIT_PCT_MAC,
            "aft_pct_mac": AC.AFT_LIMIT_PCT_MAC,
            "max_crosswind_kt": AC.MAX_DEMONSTRATED_CROSSWIND_KT,
            "max_altitude_ft": AC.MAX_OPERATING_ALTITUDE_FT,
        },
        fuel={
            "capacity_gal": AC.FUEL_TOTAL_CAPACITY_GAL,
            "per_tank_gal": AC.FUEL_PER_TANK_GAL,
            "approved": AC.APPROVED_FUEL,
        },
        risk_categories=CATEGORIES,
    )


@app.route("/api/weather/<station_id>")
def api_weather(station_id):
    metar = weather.get_metar(station_id)
    taf = weather.get_taf(station_id)
    radar_station = weather.get_radar_station(station_id)
    return jsonify({
        "metar": metar,
        "taf": taf,
        "radar_station": radar_station,
        "radar_url": f"https://radar.weather.gov/ridge/standard/{radar_station}_loop.gif",
    })


@app.route("/api/density-altitude")
def api_density_altitude():
    field_elev = request.args.get("field_elevation_ft")
    altimeter = request.args.get("altimeter_inhg")
    temp_c = request.args.get("temp_c")
    pa = weather.compute_pressure_altitude(field_elev, altimeter)
    da = weather.compute_density_altitude(pa, temp_c) if pa is not None else None
    return jsonify({"pressure_altitude_ft": pa, "density_altitude_ft": da})


@app.route("/api/calculate-wb", methods=["POST"])
def api_calculate_wb():
    data = request.get_json(force=True) or {}
    result = calculate_wb(
        pilot_lb=data.get("pilot_lb", 0),
        passenger_lb=data.get("passenger_lb", 0),
        baggage_lb=data.get("baggage_lb", 0),
        fuel_gal=data.get("fuel_gal", 0),
        ground_fuel_use_gal=data.get("ground_fuel_use_gal", 0),
    )
    return jsonify(result)


@app.route("/api/calculate-risk", methods=["POST"])
def api_calculate_risk():
    data = request.get_json(force=True) or {}
    result = score_risk(data.get("responses", {}))
    return jsonify(result)


@app.route("/api/submit", methods=["POST"])
def api_submit():
    payload = request.get_json(force=True) or {}
    form_data = payload.get("form_data", {})
    weather_data = payload.get("weather_data", {})

    wb_result = calculate_wb(
        pilot_lb=form_data.get("pilot_lb", 0),
        passenger_lb=form_data.get("passenger_lb", 0),
        baggage_lb=form_data.get("baggage_lb", 0),
        fuel_gal=form_data.get("fuel_gal", 0),
        ground_fuel_use_gal=form_data.get("ground_fuel_use_gal", 0),
    )
    risk_result = score_risk(form_data.get("risk_responses", {}))

    database.log_submission(form_data, wb_result, risk_result)

    pdf_buffer = generate_pdf(form_data, wb_result, risk_result, weather_data)
    filename = f"N5673T_Flight_Assessment_{form_data.get('date', 'undated')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/history")
def history():
    submissions = database.get_history()
    return render_template("history.html", submissions=submissions)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
