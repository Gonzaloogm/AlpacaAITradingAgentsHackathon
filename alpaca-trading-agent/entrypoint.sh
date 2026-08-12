#!/bin/bash
set -e

echo "╔══════════════════════════════════════════╗"
echo "║  Alpaca AI Trading Agent                 ║"
echo "║  Starting backend server...              ║"
echo "╚══════════════════════════════════════════╝"

# Verify required environment variables
if [ -z "$ALPACA_API_KEY" ] || [ "$ALPACA_API_KEY" = "your_alpaca_api_key_here" ]; then
    echo "ERROR: ALPACA_API_KEY is not set. Copy .env.example to .env and fill in your credentials."
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
    echo "WARNING: ANTHROPIC_API_KEY is not set. Chat and AI decision features will be disabled."
fi

# Start the FastAPI server
exec python -m uvicorn backend.server:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --log-level "${LOG_LEVEL:-info}"
