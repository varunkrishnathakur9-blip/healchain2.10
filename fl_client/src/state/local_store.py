import json
from pathlib import Path
import os

# Use absolute path based on where the script is running from
# This ensures the file is saved in the fl_client directory
def get_store_path():
    # Try to find fl_client directory based on current file location
    # This file is in fl_client/src/state/local_store.py
    current_file = Path(__file__).resolve()
    # Go up from src/state/ to fl_client/
    fl_client_dir = current_file.parent.parent.parent
    # miner_state.json should be in fl_client root
    return fl_client_dir / "miner_state.json"

STORE = get_store_path()

def load_state():
    if STORE.exists():
        try:
            return json.loads(STORE.read_text())
        except Exception as e:
            print(f"[local_store] Warning: Could not load state from {STORE}: {e}")
            return {}
    return {}

def save_state(state):
    try:
        # Ensure directory exists
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[local_store] Warning: Could not save state to {STORE}: {e}")
