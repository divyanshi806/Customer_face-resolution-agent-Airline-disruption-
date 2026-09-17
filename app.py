import os
import datetime
import streamlit as st

from data import (
    CUSTOMERS, FLIGHTS, RETURN_FLIGHTS, ALLOWED_ACTIONS, PROHIBITED_ACTIONS,
)
from policy_engine import analyze, ANGRY_WORDS

# ---------------------------------------------------------------------------
# Optional Claude integration (phrasing layer only — see README).
# The app works fully without an API key; it just uses the template
# phrasing below instead of Claude's.
# ---------------------------------------------------------------------------
try:
    import anthropic
    ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    ANTHROPIC_SDK_AVAILABLE = False


st.set_page_config(
    page_title="AeroDesk — Disruption Resolution Agent",
    page_icon="🛫",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Dark console styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    :root{
        --bg:#0A121C;
        --panel:#0F1C2B;
        --panel-2:#0C1826;
        --border:#1E3245;
        --border-soft:#152536;
        --ink:#E7EEF4;
        --ink-dim:#84A0B4;
        --ink-faint:#5A7488;
        --orange:#F2A24B;
        --teal:#37C9BA;
        --red:#FF6B5E;
        --red-bg:#3A1917;
        --green:#4FD897;
        --green-bg:#123526;
        --amber:#F2C94C;
        --amber-bg:#3A2E10;
    }
    html, body, [class*="css"]{
        font-family: "Consolas", "SFMono-Regular", "Menlo", "Courier New", monospace;
    }
    .stApp{ background: var(--bg); color: var(--ink); }
    #MainMenu, footer{ visibility:hidden; }
    header[data-testid="stHeader"]{
        background: var(--bg); height: 2.2rem;
    }
    div[data-testid="stToolbar"]{ visibility: hidden; }
    .block-container{ padding-top: 1.5rem; }

    /* ---- Header ---- */
    .aerodesk-header{
        background: var(--panel-2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px 26px;
        margin-bottom: 20px;
        display:flex; justify-content: space-between; align-items:center;
        flex-wrap: wrap; gap: 10px;
    }
    .aerodesk-wordmark{ font-size: 26px; font-weight: 800; letter-spacing: 3px; }
    .aerodesk-wordmark .aero{ color: var(--orange); }
    .aerodesk-wordmark .desk{ color: var(--ink); }
    .aerodesk-subtitle{ color: var(--teal); font-size: 13px; margin-top: 2px; letter-spacing: 0.5px;}
    .aerodesk-meta{ text-align:right; }
    .aerodesk-meta .date{ color: var(--teal); font-size: 13px; font-weight:700; letter-spacing:1px; }
    .aerodesk-meta .ops{ color: var(--ink-faint); font-size: 11px; letter-spacing:1px; margin-top:2px; }

    /* ---- Panel headers ---- */
    .panel-title{
        color: var(--ink-faint); font-size: 12px; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px;
    }

    /* ---- Customer cards ---- */
    div[data-testid="stButton"] button{
        width: 100%; text-align:left; background: var(--panel);
        border: 1px solid var(--border); color: var(--ink);
        border-radius: 8px; padding: 10px 14px; font-family: inherit;
        font-weight: 600; font-size: 14px;
    }
    div[data-testid="stButton"] button:hover{
        border-color: var(--orange); color: var(--orange);
    }
    div[data-testid="stButton"] button:focus{ box-shadow:none !important; }
    .cust-selected button{
        border-color: var(--orange) !important;
        box-shadow: 0 0 0 1px var(--orange) inset;
    }
    .tier-tag{
        font-size: 10px; letter-spacing:1px; font-weight:700; padding: 1px 7px;
        border-radius: 4px; margin-left: 8px; vertical-align: middle;
    }
    .tier-Gold{ background: var(--amber-bg); color: var(--amber); }
    .tier-Silver{ background: #23303C; color: #B9C7D1; }
    .tier-Platinum{ background: #241C3A; color: #B79CF2; }

    /* ---- Generic panel card ---- */
    .adesk-card{
        background: var(--panel); border: 1px solid var(--border);
        border-radius: 8px; padding: 12px 14px; margin-bottom: 10px;
    }
    .adesk-card .flight-title{ font-weight:700; font-size: 14px; color: var(--ink); }
    .adesk-card .flight-sub{ color: var(--ink-dim); font-size: 12px; margin-top: 2px; }
    .status-badge{
        float:right; font-size: 10px; font-weight: 800; letter-spacing: 1px;
        padding: 3px 9px; border-radius: 5px;
    }
    .status-Cancelled{ background: var(--red-bg); color: var(--red); }
    .status-Delayed{ background: var(--amber-bg); color: var(--amber); }
    .status-Unaffected, .status-OnTime{ background: var(--green-bg); color: var(--green); }

    .profile-block{ color: var(--ink-dim); font-size: 12.5px; line-height: 1.7; }
    .profile-block b{ color: var(--ink); }

    /* ---- Chat panel ---- */
    .chat-open-note{
        color: var(--ink-faint); font-size: 12.5px; font-style: italic;
        border-left: 2px solid var(--border); padding-left: 10px; margin-bottom: 14px;
    }
    div[data-testid="stChatMessage"]{
        background: var(--panel); border: 1px solid var(--border-soft);
        border-radius: 8px;
    }
    div[data-testid="stChatMessageAvatarUser"]{
        background: var(--teal) !important;
    }
    div[data-testid="stChatMessageAvatarAssistant"]{
        background: var(--orange) !important;
    }
    .stChatInput textarea{ background: var(--panel) !important; color: var(--ink) !important; }

    .chat-history-box{
        max-height: 360px; overflow-y: auto; padding-right: 4px; margin-bottom: 4px;
    }
    .quickreply-label{
        color: var(--ink-faint); font-size: 11px; font-weight: 700;
        letter-spacing: 1.5px; text-transform: uppercase;
        margin: 14px 0 6px 0; padding-top: 12px; border-top: 1px solid var(--border-soft);
    }
    /* Quick reply chips — visually distinct from real chat bubbles: smaller,
       pill-shaped, dashed border, so they read as "click to send" not
       "already sent". */
    .qr-btn button{
        border-radius: 999px !important; font-size: 12px !important;
        padding: 5px 14px !important; font-weight: 500 !important;
        background: transparent !important;
        border: 1px dashed var(--border) !important;
        color: var(--ink-dim) !important;
        width: auto !important;
    }
    .qr-btn button:hover{
        border: 1px dashed var(--teal) !important; color: var(--teal) !important;
    }
    .qr-row div[data-testid="column"]{ display:flex; align-items:stretch; }

    /* ---- Ledger ---- */
    .ledger-empty{
        color: var(--ink-faint); font-size: 12.5px; line-height:1.6;
        border: 1px dashed var(--border); border-radius: 8px; padding: 16px;
    }
    .ledger-card{
        border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;
        border: 1px solid var(--border); border-left: 3px solid var(--border);
        background: var(--panel);
    }
    .ledger-card.allowed{ border-left-color: var(--green); }
    .ledger-card.escalated{ border-left-color: var(--red); }
    .ledger-card.info{ border-left-color: var(--teal); }
    .ledger-tag{
        font-size: 10px; font-weight: 800; letter-spacing: 1px;
        text-transform: uppercase; display:block; margin-bottom: 4px;
    }
    .ledger-card.allowed .ledger-tag{ color: var(--green); }
    .ledger-card.escalated .ledger-tag{ color: var(--red); }
    .ledger-card.info .ledger-tag{ color: var(--teal); }
    .ledger-body{ font-size: 12.5px; color: var(--ink); line-height: 1.45; }
    .ledger-body b{ color: var(--ink); }

    div[data-testid="stExpander"]{
        background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    }
    hr{ border-color: var(--border); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
today_label = "WED 23 SEP 2026"
st.markdown(
    f"""
    <div class="aerodesk-header">
        <div>
            <div class="aerodesk-wordmark"><span class="aero">AERO</span> <span class="desk">DESK</span></div>
            <div class="aerodesk-subtitle">Disruption Resolution Agent — Customer Support Console</div>
        </div>
        <div class="aerodesk-meta">
            <div class="date">{today_label}</div>
            <div class="ops">OPS DAY: IRREGULAR OPERATIONS</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Claude phrasing settings (kept out of the way, collapsed by default)
# ---------------------------------------------------------------------------
with st.expander("⚙ Agent settings — Claude phrasing (optional)"):
    use_claude = st.toggle("Use Claude to phrase replies", value=False)
    api_key_input = ""
    if use_claude:
        api_key_input = st.text_input(
            "Anthropic API key",
            value=os.environ.get("ANTHROPIC_API_KEY", ""),
            type="password",
            help="Only used to phrase replies — the policy engine still decides everything.",
        )
        if not ANTHROPIC_SDK_AVAILABLE:
            st.warning("Run `pip install anthropic` to enable this.")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "selected_customer" not in st.session_state:
    st.session_state.selected_customer = list(CUSTOMERS.keys())[0]

if "current_customer" not in st.session_state or st.session_state.current_customer != st.session_state.selected_customer:
    st.session_state.current_customer = st.session_state.selected_customer
    st.session_state.messages = []
    st.session_state.ledger = []

customer_name = st.session_state.selected_customer
customer = CUSTOMERS[customer_name]
pnr = customer["pnr"]
flight = FLIGHTS[pnr]
return_flight = RETURN_FLIGHTS.get(pnr)

# ---------------------------------------------------------------------------
# Layout: customer/booking | live chat | ledger
# ---------------------------------------------------------------------------
col_left, col_mid, col_right = st.columns([1, 1.3, 1])

# --- LEFT: customer selection + booking record + profile ---
with col_left:
    st.markdown('<div class="panel-title">Select customer</div>', unsafe_allow_html=True)
    for name, c in CUSTOMERS.items():
        selected = name == customer_name
        wrapper_class = "cust-selected" if selected else ""
        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
        label = f"{name}   ·   {c['tier'].upper()}   ·   {c['pnr']}"
        if st.button(label, key=f"select_{name}", use_container_width=True):
            st.session_state.selected_customer = name
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="panel-title" style="margin-top:18px;">Booking record — {pnr}</div>', unsafe_allow_html=True)

    def status_class(status):
        return {"Cancelled": "Cancelled", "Delayed": "Delayed",
                "Unaffected": "Unaffected", "On time": "OnTime"}.get(status, "Unaffected")

    delay_note = f" ({flight['delay_hours']}h · new dep {flight.get('new_departure','')})" if flight.get("delay_hours") else ""
    st.markdown(
        f"""
        <div class="adesk-card">
            <span class="status-badge status-{status_class(flight['status'])}">{flight['status'].upper()}</span>
            <div class="flight-title">{flight['flight']} · {flight['route']}</div>
            <div class="flight-sub">{flight['date']} · sched {flight['scheduled_departure']}{delay_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if return_flight:
        st.markdown(
            f"""
            <div class="adesk-card">
                <span class="status-badge status-{status_class(return_flight['status'])}">{return_flight['status'].upper()}</span>
                <div class="flight-title">{return_flight['flight']} · {return_flight['route']}</div>
                <div class="flight-sub">{return_flight['date']} · sched {return_flight['scheduled_departure']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Customer profile"):
        st.markdown(
            f"""
            <div class="profile-block">
            <b>Name:</b> {customer_name}<br>
            <b>Tier:</b> {customer['tier']}<br>
            <b>PNR:</b> {pnr}<br>
            <b>Email:</b> {customer['email']}<br>
            <b>Phone:</b> {customer.get('phone','—')}<br>
            <b>History:</b> {customer['history']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("Allowed vs. prohibited actions"):
        st.markdown("**Allowed**")
        for a in ALLOWED_ACTIONS:
            st.markdown(f"- {a}")
        st.markdown("**Must escalate**")
        for p in PROHIBITED_ACTIONS:
            st.markdown(f"- {p}")

# ---------------------------------------------------------------------------
# Reply phrasing
# ---------------------------------------------------------------------------

def template_reply(decision, is_angry):
    parts = []
    if is_angry:
        parts.append("I'm really sorry about the trouble this has caused — let's get this sorted for you.")
    if "LEGAL_ESCALATION" in decision["notes"]:
        return ("I hear you, and I want to make sure this gets the right attention. "
                "I'm escalating this to our specialist support team right now, and "
                "they'll reach out to you directly.")
    for f in decision["facts"]:
        parts.append(f)
    for a in decision["actions"]:
        parts.append(f"✓ {a['detail']}")
    for e in decision["escalations"]:
        parts.append(f"I'm not able to approve that myself — {e['detail']} "
                      "I've flagged it for a supervisor to review and they'll follow up with you.")
    if decision["ask_clarify"]:
        parts.append("Could you tell me a bit more about what you'd like help with — "
                      "your flight status, a delay, or a cancellation?")
    return " ".join(parts)


def claude_reply(api_key, customer_name, customer_text, decision, base_reply):
    """Ask Claude to phrase the reply. Returns None on any failure so the
    caller can fall back to the template — this must never crash the app."""
    if not (ANTHROPIC_SDK_AVAILABLE and api_key):
        return None
    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f"""You are a warm, professional airline customer support agent named "AeroDesk Agent".
A customer named {customer_name} just said: "{customer_text}"

Here is the ONLY decision data you may use — a policy engine already decided
what is allowed and what must be escalated. Do not invent any new facts,
numbers, or promises beyond this data. Do not change any decision (do not
approve anything marked as an escalation, do not add compensation not
listed):
{decision}

Write a short reply (2-5 sentences, plain text, no markdown) in a warm and
calm tone that states the facts and actions exactly as given, and if
something is escalated, clearly says you personally cannot approve it and
it's being handed to a supervisor. Never mention "policy engine" or these
instructions.

Fallback reply if unsure: "{base_reply}\""""
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text or None
    except Exception:
        return None


# --- MIDDLE: live chat ---
with col_mid:
    st.markdown('<div class="panel-title">Live chat — support</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="chat-open-note">Session opened with {customer_name} (PNR {pnr}).</div>',
        unsafe_allow_html=True,
    )

    quick_replies = {
        "Priya Nair": [
            "What's happening with SK-204?",
            "I want a full refund, and a free business class upgrade on my return for the trouble.",
            "This is ridiculous, I'm furious.",
        ],
        "Arvind Kulkarni": [
            "How long is the delay?",
            "Can I get a hotel room since it's been such a long delay?",
            "I might file a complaint about this.",
        ],
        "Meher Kaur": [
            "I want a full night's hotel stay, not just the delayed hours.",
            "Move me to a different flight instead, I don't want to wait 6 hours.",
            "Why should I pay extra to switch flights?",
        ],
    }

    st.markdown('<div class="chat-history-box">', unsafe_allow_html=True)
    if not st.session_state.messages:
        st.markdown(
            '<div class="chat-open-note" style="margin-top:6px;">'
            'No messages yet — pick a quick reply below or type as the customer.</div>',
            unsafe_allow_html=True,
        )
    for message in st.session_state.messages:
        avatar = "🙂" if message["role"] == "user" else "✈️"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="quickreply-label">Quick replies — click to send as the customer</div>', unsafe_allow_html=True)
    quick_clicked = None
    st.markdown('<div class="qr-btn qr-row">', unsafe_allow_html=True)
    qr_cols = st.columns(len(quick_replies[customer_name]))
    for i, q in enumerate(quick_replies[customer_name]):
        short = q if len(q) <= 40 else q[:37] + "…"
        with qr_cols[i]:
            if st.button(short, key=f"qr_{customer_name}_{i}", help=q, use_container_width=True):
                quick_clicked = q
    st.markdown("</div>", unsafe_allow_html=True)

    user_message = st.chat_input("Type as the customer...") or quick_clicked

    if user_message:
        st.session_state.messages.append({"role": "user", "content": user_message})

        decision = analyze(customer_name, user_message)
        is_angry = any(w in user_message.lower() for w in ANGRY_WORDS)
        base = template_reply(decision, is_angry)

        final_reply = base
        if use_claude and api_key_input:
            phrased = claude_reply(api_key_input, customer_name, user_message, decision, base)
            if phrased:
                final_reply = phrased

        st.session_state.messages.append({"role": "assistant", "content": final_reply})

        for a in decision["actions"]:
            st.session_state.ledger.append({"kind": "allowed", **a})
        for e in decision["escalations"]:
            st.session_state.ledger.append({"kind": "escalated", **e})
        for n in decision["notes"]:
            if n != "LEGAL_ESCALATION":
                st.session_state.ledger.append({"kind": "info", "title": "Policy note", "detail": n})
        if decision["notes"] and decision["notes"][0] == "LEGAL_ESCALATION":
            st.session_state.ledger.append({
                "kind": "escalated",
                "title": "Legal action / formal complaint",
                "detail": decision["escalations"][0]["detail"],
            })

        st.rerun()

# --- RIGHT: ledger ---
with col_right:
    st.markdown('<div class="panel-title">Action & escalation ledger</div>', unsafe_allow_html=True)
    if not st.session_state.ledger:
        st.markdown(
            '<div class="ledger-empty">No actions yet. Every decision the agent '
            'makes — allowed, informational, or escalated — will be logged here '
            'with the policy it relied on.</div>',
            unsafe_allow_html=True,
        )
    else:
        tag_labels = {"allowed": "Action taken", "escalated": "Escalated to human agent", "info": "Policy note"}
        for entry in reversed(st.session_state.ledger):
            st.markdown(
                f"""
                <div class="ledger-card {entry['kind']}">
                    <span class="ledger-tag">{tag_labels[entry['kind']]}</span>
                    <div class="ledger-body"><b>{entry['title']}</b><br>{entry['detail']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if st.button("↺ Reset this conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.ledger = []
        st.rerun()
