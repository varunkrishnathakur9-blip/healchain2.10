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
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

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


def update_env_file(miner_address: str, config: dict):
    """
    Optionally update .env file with configuration for persistence.
    This allows the FL client service to remember configuration across restarts.
    """
    try:
        env_path = ROOT_DIR / ".env"
        
        # Read existing .env file
        env_lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                env_lines = f.readlines()
        
        # Update or add configuration
        updates = {
            "MINER_ADDRESS": miner_address,
            "BACKEND_URL": config.get("backendUrl", BACKEND_URL),
        }
        
        if config.get("tpPublicKey"):
            updates["TP_PUBLIC_KEY"] = config["tpPublicKey"]
        if config.get("aggregatorPublicKey"):
            updates["AGGREGATOR_PK"] = config["aggregatorPublicKey"]
        
        # Update existing lines or append new ones
        updated = set()
        new_lines = []
        for line in env_lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                new_lines.append(line)
                continue
            
            key = line_stripped.split("=")[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated.add(key)
            else:
                new_lines.append(line)
        
        # Add any new keys that weren't in the file
        for key, value in updates.items():
            if key not in updated:
                new_lines.append(f"{key}={value}\n")
        
        # Write back to .env file
        with open(env_path, "w") as f:
            f.writelines(new_lines)
        
        print(f"[Service] Updated .env file with configuration for {miner_address}")
    except Exception as e:
        # Don't fail if .env update fails - just log it
        print(f"[Service] Warning: Could not update .env file: {e}")


@app.route("/api/train", methods=["POST"])
def trigger_training():
    """
    Trigger training for a specific task.
    
    Request body:
    {
        "taskID": "task_001",
        "minerAddress": "0x...",
        "config": {
            "minerAddress": "0x...",
            "backendUrl": "http://localhost:3000",
            "tpPublicKey": "x_hex,y_hex",
            "aggregatorPublicKey": "x_hex,y_hex"
        }
    }
    
    The service accepts dynamic configuration, so .env updates are not required.
    If config is provided, it will be used and optionally saved to .env for persistence.
    """
    try:
        data = request.get_json()
        task_id = data.get("taskID")
        miner_address = data.get("minerAddress")
        config = data.get("config", {})

        if not task_id:
            return jsonify({"error": "taskID is required"}), 400

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
            # Store config for this miner
            miner_configs[miner_address] = {
                "backendUrl": config.get("backendUrl", BACKEND_URL),
                "tpPublicKey": config.get("tpPublicKey", ""),
                "aggregatorPublicKey": config.get("aggregatorPublicKey", ""),
            }
            
            # Optionally update .env file for persistence
            update_env_file(miner_address, config)

        # Use stored config or defaults
        current_config = miner_configs.get(miner_address, {})
        effective_backend_url = current_config.get("backendUrl", BACKEND_URL)

        # Fetch task details from backend (using effective backend URL)
        task = get_task_details(task_id, effective_backend_url)
        if not task:
            return jsonify({"error": f"Task {task_id} not found"}), 404

        # Inject public keys into task if available from config
        if current_config.get("tpPublicKey"):
            task["tpPublicKey"] = current_config["tpPublicKey"]
        if current_config.get("aggregatorPublicKey"):
            task["aggregatorPublicKey"] = current_config["aggregatorPublicKey"]

        # Validate task is acceptable
        if not is_task_acceptable(task, manifest):
            return jsonify({
                "error": f"Task {task_id} is not acceptable (dataset mismatch or other validation failed)"
            }), 400

        # Update status to TRAINING
        training_status[task_id] = {
            "taskID": task_id,
            "minerAddress": miner_address,
            "status": "TRAINING",
            "progress": 0
        }

        # Run training (this is synchronous, can be made async if needed)
        try:
            payload = run_task(task, miner_address)
            
            # M3: Automatically submit to aggregator via backend (Algorithm 3 requirement)
            # Note: Automatic submission requires wallet authentication from frontend.
            # Since training is triggered from backend (no frontend interaction), we skip
            # automatic submission and let the user manually submit from the frontend.
            # The payload is saved so manual submission can use it.
            submission_result = {
                "submitted": False,
                "status": "PENDING_MANUAL",
                "message": "Training completed. Please use the 'Submit Gradient' button on the training dashboard to submit with wallet signature.",
                "note": "Automatic submission requires wallet authentication. The payload has been saved for manual submission."
            }
            print(f"[M3] ⚠️  Automatic submission skipped (requires wallet auth from frontend)")
            print(f"[M3] 💡 Please use the 'Submit Gradient' button on the training dashboard to submit with your wallet signature.")
            
            # Store payload for potential resubmission
            training_payloads[task_id] = {
                "payload": payload,
                "minerAddress": miner_address,
                "backendUrl": effective_backend_url
            }
            
            # Update status to COMPLETED with submission info
            training_status[task_id] = {
                "taskID": task_id,
                "minerAddress": miner_address,
                "status": "COMPLETED",
                "progress": 100,
                "submitted": submission_result["submitted"] if submission_result else False,
                "submissionStatus": submission_result["status"] if submission_result else None,
                "submissionError": submission_result.get("error") if submission_result else None
            }

            return jsonify({
                "success": True,
                "message": "Training completed successfully",
                "taskID": task_id,
                "payload": payload,
                "submission": submission_result
            }), 200

        except Exception as e:
            # Update status to FAILED
            training_status[task_id] = {
                "taskID": task_id,
                "minerAddress": miner_address,
                "status": "FAILED",
                "error": str(e)
            }
            return jsonify({
                "success": False,
                "error": f"Training failed: {str(e)}"
            }), 500

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
            "scoreCommit": payload["scoreCommit"],
            "encryptedHash": payload["encryptedHash"],
            "ciphertext": json.dumps(payload["ciphertext"]),  # JSON array of EC points (required for aggregator)
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

