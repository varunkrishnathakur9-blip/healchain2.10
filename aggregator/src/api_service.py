# HealChain Aggregator - HTTP API Service
# HTTP wrapper for the aggregator to be called by backend

"""
HealChain Aggregator – HTTP API Service
=======================================

Provides HTTP API endpoints for the backend to trigger aggregation.
This service wraps the aggregator's main functionality in an HTTP interface.

Endpoints:
----------
POST /api/aggregate
    Trigger aggregation for a task
    Body: { taskID: str, aggregatorAddress: str }
    Returns: { success: bool, message: str }

GET /api/health
    Health check endpoint
    Returns: { status: "ok" }
"""

import os
import sys
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add src/ to Python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from utils.logging import setup_logging, get_logger
from main import HealChainAggregator

# Initialize logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger("api_service")

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for backend calls

# Store running aggregator instances
running_aggregators: dict[str, threading.Thread] = {}

# Store error messages for debugging
aggregator_errors: dict[str, str] = {}


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok"})


@app.route("/api/public-keys", methods=["GET"])
def get_public_keys():
    """
    Get public keys for NDD-FE encryption.
    Returns AGGREGATOR_PK and TP_PUBLIC_KEY from environment.
    """
    aggregator_pk = os.getenv("AGGREGATOR_PK", "")
    tp_public_key = os.getenv("TP_PUBLIC_KEY", "")
    
    if not aggregator_pk or not tp_public_key:
        logger.warning("[API] Public keys not configured in environment")
    
    return jsonify({
        "aggregatorPublicKey": aggregator_pk,
        "tpPublicKey": tp_public_key
    })


@app.route("/api/aggregate", methods=["POST"])
def trigger_aggregate():
    """
    Trigger aggregation for a task.
    
    Expected body:
    {
        "taskID": "task_001",
        "aggregatorAddress": "0x..."
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        task_id = data.get("taskID") or data.get("task_id")
        aggregator_address = data.get("aggregatorAddress") or data.get("aggregator_address")
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": "taskID is required"
            }), 400
        
        if not aggregator_address:
            return jsonify({
                "success": False,
                "error": "aggregatorAddress is required"
            }), 400
        
        # Check if aggregator is already running for this task
        if task_id in running_aggregators:
            thread = running_aggregators[task_id]
            if thread.is_alive():
                return jsonify({
                    "success": False,
                    "error": f"Aggregator is already running for task {task_id}"
                }), 400
        
        # Start aggregator in a separate thread
        def run_aggregator():
            # Set environment variables in this thread
            original_task_id = os.environ.get("TASK_ID")
            original_agg_addr = os.environ.get("AGGREGATOR_ADDRESS")
            
            try:
                # Set environment variables for this task
                os.environ["TASK_ID"] = task_id
                if aggregator_address:
                    os.environ["AGGREGATOR_ADDRESS"] = aggregator_address
                
                logger.info(f"[API] Starting aggregator for task {task_id}")
                logger.info(f"[API] Environment: TASK_ID={task_id}, AGGREGATOR_ADDRESS={aggregator_address}")
                
                aggregator = HealChainAggregator(task_id)
                logger.info(f"[API] Aggregator instance created, calling run()")
                aggregator.run()
                logger.info(f"[API] Aggregator completed for task {task_id}")
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n{traceback.format_exc()}"
                logger.error(f"[API] Aggregator error for task {task_id}: {e}", exc_info=True)
                logger.error(f"[API] Full traceback:\n{traceback.format_exc()}")
                aggregator_errors[task_id] = error_msg
            finally:
                # Restore original environment variables
                if original_task_id:
                    os.environ["TASK_ID"] = original_task_id
                elif "TASK_ID" in os.environ:
                    del os.environ["TASK_ID"]
                
                if original_agg_addr:
                    os.environ["AGGREGATOR_ADDRESS"] = original_agg_addr
                elif "AGGREGATOR_ADDRESS" in os.environ:
                    del os.environ["AGGREGATOR_ADDRESS"]
                
                # Remove from running aggregators when done
                if task_id in running_aggregators:
                    del running_aggregators[task_id]
                logger.info(f"[API] Aggregator thread finished for task {task_id}")
        
        thread = threading.Thread(target=run_aggregator, daemon=True)
        thread.start()
        running_aggregators[task_id] = thread
        
        logger.info(f"[API] Aggregator started for task {task_id}")
        
        return jsonify({
            "success": True,
            "message": f"Aggregation started for task {task_id}"
        })
        
    except Exception as e:
        logger.error(f"[API] Error in /api/aggregate: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/status/<task_id>", methods=["GET"])
def get_status(task_id: str):
    """Get aggregator status for a task."""
    is_running = False
    thread_info = None
    
    if task_id in running_aggregators:
        thread = running_aggregators[task_id]
        is_running = thread.is_alive()
        thread_info = {
            "exists": True,
            "is_alive": is_running,
            "name": thread.name
        }
    else:
        thread_info = {"exists": False}
    
    status_data = {
        "taskID": task_id,
        "running": is_running,
        "thread_info": thread_info
    }
    
    # Include error message if available
    if task_id in aggregator_errors:
        status_data["error"] = aggregator_errors[task_id]
    
    if is_running:
        status_data["status"] = "AGGREGATING"
    else:
        status_data["status"] = "IDLE"
    
    logger.debug(f"[API] Status check for task {task_id}: running={is_running}, thread_info={thread_info}")
    
    return jsonify(status_data)


if __name__ == "__main__":
    port = int(os.getenv("AGGREGATOR_PORT", "5002"))
    host = os.getenv("AGGREGATOR_HOST", "0.0.0.0")
    
    logger.info(f"[API] Starting aggregator HTTP service on {host}:{port}")
    app.run(host=host, port=port, debug=False)
