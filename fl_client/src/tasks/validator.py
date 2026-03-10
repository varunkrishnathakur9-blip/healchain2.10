def is_task_acceptable(task, manifest):
    """
    Validate task is acceptable for this miner.
    """
    # Check dataset type matches
    task_dataset = task.get("dataset", "").lower()
    manifest_type = manifest.get("type", "").lower()
    
    if task_dataset != manifest_type:
        print(f"[Validator] Dataset mismatch: task={task_dataset}, miner={manifest_type}")
        return False
    
    # Check that task has model reference
    if "modelURL" not in task and "modelIPFSHash" not in task and "initialModelLink" not in task:
        # For backward compatibility during migration, we might log warning instead of failing
        # But for real training upgrade, we want to enforce this
        print(f"[Validator] Task missing model reference (modelURL, initialModelLink or modelIPFSHash)")
        # return False # Uncomment this to enforce strict validation
    
    # Check public keys are available (strict).
    tp_key = (task.get("tpPublicKey") or "").strip()
    agg_key = (task.get("aggregatorPublicKey") or "").strip()
    if not tp_key or not agg_key:
        print("[Validator] Task missing required public keys (tpPublicKey/aggregatorPublicKey)")
        return False
    
    return True
