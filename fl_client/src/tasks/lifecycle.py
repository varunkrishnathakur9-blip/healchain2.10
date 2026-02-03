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
from state.local_store import load_state, save_state
from config.settings import LOCAL_EPOCHS, DGC_THRESHOLD
from utils.quantize_gradients import quantize_gradients
from config.gradient_bounds import QUANTIZATION_SCALE, MAX_GRAD_MAGNITUDE
from crypto.keys import derive_public_key

def run_task(task, miner_addr):
    task_id = task["taskID"]
    print(f"\n[M3] Starting real FL training for {task_id}")

    # Step 1: Load Initial Model
    print(f"[M3] Loading initial model...")
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

    # Step 2: Load Dataset
    print(f"[M3] Loading local dataset...")
    dataset_type = task.get("dataset", "chestxray")
    loader = load_local_dataset(dataset_type)
    print(f"[M3] ✅ Dataset loaded: {dataset_type}")

    # Step 3: Train
    print(f"[M3] Training locally...")
    model = local_train(model, loader, LOCAL_EPOCHS)
    print(f"[M3] ✅ Training complete")
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

    # M3: NDD-FE Encryption (Algorithm 3 from BTP Report)
    # Get public keys from environment or task metadata
    import os
    pk_tp_hex = os.getenv("TP_PUBLIC_KEY", "")
    pk_agg_hex = os.getenv("AGGREGATOR_PK", "")
    
    # Get miner private key for NDD-FE encryption
    miner_private_key_str = os.getenv("MINER_PRIVATE_KEY", "")
    if miner_private_key_str:
        # Strip 0x prefix if present and convert to int
        sk_miner_str = miner_private_key_str.strip()
        if sk_miner_str.startswith('0x') or sk_miner_str.startswith('0X'):
            sk_miner_str = sk_miner_str[2:]
        sk_miner = int(sk_miner_str, 16) if sk_miner_str else 1
    else:
        sk_miner = 1  # Default fallback (should not be used in production)
    
    # If public keys not in env, try to get from task metadata
    if not pk_tp_hex or not pk_agg_hex:
        # Fallback: Use default keys for testing (should be provided by backend)
        # In production, these should come from task metadata or backend API
        if not pk_tp_hex:
            pk_tp_hex = task.get("tpPublicKey", "")
        if not pk_agg_hex:
            pk_agg_hex = task.get("aggregatorPublicKey", "")
    
    # Perform real NDD-FE encryption
    if pk_tp_hex and pk_agg_hex:
        ctr = 0  # Counter for randomness derivation
        ciphertext = encrypt_update(
            delta_prime=delta_p_quantized.tolist(),
            pk_tp_hex=pk_tp_hex,
            pk_agg_hex=pk_agg_hex,
            sk_miner=sk_miner,
            ctr=ctr,
            task_id=task["taskID"]
        )
    else:
        # Fallback: Use mock if keys not available (for testing)
        # This should not happen in production
        import warnings
        warnings.warn("Public keys not available, using mock ciphertext")
        ciphertext = ["0xmockpoint1,0xmockpoint2", "0xmockpoint3,0xmockpoint4"]

    # Generate real signature for submission
    ciphertext_concat = ",".join(ciphertext)
    
    # Get miner private key from environment
    miner_private_key = os.getenv("MINER_PRIVATE_KEY")
    if not miner_private_key:
        raise ValueError("MINER_PRIVATE_KEY not set in environment. Please set it in .env file.")
    
    # Derive real ECDSA public key for signature verification (x,y format)
    real_miner_pk = derive_public_key(miner_private_key)
    print(f"[M3] Using derived public key for signature: {real_miner_pk}")

    signature, canonical_msg = generate_miner_signature(
        task_id=task["taskID"],
        ciphertext=ciphertext_concat,
        score_commit=commit,
        miner_pk=real_miner_pk,
        miner_private_key=miner_private_key
    )
    
    # Compute encryptedHash (hash of ciphertext for backend storage)
    import hashlib
    encrypted_hash = hashlib.sha256(ciphertext_concat.encode('utf-8')).hexdigest()
    
    # Build full payload for submission
    payload = {
        "taskID": task["taskID"],
        "ciphertext": ciphertext,
        "ciphertext_concat": ciphertext_concat,  # For hashing
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

    return payload
