import os
import glob

def replace_in_file(filepath, pairs):
    if not os.path.exists(filepath): return
    with open(filepath, 'r') as f:
        content = f.read()
    for old, new in pairs:
        content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)

replacements = {
    "frontend/src/components/chat/QuickActions.jsx": [
        ("generate_attestation", "check_positions"),
        ("Attestation", "Positions")
    ],
    "frontend/src/components/agent/PnLChart.jsx": [
        ("Stabilizing Enclave Link...", "Loading Chart Data...")
    ],
}

for filepath, pairs in replacements.items():
    replace_in_file(filepath, pairs)

