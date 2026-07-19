# N5673T Flight Assessment

Digitized Flight Assessment Form for N5673T (Tecnam P92 Echo MK2, KPWK
leaseback). Flask/Python backend + mobile-friendly HTML frontend, matching
the pattern of the other Lickerman apps (CLEARANCE, PPL audio quiz, family
calendar, workout planner).

## What it does

- **Weight & balance**: enter pilot/passenger weight, baggage, and fuel
  load — moments, CG, and envelope checks compute automatically. Constants
  are hardcoded from the Tecnam weighing report (27/01/2022) and the P92
  LSA Flight Manual Sections 2 & 3.
- **Live weather**: pulls METAR/TAF from aviationweather.gov (no API key)
  and computes pressure/density altitude.
- **Risk assessment matrix**: the four-category 1–5 scoring form with
  live-updating totals and color-coded thresholds (green/yellow/red),
  matching the paper form's approval logic.
- **Mission briefing / performance / maintenance data**: simple form
  fields, matching the paper form.
- **PDF export**: submitting generates a printable PDF and resets the form
  to blank for the next pilot. Each submission is also logged to a small
  SQLite history (`/history`) so there's a flight record over time.

## Stack

- Flask (Python)
- xhtml2pdf for PDF generation (pure Python — no system dependencies to
  fight with on Render, unlike WeasyPrint)
- SQLite for submission history, stored on a Render persistent disk at
  `/data`, same pattern as lickerman-finance
- Vanilla JS frontend, no build step

## Local development

```
pip install -r requirements.txt
python app.py
```
Visit http://localhost:5000

## Deploy to Render

1. Push this repo to GitHub (e.g. `tlickerman/n5673t-flight-app`).
2. In Render, create a new Web Service from the repo — `render.yaml` is
   already set up with the build/start commands and a 1GB persistent disk
   mounted at `/data` for the SQLite history.
3. Once deployed, open the Render URL on your iPhone and use Share → Add
   to Home Screen for a native-app-like PWA experience.

## Constants that need verification

A few values in `aircraft_constants.py` are flagged and should be checked
against the aircraft's actual cockpit limitations placard (POH Section 8,
which wasn't available at build time):

- **CG envelope**: using 18%/32% MAC from POH Section 2.1.16. Section
  3.2.1 states 19%/30% MAC — the two sections disagree. Section 2 (Operating
  Limitations) is used since it governs legal operation, but confirm
  against the placard.
- **Vs0/Vs1**: back-solved from the airspeed indicator arc markings
  (Section 2.1.2), not directly published in the available POH excerpt.
  Marked "calculated, verify" in the UI.
- **Vle/Vlo/Vmc**: marked N/A (fixed gear, single engine) — confirm this
  is correct for this airframe.
- **Vg (best glide) and approach speeds**: not present in the POH excerpts
  provided; fields show "N/A — verify POH Section 4" until sourced.

All other constants (empty weight, arms, weights, fuel, crosswind, V-speeds
Vne/Vno/Va/Vfe/Vx/Vy) are sourced directly from the Tecnam weighing report
and POH Sections 2–3 and shouldn't need adjustment unless the aircraft is
reweighed or the equipment list changes.

## Known limitations / next steps

- The paper form's "Front Seats / Rear Seats" and "Baggage 1 / Baggage 2"
  rows were collapsed to single rows per your confirmation, since the P92
  is a 2-seat side-by-side aircraft with one baggage compartment.
- Multi-engine-only sections of the paper form were omitted (N/A for this
  airframe).
- The Regional Wx page (page 2 of the paper form) is a free-text notes
  field rather than an embedded map — could add an embedded
  aviationweather.gov graphical AIRMET/SIGMET image if useful later.
- No authentication — anyone with the URL can submit. Fine for a
  single-aircraft leaseback logbook; flag if that needs to change.
