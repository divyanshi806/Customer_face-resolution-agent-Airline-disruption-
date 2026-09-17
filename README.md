# AeroDesk — Airline Customer Resolution Agent

AIONOS Assignment 3 — Customer-Facing Resolution Agent (Streamlit prototype).

## Objective

Build a customer-facing agent for airline disruptions that:
- Understands customer intent from free text
- Uses only the supplied customer, booking and policy data
- Applies policy-based decisions (never invents rules or compensation)
- Handles frustrated or confused customers
- Executes and records allowed actions
- Escalates requests outside the agent's authority

## Architecture (for the demo video)

The agent is built as two deliberately separate layers, so policy can never
drift even if the language model changes what it says:

```
Customer message
      │
      ▼
┌─────────────────────┐     reads      ┌───────────────┐
│  Intent parser        │◄──────────────│   data.py       │
│  (policy_engine.py)    │               │  customers,     │
│  keyword/rule based    │               │  flights, fare  │
└─────────┬───────────┘               │  quotes, rules  │
          │ decision (facts, actions,  └───────────────┘
          │  escalations) — plain dict
          ▼
┌─────────────────────┐
│  Reply phrasing        │
│  • Template (default)  │
│  • Claude API (optional)│  ← phrasing ONLY, never decides policy
└─────────┬───────────┘
          │
          ▼
   Chat reply + ledger entry
   (action/escalation + the policy it relied on)
```

1. **`data.py`** — the supplied data pack (customers, bookings, fare-difference
   quotes, allowed/prohibited action lists), unmodified from the assignment.
2. **`policy_engine.py`** — the only place that decides anything. `analyze()`
   reads the customer's message, detects intent (cancellation, delay, refund,
   rebooking, hotel, fare difference, legal threat, sentiment), and returns a
   plain dict of facts / allowed actions / escalations, each one traceable to
   a specific rule in the data pack. This function never calls an LLM.
3. **`app.py`** — the Streamlit UI. It calls `analyze()` to get the decision,
   then turns it into a reply two possible ways:
   - **Template phrasing (default, always on)** — deterministic sentence
     assembly, so the app is fully functional with zero external dependencies
     or API keys.
   - **Claude phrasing (optional toggle in the sidebar)** — sends *only* the
     decision dict (not the policy engine, not the raw data pack) to Claude
     and asks it to rewrite it in a warmer, more natural voice. Claude is
     explicitly told not to add facts or approve anything not already in the
     decision. If the call fails for any reason, the app silently falls back
     to the template reply.
4. Every action or escalation is appended to an **action ledger**
   (`st.session_state.ledger`) shown in the right-hand column, so a reviewer
   can see exactly what the agent did and which policy justified it.

### Why keep policy and phrasing separate?

If an LLM decided policy directly, its answer could vary run to run and
could be persuaded off-policy by a determined customer message. Here, the
LLM (when enabled) only ever rewrites a decision that was already made by
plain Python — it cannot approve an escalation, invent a compensation
amount, or change what the customer is entitled to.

## Tech stack

- Python + Streamlit (UI)
- `anthropic` Python SDK (optional — reply phrasing only)

## Project structure

- `app.py` — Streamlit UI, chat loop, ledger, optional Claude call
- `data.py` — supplied customer, flight and policy data
- `policy_engine.py` — deterministic intent detection + policy decisions
- `VS_Code_Notebook.ipynb` — quick sanity checks against the policy engine
- `requirements.txt` — dependencies

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

### Enabling Claude-phrased replies (optional)

The app works fully without this — you'll just get the template phrasing.
To turn on Claude:

1. Get an API key from the [Anthropic Console](https://console.anthropic.com/).
2. In the app's sidebar, toggle **"Use Claude to phrase replies"** and paste
   the key (or set it once via `export ANTHROPIC_API_KEY=sk-...` before
   running, and the field will pre-fill).

## Test customers

1. **Priya Nair** (Gold, SK4821X) — cancelled flight; try asking for a
   refund, then for a free upgrade "for the trouble."
2. **Arvind Kulkarni** (Silver, TR1190B) — 4-hour delay; try asking for a
   hotel room, then mention filing a complaint.
3. **Meher Kaur** (Platinum, WL7742) — 6-hour delay; try asking for a full
   night's stay, then for a flight switch, then ask why she should pay the
   fare difference.

## Design principle

Natural-language interaction is separated from policy enforcement. The
agent never invents compensation or takes an action beyond the authority
defined in the supplied assignment data — anything outside that authority
is written to the ledger as an escalation, not silently approved.
