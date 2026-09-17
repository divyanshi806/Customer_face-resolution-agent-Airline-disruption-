"""
Deterministic policy engine for the AeroDesk resolution agent.

Design principle (see README): natural-language phrasing is handled
separately (optionally by Claude, in app.py). This module is the ONLY
place that decides policy — what's allowed, and what must be escalated.
It never calls an LLM and never guesses; every decision traces back to a
rule in the supplied data pack.
"""

from data import (
    CUSTOMERS,
    FLIGHTS,
    FARE_DIFFERENCE_QUOTES,
    FARE_DIFFERENCE_WAIVER_LIMIT,
)

# --------------------------------------------------------------------------
# Original helper functions (kept as-is for the notebook / unit tests)
# --------------------------------------------------------------------------

def cancellation_policy():
    return {
        "rebooking": True,
        "refund": True,
        "free_rebooking_window": "within 24 hours",
    }


def delay_policy(delay_hours):
    if delay_hours < 3:
        return ["Meal voucher"]
    elif delay_hours <= 5:
        return ["Meal voucher", "Lounge access"]
    else:
        return [
            "Meal voucher",
            "Lounge access",
            "Hotel accommodation for delayed hours only",
        ]


def fare_difference_policy(amount):
    if amount <= FARE_DIFFERENCE_WAIVER_LIMIT:
        return {
            "status": "allowed",
            "message": "Fare difference is within agent authority.",
        }

    return {
        "status": "escalate",
        "message": f"Fare difference exceeds ₹{FARE_DIFFERENCE_WAIVER_LIMIT}. "
                   "Supervisor approval required.",
    }


def check_escalation(request):
    request = request.lower()

    escalation_keywords = [
        "legal action",
        "formal complaint",
        "business upgrade",
        "extra compensation",
        "different payment method",
    ]

    for keyword in escalation_keywords:
        if keyword in request:
            return True, keyword

    return False, None


# --------------------------------------------------------------------------
# General intent + decision engine used by the chat UI
# --------------------------------------------------------------------------

LEGAL_WORDS = [
    "legal action", "lawsuit", "sue ", "sue me", "sue you", "lawyer",
    "consumer court", "formal complaint", "file a complaint",
]
ANGRY_WORDS = [
    "furious", "unacceptable", "ridiculous", "angry", "terrible",
    "worst", "outraged", "fed up",
]
CANCEL_WORDS = ["cancel", "cancelled", "cancellation"]
DELAY_WORDS = ["delay", "delayed", "late"]
REFUND_WORDS = ["refund", "money back", "cash back", "cash refund"]
REBOOK_WORDS = ["rebook", "rebooking", "next flight", "next available"]
UPGRADE_WORDS = ["business class", "first class", "upgrade"]
SWITCH_FLIGHT_WORDS = [
    "different flight", "earlier flight", "another flight", "move me",
    "switch flight", "move to a different",
]
HOTEL_WORDS = ["hotel", "accommodation", "a room", "full night", "stay the night"]
FULL_NIGHT_WORDS = ["full night", "whole night", "entire night"]
VOUCHER_WORDS = ["voucher", "lounge", "meal"]
WAIVE_WORDS = [
    "waive", "without paying", "don't want to pay", "dont want to pay",
    "shouldn't have to pay", "shouldnt have to pay", "why should i pay",
    "for free", "free upgrade",
]
STATUS_WORDS = ["what's happening", "whats happening", "status", "what happened", "why is my flight"]


def _has(text, words):
    return any(w in text for w in words)


def analyze(customer_name: str, message: str) -> dict:
    """
    Decide what the agent may do in response to `message` from
    `customer_name`. Returns a dict:
        {
          "facts": [str, ...],
          "actions": [{"title": str, "detail": str}, ...],
          "escalations": [{"title": str, "detail": str}, ...],
          "notes": [str, ...],
          "ask_clarify": bool,
        }
    This function is the single source of truth for policy — the chat UI
    and any LLM phrasing layer must not add or override anything here.
    """
    t = message.lower()
    decision = {
        "facts": [], "actions": [], "escalations": [], "notes": [],
        "ask_clarify": False,
    }

    customer = CUSTOMERS[customer_name]
    pnr = customer["pnr"]
    flight = FLIGHTS[pnr]

    # Legal threats / formal complaints always win, and are handled alone.
    if _has(t, LEGAL_WORDS):
        decision["escalations"].append({
            "title": "Legal action / formal complaint mentioned",
            "detail": "Per policy, any mention of legal action or a formal "
                      "complaint must be escalated to a human agent "
                      "immediately, regardless of the underlying request.",
        })
        decision["notes"].append("LEGAL_ESCALATION")
        return decision

    # --- Cancellation flow ---
    if flight["status"] == "Cancelled" and (_has(t, CANCEL_WORDS) or _has(t, STATUS_WORDS)):
        decision["facts"].append(
            f"{flight['flight']} ({flight['route']}, {flight['date']}) is "
            f"cancelled due to {flight.get('reason', 'operational reasons')}."
        )
        wants_refund = _has(t, REFUND_WORDS)
        wants_rebook = _has(t, REBOOK_WORDS)
        wants_upgrade = _has(t, UPGRADE_WORDS)

        if wants_refund and not wants_upgrade:
            decision["actions"].append({
                "title": "Refund initiated",
                "detail": f"Full refund for {flight['flight']} initiated to "
                          "the original payment method. Processed within 7 "
                          "business days, per the Refund Processing Rule.",
            })
        elif wants_rebook:
            priority = " Priority rebooking applies for Gold/Platinum tier." \
                if customer["tier"] in ("Gold", "Platinum") else ""
            decision["actions"].append({
                "title": "Rebooking offered",
                "detail": f"Free rebooking on the next available flight "
                          f"within 24 hours for {flight['flight']}, at no "
                          f"charge.{priority}",
            })
        else:
            decision["actions"].append({
                "title": "Cancellation options presented",
                "detail": "Per the Cancellation Rebooking Rule: free "
                          "rebooking on the next available flight within "
                          "24 hours, or a full refund — customer's choice.",
            })

    # --- Delay flow ---
    if flight["status"] == "Delayed" and (_has(t, DELAY_WORDS) or _has(t, HOTEL_WORDS) or _has(t, VOUCHER_WORDS)):
        h = flight["delay_hours"]
        decision["facts"].append(
            f"{flight['flight']} ({flight['route']}) is delayed {h} hours, "
            f"new departure {flight['new_departure']}."
        )
        comp = delay_policy(h)
        base_detail = " + ".join(comp[:2]) if len(comp) >= 2 else comp[0]
        if h > 3:
            decision["actions"].append({
                "title": "Meal voucher + lounge access issued",
                "detail": "Delay exceeds 3 hours: ₹500 meal voucher and "
                          "lounge access applied.",
            })
        else:
            decision["actions"].append({
                "title": "Meal voucher issued",
                "detail": "Delay is under 3 hours: ₹500 meal voucher applied.",
            })

        wants_hotel = _has(t, HOTEL_WORDS)
        wants_full_night = _has(t, FULL_NIGHT_WORDS)
        if h > 5:
            if wants_full_night:
                decision["escalations"].append({
                    "title": "Full night hotel stay requested",
                    "detail": "Policy only covers hotel accommodation for "
                              "the delayed-hours portion, not a full "
                              "night's stay. Approving a full night is "
                              "beyond the standard policy amount and "
                              "requires supervisor sign-off.",
                })
                decision["actions"].append({
                    "title": "Delayed-hours hotel accommodation offered",
                    "detail": "Delay exceeds 5 hours, so hotel "
                              "accommodation covering the delayed-hours "
                              "portion has been arranged (not a full "
                              "night's stay).",
                })
            elif wants_hotel:
                decision["actions"].append({
                    "title": "Hotel accommodation arranged",
                    "detail": "Delay exceeds 5 hours, so accommodation "
                              "covering the delayed-hours portion has "
                              "been arranged, per policy.",
                })
        elif wants_hotel:
            decision["escalations"].append({
                "title": "Hotel accommodation requested — not entitled",
                "detail": f"Hotel accommodation only applies to delays "
                          f"over 5 hours. This delay is {h} hours, so it "
                          "is not covered without supervisor approval.",
            })

    # --- Upgrade "for the trouble" — additional compensation beyond policy ---
    if _has(t, UPGRADE_WORDS):
        decision["escalations"].append({
            "title": "Free upgrade requested as compensation",
            "detail": "A complimentary upgrade beyond the standard "
                      "cancellation/delay remedy is additional "
                      "compensation not covered by policy. This needs "
                      "supervisor approval.",
        })

    # --- Voluntary switch to a different, higher-fare flight ---
    fare_quote = FARE_DIFFERENCE_QUOTES.get(pnr)
    if _has(t, SWITCH_FLIGHT_WORDS) and fare_quote:
        if _has(t, WAIVE_WORDS):
            result = fare_difference_policy(fare_quote)
            decision["escalations"].append({
                "title": "Fare difference waiver requested",
                "detail": f"Moving to the requested flight carries a "
                          f"₹{fare_quote} fare difference. {result['message']}",
            })
        else:
            decision["actions"].append({
                "title": "Voluntary rebooking quoted",
                "detail": f"Moving to the alternate flight is possible, "
                          "but since it is a voluntary change (not "
                          f"airline-caused) it carries a ₹{fare_quote} "
                          "fare difference, payable to proceed.",
            })
            if fare_quote > FARE_DIFFERENCE_WAIVER_LIMIT:
                decision["notes"].append(
                    f"Fare difference of ₹{fare_quote} exceeds the "
                    f"₹{FARE_DIFFERENCE_WAIVER_LIMIT} threshold agents can "
                    "waive — flagged for awareness; only escalate if the "
                    "customer asks for it to be waived."
                )

    if not decision["actions"] and not decision["escalations"] and not decision["facts"]:
        decision["ask_clarify"] = True

    return decision
