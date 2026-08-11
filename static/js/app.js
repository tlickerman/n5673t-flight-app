function togglePanel(headerEl) {
  headerEl.parentElement.classList.toggle("collapsed");
}

function fmt(n) {
  if (n === null || n === undefined || isNaN(n)) return "\u2014";
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: 1 });
}

// ---------------------------------------------------------------------
// Weight & Balance
// ---------------------------------------------------------------------
async function calcWB() {
  const payload = {
    pilot_lb: parseFloat(document.getElementById("pilot_lb").value) || 0,
    passenger_lb: parseFloat(document.getElementById("passenger_lb").value) || 0,
    baggage_lb: parseFloat(document.getElementById("baggage_lb").value) || 0,
    fuel_gal: parseFloat(document.getElementById("fuel_gal").value) || 0,
    ground_fuel_use_gal: parseFloat(document.getElementById("ground_fuel_use_gal").value) || 0,
  };
  const resp = await fetch("/api/calculate-wb", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const r = await resp.json();
  window._lastWB = r;

  document.getElementById("wb-empty-w").textContent = fmt(r.empty.weight_lb);
  document.getElementById("wb-empty-a").textContent = fmt(r.empty.arm_in);
  document.getElementById("wb-empty-m").textContent = fmt(r.empty.moment_lb_in);

  document.getElementById("wb-pilot-w").textContent = fmt(r.pilot.weight_lb);
  document.getElementById("wb-pilot-a").textContent = fmt(r.pilot.arm_in);
  document.getElementById("wb-pilot-m").textContent = fmt(r.pilot.moment_lb_in);

  document.getElementById("wb-pax-w").textContent = fmt(r.passenger.weight_lb);
  document.getElementById("wb-pax-a").textContent = fmt(r.passenger.arm_in);
  document.getElementById("wb-pax-m").textContent = fmt(r.passenger.moment_lb_in);

  document.getElementById("wb-bag-w").textContent = fmt(r.baggage.weight_lb);
  document.getElementById("wb-bag-a").textContent = fmt(r.baggage.arm_in);
  document.getElementById("wb-bag-m").textContent = fmt(r.baggage.moment_lb_in);

  document.getElementById("wb-zfw-w").textContent = fmt(r.zero_fuel.weight_lb);
  document.getElementById("wb-zfw-a").textContent = fmt(r.zero_fuel.arm_in);
  document.getElementById("wb-zfw-m").textContent = fmt(r.zero_fuel.moment_lb_in);

  document.getElementById("wb-fuel-w").textContent = fmt(r.fuel.weight_lb);
  document.getElementById("wb-fuel-a").textContent = fmt(r.fuel.arm_in);
  document.getElementById("wb-fuel-m").textContent = fmt(r.fuel.moment_lb_in);

  document.getElementById("wb-ramp-w").textContent = fmt(r.ramp.weight_lb);
  document.getElementById("wb-ramp-a").textContent = fmt(r.ramp.arm_in);
  document.getElementById("wb-ramp-m").textContent = fmt(r.ramp.moment_lb_in);

  document.getElementById("wb-gfu-w").textContent = fmt(r.ground_fuel_use_lb);

  document.getElementById("wb-to-w").textContent = fmt(r.takeoff.weight_lb);
  document.getElementById("wb-to-a").textContent = fmt(r.takeoff.arm_in);
  document.getElementById("wb-to-m").textContent = fmt(r.takeoff.moment_lb_in);

  document.getElementById("wb-burn-w").textContent = fmt(r.est_fuel_burn_lb);

  document.getElementById("wb-ldg-w").textContent = fmt(r.landing.weight_lb);
  document.getElementById("wb-ldg-a").textContent = fmt(r.landing.arm_in);
  document.getElementById("wb-ldg-m").textContent = fmt(r.landing.moment_lb_in);

  document.getElementById("wb-pct-mac").textContent =
    `T/O CG: ${fmt(r.takeoff.pct_mac)}% MAC \u00b7 LDG CG: ${fmt(r.landing.pct_mac)}% MAC`;

  const statusEl = document.getElementById("wb-status");
  if (r.within_limits) {
    statusEl.innerHTML = `<div class="status-banner ok"><span class="dot green"></span>Within weight &amp; CG limits</div>`;
  } else {
    statusEl.innerHTML = `<div class="status-banner warn"><span class="dot red"></span>${r.warnings.join("<br><br>")}</div>`;
  }
}

// ---------------------------------------------------------------------
// Weather
// ---------------------------------------------------------------------
async function fetchWeather() {
  const station = document.getElementById("wx_station").value.trim().toUpperCase();
  if (!station) return;
  const resp = await fetch(`/api/weather/${station}`);
  const data = await resp.json();
  window._lastWeather = data;
  const m = data.metar || {};

  const displayEl = document.getElementById("metar-display");
  if (m.error) {
    displayEl.innerHTML = `<div class="status-banner warn"><span class="dot red"></span>${m.error}</div>`;
    return;
  }
  displayEl.innerHTML = `<div class="metar-raw">${m.raw || ""}</div>`;
  document.getElementById("metar-decoded").textContent = m.decoded || "";

  if (data.radar_url) {
    const radarImg = document.getElementById("radar-map");
    radarImg.src = `${data.radar_url}?t=${Date.now()}`;
    radarImg.style.display = "block";
    document.getElementById("radar-station-label").textContent = data.radar_station || "KLOT";
  }

  if (m.wind_dir_deg !== undefined) {
    const gust = m.wind_gust_kt ? ` G${m.wind_gust_kt}` : "";
    document.getElementById("surface_wind").value = `${m.wind_dir_deg || "VRB"}\u00b0 @ ${m.wind_speed_kt || 0}kt${gust}`;
  }
  document.getElementById("visibility").value = m.visibility_sm !== undefined ? `${m.visibility_sm} SM` : "";
  document.getElementById("ceiling").value = m.ceiling_ft !== undefined && m.ceiling_ft !== null ? `${m.ceiling_ft} ft` : "Unlimited / SKC";
  document.getElementById("temp_dewpoint").value = `${fmt(m.temp_c)}\u00b0C / ${fmt(m.dewpoint_c)}\u00b0C`;
  document.getElementById("altimeter").value = m.altimeter_inhg !== undefined ? `${m.altimeter_inhg} inHg` : "";

  if (m.altimeter_inhg) {
    const fieldElevEl = document.getElementById("field_elevation");
    if (!fieldElevEl.value && m.elevation_m) {
      fieldElevEl.value = Math.round(m.elevation_m * 3.28084);
    }
    await computeDensityAltitude(m.altimeter_inhg, m.temp_c);
  }
}

async function computeDensityAltitude(altimeterInHg, tempC) {
  const fieldElev = document.getElementById("field_elevation").value;
  if (!fieldElev) return;
  const params = new URLSearchParams({
    field_elevation_ft: fieldElev,
    altimeter_inhg: altimeterInHg,
    temp_c: tempC,
  });
  const resp = await fetch(`/api/density-altitude?${params}`);
  const r = await resp.json();
  document.getElementById("pressure_altitude").value = r.pressure_altitude_ft !== null ? `${r.pressure_altitude_ft} ft` : "";
  document.getElementById("density_altitude").value = r.density_altitude_ft !== null ? `${r.density_altitude_ft} ft` : "";
}

// ---------------------------------------------------------------------
// Risk Assessment
// ---------------------------------------------------------------------
function calcRisk() {
  const selects = document.querySelectorAll("[id^='risk-']");
  const categoryTotals = {};
  let grandTotal = 0;
  let anyFive = false;

  selects.forEach((sel) => {
    const cat = sel.dataset.cat;
    const val = parseInt(sel.value) || 0;
    categoryTotals[cat] = (categoryTotals[cat] || 0) + val;
    grandTotal += val;
    if (val === 5) anyFive = true;
  });

  Object.keys(categoryTotals).forEach((cat) => {
    const el = document.getElementById(`cat-total-${cat}`);
    if (el) el.textContent = categoryTotals[cat];
  });

  const ring = document.getElementById("risk-gauge-ring");
  const label = document.getElementById("risk-gauge-label");
  ring.textContent = grandTotal;

  let levelText, colorClass;
  if (grandTotal <= 29) { colorClass = "green"; levelText = "Low risk \u2014 SP solos require IP sign-off"; }
  else if (grandTotal <= 39) { colorClass = "yellow"; levelText = "Elevated risk \u2014 all solos require IP sign-off"; }
  else { colorClass = "red"; levelText = "High risk \u2014 manager approval required"; }

  ring.className = `gauge-ring ${colorClass}`;
  label.textContent = anyFive ? `${levelText}. A rating of 5 was selected \u2014 manager approval required regardless of total.` : levelText;

  window._lastRiskTotal = grandTotal;
  window._lastRiskAnyFive = anyFive;
}

// ---------------------------------------------------------------------
// Submit / Reset
// ---------------------------------------------------------------------
function collectFormData() {
  const ids = [
    "date", "n_number", "pilot_1", "pilot_2", "start_time", "stop_time",
    "departure_airport", "destination_airport", "mission_notes",
    "departure_routing", "arrival_routing", "notams", "emergency_procedures",
    "risk_considerations", "hours_prev_24", "wx_station", "crosswind_component",
    "field_elevation", "regional_wx_notes", "pilot_lb", "passenger_lb", "baggage_lb",
    "fuel_gal", "ground_fuel_use_gal", "expected_runway", "runway_length",
    "to_ground_roll", "ldg_ground_roll", "to_dist_50", "ldg_dist_50",
    "mx_50hr", "mx_100hr", "mx_ad_hrs", "mx_ad_days", "mx_annual",
    "mx_registration", "final_notes",
  ];
  const data = {};
  ids.forEach((id) => {
    const el = document.getElementById(id);
    if (el) data[id] = el.value;
  });

  const riskResponses = {};
  document.querySelectorAll("[id^='risk-']").forEach((sel) => {
    riskResponses[sel.id.replace("risk-", "")] = parseInt(sel.value) || 0;
  });
  data.risk_responses = riskResponses;
  return data;
}

async function submitForm() {
  const formData = collectFormData();
  const resp = await fetch("/api/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ form_data: formData, weather_data: window._lastWeather || {} }),
  });

  if (!resp.ok) {
    alert("PDF generation failed. Please try again.");
    return;
  }

  const blob = await resp.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `N5673T_Flight_Assessment_${formData.date || "undated"}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  showSaveConfirmation();
}

function showSaveConfirmation() {
  const btn = document.querySelector(".footer-actions button.primary");
  if (!btn) return;
  const original = btn.textContent;
  btn.textContent = "Saved \u2713";
  setTimeout(() => { btn.textContent = original; }, 2000);
}

function resetForm() {
  document.querySelectorAll("input[type=text], input[type=number], input[type=date], input[type=time], textarea").forEach((el) => {
    if (el.id === "n_number") { el.value = "N5673T"; }
    else if (el.id === "departure_airport" || el.id === "wx_station") { el.value = "KPWK"; }
    else if (el.id === "fuel_gal") { el.value = FUEL_CAPACITY_GAL; }
    else if (el.id === "pilot_lb" || el.id === "passenger_lb" || el.id === "baggage_lb") { el.value = 0; }
    else if (el.id === "ground_fuel_use_gal") { el.value = 0.5; }
    else if (!el.readOnly) { el.value = ""; }
  });
  document.querySelectorAll("[id^='risk-']").forEach((sel) => { sel.selectedIndex = 0; });
  document.getElementById("metar-display").innerHTML = "";
  document.getElementById("metar-decoded").textContent = "";
  const radarImg = document.getElementById("radar-map");
  radarImg.src = "";
  radarImg.style.display = "none";
  window._lastWeather = null;
  calcWB();
  calcRisk();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("date").valueAsDate = new Date();
  calcWB();
  calcRisk();
});
