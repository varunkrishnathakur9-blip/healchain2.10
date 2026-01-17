from pathlib import Path
import sys
import json
import os
import requests
from dotenv import load_dotenv
load_dotenv()

# Add src directory to Python path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))

from tasks.watcher import poll_tasks
from tasks.validator import is_task_acceptable
from tasks.lifecycle import run_task

# --- Config ---
BACKEND = os.getenv("BACKEND_URL", "http://localhost:3000")
MINER_ADDRESS = os.getenv("MINER_ADDRESS")

if not MINER_ADDRESS:
    raise RuntimeError("MINER_ADDRESS not set in environment")

# --- Load dataset manifest safely ---
ROOT = Path(__file__).resolve().parent.parent
manifest_path = ROOT / "src" / "dataset" / "local_manifest.json"

with open(manifest_path) as f:
    manifest = json.load(f)

# --- Poll tasks ---
tasks = poll_tasks(BACKEND)

for task in tasks:
    try:
        if not is_task_acceptable(task, manifest):
            continue

        payload = run_task(task, MINER_ADDRESS)

        print(f"[M3] Prepared submission for task {task['taskID']}")
        print(f"   Score Commit: {payload['scoreCommit']}")
        print(f"   Encrypted Hash: {payload['encryptedHash']}")
        print(f"   Signature: {payload['signature'][:32]}...")

        # M3: Send submission to backend
        try:
            submission_data = {
                "taskID": payload["taskID"],
                "minerAddress": payload["minerAddress"],  # For submitGradient service
                "address": payload["minerAddress"],  # For requireWalletAuth middleware
                "scoreCommit": payload["scoreCommit"],
                "encryptedHash": payload["encryptedHash"],
                "message": payload["message"],
                "signature": payload["signature"]
            }
            
            response = requests.post(
                f"{BACKEND}/aggregator/submit-update",
                json=submission_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Submission successful: {result.get('status', 'SUBMITTED')}")
            else:
                print(f"   ❌ Submission failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Failed to send submission to backend: {e}")
            print(f"   💡 Submission payload (for manual retry):")
            print(f"      {submission_data}")

    except Exception as e:
        print(f"[WARN] Task {task.get('taskID')} failed: {e}")
        import traceback
        traceback.print_exc()