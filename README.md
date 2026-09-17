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

## Architecture ()

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

##  Assumptions

Everything the agent knows comes from the supplied data pack — nothing was invented. Where the brief or the data pack left a detail unstated, the following conservative assumptions were made, and each one narrows the agent's authority rather than widening it:

Meal voucher value — stated as a concrete ₹500 rather than left vague, so the reply can be specific instead of hand-wavy.
Refund method and timeline — refunds go to the original payment method only, processed within 7 business days, per the Refund Processing Rule. Refunding to a different method is explicitly prohibited.
"Full night" vs. delayed-hours hotel — a full night's stay is treated as different from the delayed-hours accommodation the policy actually covers (delay > 5h). A full-night request is always escalated, even when a delayed-hours stay would otherwise be approved.
Tier benefits are procedural, not financial — Gold/Platinum tier gets priority rebooking language only; tier does not unlock any additional compensation, since the data pack doesn't authorise that.
Fare-difference waiver threshold (₹1,500) — applied literally: any quoted fare difference at or under the limit is treated as within agent authority to waive; anything above it is escalated for supervisor approval. The engine flags an above-threshold fare difference for awareness but only raises it as an escalation if the customer actually asks for the difference to be waived.
"Ask only necessary questions" — the agent only asks a clarifying question when intent genuinely can't be determined from the message (ask_clarify); it never asks the customer to re-confirm information (tier, PNR, flight) already present in their profile or booking record.
Legal / formal-complaint language always wins — any mention of legal action or a formal complaint short-circuits the rest of the analysis and is escalated immediately, even if the same message also contains a request the agent could otherwise fulfil.
Angry or frustrated tone doesn't change what's approved — detected anger only changes the opening line of the reply (an apology first); it never expands what the agent is allowed to do.
Return-leg data is display-only — the one return flight present in the data pack (Priya Nair's) is shown for context in the booking record but is never read by the policy engine, since the assignment scenarios don't involve a return-leg disruption.
No data outside the supplied pack — no live PNR lookup, external API, or database; if a customer or PNR isn't in data.py, the app has no way to act on it, by design.
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
