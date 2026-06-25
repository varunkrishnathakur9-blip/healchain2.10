from dataset.loader import load_local_dataset
from model.loader import load_model_from_task
from training.model import SimpleModel
from training.trainer import local_train
from training.gradient import compute_gradient
from model_compression.dgc import dgc_compress
from scoring.norm import gradient_l2_norm
from crypto.nddfe import encrypt_update
from commit.commit import commit_score
from crypto.signature import generate_miner_signature
from state.local_store import load_state, save_state, save_reveal_record
from config.settings import LOCAL_EPOCHS, DGC_THRESHOLD
from utils.quantize_gradients import quantize_gradients
from config.gradient_bounds import QUANTIZATION_SCALE, MAX_GRAD_MAGNITUDE
from crypto.keys import derive_public_key
from utils.performance_metrics import record_metric_event
import json
import time


SPARSE_PROTOCOL_VERSION = "nddfe_sparse_v1"


def _count_dataset_samples(dataset):
    try:
        total = 0
        for batch in dataset:
            labels = batch[1]
            if hasattr(labels, "shape") and labels.shape[0] is not None:
                total += int(labels.shape[0])
            else:
                total += int(len(labels))
        return total
    except Exception:
        return None


def _scalar_float(value):
    if value is None:
        return None
    try:
        if hasattr(value, "numpy"):
            value = value.numpy()
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, (list, tuple)):
            if len(value) != 1:
                return None
            value = value[0]
        return float(value)
    except (TypeError, ValueError):
        return None


def _flatten_metric_dict(result, prefix=""):
    if not isinstance(result, dict):
        return {}

    flattened = {}
    for key, value in result.items():
        metric_name = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_metric_dict(value, metric_name))
        else:
            flattened[metric_name] = value
    return flattened


def _metric_by_name(metric_values, explicit_names, contains=None):
    normalized_explicit = {name.lower() for name in explicit_names}
    for key, value in metric_values.items():
        normalized_key = str(key).lower().replace(" ", "_")
        last_part = normalized_key.rsplit(".", 1)[-1]
        if normalized_key in normalized_explicit or last_part in normalized_explicit:
            scalar = _scalar_float(value)
            if scalar is not None:
                return scalar

    if contains:
        for key, value in metric_values.items():
            normalized_key = str(key).lower().replace(" ", "_")
            if contains in normalized_key:
                scalar = _scalar_float(value)
                if scalar is not None:
                    return scalar
    return None


def _single_non_loss_metric(metric_values):
    candidates = []
    for key, value in metric_values.items():
        normalized_key = str(key).lower().replace(" ", "_")
        if "loss" in normalized_key:
            continue
        scalar = _scalar_float(value)
        if scalar is not None:
            candidates.append(scalar)
    return candidates[0] if len(candidates) == 1 else None


def _evaluate_with_return_dict(model, dataset):
    try:
        return model.evaluate(dataset, verbose=0, return_dict=True)
    except TypeError:
        return model.evaluate(dataset, verbose=0)


def _evaluate_local_model(model, dataset):
    metrics = {
        "local_loss": None,
        "local_accuracy": None,
        "samples_used": _count_dataset_samples(dataset),
    }
    try:
        result = _evaluate_with_return_dict(model, dataset)
        values = list(result) if isinstance(result, (list, tuple)) else [result]
        by_name = _flatten_metric_dict(result)

        if not by_name:
            names = list(getattr(model, "metrics_names", []) or [])
            by_name = {name: value for name, value in zip(names, values)}

        loss = _metric_by_name(by_name, {"loss"}, contains="loss")
        if loss is None and values:
            loss = _scalar_float(values[0])

        accuracy = _metric_by_name(
            by_name,
            {
                "accuracy",
                "acc",
                "binary_accuracy",
                "categorical_accuracy",
                "sparse_categorical_accuracy",
            },
            contains="accuracy",
        )
        if accuracy is None:
            accuracy = _single_non_loss_metric(by_name)
        if accuracy is None and len(values) == 2:
            # Keras 3 may report metrics_names as ["loss", "compile_metrics"]
            # while still returning [loss, accuracy] for a single compiled metric.
            accuracy = _scalar_float(values[1])

        metrics["local_loss"] = loss
        metrics["local_accuracy"] = accuracy
    except Exception as e:
        metrics["local_evaluation_error"] = str(e)
    return metrics


def _resolve_task_counter(task: dict) -> int:
    """
    Resolve the NDD-FE counter (ctr) from task metadata.
    Uses task ctr when provided, otherwise falls back to currentRound.
    """
    raw_ctr = task.get("ctr", task.get("currentRound", 1))
    try:
        ctr = int(raw_ctr)
    except Exception as e:
        raise ValueError(f"Invalid task counter value: {raw_ctr!r}") from e
    if ctr < 0:
        raise ValueError(f"Task counter must be >= 0, got {ctr}")
    return ctr

def run_task(task, miner_addr, progress_callback=None, miner_private_key_override=None):
    task_id = task["taskID"]
    pipeline_start = time.perf_counter()
    timings = {}
    print(f"\n[M3] Starting real FL training for {task_id}")

    # Step 1: Load Initial Model
    print(f"[M3] Loading initial model...")
    stage_start = time.perf_counter()
    try:
        model = load_model_from_task(task)
        print(f"[M3] ✅ Initial model loaded")
        # Inspect model input shape and first layer
        try:
            if hasattr(model, 'model'):
                print("[DEBUG] Model input shape:", model.model.input_shape)
                print("[DEBUG] Model summary:")
                model.model.summary()
            else:
                print("[DEBUG] Model input shape:", model.input_shape)
                print("[DEBUG] Model summary:")
                model.summary()
        except Exception as e:
            print(f"[DEBUG] Could not print model summary: {e}")
    except Exception as e:
        print(f"[M3] ❌ Failed to load model: {e}")
        print(f"[M3] Falling back to local SimpleCNN")
        from training.model import SimpleCNN
        model = SimpleCNN()
    timings["model_load_sec"] = time.perf_counter() - stage_start

    # Step 2: Load Dataset
    print(f"[M3] Loading local dataset...")
    stage_start = time.perf_counter()
    dataset_type = task.get("dataset", "chestxray")
    loader = load_local_dataset(dataset_type)
    timings["dataset_load_sec"] = time.perf_counter() - stage_start
    print(f"[M3] ✅ Dataset loaded: {dataset_type}")

    # Step 3: Train
    print(f"[M3] Training locally...")
    if progress_callback:
        progress_callback(10, "Training Model...")
    stage_start = time.perf_counter()
    model = local_train(model, loader, LOCAL_EPOCHS)
    timings["local_training_sec"] = time.perf_counter() - stage_start
    print(f"[M3] ✅ Training complete")
    local_eval_metrics = _evaluate_local_model(model, loader)
    if local_eval_metrics.get("local_accuracy") is not None:
        print(
            "[M3] Local evaluation: "
            f"loss={local_eval_metrics.get('local_loss')}, "
            f"accuracy={local_eval_metrics.get('local_accuracy')}"
        )
    if progress_callback:
        progress_callback(30, "Compressing Gradients (DGC)...")
    stage_start = time.perf_counter()
    grad = compute_gradient(model)
    delta_p = dgc_compress(grad, DGC_THRESHOLD, MAX_GRAD_MAGNITUDE)
    
    # Quantize gradients for BSGS compatibility
    delta_p_quantized, scale = quantize_gradients(delta_p, QUANTIZATION_SCALE)
    
    # Validate quantized gradients are within BSGS bounds
    from utils.quantize_gradients import validate_quantized_range
    if not validate_quantized_range(delta_p_quantized):
        raise ValueError("Quantized gradients exceed BSGS bounds")

    # Compute score on quantized gradients for consistency
    score = gradient_l2_norm(delta_p_quantized, scale)
    commit, nonce = commit_score(score, task["taskID"], miner_addr)
    timings["gradient_compress_score_commit_sec"] = time.perf_counter() - stage_start

    # M3: NDD-FE Encryption (Algorithm 3 from BTP Report)
    # Get public keys from environment or task metadata
    # M3: NDD-FE Encryption (Algorithm 3 from BTP Report)
    # Get public keys from task metadata (priority) or environment
    if progress_callback:
        progress_callback(40, "Preparing Encryption...")
    import os
    
    # Priority 1: Task Metadata
    pk_tp_hex = task.get("tpPublicKey", "")
    pk_agg_hex = task.get("aggregatorPublicKey", "")
    
    # Priority 2: Environment Variables (Fallback)
    if not pk_tp_hex:
        pk_tp_hex = os.getenv("TP_PUBLIC_KEY", "")
    if not pk_agg_hex:
        pk_agg_hex = os.getenv("AGGREGATOR_PK", "")

    # Get miner private key for NDD-FE encryption
    miner_private_key_str = miner_private_key_override or os.getenv("MINER_PRIVATE_KEY", "")
    if miner_private_key_str:
        # Strip 0x prefix if present and convert to int
        sk_miner_str = miner_private_key_str.strip()
        if sk_miner_str.startswith('0x') or sk_miner_str.startswith('0X'):
            sk_miner_str = sk_miner_str[2:]
        sk_miner = int(sk_miner_str, 16) if sk_miner_str else 1
    else:
        sk_miner = 1  # Default fallback (should not be used in production)
    
    # Perform real NDD-FE encryption with sparse format.
    # Hard-fail if keys are missing to avoid insecure/mock submissions.
    if not pk_tp_hex or not pk_agg_hex:
        raise ValueError(
            "Missing NDD-FE public keys for task encryption. "
            f"tpPublicKey_present={bool(pk_tp_hex)}, aggregatorPublicKey_present={bool(pk_agg_hex)}. "
            "Refusing to use mock ciphertext."
        )

    import torch
    start_time = time.perf_counter()
    
    # Extract sparse representation (non-zero indices and values)
    print(f"[M3] Extracting sparse gradients...")
    nonzero_mask = delta_p_quantized != 0
    nonzero_indices = torch.nonzero(delta_p_quantized, as_tuple=False).squeeze().tolist()
    nonzero_values = delta_p_quantized[nonzero_mask].tolist()
    
    # Handle edge case: if nonzero_indices is a single int (only one non-zero), wrap in list
    if isinstance(nonzero_indices, int):
        nonzero_indices = [nonzero_indices]
    
    total_params = len(delta_p_quantized)
    num_nonzero = len(nonzero_values)
    sparsity = (total_params - num_nonzero) / total_params * 100
    
    print(f"[M3] Total parameters: {total_params:,}")
    print(f"[M3] Non-zero values: {num_nonzero:,}")
    print(f"[M3] Sparsity: {sparsity:.2f}%")
    print(f"[M3] Starting Encryption (sparse format)...")
    
    ctr = _resolve_task_counter(task)
    ciphertext_sparse, base_mask_hex = encrypt_update(
        delta_prime=nonzero_values,  # Only encrypt non-zero values!
        pk_tp_hex=pk_tp_hex,
        pk_agg_hex=pk_agg_hex,
        sk_miner=sk_miner,
        ctr=ctr,
        task_id=task["taskID"],
        progress_callback=progress_callback,
        return_base_mask=True,
    )
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    timings["ndd_fe_encrypt_sec"] = duration
    print(f"[M3] ✅ Encryption complete. Time taken: {duration:.2f} seconds")
    print(f"[M3] Payload size reduced by ~{sparsity:.0f}%")

    # Build canonical sparse payload.
    sparse_cipher_payload = {
        "format": "sparse",
        "protocolVersion": SPARSE_PROTOCOL_VERSION,
        "ctr": ctr,
        "totalSize": total_params,
        "nonzeroIndices": nonzero_indices,
        "values": ciphertext_sparse,
        "baseMask": base_mask_hex,
    }
    ciphertext_canonical = json.dumps(
        sparse_cipher_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    
    # Get miner private key from environment
    miner_private_key = miner_private_key_override or os.getenv("MINER_PRIVATE_KEY")
    if not miner_private_key:
        raise ValueError("MINER_PRIVATE_KEY not set in environment. Please set it in .env file.")
    
    # Derive real ECDSA public key for signature verification (x,y format)
    real_miner_pk = derive_public_key(miner_private_key)
    print(f"[M3] Using derived public key for signature: {real_miner_pk}")

    stage_start = time.perf_counter()
    signature, canonical_msg = generate_miner_signature(
        task_id=task["taskID"],
        ciphertext=ciphertext_canonical,
        score_commit=commit,
        miner_pk=real_miner_pk,
        miner_private_key=miner_private_key
    )
    timings["submission_signature_sec"] = time.perf_counter() - stage_start
    
    # Compute encryptedHash (hash of ciphertext for backend storage)
    import hashlib
    encrypted_hash = hashlib.sha256(ciphertext_canonical.encode('utf-8')).hexdigest()
    
    # Build full payload for submission (SPARSE FORMAT)
    payload = {
        "taskID": task["taskID"],
        "format": "sparse",  # Indicate sparse format to aggregator
        "totalSize": total_params,  # Total number of parameters
        "nonzeroIndices": nonzero_indices,  # Indices of non-zero values
        # Ciphertext payload includes miner base mask so aggregator can decrypt sparse data exactly.
        "ciphertext": sparse_cipher_payload,
        # Keep legacy key for aggregator verifier compatibility.
        # It now carries canonical sparse payload, not a plain joined values list.
        "ciphertext_concat": ciphertext_canonical,
        "encryptedHash": encrypted_hash,  # For backend
        "scoreCommit": commit,
        "signature": signature,
        "message": canonical_msg,  # Canonical message that was signed
        "miner_pk": real_miner_pk,
        "minerAddress": miner_addr,  # Backend expects this field name
        "quantization_scale": scale
    }

    # Save full payload to state for persistence (so it survives service restarts)
    state = load_state()
    if task["taskID"] not in state:
        state[task["taskID"]] = {}
    state[task["taskID"]]["payload"] = payload
    state[task["taskID"]]["score"] = score
    state[task["taskID"]]["nonce"] = nonce
    state[task["taskID"]]["commit"] = commit
    state[task["taskID"]]["revealed"] = False
    state[task["taskID"]]["quantization_scale"] = scale
    save_state(state)

    reveal_artifact_path = save_reveal_record(
        task_id=task["taskID"],
        miner_address=miner_addr,
        score=score,
        nonce_hex=nonce,
        commit_hex=commit,
    )
    if reveal_artifact_path:
        print(f"[M3] Reveal artifact saved: {reveal_artifact_path}")

    timings["training_pipeline_total_sec"] = time.perf_counter() - pipeline_start
    record_metric_event(
        component="fl_client",
        task_id=task_id,
        event_type="training_pipeline",
        payload={
            "miner_address": miner_addr,
            "dataset": dataset_type,
            "local_epochs": LOCAL_EPOCHS,
            "dgc_threshold": DGC_THRESHOLD,
            "quantization_scale": scale,
            "total_parameters": total_params,
            "nonzero_parameters": num_nonzero,
            "sparsity_percent": sparsity,
            "compression_ratio": num_nonzero / total_params if total_params else None,
            "score": score,
            "score_commit": commit,
            "gradient_norm_l2": score,
            **local_eval_metrics,
            "timings_sec": timings,
        },
    )

    return payload
