import os

replacements = {
    "index.html": [
        ("AI Trading Agent | ERC-8004 Dashboard", "APEX | Alpaca AI Trading Agent"),
        ("AI Trading Agent — ERC-8004 TEE-secured agent dashboard with on-chain identity", "APEX — Alpaca AI Trading Agent Dashboard")
    ],
    "src/components/layout/Layout.jsx": [
        ("AI Trading Agent · ERC-8004 · Intel TDX · Sepolia Testnet · Strykr Hub", "APEX | Alpaca AI Trading Agent")
    ],
    "src/components/chat/ChatInterface.jsx": [
        ("TEE Agent Auditor V1.0 Connected\\n\\nI am the autonomous supervisor of the AGENT-4108-TDX strategy. You can audit my enclave state by asking about:\\n- **Hardware Security**: \"What is your attestation status?\"\\n- **Trading Logic**: \"Explain your Delta-Neutral strategy.\"\\n- **Portfolio Audit**: \"Show me your current equity and realized gains.\"\\n\\nI am currently running inside a **SECURED INTEL TDX ENCLAVE**.", 
         "APEX AI Trading Agent\\n\\nI am your autonomous trading agent. You can ask me about:\\n- **Current Positions**: \"What are our open positions?\"\\n- **Trading Logic**: \"Explain your strategy.\"\\n- **Portfolio**: \"Show me my current equity.\""),
        ("Agent Auditor V1.0", "APEX AI Assistant"),
        ("Internal Integrity Stream", "System Chat"),
        ("Audit session cleared", "Chat session cleared"),
        ("AUDITING ENCLAVE...", "AGENT THINKING...")
    ],
    "src/pages/LandingPage.jsx": [
        ("TEE Attestation", "AI Decision Engine"),
        ("Intel TDX hardware isolation. Every trade is cryptographically attested and verifiable on-chain.", "Powered by Google Gemini and Anthropic Claude for intelligent market analysis."),
        ("Delta-Neutral Strategy", "Pairs Trading Strategy"),
        ("ERC-8004 Identity", "MCP Integration"),
        ("On-chain agent registration with reputation scoring. Fully compliant with the ERC-8004 standard.", "Using the Model Context Protocol (MCP) to seamlessly interact with Alpaca trading APIs."),
        ("ERC-8004 · Intel TDX · Base Sepolia", "Alpaca · FastAPI · React"),
        ("STRIKER - Verified Autonomous Trading", "APEX - Autonomous AI Trading"),
        ("STRIKER", "APEX"),
        ("A TEE-secured, AI-driven delta-neutral trading agent with on-chain identity and reputation.", "An AI-driven pairs trading agent powered by Gemini and Alpaca."),
        ("Every decision signed inside an Intel TDX enclave. Every trade attested on Base Sepolia.", "Real-time decision making with transparent reasoning logs."),
        ("Enter the Enclave", "Enter Dashboard"),
        ("Hackathon Demo · LabLab ERC-8004 Challenge", "Hackathon Demo · Alpaca AI Trading")
    ]
}

def replace_in_file(filepath, pairs):
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        content = f.read()
    for old, new in pairs:
        content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

for filepath, pairs in replacements.items():
    replace_in_file("frontend/" + filepath, pairs)
