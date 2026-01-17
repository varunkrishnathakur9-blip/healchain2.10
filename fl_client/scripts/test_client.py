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

# Test imports
try:
    from tasks.watcher import poll_tasks
    from tasks.validator import is_task_acceptable
    from tasks.lifecycle import run_task
    print("✅ All imports successful!")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test configuration
BACKEND = os.getenv("BACKEND_URL", "http://localhost:3000")
MINER_ADDRESS = os.getenv("MINER_ADDRESS")

if not MINER_ADDRESS:
    print("❌ MINER_ADDRESS not set in environment")
    sys.exit(1)

print(f"📍 Backend URL: {BACKEND}")
print(f"🔑 Miner Address: {MINER_ADDRESS}")

# Test dataset loading
try:
    ROOT = Path(__file__).resolve().parent.parent
    manifest_path = ROOT / "src" / "dataset" / "local_manifest.json"
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    print(f"✅ Dataset manifest loaded: {manifest}")
except Exception as e:
    print(f"❌ Failed to load dataset manifest: {e}")
    sys.exit(1)

# Test backend connection (with error handling)
try:
    tasks = poll_tasks(BACKEND)
    print(f"✅ Backend connection successful! Found {len(tasks)} tasks")
    
    for task in tasks:
        try:
            if not is_task_acceptable(task, manifest):
                print(f"⏭️  Task {task.get('taskID')} not acceptable, skipping")
                continue

            payload = run_task(task, MINER_ADDRESS)
            print(f"✅ Task {task.get('taskID')} processed successfully")
            print(f"📦 Payload: {payload}")

        except Exception as e:
            print(f"⚠️  Task {task.get('taskID')} failed: {e}")

except requests.exceptions.ConnectionError:
    print("⚠️  Backend server not running on port 3000")
    print("💡 Start the backend server first: npm run dev (from backend directory)")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("⚠️  Backend endpoint /tasks/open not found")
        print("💡 Check if the backend has the correct API endpoints")
    else:
        print(f"⚠️  Backend returned HTTP {e.response.status_code}")
except Exception as e:
    print(f"⚠️  Backend connection failed: {e}")

print("\n🎉 FL Client script test completed!")
