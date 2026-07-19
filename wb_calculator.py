"""
Weight & Balance calculator for N5673T.

All internal math is done in pounds / inches (lb-in moments), matching the
Takeoff Data Sheet form layout, using constants converted from the metric
POH source data in aircraft_constants.py.
"""

import aircraft_constants as AC


def _station(weight_lb, arm_in):
    weight_lb = float(weight_lb or 0)
    moment_lb_in = round(weight_lb * arm_in, 1)
    return {"weight_lb": weight_lb, "arm_in": arm_in, "moment_lb_in": moment_lb_in}


def calculate_wb(pilot_passenger_lb=0, baggage_lb=0, fuel_gal=0, ground_fuel_use_gal=0):
    """
    Compute the full weight & balance chain matching the paper Takeoff Data
    Sheet: Basic Empty -> + occupants/baggage -> Zero Fuel Wt -> + fuel ->
    Ramp Wt -> - ground fuel use (taxi) -> T/O Wt -> - est. fuel burn ->
    Est. Landing Wt. Returns a dict ready to render in the form and PDF.
    """
    warnings = []

    empty = {
        "weight_lb": AC.EMPTY_WEIGHT_LB,
        "arm_in": AC.EMPTY_WEIGHT_ARM_IN,
        "moment_lb_in": AC.EMPTY_WEIGHT_MOMENT_LB_IN,
    }

    occupants = _station(pilot_passenger_lb, AC.PILOT_PASSENGER_ARM_IN)
    baggage = _station(baggage_lb, AC.BAGGAGE_ARM_IN)

    if float(baggage_lb or 0) > AC.BAGGAGE_MAX_LB:
        warnings.append(
            f"Baggage {baggage_lb} lb exceeds max baggage weight of {AC.BAGGAGE_MAX_LB} lb."
        )

    # Zero Fuel Weight = empty + occupants + baggage
    zfw_weight = empty["weight_lb"] + occupants["weight_lb"] + baggage["weight_lb"]
    zfw_moment = empty["moment_lb_in"] + occupants["moment_lb_in"] + baggage["moment_lb_in"]
    zfw_arm = round(zfw_moment / zfw_weight, 2) if zfw_weight else 0
    zfw_pct_mac = _arm_to_pct_mac(zfw_arm)
    zero_fuel = {"weight_lb": round(zfw_weight, 1), "arm_in": zfw_arm,
                 "moment_lb_in": round(zfw_moment, 1), "pct_mac": zfw_pct_mac}

    # Fuel load
    fuel_gal = float(fuel_gal or 0)
    fuel_liters = fuel_gal * 3.78541
    if fuel_liters > AC.FUEL_TOTAL_CAPACITY_L + 0.01:
        warnings.append(
            f"Fuel load {fuel_gal:.1f} gal exceeds total capacity of "
            f"{AC.FUEL_TOTAL_CAPACITY_GAL} gal."
        )
    fuel_lb = round(fuel_liters * AC.LB_PER_LITER_FUEL, 1)
    fuel = _station(fuel_lb, AC.FUEL_ARM_IN)

    # Ramp Weight = ZFW + fuel
    ramp_weight = zfw_weight + fuel["weight_lb"]
    ramp_moment = zfw_moment + fuel["moment_lb_in"]
    ramp_arm = round(ramp_moment / ramp_weight, 2) if ramp_weight else 0
    ramp_pct_mac = _arm_to_pct_mac(ramp_arm)
    ramp = {"weight_lb": round(ramp_weight, 1), "arm_in": ramp_arm,
            "moment_lb_in": round(ramp_moment, 1), "pct_mac": ramp_pct_mac}

    # Ground fuel use (taxi) — subtract before takeoff
    ground_fuel_use_gal = float(ground_fuel_use_gal or 0)
    ground_fuel_lb = round(ground_fuel_use_gal * 3.78541 * AC.LB_PER_LITER_FUEL, 1)
    ground_fuel_moment = round(ground_fuel_lb * AC.FUEL_ARM_IN, 1)

    to_weight = ramp_weight - ground_fuel_lb
    to_moment = ramp_moment - ground_fuel_moment
    to_arm = round(to_moment / to_weight, 2) if to_weight else 0
    to_pct_mac = _arm_to_pct_mac(to_arm)
    takeoff = {"weight_lb": round(to_weight, 1), "arm_in": to_arm,
               "moment_lb_in": round(to_moment, 1), "pct_mac": to_pct_mac}

    if to_weight > AC.MAX_TAKEOFF_WEIGHT_LB:
        warnings.append(
            f"Takeoff weight {to_weight:.1f} lb exceeds max takeoff weight of "
            f"{AC.MAX_TAKEOFF_WEIGHT_LB} lb."
        )
    if not (AC.FWD_LIMIT_PCT_MAC <= to_pct_mac <= AC.AFT_LIMIT_PCT_MAC):
        warnings.append(
            f"Takeoff CG {to_pct_mac:.1f}% MAC is outside the "
            f"{AC.FWD_LIMIT_PCT_MAC}-{AC.AFT_LIMIT_PCT_MAC}% MAC envelope."
        )

    # Estimated fuel burn (+25% reserve factored in per form) — using
    # remaining usable fuel minus 25% margin as a conservative landing estimate
    est_burn_lb = round(fuel["weight_lb"] * 0.75, 1)  # assume 75% of loaded fuel burned
    est_burn_moment = round(est_burn_lb * AC.FUEL_ARM_IN, 1)

    ldg_weight = to_weight - est_burn_lb
    ldg_moment = to_moment - est_burn_moment
    ldg_arm = round(ldg_moment / ldg_weight, 2) if ldg_weight else 0
    ldg_pct_mac = _arm_to_pct_mac(ldg_arm)
    landing = {"weight_lb": round(ldg_weight, 1), "arm_in": ldg_arm,
               "moment_lb_in": round(ldg_moment, 1), "pct_mac": ldg_pct_mac}

    if ldg_weight > AC.MAX_LANDING_WEIGHT_LB:
        warnings.append(
            f"Est. landing weight {ldg_weight:.1f} lb exceeds max landing weight of "
            f"{AC.MAX_LANDING_WEIGHT_LB} lb."
        )
    if not (AC.FWD_LIMIT_PCT_MAC <= ldg_pct_mac <= AC.AFT_LIMIT_PCT_MAC):
        warnings.append(
            f"Est. landing CG {ldg_pct_mac:.1f}% MAC is outside the "
            f"{AC.FWD_LIMIT_PCT_MAC}-{AC.AFT_LIMIT_PCT_MAC}% MAC envelope."
        )

    return {
        "empty": empty,
        "occupants": occupants,
        "baggage": baggage,
        "zero_fuel": zero_fuel,
        "fuel": fuel,
        "ramp": ramp,
        "ground_fuel_use_lb": ground_fuel_lb,
        "takeoff": takeoff,
        "est_fuel_burn_lb": est_burn_lb,
        "landing": landing,
        "limits": {
            "max_takeoff_lb": AC.MAX_TAKEOFF_WEIGHT_LB,
            "max_landing_lb": AC.MAX_LANDING_WEIGHT_LB,
            "fwd_pct_mac": AC.FWD_LIMIT_PCT_MAC,
            "aft_pct_mac": AC.AFT_LIMIT_PCT_MAC,
            "cg_source_note": AC.CG_LIMIT_SOURCE_NOTE,
        },
        "warnings": warnings,
        "within_limits": len(warnings) == 0,
    }


def _arm_to_pct_mac(arm_in):
    """Convert an arm (inches from prop-flange datum) to %MAC using the
    leading-edge-referenced MAC framework established in aircraft_constants."""
    leading_edge_offset_in = AC.DATUM_OFFSET_LEADING_EDGE_TO_PROP_FLANGE_M * AC.IN_PER_M
    arm_from_leading_edge = arm_in - leading_edge_offset_in
    pct = (arm_from_leading_edge / AC.MAC_IN) * 100
    return round(pct, 1)
