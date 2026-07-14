# HealChain Monitor Integration Examples

Use these lightweight hooks when you add richer instrumentation to M1-M7.
All events are JSONL rows in `C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics` and are best-effort.

```python
from experimentation_and_result_Analysis.monitor_protocol_performance import (
    record_client_training_metric,
    record_gradient_submission_metric,
    record_aggregation_metric,
    record_blockchain_transaction_metric,
    record_attack_metric,
)

record_client_training_metric(
    metrics_dir="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics",
    task_id="task_iid_5c_clean_0",
    client_id="0xMiner",
    round_id=1,
    local_accuracy=0.91,
    local_loss=0.32,
    samples_used=512,
    training_time_sec=42.5,
    gradient_norm_l2=8.1,
    cosine_similarity_to_global=0.97,
)

record_gradient_submission_metric(
    metrics_dir="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics",
    task_id="task_iid_5c_clean_0",
    client_id="0xMiner",
    round_id=1,
    bytes_uploaded=1048576,
    bytes_downloaded=2048,
    compression_ratio=0.12,
    duration_sec=1.4,
)

record_aggregation_metric(
    metrics_dir="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics",
    task_id="task_iid_5c_clean_0",
    round_id=1,
    accuracy=0.93,
    validation_loss=0.21,
    tp=180,
    tn=160,
    fp=12,
    fn=8,
    aggregation_time_sec=5.8,
)

record_blockchain_transaction_metric(
    metrics_dir="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics",
    task_id="task_iid_5c_clean_0",
    round_id=1,
    tx_hash="0x...",
    tx_type="gradient_submission",
    gas_used=95000,
    gas_price_wei=20_000_000_000,
    success=True,
    confirmation_time_sec=3.2,
)

record_attack_metric(
    metrics_dir="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics",
    task_id="task_iid_5c_clean_0",
    round_id=1,
    attack_type="label_flipping",
    attack_ratio=0.3,
    poisoned_samples=100,
    poisoned_target_success=34,
    clean_accuracy=0.94,
    robust_accuracy=0.88,
    detection_tp=3,
    detection_tn=7,
    detection_fp=1,
    detection_fn=0,
)
```
