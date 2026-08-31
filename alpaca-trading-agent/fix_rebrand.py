import os
import re

def replace_in_file(filepath, pairs):
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        content = f.read()
    for old, new in pairs:
        content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

def walk_and_replace(directory, pairs):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".jsx") or file.endswith(".html") or file.endswith(".js"):
                replace_in_file(os.path.join(root, file), pairs)

replacements = [
    ("APEX", "Vantage"),
    ("Vantage | Alpaca AI Trading Agent", "Vantage — Your AI Trader"),
    ("Vantage — Alpaca AI Trading Agent Dashboard", "Vantage — Your AI Trader"),
    ("Vantage AI Trading Agent", "Vantage"),
    ("Alpaca · FastAPI · React", "Vantage · Powered by Alpaca · Paper Trading")
]

walk_and_replace("frontend", replacements)
