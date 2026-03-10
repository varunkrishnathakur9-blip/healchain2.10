"""
HealChain FL Client Service
HTTP service for triggering training from backend/frontend

The service fetches task details from backend when triggered,
so .env only needs static miner-specific config (MINER_ADDRESS, keys, etc.)
"""

from pathlib import Path
import sys
import os
import json
import getpass
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from eth_account import Account

# Load environment variables
load_dotenv()

# Add src directory to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tasks.watcher import poll_tasks
from tasks.validator import is_task_acceptable
from tasks.lifecycle import run_task
from state.local_store import load_state, save_state
from crypto.keys import derive_public_key

app = Flask(__name__)
CORS(app)  # Enable CORS for backend requests

# Configuration - can be set via .env or passed dynamically in requests
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
MINER_ADDRESS = os.getenv("MINER_ADDRESS")  # Optional - can be passed per request

# Dynamic configuration storage (per miner address)
miner_configs = {}  # minerAddress -> config dict

# Load dataset manifest
MANIFEST_PATH = ROOT_DIR / "src" / "dataset" / "local_manifest.json"
try:
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
except FileNotFoundError:
    print(f"[Service] Warning: Manifest file not found at {MANIFEST_PATH}")
    print("[Service] Creating default manifest...")
    manifest = {
        "dataset": "chestxray",
        "path": "data/chestxray",
        "format": "image"
    }
    # Create directory if it doesn't exist
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[Service] Created default manifest at {MANIFEST_PATH}")

# Training status tracking
training_status = {}  # taskID -> status dict

# Store training payloads for resubmission
training_payloads = {}  # taskID -> {payload, minerAddress, backendUrl}


def get_task_details(task_id: str, backend_url: str = None):
    """
    Fetch task details from backend.
    This allows .env to only contain static miner-specific config.
    """
    import requests
    try:
        # Use provided backend URL or default
        url = f"{(backend_url or BACKEND_URL)}/tasks/{task_id}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"[Service] Error fetching task details: {e}")
        return None


def update_env_file(updates: dict):
    """
    Persist selected keys in fl_client/.env and mirror them into process env.
    """
    env_path = ROOT_DIR / ".env"
    env_lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            env_lines = f.readlines()

    applied = set()
    new_lines = []
    for line in env_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            applied.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in applied:
            new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    for key, value in updates.items():
        os.environ[key] = str(value)


def fetch_task_public_keys(task_id: str, backend_url: str):
    """
    Fetch current task public keys from backend.
    """
    import requests
    try:
        resp = requests.get(f"{backend_url}/tasks/{task_id}/public-keys", timeout=8)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return {
            "tpPublicKey": data.get("tpPublicKey", ""),
            "aggregatorPublicKey": data.get("aggregatorPublicKey", ""),
        }
    except Exception:
        return None


def prompt_and_set_miner_credentials():
    """
    Ask for miner private key on service startup and persist MINER_PRIVATE_KEY + MINER_ADDRESS.
    """
    global MINER_ADDRESS

    # Clear persisted private key first (as requested) before accepting new input.
    update_env_file({"MINER_PRIVATE_KEY": ""})

    while True:
        raw_key = getpass.getpass("[FL Client Service] Enter miner private key (0x...): ").strip()
        if not raw_key:
            print("[FL Client Service] Private key cannot be empty.")
            continue
        key = raw_key if raw_key.startswith(("0x", "0X")) else f"0x{raw_key}"

        try:
            # Validate wallet key format and derive corresponding address.
            derived_address = Account.from_key(key).address.lower()
            # Validate it also works for miner_pk derivation path.
            _ = derive_public_key(key)
            update_env_file({
                "MINER_PRIVATE_KEY": key,
                "MINER_ADDRESS": derived_address,
            })
            MINER_ADDRESS = derived_address
            print(f"[FL Client Service] Loaded miner address: {derived_address}")
            return
        except Exception as e:
            print(f"[FL Client Service] Invalid private key: {e}")


def check_miner_key_status(task_id: str, miner_address: str, backend_url: str = None):
    """
    Preflight check: ensure this miner's derived public key is not already
    used by another miner for the same task.
    """
    import requests

    miner_private_key = os.getenv("MINER_PRIVATE_KEY", "")
    if not miner_private_key:
        return False, "MINER_PRIVATE_KEY is not set in .env"

    try:
        miner_pk = derive_public_key(miner_private_key)
    except Exception as e:
        return False, f"Failed to derive miner public key from MINER_PRIVATE_KEY: {e}"

    try:
        url = f"{(backend_url or BACKEND_URL)}/miners/{task_id}/key-status"
        resp = requests.get(
            url,
            params={
                "address": miner_address.lower(),
                "publicKey": miner_pk
            },
            timeout=8
        )

        if resp.status_code != 200:
            return False, f"Key status check failed (HTTP {resp.status_code}): {resp.text}"

        data = resp.json()
        if not data.get("valid"):
            return False, data.get("message") or data.get("reason") or "Miner public key validation failed"

        return True, "OK"
    except Exception as e:
        return False, f"Could not validate miner public key uniqueness: {e}"


def get_effective_miner_private_key(miner_address: str):
    """
    Resolve miner private key from environment.
    Manual mode: user updates .env and restarts service per miner.
    """
    return os.getenv("MINER_PRIVATE_KEY", "")


import threading

def training_worker(task, miner_address, effective_backend_url, task_id, miner_private_key):
    """
    Background worker for running FL training.
    """
    try:
        print(f"[Service] Background training started for task {task_id}")
        
        # Define progress callback to update global status
        def progress_callback(percent, msg):
            # Map encryption progress (which is 0-100 of that step) to overall progress
            # Training/Compression: 0-40%
            # Encryption: 40-100%
            if "[Crypto]" in msg:
                # Encryption phase (starts at 40%)
                effective_progress = 40 + (percent * 0.6)
            else:
                # Other phases (0-40%)
                effective_progress = percent
                
            training_status[task_id].update({
                "progress": int(effective_progress),
                "message": msg
            })
            
        payload = run_task(
            task,
            miner_address,
            progress_callback=progress_callback,
            miner_private_key_override=miner_private_key
        )
        
        # Store payload for manual submission (M3)
        training_payloads[task_id] = {
            "payload": payload,
            "minerAddress": miner_address,
            "backendUrl": effective_backend_url
        }
        
        # Update status to COMPLETED
        training_status[task_id].update({
            "status": "COMPLETED",
            "progress": 100,
            "submitted": False,
            "submissionStatus": "PENDING_MANUAL"
        })
        print(f"[Service] Background training completed for task {task_id}")
        
    except Exception as e:
        print(f"[Service] Background training failed for task {task_id}: {e}")
        import traceback
        traceback.print_exc()
        training_status[task_id].update({
            "status": "FAILED",
            "error": str(e)
        })

@app.route("/api/train", methods=["POST"])
def trigger_training():
    """
    Trigger training for a specific task.
    
    The service is now asynchronous to prevent timeouts.
    """
    try:
        data = request.get_json()
        task_id = data.get("taskID")
        miner_address = data.get("minerAddress")
        config = data.get("config", {})

        if not task_id:
            return jsonify({"error": "taskID is required"}), 400

        # Prevent concurrent training for the same task
        if task_id in training_status and training_status[task_id]["status"] == "TRAINING":
            return jsonify({"error": f"Training already in progress for task {task_id}"}), 400

        # Get miner address from request or config or .env
        if not miner_address:
            miner_address = config.get("minerAddress") or MINER_ADDRESS

        if not miner_address:
            return jsonify({
                "error": "minerAddress is required. Provide it in request body, config, or set MINER_ADDRESS in .env"
            }), 400

        miner_address = miner_address.lower()

        # Update configuration from request (if provided)
        if config:
            miner_configs[miner_address] = {
                "backendUrl": config.get("backendUrl", BACKEND_URL),
                "tpPublicKey": config.get("tpPublicKey", ""),
                "aggregatorPublicKey": config.get("aggregatorPublicKey", ""),
            }

        # Use stored config or defaults
        current_config = miner_configs.get(miner_address, {})
        effective_backend_url = current_config.get("backendUrl", BACKEND_URL)
        effective_miner_private_key = get_effective_miner_private_key(miner_address)

        if not effective_miner_private_key:
            return jsonify({
                "error": "MINER_PRIVATE_KEY is not configured for this miner.",
                "suggestion": "Set MINER_PRIVATE_KEY in fl_client/.env and restart the FL client service."
            }), 400

        # Guard against accidentally using one FL service instance for multiple miners
        # with a single shared key.
        configured_miner_address = (MINER_ADDRESS or "").lower()
        if configured_miner_address and configured_miner_address != miner_address:
            return jsonify({
                "error": (
                    f"FL service configured for miner {configured_miner_address} "
                    f"but request is for {miner_address}."
                ),
                "suggestion": (
                    "Run one FL service per miner (distinct .env with unique MINER_PRIVATE_KEY), "
                    "or restart this service after updating MINER_ADDRESS and MINER_PRIVATE_KEY."
                )
            }), 400

        # Fetch task details from backend
        task = get_task_details(task_id, effective_backend_url)
        if not task:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        # Always fetch latest task keys from backend for this task.
        latest_keys = fetch_task_public_keys(task_id, effective_backend_url)
        if latest_keys:
            task["tpPublicKey"] = latest_keys.get("tpPublicKey", "") or task.get("tpPublicKey", "")
            task["aggregatorPublicKey"] = latest_keys.get("aggregatorPublicKey", "") or task.get("aggregatorPublicKey", "")
            update_env_file({
                "MINER_ADDRESS": miner_address,
                "TP_PUBLIC_KEY": task.get("tpPublicKey", ""),
                "AGGREGATOR_PK": task.get("aggregatorPublicKey", ""),
            })

        # Preflight: ensure this miner uses a unique keypair for this task
        key_ok, key_msg = check_miner_key_status(task_id, miner_address, effective_backend_url)
        if not key_ok:
            return jsonify({
                "error": "Miner key validation failed",
                "details": key_msg,
                "suggestion": (
                    "Each miner must use a unique MINER_PRIVATE_KEY for a task. "
                    "Update fl_client/.env for this miner instance."
                )
            }), 400

        # Inject public keys into task
        if current_config.get("tpPublicKey"):
            task["tpPublicKey"] = current_config["tpPublicKey"]
        if current_config.get("aggregatorPublicKey"):
            task["aggregatorPublicKey"] = current_config["aggregatorPublicKey"]

        # Validate task is acceptable
        if not is_task_acceptable(task, manifest):
            return jsonify({
                "error": f"Task {task_id} is not acceptable (dataset mismatch or other validation failed)"
            }), 400

        # Initialize status as TRAINING
        training_status[task_id] = {
            "taskID": task_id,
            "minerAddress": miner_address,
            "status": "TRAINING",
            "progress": 0
        }

        # Start training in background thread
        thread = threading.Thread(
            target=training_worker, 
            args=(task, miner_address, effective_backend_url, task_id, effective_miner_private_key),
            name=f"TrainingWorker-{task_id}"
        )
        thread.start()

        return jsonify({
            "success": True,
            "message": "Training started successfully in the background",
            "taskID": task_id,
            "status": "TRAINING"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/train/status", methods=["GET"])
def get_training_status():
    """
    Get training status for a task.
    
    Query params:
    - taskID: Task identifier
    - minerAddress: Miner address (optional, defaults to MINER_ADDRESS)
    """
    try:
        task_id = request.args.get("taskID")
        miner_address = request.args.get("minerAddress") or MINER_ADDRESS

        if not task_id:
            return jsonify({"error": "taskID is required"}), 400

        if not miner_address:
            return jsonify({"error": "minerAddress is required"}), 400

        # Check if we have status for this task
        if task_id in training_status:
            status = training_status[task_id]
            # Verify miner address matches
            if status["minerAddress"].lower() == miner_address.lower():
                return jsonify(status), 200

        # Return IDLE status if no status found
        return jsonify({
            "taskID": task_id,
            "minerAddress": miner_address,
            "status": "IDLE"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/submit", methods=["POST"])
def submit_gradient():
    """
    Manually submit gradient to aggregator (M3).
    Can be used to resubmit if automatic submission failed.
    
    Request body:
    {
        "taskID": "task_001",
        "minerAddress": "0x..." (optional, defaults to MINER_ADDRESS)
    }
    """
    print(f"[M3] Received submission request: {request.get_json()}")
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
            
        task_id = data.get("taskID")
        miner_address = data.get("minerAddress") or MINER_ADDRESS

        if not task_id:
            return jsonify({"error": "taskID is required"}), 400

        if not miner_address:
            return jsonify({"error": "minerAddress is required"}), 400

        miner_address = miner_address.lower()

        # First, check in-memory training_payloads
        payload_data = None
        backend_url = None
        
        if task_id in training_payloads:
            stored = training_payloads[task_id]
            if stored["minerAddress"].lower() == miner_address.lower():
                payload_data = stored["payload"]
                backend_url = stored["backendUrl"]
        
        # If not in memory, try loading from persisted state (miner_state.json)
        if not payload_data:
            try:
                state = load_state()
                if task_id in state and "payload" in state[task_id]:
                    stored_payload = state[task_id]["payload"]
                    # Verify miner address matches
                    if stored_payload.get("minerAddress", "").lower() == miner_address.lower():
                        payload_data = stored_payload
                        # Use current backend URL from config
                        # Check if we have config for this miner
                        if miner_address in miner_configs:
                            backend_url = miner_configs[miner_address].get("backendUrl", BACKEND_URL)
                        else:
                            backend_url = BACKEND_URL
                        print(f"[M3] Loaded payload from persisted state for task {task_id}")
            except Exception as e:
                print(f"[M3] Warning: Could not load payload from state: {e}")
                import traceback
                traceback.print_exc()
        
        # If still no payload found, return detailed error
        if not payload_data:
            # Check if task exists in state but without payload (old training)
            state = load_state()
            has_old_training = False
            if task_id in state:
                if "score" in state[task_id] or "commit" in state[task_id]:
                    has_old_training = True
            
            if has_old_training:
                return jsonify({
                    "error": f"Training data found for task {task_id}, but submission payload is missing. This may happen if training completed before payload persistence was added, or if the FL client service was restarted after training completed.",
                    "suggestion": "Please retrain the task to generate a new payload with submission data (ciphertext, encryptedHash, signature). After retraining, the payload will be saved and you can submit it.",
                    "action": "RETRAIN"
                }), 404
            else:
                return jsonify({
                    "error": f"No training payload found for task {task_id}. Please complete training first.",
                    "suggestion": "Please trigger training again to generate a new payload."
                }), 404

        payload = payload_data

        # Preflight again before submission to fail fast with clear reason
        effective_miner_private_key = get_effective_miner_private_key(miner_address)
        key_ok, key_msg = check_miner_key_status(task_id, miner_address, backend_url)
        if not key_ok:
            return jsonify({
                "error": "Miner key validation failed before submission",
                "details": key_msg,
                "suggestion": "Use a unique MINER_PRIVATE_KEY per miner instance and retrain/resubmit."
            }), 400

        # Get wallet auth from request (if provided by backend from frontend)
        # This is needed for backend API authentication
        # The payload signature is for gradient submission verification, not API auth
        wallet_auth = data.get("walletAuth")
        
        if not wallet_auth:
            return jsonify({
                "error": "Wallet authentication required. Please submit from the frontend with wallet signature.",
                "suggestion": "Use the 'Submit Gradient' button on the training dashboard to submit with proper wallet authentication."
            }), 400

        # Use wallet auth from frontend (passed through backend)
        api_address = wallet_auth.get("address")
        api_message = wallet_auth.get("message")
        api_signature = wallet_auth.get("signature")
        
        if not api_address or not api_message or not api_signature:
            return jsonify({
                "error": "Invalid wallet authentication. Missing address, message, or signature.",
                "details": {
                    "hasAddress": bool(api_address),
                    "hasMessage": bool(api_message),
                    "hasSignature": bool(api_signature),
                    "walletAuthKeys": list(wallet_auth.keys()) if wallet_auth else []
                }
            }), 400
        
        # Ensure message is a string (not None or other type)
        if not isinstance(api_message, str):
            return jsonify({
                "error": f"Invalid message type. Expected string, got {type(api_message).__name__}",
                "messageValue": str(api_message)[:100] if api_message else None
            }), 400
        
        # Ensure signature is a string
        if not isinstance(api_signature, str):
            return jsonify({
                "error": f"Invalid signature type. Expected string, got {type(api_signature).__name__}",
                "signatureValue": str(api_signature)[:50] if api_signature else None
            }), 400

        # Submit to backend with both gradient data and wallet auth
        import requests
        import json
        submission_data = {
            # Gradient submission fields (M3) - Algorithm 3
            "taskID": payload["taskID"],
            "minerAddress": payload["minerAddress"],
            "miner_pk": payload.get("miner_pk"),  # Public key used to sign submission
            "scoreCommit": payload["scoreCommit"],
            "encryptedHash": payload["encryptedHash"],
            "ciphertext": json.dumps(payload["ciphertext"]),  # JSON payload (sparse metadata + values)
            "minerSignature": payload.get("signature"),  # Miner signature for submission verification (separate from wallet auth)
            # Wallet auth fields (for API authentication - required by requireWalletAuth middleware)
            "address": api_address,
            "message": api_message,
            "signature": api_signature  # Wallet signature for API authentication
        }

        print(f"[M3] Submitting to backend: {backend_url}/aggregator/submit-update")
        print(f"[M3] Wallet auth - Address: {api_address}")
        print(f"[M3] Wallet auth - Message preview: {api_message[:50] if api_message else 'None'}...")
        print(f"[M3] Wallet auth - Signature preview: {api_signature[:20] if api_signature else 'None'}...")

        response = requests.post(
            f"{backend_url}/aggregator/submit-update",
            json=submission_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"[M3] Backend response status: {response.status_code}")
        if response.status_code != 200:
            print(f"[M3] Backend response body: {response.text}")

        if response.status_code == 200:
            result = response.json()
            
            # Update training status with submission info
            import time
            current_timestamp = int(time.time())  # Unix timestamp in seconds
            
            if task_id in training_status:
                training_status[task_id]["submitted"] = True
                training_status[task_id]["submissionStatus"] = result.get("status", "SUBMITTED")
                training_status[task_id]["submittedAt"] = str(current_timestamp)  # Unix timestamp in seconds (string)
                training_status[task_id].pop("submissionError", None)
            else:
                # If status doesn't exist, create it
                training_status[task_id] = {
                    "taskID": task_id,
                    "minerAddress": miner_address,
                    "status": "COMPLETED",
                    "progress": 100,
                    "submitted": True,
                    "submissionStatus": result.get("status", "SUBMITTED"),
                    "submittedAt": str(current_timestamp)
                }
            
            return jsonify({
                "success": True,
                "message": "Gradient submitted to aggregator successfully",
                "status": result.get("status", "SUBMITTED")
            }), 200
        else:
            error_msg = response.text
            return jsonify({
                "success": False,
                "error": f"Submission failed: {response.status_code} - {error_msg}",
                "statusCode": response.status_code
            }), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "minerAddress": MINER_ADDRESS or "(dynamic)",
        "backendUrl": BACKEND_URL,
        "configuredMiners": list(miner_configs.keys()),
        "availableRoutes": [
            "/api/health",
            "/api/train",
            "/api/train/status",
            "/api/submit"
        ]
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("FL_CLIENT_SERVICE_PORT", "5001"))
    prompt_and_set_miner_credentials()
    print(f"[FL Client Service] Starting on port {port}")
    print(f"[FL Client Service] Miner Address: {MINER_ADDRESS}")
    print(f"[FL Client Service] Backend URL: {BACKEND_URL}")
    print(f"[FL Client Service] Health check: http://localhost:{port}/api/health")
    print(f"[FL Client Service] Available routes:")
    print(f"  - POST /api/train - Trigger training")
    print(f"  - GET /api/train/status - Get training status")
    print(f"  - POST /api/submit - Submit gradient to aggregator (M3)")
    print(f"  - GET /api/health - Health check")
    app.run(host="0.0.0.0", port=port, debug=False)

