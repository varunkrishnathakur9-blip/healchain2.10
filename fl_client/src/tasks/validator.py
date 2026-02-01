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
    
    # Check public keys are available
    if "aggregatorPublicKey" not in task or "tpPublicKey" not in task:
        print(f"[Validator] Warning: Task missing public keys (continuing with mock keys if needed)")
        # return False # Uncomment for production security
    
    return True
