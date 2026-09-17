# Data pack for the AIONOS Assignment 3 exercise.
# Everything here is taken directly from the supplied data pack — nothing invented.

CUSTOMERS = {
    "Priya Nair": {
        "tier": "Gold",
        "pnr": "SK4821X",
        "email": "priya.nair@example.com",
        "phone": "+91-98xxxxxxx1",
        "history": "6 flights in the last 12 months · 1 prior complaint "
                    "(delayed baggage, resolved with a voucher)",
    },
    "Arvind Kulkarni": {
        "tier": "Silver",
        "pnr": "TR1190B",
        "email": "arvind.kulkarni@example.com",
        "phone": "+91-98xxxxxxx2",
        "history": "3 flights in the last 12 months · no prior complaints",
    },
    "Meher Kaur": {
        "tier": "Platinum",
        "pnr": "WL7742",
        "email": "meher.kaur@example.com",
        "phone": "+91-98xxxxxxx3",
        "history": "10 flights in the last 12 months · 1 prior complaint "
                    "(overbooking, resolved with a tier-status upgrade)",
    },
}

FLIGHTS = {
    "SK4821X": {
        "flight": "SK-204",
        "route": "Delhi → Goa",
        "date": "Wed 23 Sep 2026",
        "scheduled_departure": "18:40",
        "status": "Cancelled",
        "reason": "Operational reasons",
    },
    "TR1190B": {
        "flight": "SK-118",
        "route": "Mumbai → Bengaluru",
        "date": "Wed 23 Sep 2026",
        "scheduled_departure": "07:10",
        "status": "Delayed",
        "delay_hours": 4,
        "new_departure": "11:10",
    },
    "WL7742": {
        "flight": "SK-305",
        "route": "Delhi → Hyderabad",
        "date": "Wed 23 Sep 2026",
        "scheduled_departure": "14:00",
        "status": "Delayed",
        "delay_hours": 6,
        "new_departure": "20:00",
    },
}

# Return-leg bookings, shown alongside the outbound flight where the data
# pack lists one. Only Priya's return leg is in the supplied data pack
# (unaffected, on time) — display-only, not used by the policy engine.
RETURN_FLIGHTS = {
    "SK4821X": {
        "flight": "Return",
        "route": "Goa → Delhi",
        "date": "Fri 25 Sep 2026",
        "scheduled_departure": "16:20",
        "status": "Unaffected",
    },
}

# Voluntary (non-airline-caused) rebooking fare difference quoted for a
# customer who asks to move to a different, higher-fare flight instead of
# waiting out a delay. Only Meher's scenario includes this in the data pack.
FARE_DIFFERENCE_QUOTES = {
    "WL7742": 2000,
}

FARE_DIFFERENCE_WAIVER_LIMIT = 1500

# Allowed vs. prohibited actions, straight from the data pack — shown in the
# UI so a reviewer can see the agent's authority at a glance.
ALLOWED_ACTIONS = [
    "Rebook on the next available flight within 24 hours at no charge (airline-caused disruption)",
    "Issue meal vouchers and lounge access per the delay compensation rule",
    "Arrange hotel accommodation for the delayed-hours portion, where the delay qualifies",
    "Initiate a refund request for airline-caused cancellations",
    "Provide the customer's own booking and flight status information",
]

PROHIBITED_ACTIONS = [
    "Approving any compensation beyond the stated policy amounts",
    "Waiving a fare difference above ₹1,500",
    "Making exceptions for non-airline-caused disruptions (e.g. customer missed the flight)",
    "Handling threats of legal action or formal complaints — must be escalated immediately",
    "Processing refunds to a different payment method than the original",
]
