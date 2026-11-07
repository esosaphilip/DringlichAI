<div align="center">

# DringlichAI

**AI-assisted triage for the emergency department — with a clinician in the loop by design.**

The model proposes. The nurse decides.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.162-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C?logo=langchain&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-local%20via%20Ollama-000000?logo=ollama&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-3DA639)

![DringlichAI walkthrough — live queue, doctor workload and AI-assisted intake](docs/media/walkthrough.gif)

<sub>33-second walkthrough · also available as a smaller, faster [MP4](docs/media/walkthrough.mp4)</sub>

</div>

[![CI](https://github.com/esosaphilip/DringlichAI/actions/workflows/ci.yml/badge.svg)](https://github.com/esosaphilip/DringlichAI/actions/workflows/ci.yml)

---

## The problem

An emergency department does not treat patients in arrival order — it ranks them by clinical
urgency, constantly, against a capacity that keeps changing. That ranking (triage) is the
highest-stakes clerical decision in the building.

A language model is genuinely good at the reading part: matching a symptom description against a
guideline and pulling out the relevant rule. It is not something you can let queue a patient
unsupervised. Getting an LLM into clinical work is therefore mostly an *architecture* problem —
how do you take the useful half and make the other half structurally impossible?

DringlichAI is a working answer to that. The AI reads the guideline and forms a judgement, and
then **halts**: the triage graph is defined with `interrupt_before=["save_to_database"]`, so a
suggestion physically cannot reach the database until a nurse approves or overrides it in the UI.

## What it does

- **Live triage queue** — patients ordered by clinical priority then arrival time, each with a
  waiting-time bar measured against a per-priority target and an "over target" flag.
- **Doctor workload board** — per-doctor status (`available` / `on break` / `off duty`), live load
  against a cap, the patients assigned to each doctor, and staff management.
- **AI intake with human sign-off** — symptom form → retrieval + LLM triage → nurse review
  showing the suggested level, the model's confidence, *why* it chose it, and the guideline it
  matched, with P1–P5 override pills.
- **Workload-aware assignment** — new patients go to the least-loaded doctor who is not off duty.
- **Realtime across desks** — every queue change is broadcast over a WebSocket, so multiple open
  workstations stay consistent without polling.
- **Bilingual** — German and English UI, switchable at runtime.
- **Undo** — removing a treated patient raises a toast with an undo action backed by a real
  restore endpoint.

## Engineering highlights

The parts worth a closer look:

- **Safety is enforced in the graph, not the frontend.** The human-in-the-loop guarantee comes
  from LangGraph's `interrupt_before`, not from hiding a button. A `POST /triage` call returns a
  suggestion and writes nothing — there is no code path from "AI ran" to "patient queued" that
  skips the approval step.
- **Retrieval over a real guideline document.** Symptoms are embedded locally with
  `nomic-embed-text` and matched against chunks of the triage guide PDF held in Chroma; the top
  passages are injected into the prompt, and the matched rule ID is surfaced back to the nurse as
  evidence rather than hidden behind a score.
- **Structured extraction instead of parsing prose.** The model is constrained to four labelled
  lines (`PRIORITY` / `CONFIDENCE` / `GUIDELINE` / `REASON`), parsed with a fallback regex chain
  and clamped to valid ranges — so a chatty model response degrades safely instead of crashing
  the request.
- **Migrations that don't destroy data.** The queue gained tickets, confidence and doctor status
  *after* the first schema existed, so the app ships a `PRAGMA table_info` + `ALTER TABLE` helper
  that upgrades an existing `triage.db` in place rather than requiring a reset.
- **Workload rebalancing as a domain rule.** Taking a doctor off duty is not a status flag — it
  reassigns that doctor's patients to the least-loaded available colleague and reports how many
  moved, inside one transaction.
- **Runs entirely on local models.** No API keys, no per-request cost, no patient data leaving
  the machine — a deliberate constraint for anything touching clinical data.

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        UI[React + Vite SPA<br/>queue · workload · intake drawer]
    end

    subgraph Server["FastAPI (single process)"]
        API[REST endpoints]
        WS[WebSocket /ws]
        GRAPH[LangGraph triage graph]
    end

    subgraph Local["Local model + data"]
        OLLAMA[Ollama<br/>mistral · nomic-embed-text]
        CHROMA[(Chroma<br/>guideline vectors)]
        DB[(SQLite<br/>triage.db)]
    end

    UI -->|fetch| API
    UI <-->|update_queue| WS
    API --> GRAPH
    GRAPH --> OLLAMA
    GRAPH --> CHROMA
    GRAPH -.->|halted before write| API
    API --> DB
    API -->|broadcast on change| WS
```

In production the same FastAPI process also serves the built SPA, so the whole application
deploys as one service on one port.

## Design decisions

| Decision | Why |
|---|---|
| HITL enforced via `interrupt_before` in the graph | A UI-only guard is a convention that the next caller can bypass; a graph interrupt is a property of the system |
| Local models via Ollama | Keeps patient data on-premise and removes per-request cost and API-key handling |
| SQLite with in-place migrations | Right weight for a single-desk workload, and it let the schema evolve without throwing away data |
| WebSocket broadcast instead of polling | Queue state must be consistent across desks the moment it changes |
| No UI framework, hand-written CSS tokens | The design is specific; a component library would have been fought more than used |
| Optimistic list update + real restore endpoint for Undo | Instant feedback in the UI, but the undo is a genuine server round trip rather than a client-side illusion |

## The AI pipeline

```mermaid
flowchart TD
    A[Nurse submits name + symptoms] --> B[RAG: similarity search over the guideline PDF]
    B --> C[Chroma · nomic-embed-text · top 2 passages]
    C --> D[Mistral returns PRIORITY / CONFIDENCE / GUIDELINE / REASON]
    D --> E[Regex parse, clamp priority 1-5 and confidence 0-100]
    E --> F{LangGraph interrupt_before save_to_database}
    F -->|graph halts — nothing persisted| G[Nurse reviews in the UI]
    G -->|approve or override| H[POST /triage/decision]
    H --> I[Issue ticket A-001, assign least-loaded doctor]
    I --> J[WebSocket broadcasts update_queue]
    J --> K[Every open desk refreshes]
```

A real response from a chest-pain case (this is the model's actual output, and the screenshot
further down is that same call rendered in the review drawer):

```json
{
  "status": "pending_approval",
  "patient_name": "Precheck Patient",
  "assigned_doctor": "Dr. med. Stefan Weber",
  "ai_suggested_priority": 1,
  "ai_confidence": 100,
  "ai_reasoning": "The patient is experiencing sudden severe chest pain, has collapsed, and is sweating heavily.",
  "ai_guideline": "CP-01"
}
```

End-to-end latency is roughly **5–12 seconds** on a laptop CPU — long enough that the UI treats
it as a real state with its own loading stage rather than a spinner flash.

## Priority model

| Level | Label | Target wait | Colour |
|-------|-------------|-------------|--------|
| P1 | Immediate | 5 min | red |
| P2 | Very urgent | 10 min | orange |
| P3 | Urgent | 30 min | amber |
| P4 | Standard | 90 min | blue |
| P5 | Non-urgent | 120 min | slate |

Targets live in [priority.js](frontend/src/lib/priority.js) and drive the waiting bars, the
"over target" KPI and the overdue flags. A doctor's load is measured against a cap of 4.

## Screens

### Live triage queue

Four KPIs, search, priority filters and a priority-sorted grid. The waiting bar turns amber as a
patient approaches the target wait and orange once they pass it.

![Live triage queue](docs/media/01-live-queue.png)

### Doctor workload

Status pills, load slots, per-doctor patient lists, and break / off-duty controls. Setting a
doctor off duty re-assigns their patients to the least-loaded available colleague.

![Doctor workload](docs/media/02-doctor-workload.png)

### AI intake — three stages

**1. Details** — name, symptoms with quick-add chips, and arrival time.

![Intake form](docs/media/03-intake-form.png)

**2. AI triage** — retrieval runs against the guideline, then Mistral scores the urgency.

![AI triage running](docs/media/04-ai-triage-loading.png)

**3. Nurse approval** — the suggested level, the model's confidence, *why* it chose it, the
matched guideline, the auto-assigned doctor, and P1–P5 overrides. Approving issues a queue
ticket; rejecting drops the case entirely.

![Nurse review with AI confidence and reasoning](docs/media/05-nurse-review.png)

### Approved, treated and undo

![Approved patient in the queue](docs/media/06-approved-queue.png)

![Treated toast with undo](docs/media/07-treated-undo-toast.png)

### Bilingual UI

![German UI](docs/media/08-german-ui.png)

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · Uvicorn · SQLite |
| AI orchestration | LangGraph `StateGraph` + `MemorySaver`, `interrupt_before` for HITL |
| LLM / embeddings | `mistral:latest` · `nomic-embed-text:latest` via Ollama |
| Retrieval | Chroma · LangChain `RecursiveCharacterTextSplitter` · `pypdf` |
| Frontend | React 18 · Vite 5 |
| Realtime | Native WebSocket |
| Styling | Hand-written CSS with design tokens — no UI framework |

## Getting started

**Prerequisites:** Python 3.12+, Node 20+, and [Ollama](https://ollama.com) running locally.

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install fastapi "uvicorn[standard]" langgraph langchain-core \
  langchain-ollama langchain-community langchain-chroma \
  langchain-text-splitters chromadb pypdf pytest

ollama pull mistral
ollama pull nomic-embed-text

python triagestore.py        # embeds the guideline PDF into ./chroma_triage_db (run once)
python -m uvicorn api:app --port 8000
```

`triage.db` and `chroma_triage_db/` are created on first run and are gitignored.

### 2. Frontend

The backend serves the production build, so a plain `npm run build` is all you need:

```bash
cd frontend
npm install
npm run build                # emits frontend/dist, served by FastAPI at /
```

Then open **http://localhost:8000**.

For hot reload during development, run the Vite dev server instead — it proxies `/patients`,
`/doctors`, `/triage` and `/ws` to `127.0.0.1:8000`:

```bash
cd frontend
npm run dev                  # http://localhost:5173
```

## API reference

Nine REST endpoints and one WebSocket channel.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | The built SPA (`frontend/dist/index.html`) |
| `GET` | `/patients` | Queue rows — priority, doctor, ticket, AI confidence |
| `POST` | `/patients` | Re-insert a patient (powers the toast **Undo**) |
| `DELETE` | `/patients/{patient_name}` | Remove a treated patient from the queue |
| `GET` | `/doctors` | Roster with status and current active load |
| `POST` | `/doctors` | Add a doctor to staff |
| `PATCH` | `/doctors/{doctor_name}/status` | Set `available` / `break` / `off`. Going `off` reassigns patients and returns `{"reassigned": n}` |
| `POST` | `/triage` | Run retrieval + LLM triage. Returns `ai_suggested_priority`, `ai_confidence`, `ai_reasoning`, `ai_guideline`. **Writes nothing.** |
| `POST` | `/triage/decision` | Nurse approve/reject. Optional `priority_override` (1–5) replaces the AI level |
| `WS` | `/ws` | Broadcasts the literal string `update_queue` on every queue change |

Interactive docs are at `/docs` while the server is running.

## Project structure

```
dringlichAI/
├── api.py                       # FastAPI app: REST + WebSocket + serves the built SPA
├── priority_analyzer_agent.py   # LangGraph RAG triage graph (the AI)
├── triagestore.py               # one-off: embeds the guideline PDF into Chroma
├── main.py                      # CLI-only triage demo, no UI
├── conftest.py                  # puts the app root on sys.path so pytest can import the modules
├── eval/                        # triage accuracy + safety evaluation harness
│   ├── golden_set.py            # fixed 20-case golden set (+ one no-match case)
│   ├── run_eval.py              # runs the real pipeline and writes results.md
│   └── results.md               # latest measured results
├── tests/                       # pytest: output parsing · safety contract · doctor assignment
├── DringlichAI_Mock_Triage_Guide.pdf
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # state, fetching, WebSocket, intake + queue flows
│   │   ├── components/          # Sidebar, Topbar, QueueScreen, DoctorsScreen,
│   │   │                        # IntakeDrawer, Toast, KpiCard, Icons
│   │   ├── lib/                 # api.js · i18n.js · priority.js
│   │   └── styles.css           # design tokens + all components
│   ├── vite.config.js           # dev proxy to the API on :8000
│   └── package.json
└── docs/media/                  # README screenshots and walkthrough
```

## Evaluation

The triage pipeline is measured against a fixed golden set: **20 cases derived from the real
guideline's discriminators**, covering all five presentation categories (chest pain, shortness of
breath, headache, abdominal pain, wounds), with a deliberate mix of easy and ambiguous cases plus
one deliberately unmatched case studied on its own. Under-triaging a true P1 is the one failure the
system cannot tolerate, so **P1 under-triage is tracked as a separate, zero-tolerance check** and
never folded into the headline accuracy number, where it would simply be averaged away.

Latest run against the real pipeline (`mistral:latest`, no mocks):

| Metric | Result |
|---|---|
| Overall exact-match accuracy | 17/20 = **85.0%** |
| P1 recall (safety-critical) | **1.00** (6/6) |
| P1 under-triage — zero-tolerance check | **PASS** (0 hard failures) |
| Matching rule retrieved in the top-2 chunks | 19/20 |

The full per-case table, per-class precision/recall and the no-match observation live in
[eval/results.md](eval/results.md). Reproduce them with:

```bash
python eval/run_eval.py     # requires Ollama running locally
```

Two honest caveats. The three misses are all single-level errors (P3→P2, P4→P2, P2→P1) rather than
gross mis-triages, and the one real retrieval miss — the ambiguous long-duration chest-ache case —
is a *different* failure mode, where the correct rule never reached the model at all; that is
exactly why the harness reports retrieval separately. And the model samples, so repeated runs land a
few points either side of this number — treat it as an estimate, not a precise score.

Fast tests run in CI on every push; the full LLM-based evaluation is re-run manually after any
change that could affect triage quality, and its result is committed deliberately rather than
auto-generated, since it depends on a local model this CI runner doesn't have.

## Testing

```bash
pytest
```

Three suites. The first two run offline; the contract test exercises the real pipeline (Ollama
required):

- [test_output_parsing.py](tests/test_output_parsing.py) — unit-tests `parse_triage_response()`, the
  code that turns the untrusted raw model string into a priority. Covers the happy path, a missing
  line, a chatty response and a fully garbled response, pinning down the documented fallback to
  priority 3.
- [test_safety_contract.py](tests/test_safety_contract.py) — **proves the human-in-the-loop claim**:
  it calls `POST /triage` and then queries the `patients` table directly to assert nothing was
  written. That guarantee used to exist only in prose; now it is a hard assertion against the
  database.
- [test_doctor_assignment.py](tests/test_doctor_assignment.py) — the least-loaded-doctor rule: empty
  roster, a single doctor, the tie-break, off-duty exclusion, and the off-duty patient rebalance
  through the real endpoint.

Not covered yet: **all frontend logic** (no JS tests), and the model's clinical judgement is
measured statistically by the evaluation harness rather than asserted case-by-case in unit tests.

## Roadmap

The honest next steps, in the order I would take them:

1. **Authentication and roles.** Today anyone who can reach the port can approve triage
   decisions. This is the first thing that has to change.
2. **Persist the graph state.** `MemorySaver` means a pending triage thread is lost on restart;
   a SQLite or Postgres checkpointer fixes that and enables multi-worker deployment.
3. **Write the override audit trail.** The review screen tells the nurse their change is logged
   with their name — that audit table is the next thing to build.
4. **Stream the triage stages.** The loading state is currently honest but opaque; streaming the
   retrieval and scoring steps would make the waiting time informative.

## Limitations

This is a demonstration project, not a medical device.

- **No authentication** — anyone who can reach the port can approve triage decisions.
- **Single process** — SQLite plus a single Uvicorn worker.
- **Local models** — `mistral:latest` is a small general-purpose model. Priority suggestions are
  illustrative and must never be trusted clinically.
- **Mock guideline** — the triage guide PDF is synthetic, so the retrieved rules and the
  `CP-01`-style rule IDs are fabricated for the demo.
- **Unparseable model output defaults to priority 3** rather than erring toward urgency or flagging
  for manual review — tested and documented in
  [test_output_parsing.py](tests/test_output_parsing.py), not yet fixed.
- **Ticket numbering has no locking** — `_next_ticket` reads the highest ticket then writes the
  next one without a transaction guard, so two simultaneous approvals could in theory land on the
  same `A-nnn` number.
- **Doctor tie-break is implicit** — when two doctors are equally loaded, the least-loaded rule
  resolves by whatever order SQLite returns rows in (currently insertion order), with no explicit
  ordering; documented by a test in [test_doctor_assignment.py](tests/test_doctor_assignment.py).
- **Not clinically validated** — the evaluation measures agreement with a synthetic guideline, not
  clinical correctness, and `practice/` and `.env` are excluded from version control.

## Author

Built by **Eseosa Edosomwan** — [@esosaphilip](https://github.com/esosaphilip)

## Licence

MIT — see [LICENSE](LICENSE).
