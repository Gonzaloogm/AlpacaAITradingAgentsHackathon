# APEX — 7-Day Build Plan (Aug 28 – Sep 4, 2026)

> Prioritized so that MCP + CLI + API integration is proven end-to-end ASAP.
> Strategy logic and UI polish are layered on after the core plumbing works.

---

## Day 1 (Thu Aug 28): Foundation — MCP + CLI + API Integration ✦ CRITICAL PATH

- [ ] Set up Alpaca paper trading account, generate API keys
- [ ] Install & verify Alpaca MCP server: `uvx alpaca-mcp-server`
- [ ] Install & verify Alpaca CLI: `brew install alpacahq/tap/cli && alpaca account get`
- [ ] Wire `mcp_client/client.py` — establish stdio MCP connection, list tools
- [ ] Wire `cli_jobs/` — wrap CLI commands, verify JSON output parsing
- [ ] **🎯 MILESTONE: Submit a test order via MCP AND via CLI, verify both work**

## Day 2 (Fri Aug 29): Agent Core — Decision Engine

- [ ] Finalize `agent/base_agent.py` with real Alpaca SDK integration
- [ ] Wire `agent/decision_engine.py` — Claude tool-calling with MCP tools
- [ ] Wire `strategy/pairs_trading.py` with real market data from Alpaca
- [ ] Connect strategy → decision engine → order execution pipeline
- [ ] **🎯 MILESTONE: Agent reads live data, Claude makes a decision, order placed — E2E**

## Day 3 (Sat Aug 30): Backend API + Reasoning Log

- [ ] Finalize `backend/server.py` — connect all endpoints to real Alpaca data
- [ ] Wire `/api/positions`, `/api/orders`, `/api/account` to alpaca-py
- [ ] Implement `reasoning_log.py` — capture each cycle's audit trail
- [ ] Wire WebSocket streaming for live trade updates
- [ ] **🎯 MILESTONE: Backend serves live Alpaca data, reasoning log captures decisions**

## Day 4 (Sun Aug 31): Frontend Dashboard

- [ ] Port reusable UI components (GlassCard, Layout, Chat, etc.)
- [ ] Build DashboardPage with Alpaca portfolio data (positions, P&L, orders)
- [ ] Build ReasoningLog component (transparency view per-trade)
- [ ] Wire ChatInterface to backend `/api/chat`
- [ ] **🎯 MILESTONE: Dashboard shows live paper trading data with reasoning log**

## Day 5 (Mon Sep 1): Strategy Refinement + Automation

- [ ] Tune pairs trading parameters on live paper data
- [ ] Implement CLI cron jobs: EOD rebalancing, position monitoring
- [ ] Add error handling, retry logic, edge cases
- [ ] Run agent autonomously for 4+ hours, fix stability issues
- [ ] (Stretch) Implement `strategy/delta_hedge_options.py`
- [ ] **🎯 MILESTONE: Agent runs autonomously without errors for extended period**

## Day 6 (Tue Sep 2): Polish + Deploy

- [ ] Frontend polish: animations, responsive design, loading/error states
- [ ] Docker Compose: verify one-command startup works
- [ ] Deploy to Render / Railway / Fly.io — get public demo URL
- [ ] Write final README with screenshots, architecture diagram
- [ ] Test demo URL end-to-end
- [ ] **🎯 MILESTONE: Demo URL live and accessible, README complete**

## Day 7 (Wed Sep 3): Presentation + Submit

- [ ] Record 3-5 minute video presentation
  - Show: MCP interaction, CLI jobs, live dashboard, reasoning log
  - Explain: architecture, strategy, AI decision-making
- [ ] Create slide deck (5-8 slides covering problem, solution, demo, tech stack)
- [ ] Fill out lablab.ai submission form (all required fields)
- [ ] Final smoke test of demo URL
- [ ] **🎯 MILESTONE: Submission complete before Sep 4 deadline**

---

## Submission Checklist

- [ ] Project title
- [ ] Short description (1 sentence)
- [ ] Long description (paragraph)
- [ ] Technology/category tags
- [ ] Cover image
- [ ] Video presentation (YouTube/Loom link)
- [ ] Slide presentation (Google Slides/Canva link)
- [ ] Public GitHub repo URL
- [ ] Hosted demo application URL
