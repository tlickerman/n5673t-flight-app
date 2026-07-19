"""
Risk Assessment Form scoring — matches the paper form's four categories
(Pilot, Aircraft, enVironment, External Factors), each item scored 1-5,
with a grand total and color-coded thresholds.
"""

# Each item: (key, label, [option labels in ascending 1-5 risk order])
PILOT_ITEMS = [
    ("illness", "Illness", ["No", "—", "Minor", "—", "Major"]),
    ("medication", "Medication", ["No", "—", "—", "—", "Yes"]),
    ("stress", "Stress", ["No", "Low", "Med", "High", "Severe"]),
    ("alcohol", "Alcohol, last 24 hrs", ["No", ">20hr", ">18hr", ">12hr", "\u226412hr"]),
    ("fatigue", "Fatigue, hrs of sleep", [">8", "6-8", "5-6", "4-5", "<4"]),
    ("eating", "Eating, hrs since last", ["<2", "2-4", "4-5", "5-6", ">6"]),
    ("emotion", "Emotion", ["Low", "—", "Med", "—", "High"]),
    ("days_in_row", "Days in a row flying", ["\u22642", "3", "4", "5", "\u22656"]),
    ("currency", "Currency for flight, days", [">1", ">15", ">30", ">45", ">60"]),
]

AIRCRAFT_ITEMS = [
    ("climb_performance", "Adequate climb performance (ft/min)",
     ["\u2265550", "\u2265450", "\u2265350", "\u2265250", "<250"]),
    ("obstacle_clearance", "T/O or LDG over 50' obstacle / \u226550% runway used",
     ["No", "—", "—", "—", "Yes"]),
    ("time_to_next_mx", "Time to next MX (hrs)", [">10", "10-8", "8-5", "5-1.5", "<1.5"]),
]

ENVIRONMENT_ITEMS = [
    ("mission_duration", "Mission duration >3hrs", ["No", "—", "—", "—", "Yes"]),
    ("back_to_back", "Back to back flights", ["No", "—", "—", "—", "Yes"]),
    ("new_airport", "Going to a new airport", ["No", "—", "—", "—", "Yes"]),
    ("dep_visibility", "Departure visibility", ["\u22656sm", "5sm", "4sm", "3sm", "<3sm"]),
    ("dep_ceiling", "Departure ceiling", ["\u22655000", "\u22653000", "\u22651500", "\u2265800", "<800"]),
    ("dest_visibility", "Destination visibility", ["\u22656sm", "5sm", "4sm", "3sm", "<3sm"]),
    ("dest_ceiling", "Destination ceiling", ["\u22655000", "\u22653000", "\u22651500", "\u2265800", "<800"]),
    ("xwind_pct", "X-wind as % of max", ["<20%", "20-49%", "50-79%", "80-99%", "\u2265100%"]),
]

EXTERNAL_ITEMS = [
    ("recent_death", "Recent death of friend/family", ["No", "—", "—", "—", "Yes"]),
    ("pressure", "Pressure to complete mission today", ["No", "—", "—", "—", "Yes"]),
    ("friend_illness", "Illness/emergency with friend/family", ["No", "—", "—", "—", "Yes"]),
    ("mission_number", "Mission # for the day", ["1st", "2nd", "3rd", "4th", "5th"]),
    ("mission_type", "Mission type", ["Dual", "Solo", "Night", "IMC", "LIFR"]),
]

CATEGORIES = {
    "pilot": {"label": "Pilot", "items": PILOT_ITEMS},
    "aircraft": {"label": "Aircraft", "items": AIRCRAFT_ITEMS},
    "environment": {"label": "enVironment", "items": ENVIRONMENT_ITEMS},
    "external": {"label": "External Factors", "items": EXTERNAL_ITEMS},
}


def score_risk(responses):
    """
    responses: dict of {item_key: rating (1-5 int)}
    Returns per-category totals, grand total, risk level, and flags.
    """
    category_totals = {}
    any_five = False
    all_keys = []

    for cat_key, cat in CATEGORIES.items():
        total = 0
        for item_key, label, options in cat["items"]:
            all_keys.append(item_key)
            rating = int(responses.get(item_key, 0) or 0)
            rating = max(0, min(5, rating))
            total += rating
            if rating == 5:
                any_five = True
        category_totals[cat_key] = total

    grand_total = sum(category_totals.values())

    if grand_total <= 29:
        level = "green"
        level_label = "Low risk (\u226429) — SP solos require IP sign-off"
    elif grand_total <= 39:
        level = "yellow"
        level_label = "Elevated risk (30\u201339) — All solos require IP sign-off"
    else:
        level = "red"
        level_label = "High risk (\u226540) — Requires manager approval"

    manager_approval_required = any_five or grand_total >= 40

    return {
        "category_totals": category_totals,
        "grand_total": grand_total,
        "level": level,
        "level_label": level_label,
        "any_five_rating": any_five,
        "manager_approval_required": manager_approval_required,
    }
