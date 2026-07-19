"""
N5673T — Tecnam P92 Echo MK2 (S/N 1673)
Constants sourced from:
  - Tecnam Weighing Report P92MK2-1673, dated 27/01/2022
  - P92 LSA Flight Manual, Section 2 (Operating Limitations, Rev.0-4) and
    Section 3 (Weight & Balance, Rev.0)

All arms are given relative to the POH datum: propeller support flange
without spacer. The Tecnam weighing report used "leading edge vertical"
as its datum; POH Section 3 gives the relationship
    arm(prop-flange) = arm(leading-edge) + 1.519 m
which is used below to convert the as-weighed empty weight arm.

NOTE — CG envelope discrepancy: Section 2.1.16 (Operating Limitations)
lists 18% MAC fwd / 32% MAC aft. Section 3.2.1 (Weight & Balance) lists
19% MAC fwd / 30% MAC aft. Section 2 governs legal operation, so it is
used here. Verify against the cockpit limitations placard (Section 8)
and update FWD_LIMIT_PCT_MAC / AFT_LIMIT_PCT_MAC below if needed.
"""

AIRCRAFT = {
    "registration": "N5673T",
    "make_model": "Tecnam P92 Echo MK2",
    "serial_number": "1673",
    "base": "KPWK",
    "has_control_lock": False,
}

# ---------------------------------------------------------------------------
# Weight & Balance — empty weight (Tecnam Weighing Report, 27/01/2022)
# ---------------------------------------------------------------------------
LB_PER_KG = 2.20462
IN_PER_M = 39.3701
LB_PER_LITER_FUEL = 1.5876  # 100LL/Mogas ~6 lb/gal / 3.785 L/gal

EMPTY_WEIGHT_KG = 371.5
EMPTY_WEIGHT_LB = round(EMPTY_WEIGHT_KG * LB_PER_KG, 1)  # 819.0 lb

EMPTY_WEIGHT_ARM_LEADING_EDGE_M = 0.2825
DATUM_OFFSET_LEADING_EDGE_TO_PROP_FLANGE_M = 1.519
EMPTY_WEIGHT_ARM_M = (
    EMPTY_WEIGHT_ARM_LEADING_EDGE_M + DATUM_OFFSET_LEADING_EDGE_TO_PROP_FLANGE_M
)  # 1.8015 m
EMPTY_WEIGHT_ARM_IN = round(EMPTY_WEIGHT_ARM_M * IN_PER_M, 2)  # 70.93 in

EMPTY_WEIGHT_MOMENT_KG_M = round(EMPTY_WEIGHT_KG * EMPTY_WEIGHT_ARM_M, 2)
EMPTY_WEIGHT_MOMENT_LB_IN = round(EMPTY_WEIGHT_LB * EMPTY_WEIGHT_ARM_IN, 1)

EMPTY_WEIGHT_CG_PCT_MAC = 20.2  # from Tecnam report; informational only

# ---------------------------------------------------------------------------
# Weight & Balance — station arms (POH Sec 3.2.2 / 3.3), prop-flange datum
# ---------------------------------------------------------------------------
PILOT_PASSENGER_ARM_M = 1.948
PILOT_PASSENGER_ARM_IN = round(PILOT_PASSENGER_ARM_M * IN_PER_M, 2)  # 76.69 in

FUEL_ARM_M = 1.774
FUEL_ARM_IN = round(FUEL_ARM_M * IN_PER_M, 2)  # 69.84 in

BAGGAGE_ARM_M = 2.320
BAGGAGE_ARM_IN = round(BAGGAGE_ARM_M * IN_PER_M, 2)  # 91.34 in
BAGGAGE_MAX_KG = 20
BAGGAGE_MAX_LB = 44

MAC_M = 1.400
MAC_IN = round(MAC_M * IN_PER_M, 2)  # 55.12 in

# ---------------------------------------------------------------------------
# Weights (POH Sec 2.1.15)
# ---------------------------------------------------------------------------
MAX_TAKEOFF_WEIGHT_KG = 600
MAX_TAKEOFF_WEIGHT_LB = 1320
MAX_LANDING_WEIGHT_KG = 600
MAX_LANDING_WEIGHT_LB = 1320

# ---------------------------------------------------------------------------
# CG envelope (POH Sec 2.1.16 — Operating Limitations governs)
# ---------------------------------------------------------------------------
FWD_LIMIT_PCT_MAC = 18.0
AFT_LIMIT_PCT_MAC = 32.0
CG_LIMIT_SOURCE_NOTE = (
    "Section 2.1.16 (18%/32% MAC) used; Section 3.2.1 states 19%/30% MAC. "
    "Verify against cockpit limitations placard."
)

# Convert %MAC limits to arm distances from datum for direct CG-vs-arm checks.
# Per POH convention, %MAC is measured relative to the leading-edge reference
# used in the CG range table (Sec 3), where fwd/aft arms in meters were given
# directly (1.785 m / 1.939 m from the *leading-edge* datum framework at
# 19/30%). Because Sec 2 revises the %MAC figures but does not republish arm
# distances, arms below are computed from %MAC x MAC + leading-edge datum
# offset, consistent with the Sec 3 method.
FWD_LIMIT_ARM_M = round(
    (FWD_LIMIT_PCT_MAC / 100) * MAC_M + DATUM_OFFSET_LEADING_EDGE_TO_PROP_FLANGE_M, 3
)
AFT_LIMIT_ARM_M = round(
    (AFT_LIMIT_PCT_MAC / 100) * MAC_M + DATUM_OFFSET_LEADING_EDGE_TO_PROP_FLANGE_M, 3
)
FWD_LIMIT_ARM_IN = round(FWD_LIMIT_ARM_M * IN_PER_M, 2)
AFT_LIMIT_ARM_IN = round(AFT_LIMIT_ARM_M * IN_PER_M, 2)

# ---------------------------------------------------------------------------
# Fuel (POH Sec 2.1.11 / 2.1.12)
# ---------------------------------------------------------------------------
FUEL_TANK_COUNT = 2
FUEL_PER_TANK_L = 45
FUEL_PER_TANK_GAL = 11.88
FUEL_TOTAL_CAPACITY_L = 90
FUEL_TOTAL_CAPACITY_GAL = 23.76
APPROVED_FUEL = ["Mogas ASTM D4814 / EN228 (min RON 95)", "Avgas 100LL (ASTM D910)"]

# ---------------------------------------------------------------------------
# Airspeed limitations, KIAS (POH Sec 2.1.1)
# ---------------------------------------------------------------------------
V_SPEEDS = {
    "Vne": {"kias": 145, "kcas": 138, "label": "Never exceed speed"},
    "Vno": {"kias": 113, "kcas": 109, "label": "Max structural cruising speed"},
    "Va": {"kias": 98, "kcas": 95, "label": "Maneuvering speed"},
    "Vfe": {"kias": 70, "kcas": 70, "label": "Max flap extended speed"},
    "Vx": {"kias": 62, "kcas": 62, "label": "Best angle of climb"},
    "Vy": {"kias": 65, "kcas": 65, "label": "Best rate of climb"},
    # Back-solved from airspeed indicator arc markings (Sec 2.1.2), not
    # published directly. White arc lower bound = 1.1 x Vs0 = 41 KIAS.
    # Green arc lower bound = 1.15 x Vs1 = 51 KIAS. Flagged as calculated.
    "Vs0": {"kias": 37, "kcas": None, "label": "Stall speed, landing config (calculated, verify)"},
    "Vs1": {"kias": 44, "kcas": None, "label": "Stall speed, clean config (calculated, verify)"},
    # Fixed gear aircraft — no retraction speeds apply.
    "Vle": {"kias": None, "kcas": None, "label": "N/A — fixed gear"},
    "Vlo": {"kias": None, "kcas": None, "label": "N/A — fixed gear"},
    # Not published in available POH excerpts for this airframe.
    "Vmc": {"kias": None, "kcas": None, "label": "N/A — single engine aircraft"},
    "Vg": {"kias": None, "kcas": None, "label": "Best glide — not in POH excerpt, verify"},
    "Vapp_short": {"kias": None, "kcas": None, "label": "Short field approach — verify POH Sec 4"},
    "Vapp_normal": {"kias": None, "kcas": None, "label": "Normal approach — verify POH Sec 4"},
    "Vapp_flapless": {"kias": None, "kcas": None, "label": "Flapless approach — verify POH Sec 4"},
}

# ---------------------------------------------------------------------------
# Airspeed indicator color arcs (POH Sec 2.1.2)
# ---------------------------------------------------------------------------
ASI_ARCS = {
    "white_arc": {"low": 41, "high": 70, "label": "Flap operating range"},
    "green_arc": {"low": 51, "high": 113, "label": "Normal operating range"},
    "yellow_arc": {"low": 113, "high": 145, "label": "Caution — smooth air only"},
    "red_line": {"value": 145, "label": "Never exceed"},
}

# ---------------------------------------------------------------------------
# Crosswind, altitude, load factors (POH Sec 2.1.17-2.1.25)
# ---------------------------------------------------------------------------
MAX_DEMONSTRATED_CROSSWIND_KT = 15
MAX_OPERATING_ALTITUDE_FT = 14000

LOAD_FACTORS = {
    "flaps_up": {"positive_g": 4, "negative_g": -2},
    "flaps_landing": {"positive_g": 2, "negative_g": 0},
}

APPROVED_MANEUVERS = [
    "Normal flight maneuvers",
    "Stalls (except whip stalls)",
    "Lazy eights",
    "Chandelles",
    "Turns up to 60° bank",
]
PROHIBITED = "Aerobatic maneuvers, spins, and turns exceeding 60° bank are not approved."

# ---------------------------------------------------------------------------
# Powerplant (POH Sec 2.1.3-2.1.7, 2.1.13)
# ---------------------------------------------------------------------------
ENGINE = {
    "manufacturer": "Bombardier Rotax GmbH",
    "model": "912 ULS2",
    "max_power_hp": 98.5,
    "max_power_rpm_prop": 2388,
    "max_power_time_limit_min": 5,
    "max_continuous_hp": 92.5,
    "max_continuous_rpm_prop": 2265,
}

PROPELLER = {
    "manufacturer": "Sensenich Propeller",
    "model": "W68T2ET-70J",
    "type": "Wood twin blade, fixed pitch",
    "diameter_mm": 1730,
}
