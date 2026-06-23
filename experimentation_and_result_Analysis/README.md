# HealChain Experimentation and Result Analysis

This folder contains the experiment tooling for the HealChain IEEE paper. Use it
to prepare IID and non-IID ChestXRay client datasets, run HealChain from M1 to
M7, monitor performance/security/blockchain metrics, and generate paper-ready
CSV, JSON, plots, LaTeX tables, and Markdown reports.

HealChain target setting:

- Dataset: ChestXRay
- Task: binary classification
- Classes: `NORMAL` and `PNEUMONIA`
- FL settings: IID and non-IID
- Attack settings: no attack, label flipping, gradient poisoning, Byzantine clients
- Attack/client ratios: `0%`, `10%`, `20%`, `30%`, `40%`, `50%`
- Scalability client counts: `5`, `10`, `20`, `50`, `100`

## 1. Install Dependencies

From a PowerShell terminal:

```powershell
cd C:\repos\healchain\experimentation_and_result_Analysis
pip install -r requirements.txt
```

The monitoring script uses `matplotlib`, `seaborn`, `scikit-learn`,
`requests`, `psutil`, and optionally `pynvml` for NVIDIA GPU metrics. If no GPU
or NVML library is available, GPU columns are written as `N/A` and the rest of
the monitor still works.

## 2. Prepare Dataset Splits

The split scripts support both common ChestXRay layouts:

Converted HealChain format:

```text
dataset/
  images/
    sample_0001.npy
  labels.json
```

Class-folder format:

```text
train/
  NORMAL/
    image_001.jpeg
  PNEUMONIA/
    image_002.jpeg
```

### IID Split

Interactive mode:

```powershell
cd C:\repos\healchain\experimentation_and_result_Analysis
python split_chestxray_iid.py
```

Non-interactive mode:

```powershell
python split_chestxray_iid.py `
  --dataset "C:\path\to\chest_xray\train" `
  --clients 5 `
  --seed 42
```

The script writes output beside the original dataset:

```text
train_iid_5_clients/
  client_01/
  client_02/
  client_03/
  client_04/
  client_05/
  split_summary.json
```

IID allocation is stratified, so each client receives approximately the same
class ratio as the original training set.

### Non-IID Split

Interactive mode:

```powershell
python split_chestxray_non_iid.py
```

Non-interactive mode:

```powershell
python split_chestxray_non_iid.py `
  --dataset "C:\path\to\chest_xray\train" `
  --clients 5 `
  --dominant-fraction 0.8 `
  --seed 42
```

The script writes:

```text
train_non_iid_5_clients/
  client_01/
  client_02/
  client_03/
  client_04/
  client_05/
  split_summary.json
```

The non-IID split is label-skewed. `--dominant-fraction 0.8` means most samples
of each class are assigned to class-primary clients, while the remainder is
spread across other clients.

Important: this script currently creates a label-skew non-IID split, not a true
Dirichlet partition. If the IEEE paper specifically states Dirichlet
partitioning, either add/use a Dirichlet splitter before final experiments or
describe the current method as label-skew non-IID. When Dirichlet is used, pass
the alpha value to the monitor with `--dirichlet-alpha`.

## 3. Assign Client Splits To Miners

Each `client_XX` folder is one miner's local training dataset.

Important current implementation detail: the FL client loader reads from:

```text
C:\repos\healchain\fl_client\local_data\chestxray
```

So, before starting a miner service, place that miner's split at that path. For
example, for miner 1 in a 5-client IID experiment, copy or sync:

```text
train_iid_5_clients\client_01 -> fl_client\local_data\chestxray
```

If you run multiple miners at the same time from one checkout, use separate
prepared FL client working directories, one per miner. Otherwise the miners will
overwrite/read the same `local_data\chestxray` folder.

For every miner:

1. Use the matching `client_XX` dataset.
2. Keep the task dataset name as `chestxray`.
3. Start the miner service on its assigned port.
4. Use a distinct miner wallet/private key.

## 4. Set A Shared Metrics Directory

The FL client and aggregator write JSONL metric events. Use one shared metrics
directory for all services in the experiment:

```powershell
$env:HEALCHAIN_METRICS_DIR="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics"
```

Set this environment variable in every terminal used for:

- FL client services
- Aggregator
- Any custom attack or blockchain instrumentation
- The monitor, if you pass `--metrics-dir`

Restart services after setting the variable so the probes write to the correct
location.

## 5. Run One Experiment From M1 To M7

Use one unique task ID for each experimental setting. A recommended naming
pattern is:

```text
task_<split>_<clients>c_<attack>_<ratio>
```

Examples:

```text
task_iid_5c_clean_0
task_iid_5c_label_flip_30
task_non_iid_10c_byzantine_40
```

Start the monitor before M1 so it can observe the full protocol lifecycle.

Clean IID example:

```powershell
cd C:\repos\healchain\experimentation_and_result_Analysis
python monitor_protocol_performance.py `
  --split-type iid `
  --task-id task_iid_5c_clean_0 `
  --num-clients 5 `
  --dataset-path "C:\path\to\train_iid_5_clients" `
  --attack-type none `
  --attack-ratio 0 `
  --backend-url http://localhost:3000 `
  --rpc-url http://127.0.0.1:8545 `
  --stop-at-terminal
```

Non-IID Byzantine example:

```powershell
python monitor_protocol_performance.py `
  --split-type non_iid `
  --task-id task_non_iid_10c_byzantine_40 `
  --num-clients 10 `
  --dataset-path "C:\path\to\train_non_iid_10_clients" `
  --attack-type byzantine `
  --attack-ratio 40 `
  --byzantine-ratio 40 `
  --backend-url http://localhost:3000 `
  --rpc-url http://127.0.0.1:8545 `
  --stop-at-terminal
```

Then proceed manually through HealChain:

1. M1: publish task and escrow reward.
2. M2: register/select miners.
3. M3: run local miner training and gradient submission.
4. M4: run secure aggregation and model evaluation.
5. M5: collect miner verification feedback.
6. M6: publish candidate/global model payload.
7. M7: reveal accuracy/scores and distribute rewards.

If you do not use `--stop-at-terminal`, press `Ctrl+C` after M7. The monitor
will still generate the report.

## 6. Correct Experimentation Runbook

Use this workflow for every final experiment. The goal is to avoid spending
hours on M1-M7 only to discover that the run is not paper-quality.

### 6.1 Pre-Run Sanity Checks

Before starting M1, verify the basic training path outside the full protocol:

1. Confirm the dataset split folder exists and contains one folder per client.
2. Confirm every client folder has both `NORMAL` and `PNEUMONIA` samples for
   IID experiments.
3. Run a small local training/evaluation check if available. The clean model
   should produce accuracy above random baseline and loss should decrease.
4. Confirm the validation set is loaded from the intended path.
5. Confirm labels are encoded consistently, for example `NORMAL=0` and
   `PNEUMONIA=1`, or document the actual mapping.

Do not proceed to the full matrix if clean accuracy is stuck at exactly
`50.00%`, loss is missing for every round, or the validation set cannot produce
TP/TN/FP/FN or prediction vectors. Fix the data/model/evaluation path first.

### 6.2 Service Setup Checklist

Use one terminal per service, and set the shared metrics directory before
starting each service:

```powershell
$env:HEALCHAIN_METRICS_DIR="C:\repos\healchain\experimentation_and_result_Analysis\monitoring_metrics"
```

Restart any backend, aggregator, or FL client service that was already running
before this variable was set.

For each miner:

1. Use a unique wallet/private key.
2. Use the correct `client_XX` dataset split.
3. Use a separate FL client working directory if running miners concurrently
   from one machine.
4. Confirm the miner service port and backend registration address are unique.
5. Record the miner address to client split mapping in your experiment notes.

### 6.3 Task Naming

Use descriptive task IDs for final runs. Avoid opaque IDs like `task_040`
except for debugging.

```text
task_iid_7c_clean_0_seed42
task_iid_7c_label_flip_20_seed42
task_non_iid_7c_byzantine_40_seed123
```

Each experimental setting and seed must use a fresh task ID.

### 6.4 M1-M7 Execution Gates

At each stage, verify the gate condition before moving on:

| Stage | Action | Gate before proceeding |
| --- | --- | --- |
| M1 | Publish task and escrow reward | Task is visible in backend; publish tx/hash is recorded |
| M2 | Register/select miners | Registered miner count equals the planned client count, or the exception is documented |
| M3 | Local training and gradient submission | Expected miners submit gradients; local accuracy/loss/sample metrics are emitted |
| M4 | Secure aggregation and evaluation | Global model is evaluated; accuracy and confusion counts or prediction vectors are emitted |
| M5 | Verification feedback | Verification votes/signatures are emitted for selected participants |
| M6 | Publish candidate/global model | Candidate hash, model hash/link, participant list, and transaction data are recorded |
| M7 | Reveal scores and distribute rewards | Rewards are distributed; final task status reaches `REWARDED` |

If a gate fails, stop and diagnose the run. Do not continue or treat the final
report as a final experiment.

### 6.5 Minimum Metrics Required For Final Results

For clean classification tables, collect:

- final accuracy, best accuracy, and per-round accuracy
- precision, recall, F1 score, specificity, and sensitivity
- TP, TN, FP, FN, or `y_true`/`y_pred` vectors
- validation loss or test loss
- per-client local accuracy, local loss, and samples used

For protocol overhead tables, collect:

- per-client training time and pipeline time
- NDD-FE encryption/decryption time
- signature time
- upload/download bytes
- aggregation time
- CPU/RAM/disk usage

For blockchain overhead tables, collect:

- transaction hash and transaction type
- gas used
- gas price
- transaction success/failure status
- confirmation time or block inclusion delay
- ETH/USD/INR cost

For attack experiments, collect:

- attack type and attack ratio
- malicious client IDs
- poisoned sample count
- clean and robust accuracy
- attack success rate
- detection TP/TN/FP/FN
- malicious filtered and benign incorrectly filtered counts

### 6.6 Repeatability

For final paper results, run each setting at least three times with different
seeds and report mean plus standard deviation:

```text
seed 42
seed 123
seed 2026
```

Keep the generated report directory, code commit/version, dataset split path,
task ID, and seed together in your experiment log.

### 6.7 Recommended Execution Order

Run experiments in this order:

1. IID clean baseline with a small client count.
2. Non-IID clean baseline with the same client count.
3. IID attack experiments after the clean IID baseline learns correctly.
4. Non-IID attack experiments after the clean non-IID baseline learns correctly.
5. Scalability runs after correctness and instrumentation are stable.

Task 40 is a good example of a pipeline-validation run: it reached `REWARDED`,
but accuracy remained `50.00%` and several required metrics were missing. Treat
such runs as diagnostics, not final result rows.

## 7. Experiment Matrix For The Paper

For a complete IEEE-style evaluation, run both split types across the required
attack ratios:

```text
split_type in [iid, non_iid]
attack_type in [none, label_flipping, gradient_poisoning, byzantine]
attack_ratio in [0, 10, 20, 30, 40, 50]
```

For scalability:

```text
num_clients in [5, 10, 20, 50, 100]
```

Recommended minimum result set:

- IID clean baseline
- Non-IID clean baseline
- IID label flipping at all ratios
- Non-IID label flipping at all ratios
- IID gradient poisoning at all ratios
- Non-IID gradient poisoning at all ratios
- IID Byzantine clients at all ratios
- Non-IID Byzantine clients at all ratios
- Scalability runs for 5, 10, 20, 50, and 100 clients

Use a fresh task ID for every row in the experiment matrix.

## 8. Monitor Outputs

Each monitor run creates:

```text
results/monitoring/<iid|non_iid>/<task_id_timestamp>/
  monitor_config.json
  monitor_snapshots.jsonl
  monitor.log
  round_metrics.csv
  client_metrics.csv
  blockchain_metrics.csv
  attack_metrics.csv
  system_metrics.csv
  experiment_summary.json
  metrics_summary.json
  experiment_report.md
  <split>_<task_id>_result_analysis.md
  integration_examples.md
  tables/
    table_accuracy.tex
    table_attack_robustness.tex
    table_blockchain_overhead.tex
    table_scalability.tex
    table_fairness.tex
```

Plots are written to:

```text
results/plots/<iid|non_iid>/<task_id_timestamp>/
```

Generated figures include:

- `accuracy_vs_round.png`
- `loss_vs_round.png`
- `asr_vs_attack_ratio.png`
- `accuracy_vs_attack_ratio.png`
- `gas_usage_vs_round.png`
- `communication_cost_vs_round.png`
- `client_fairness_distribution.png`
- `gradient_similarity_histogram.png`
- `blockchain_latency_distribution.png`
- `scalability_curves.png`
- `confusion_matrix_round_<n>.png` when confusion matrix values are available

All plots are saved at publication quality with 300 DPI.

## 9. Metrics Collected

The monitor aggregates metrics from backend polling, FL client probes,
aggregator probes, system sampling, optional RPC transaction receipts, and any
custom attack instrumentation.

Machine learning metrics:

- Accuracy, precision, recall, F1 score
- ROC AUC, PR AUC
- Specificity, sensitivity
- Confusion matrix, TP, TN, FP, FN
- Training loss, validation loss, test loss
- Accuracy/loss vs round
- Convergence round

Convergence round is defined as the first round where moving average accuracy
changes by less than `0.1%` for 5 consecutive rounds.

Federated learning metrics:

- Per-client local accuracy and local loss
- Per-client samples used
- Per-client training time
- Gradient L2 norm
- Cosine similarity to global gradient
- Gradient variance and divergence
- Update magnitude, global-model distance, parameter drift
- Compression ratio and sparsity

Attack and robustness metrics:

- Malicious detection TP, TN, FP, FN
- Detection TPR, FPR, precision, recall, F1
- Attack success rate
- Clean accuracy
- Robust accuracy
- Accuracy drop
- Malicious clients filtered
- Benign clients incorrectly filtered

Blockchain metrics:

- Transaction count
- Successful and failed transactions
- Gas used by submission, aggregation, and reward distribution
- ETH, USD, and INR cost
- Confirmation time
- Block inclusion delay
- Aggregation completion latency

Communication and system metrics:

- Bytes uploaded and downloaded
- Total MB transmitted
- Average communication per round/client
- CPU, RAM, disk growth
- Optional GPU utilization, memory, and temperature

Fairness metrics:

- Contribution score
- Participation frequency
- Reward received
- Jain fairness index

If a value is shown as `N/A`, the protocol completed without emitting that
specific metric. The report is still valid, but the missing field should not be
claimed in the paper.

### 9.1 Why Task 40 Has `N/A` Metrics

Task `task_040` completed the protocol and reached `REWARDED`, but its metric
events were mostly timing and communication events:

```text
gradient_submission_communication, training_pipeline, run_started,
key_initialization, secure_aggregation_total, model_update_evaluation,
ndd_fe_decrypt, submission_collection, dequantization, bsgs_recovery,
candidate_local_verification, verification_vote, run_completed,
candidate_broadcast_communication, candidate_formation_broadcast,
candidate_signature
```

The `N/A` values come from missing source fields, not from report generation
failure:

| `N/A` area | Reason in task 40 | Fix for future runs |
| --- | --- | --- |
| Precision, recall, F1, specificity, sensitivity | The backend exposed final accuracy, but no TP/TN/FP/FN, 2x2 confusion matrix, or `y_true`/`y_pred` vectors were emitted | Emit `tp`, `tn`, `fp`, `fn`, `confusion_matrix`, or `y_true`/`y_pred` during global evaluation in M4 |
| ROC AUC and PR AUC | No probability/score vector was emitted | Emit `y_score`, `probabilities`, or `scores` with `y_true` |
| Confusion matrix plot | No confusion counts or prediction vectors were available | Emit confusion counts or vectors before report generation |
| Local loss and samples used | Client events did not include `local_loss` or `samples_used` | Add `record_client_training_metric(...)` calls in each FL client after local evaluation |
| Gradient norm/similarity/variance/divergence | Submission events did not include these gradient statistics | Emit gradient statistics before encryption/submission, or compute them in a privacy-safe debug path |
| Participation frequency | No service emitted a participation count/frequency per miner | Emit participation count after miner selection or reward calculation |
| Blockchain gas/cost/confirmation | Task snapshots exposed tx hashes, but no gas/status/confirmation fields were emitted or enriched from RPC | Pass a working `--rpc-url`, ensure receipts are available, or emit `gas_used`, `gas_price_wei`, `success`, and `confirmation_time_sec` with `record_blockchain_transaction_metric(...)` |
| Successful/failed transaction counts | No transaction status was emitted; `0 successful` and `0 failed` means unknown, not failed | Emit `success=True/False` or use RPC receipt enrichment |
| Attack metrics | Attack type was `none`, so attack success/detection metrics do not apply | Only expect these for attack runs; emit detection counts for label-flipping, poisoning, or Byzantine settings |
| GPU metrics | GPU/NVML data was unavailable | Install NVIDIA drivers and `pynvml`, or leave GPU fields out of claims |
| Throughput | The task 40 monitor config did not set `--num-clients`, so throughput could not be computed | Always pass `--num-clients <N>` for final runs |

Task 40 also showed a participation mismatch: the report context expected seven
clients, while backend snapshots showed six registered miners and five gradient
submissions. For final experiments, resolve that mismatch before M4 or document
the run as incomplete.

## 10. Adding Richer Instrumentation

The monitor already reads the basic JSONL timing events emitted by the FL client
and aggregator. For richer attack, client, or blockchain metrics, use the helper
functions documented in each run's `integration_examples.md`.

Example:

```python
from experimentation_and_result_Analysis.monitor_protocol_performance import (
    record_client_training_metric,
    record_attack_metric,
)

record_client_training_metric(
    metrics_dir="C:/repos/healchain/experimentation_and_result_Analysis/monitoring_metrics",
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

record_attack_metric(
    metrics_dir="C:/repos/healchain/experimentation_and_result_Analysis/monitoring_metrics",
    task_id="task_iid_5c_label_flip_30",
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

## 11. Generate Reports From Existing Logs Only

If a run already completed and you only want to regenerate artifacts from
existing JSONL metrics:

```powershell
python monitor_protocol_performance.py `
  --split-type iid `
  --task-id task_iid_5c_clean_0 `
  --num-clients 5 `
  --generate-only
```

This skips live backend polling and rebuilds the CSV/JSON/Markdown/LaTeX/plots
from available metric logs.

## 12. Using Results In The IEEE Paper

Use these generated artifacts directly:

- Main result tables: `tables/*.tex`
- Learning curves: `accuracy_vs_round.png`, `loss_vs_round.png`
- Robustness plots: `asr_vs_attack_ratio.png`, `accuracy_vs_attack_ratio.png`
- Blockchain overhead: `gas_usage_vs_round.png`, `blockchain_latency_distribution.png`
- Communication overhead: `communication_cost_vs_round.png`
- Fairness: `client_fairness_distribution.png`, `table_fairness.tex`
- Summary text: `experiment_report.md`

For every paper table, record:

- Task ID
- Split type
- Client count
- Attack type and ratio
- Dataset split folder
- Commit/version of code used
- Generated report directory

This makes every reported number traceable to a specific run.

## 13. Legacy Baseline Reporting

Older benchmark scripts are still available:

```powershell
python run_real_analysis.py
```

This older workflow extracts task metrics for previously selected tasks and
generates baseline benchmark reports under:

```text
results/
experimentation_results/reports/
```

Use the upgraded `monitor_protocol_performance.py` workflow for the IEEE
experimentation and results section. Use `run_real_analysis.py` only when you
need the older baseline/demo report format.

## 14. Troubleshooting

Backend or DB not reachable:

- Start the HealChain backend and database before running M1-M7.
- Confirm `--backend-url` matches the backend port, usually `http://localhost:3000`.

RPC not reachable:

- Check Ganache/local chain is running.
- Pass the correct `--rpc-url`.
- If RPC is omitted, gas/cost fields are filled only when services emit them.

Missing metric values:

- Ensure `HEALCHAIN_METRICS_DIR` is set in every service terminal.
- Restart FL client and aggregator after setting the variable.
- Start the monitor before M1 to capture the full timeline.
- Add explicit helper calls for metrics that are not emitted by the current services.
- For classification metrics, emit TP/TN/FP/FN, a 2x2 `confusion_matrix`, or
  `y_true`/`y_pred` vectors during M4 evaluation.
- For blockchain gas/cost metrics, pass a working `--rpc-url` or emit gas and
  transaction status fields directly.
- For throughput, always pass `--num-clients`.

Multiple miners reading the same data:

- The current FL client loader reads `fl_client\local_data\chestxray`.
- Use separate working copies or update the loader/config before running many
  miners concurrently from one checkout.

No GPU metrics:

- Install `pynvml` and NVIDIA drivers if GPU metrics are required.
- CPU/RAM/disk monitoring works without GPU support.

Markdown or encoding artifacts in old reports:

- Regenerate reports using `monitor_protocol_performance.py`.
