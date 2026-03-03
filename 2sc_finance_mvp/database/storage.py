import json
import os
from config.settings import JSON_PATH

def load_transactions():
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r") as f:
            return json.load(f)
    return []

def save_transactions(new_txns):
    existing = load_transactions()
    combined = existing + new_txns
    
    # Deduplicate based on Date, Desc, and Balance (the 'Fingerprint')
    seen = set()
    unique = []
    for t in combined:
        fingerprint = f"{t['date']}|{t['description']}|{t['balance']}"
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(t)
            
    with open(JSON_PATH, "w") as f:
        json.dump(unique, f, indent=2)
    return unique