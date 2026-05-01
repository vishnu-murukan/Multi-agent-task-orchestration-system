# Multi-Agent Task Orchestration System

A modular, fault-tolerant system where multiple AI agents collaborate through a structured pipeline to solve complex tasks — with real-time visibility into every step.

**Stack:** Python (FastAPI) · TypeScript (Next.js) · SSE for real-time updates

---

## 🚀 Overview

This project implements a **multi-agent orchestration system** designed to demonstrate how independent agents can collaborate through a controlled pipeline.

Instead of focusing on LLM capabilities, the system emphasizes:

- **Orchestration logic**
- **State management**
- **Fault tolerance**
- **Real-time system transparency**

---

## 🧠 How It Works

```
User Input
     ↓
🧠 Planner     → breaks request into sub-tasks
     ↓
🔍 Researcher  → gathers info per sub-task (parallel)
     ↓
✍️  Writer      → synthesizes research into draft report
     ↓
🔎 Reviewer    → evaluates quality → APPROVE or REJECT with feedback
     ↓ (if rejected, loops back to Writer for revision)
✅  Done        → final report rendered in UI
```

Each agent has a **single responsibility**, making the system modular, extensible, and easy to reason about.

---

## ⚙️ Key Features

### 🔹 Real-Time Updates (SSE)
Server-Sent Events stream live pipeline updates to the frontend — no polling required.

### 🔹 Iterative Feedback Loop
Reviewer evaluates the Writer's output and rejects the first draft with structured feedback. Writer revises and resubmits. Loop continues until approved or `MAX_REVISIONS` reached.

### 🔹 Parallel Research Execution
Sub-tasks from the Planner are executed concurrently using `ThreadPoolExecutor`. Individual sub-task failures are isolated — one failure doesn't stop others.

### 🔹 Retry / Error Handling
Every agent call is wrapped in retry logic:
```
Attempt 1 → fails → wait 1s → Attempt 2 → fails → wait 1s → Attempt 3 → FAILED
```
Task marked `FAILED` only after all retries exhausted.

### 🔹 Transparent Execution Chain
Every agent step is logged with input summary, output summary, status, and timestamp — all visible in the UI as an expandable chain that flows directly into the final report.

### 🔹 Unit Tests
30+ unit tests covering agent logic, orchestrator flow, retry handling, and the reviewer loop.

---

## 🖥️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, asyncio |
| Frontend | Next.js, React, TypeScript |
| Real-time | Server-Sent Events (SSE) |
| Testing | pytest, pytest-asyncio |

---

## 🧪 Setup & Running

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:3000`

### Run Tests

```bash
cd backend
pip install pytest pytest-asyncio
pytest tests.py -v
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/tasks` | Submit a new task |
| `GET` | `/tasks/:id` | Get current task state and results |
| `GET` | `/tasks/:id/stream` | SSE stream for real-time updates |
| `GET` | `/tasks` | List all tasks |
| `GET` | `/health` | Health check |

### Example

```bash
# Submit a task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"request": "Research pros and cons of microservices vs monoliths"}'

# Poll for result
curl http://localhost:8000/tasks/<task_id>
```

---

## ⚖️ Key Design Decisions

### Why SSE over WebSockets?
Only server → client communication is needed after task submission. SSE is simpler, HTTP-native, and auto-reconnects. WebSockets would be overkill here.

### Why Async Orchestrator + Sync Agents?
Orchestrator is async to run pipelines in the background without blocking HTTP responses. Agents are sync to keep them simple, stateless, and easy to unit test in isolation.

### Why Simulated Agents?
The focus is on **orchestration design**, not model capability. The assignment explicitly permits hardcoded/templated responses. The `BaseAgent` interface is designed so real LLM calls (Gemini, Claude, GPT-4) can be plugged in without changing the orchestrator or API layer.

### Why In-Memory Storage?
Simplicity and zero external dependencies for this scope. In production: Redis for shared state + PostgreSQL for persistence.

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app, endpoints, SSE
│   ├── orchestrator.py      # Pipeline coordinator + retry logic
│   ├── state.py             # Task state model + TaskStatus enum
│   ├── tests.py             # Unit tests — 30+ test cases
│   ├── requirements.txt
│   └── agents/
│       ├── __init__.py      # Agent exports
│       ├── base_agent.py    # Abstract base — AgentInput/Output contract
│       ├── planner.py       # Breaks request into sub-tasks
│       ├── researcher.py    # Parallel knowledge lookup per sub-task
│       ├── writer.py        # Synthesizes research + handles revisions
│       └── reviewer.py      # Quality evaluation + approve/reject
├── frontend/
│   ├── app/
│   │   ├── globals.css      # Global styles — fixes SSR hydration
│   │   ├── layout.tsx       # Root layout — imports globals.css
│   │   └── page.tsx         # Main UI — form, pipeline, chain, report
│   ├── hooks/
│   │   └── useSSE.ts        # EventSource hook + API calls
│   ├── types/
│   │   └── index.ts         # TypeScript types
│   ├── next.config.js
│   ├── tsconfig.json
│   └── package.json
├── design-doc.md            # Architecture decisions + trade-offs
└── README.md
```

---

## 🔮 Future Improvements

- Real LLM integration (Gemini, Claude, GPT-4) — swap agent internals only
- Persistent storage (Redis + PostgreSQL)
- Configurable pipeline from UI (skip review step, add Fact Checker)
- Exponential backoff for retries
- Streaming token-level agent output
- Multi-user support

---

## 📄 Design Document

See [design-doc.md](./design-doc.md) for full architectural write-up covering:
- All trade-offs (SSE vs WebSockets, polling vs SSE, sync vs async agents)
- Reviewer feedback loop design
- Parallel researcher implementation
- Retry / error handling strategy
- What I'd add with more time

---

> **Built to demonstrate system thinking, not just implementation.**
