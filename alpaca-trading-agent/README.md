# APEX ⚡ AI Trading Agent

*(Submission for the Alpaca AI Trading Agents Hackathon — lablab.ai)*

<!-- TODO: Replace with actual cover image -->
![Project Cover](./assets/cover.png)

**Demo URL:** `[Coming Soon]`
**Video Presentation:** `[Coming Soon]`

---

## 📖 Short Description

Autonomous AI trading agent powered by Claude (primary) and Gemini (fallback) alongside the Alpaca stack (API + MCP + CLI) for intelligent paper trading of US equities.

## 🚀 Long Description

APEX is an AI-powered autonomous trading agent that combines Claude's reasoning capabilities with Alpaca's complete trading infrastructure. It uses a **pairs trading strategy** between correlated equities (SPY/QQQ by default), with the AI dynamically calibrating entry/exit thresholds based on market conditions.

What makes APEX unique is its **three-pillar integration** of Alpaca's developer stack:

1. **Alpaca MCP Server** — Claude communicates directly with the brokerage via structured MCP tools for interactive analysis, order execution, and portfolio queries. This is the core of the agent's decision loop.

2. **Alpaca CLI** — Scheduled jobs (end-of-day rebalancing, periodic position monitoring) run via the CLI with structured JSON output, demonstrating the CLI's strength in automation pipelines.

3. **Alpaca Trading API** — The `alpaca-py` SDK provides direct API access for real-time market data streaming and high-frequency position management.

Every decision the agent makes is logged in a **Reasoning Transparency Log** — an audit trail showing: market signal → LLM reasoning → MCP tools called → order placed → resulting P&L. This replaces traditional black-box trading with explainable AI.

## 🛠️ Tags & Technologies

- **Track:** AI Trading Agents
- **Categories:** Autonomous Trading, Pairs Trading, AI Decision Engine
- **Tech Stack:** Python 3.12, FastAPI, Claude (Anthropic, primary), Gemini (Google, fallback), Alpaca MCP Server v2, Alpaca CLI, Alpaca Trading API (alpaca-py), React 19, Vite, TailwindCSS v4

---

## 🤖 Dual AI Provider Setup

APEX uses **Anthropic Claude as the primary decision engine** for its best-in-class reasoning and tool-use with Alpaca's MCP Server. If Claude becomes unavailable due to quota or credit exhaustion, APEX **automatically falls back to Google Gemini** — with zero code changes needed.

| Provider | Role | Free Tier |
|---|---|---|
| **Claude** (Anthropic) | Primary — reasoning, MCP tool-calling | One-time \$5 credit on signup |
| **Gemini** (Google) | Fallback — equivalent prompt, adapted tool schemas | Recurring free daily quota via AI Studio |

**How the fallback works:**
1. Every call hits Claude first — zero performance overhead when credits are available.
2. If Anthropic returns HTTP 402 (credit exhausted) or HTTP 429 (rate limit), the same request is automatically retried via Gemini.
3. The `analyze_market()` response includes a `"provider"` field (`"claude"` or `"gemini"`) for full observability in logs and the reasoning transparency log.

**Tool schema compatibility:** Anthropic and Gemini use different tool/function-calling formats. The Gemini path transparently adapts Anthropic-format tool definitions (`input_schema`) to Gemini's `FunctionDeclaration` format — the Claude path is never modified.

**Setup:** Add `GEMINI_API_KEY` to your `.env` (see Configure step below). Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey) — no credit card required.

---

## ⚙️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                       │
│  Dashboard  │  Chat Interface  │  Reasoning Log  │  P&L Chart  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                             │
│  /api/account  │  /api/positions  │  /api/chat  │  /api/stream  │
│  /api/orders   │  /api/reasoning-log  │  /api/strategy/*        │
└──────┬─────────────────┬───────────────────┬────────────────────┘
       │                 │                   │
       ▼                 ▼                   ▼
┌──────────────┐ ┌───────────────┐ ┌──────────────────────────┐
│ DECISION     │ │ STRATEGY      │ │ TRANSPARENCY LOG         │
│ ENGINE       │ │ MODULE        │ │                          │
│              │ │               │ │ signal → reasoning →     │
│ Claude LLM   │ │ Pairs Trading │ │ MCP calls → order → P&L │
│ + Tool Use   │ │ (SPY/QQQ)     │ │                          │
└──────┬───────┘ └───────┬───────┘ └──────────────────────────┘
       │                 │
       ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                ALPACA INTEGRATION LAYER                         │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ MCP Client  │  │ alpaca-py    │  │ CLI Jobs           │     │
│  │ (60+ tools) │  │ SDK          │  │ (cron/scheduled)   │     │
│  │             │  │              │  │                    │     │
│  │ Interactive │  │ Market Data  │  │ EOD Rebalancing    │     │
│  │ Chat + Orders│ │ Streaming    │  │ Position Monitor   │     │
│  └──────┬──────┘  └──────┬───────┘  └────────┬───────────┘     │
│         │                │                   │                  │
│         ▼                ▼                   ▼                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          Alpaca Paper Trading Environment               │    │
│  │     (Simulated Funds · Real Market Data · Free)         │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Local Setup & Run

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- [uv](https://docs.astral.sh/uv/) — `pip install uv` or `brew install uv`
- [Alpaca CLI](https://github.com/alpacahq/cli) — `brew install alpacahq/tap/cli` (optional, for CLI jobs)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_TEAM/alpaca-trading-agent.git
cd alpaca-trading-agent

# Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
#   - ALPACA_API_KEY & ALPACA_SECRET_KEY (from https://app.alpaca.markets/paper/dashboard)
#   - ANTHROPIC_API_KEY (from https://console.anthropic.com) — primary AI
#   - GEMINI_API_KEY (from https://aistudio.google.com/app/apikey, free) — fallback AI
```

### 3. Run

```bash
# Terminal 1: Backend
python -m uvicorn backend.server:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3 (optional): Alpaca MCP Server
uvx alpaca-mcp-server
```

### Docker (Alternative)

```bash
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 📁 Project Structure

```
alpaca-trading-agent/
├── agent/              # Core agent architecture (BaseAgent, DecisionEngine)
├── mcp_client/         # Alpaca MCP server integration (stdio client)
├── cli_jobs/           # Scheduled CLI tasks (rebalancing, monitoring)
├── strategy/           # Interchangeable strategy modules (Pairs Trading, Delta Hedge)
├── backend/            # FastAPI server (API, WebSocket, Reasoning Log)
├── frontend/           # React dashboard (Vite + TailwindCSS)
├── docker-compose.yml  # One-command deployment
├── .env.example        # Credential template
└── requirements.txt    # Python dependencies
```

---

## 🏆 Hackathon Submission

| Field | Value |
|---|---|
| **Project Title** | APEX — AI Trading Agent |
| **Team Size** | 2 |
| **Hackathon** | Alpaca AI Trading Agents (lablab.ai) |
| **Dates** | Aug 28 – Sep 4, 2026 |
| **Required Tech** | Alpaca API ✅ · Alpaca MCP ✅ · Alpaca CLI ✅ |

---

## 📄 License

MIT License — see [LICENSE](./LICENSE).
