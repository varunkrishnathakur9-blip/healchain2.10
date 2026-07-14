# HealChain Experiment Report

## Experiment Setup

| Item | Value |
| --- | --- |
| Task ID | `task_iid_5c_clean_0` |
| Experiment ID | `task_iid_5c_clean_0_20260706_201419` |
| Dataset | ChestXRay |
| Task | Binary Chest X-Ray classification |
| Classes | NORMAL, PNEUMONIA |
| Distribution | IID |
| Dirichlet alpha | N/A |
| Number of clients | 5 |
| Attack type | none |
| Attack ratio | 0.00% |
| Final observed status | REWARDED |

## Key Results

| Metric | Value |
| --- | --- |
| Best accuracy | 52.00% |
| Worst accuracy | 52.00% |
| Final accuracy | 52.00% |
| Precision | 100.00% |
| Recall / sensitivity | 4.00% |
| Specificity | 100.00% |
| F1 score | 7.69% |
| ROC AUC | N/A |
| PR AUC | N/A |
| Convergence round | N/A |

## Robustness Under Attack

| Metric | Value |
| --- | --- |
| Attack success rate | N/A |
| Clean accuracy | 52.00% |
| Robust accuracy | N/A |
| Accuracy drop | N/A |
| Detection TPR | N/A |
| Detection FPR | N/A |
| Detection F1 | N/A |
| Malicious filtered | N/A |
| Benign incorrectly filtered | N/A |

## Performance And Overheads

| Metric | Value |
| --- | --- |
| Max local training time | 2609.467 s |
| Mean local training time | 1398.871 s |
| Training pipeline wall proxy | 4396.545 s |
| Aggregation including communication | 7670.963 s |
| NDD-FE encrypt + decrypt overhead | 6941.485 s |
| Digital signature overhead | 13.604 s |
| Communication uploaded | 1263432633 bytes |
| Communication downloaded | 0 bytes |
| Total communication | 1204.9033 MB |

## Blockchain Overhead

| Metric | Value |
| --- | --- |
| Transaction count | 2 |
| Successful transactions | 2 |
| Failed transactions | 0 |
| Average gas used | 339383.00 |
| Total ETH cost | 0.00530692 |
| Total USD cost | 18.5742 |
| Total INR cost | 1541.66 |
| Mean confirmation time | N/A |
| Mean block inclusion delay | 4.50 |

## Resource Usage

| Metric | Value |
| --- | --- |
| Average CPU usage | 60.88% |
| Peak CPU usage | 100.00% |
| Average RAM usage | 7111.80 MB |
| Peak RAM usage | 7635.97 MB |
| Disk usage growth | 38.63 MB |
| Average GPU utilization | N/A% |
| Peak GPU memory | N/A MB |

## Fairness And Scalability

| Metric | Value |
| --- | --- |
| Jain fairness index | 0.9464 |
| Mean reward | 4.00000000 ETH |
| Reward std | 1.06385297 ETH |
| Scalability clients | 5 |
| Throughput | 0.0011 clients/s |

## Generated Artifacts

- CSV files: `round_metrics.csv`, `client_metrics.csv`, `blockchain_metrics.csv`, `attack_metrics.csv`, `system_metrics.csv`
- JSON summary: `experiment_summary.json`
- LaTeX tables: `tables/`
- Figures: `C:\repos\healchain\experimentation_and_result_Analysis\results\plots\iid\task_iid_5c_clean_0_20260706_201419`

Values shown as `N/A` indicate that the corresponding metric was not emitted by
the running service during this experiment. The included integration examples
show the event payload fields expected by this monitor.
