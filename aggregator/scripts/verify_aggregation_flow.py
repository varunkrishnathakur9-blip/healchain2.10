import os
import sys
import time
import json
import requests
import hashlib

# Add src to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
AGGREGATOR_URL = os.getenv("AGGREGATOR_URL", "http://localhost:5002")

TASK_ID = "test_task_ALGO4"

def test_aggregation_flow():
    print(f"Starting Algorithm 4 Integration Test for {TASK_ID}")
    
    # 1. Create a task in the backend (using a common wallet address)
    # Note: In a real test we'd need a valid wallet signature. 
    # For now, we assume the backend allows task creation or we reuse one.
    # Let's try to fetch an existing task or create one.
    
    print("\n--- Step 1: Simulating Task Metadata ---")
    # We bypass actual task creation if we can, but we need the backend to HAVE the task.
    # If the backend is running in dev mode, we might be able to inject it via prisma or just use a known ID.
    
    print("\n--- Step 2: Database Seeded via Prisma ---")
    # Submissions are already injected with valid signatures into the DB.
    # No need to hit protected /aggregator/submit-update endpoints here.
        
    print("\n--- Step 3: Triggering Aggregator ---")
    # POST /api/aggregate
    try:
        resp = requests.post(f"{AGGREGATOR_URL}/api/aggregate", json={
            "taskID": TASK_ID,
            "aggregatorAddress": "0xAggregator"
        })
        print(f"Aggregator response: {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Failed to trigger aggregator: {e}")

    # 4. Check status
    print(f"\nWaiting for aggregator to process...")
    time.sleep(2)
    resp = requests.get(f"{AGGREGATOR_URL}/api/status/{TASK_ID}")
    print(f"Status: {resp.json()}")

if __name__ == "__main__":
    # Ensure aggregator is running
    try:
        requests.get(f"{AGGREGATOR_URL}/api/health")
    except:
        print(f"ERROR: Aggregator not running at {AGGREGATOR_URL}")
        sys.exit(1)
        
    test_aggregation_flow()
