"""
Publication-grade HealChain experiment monitor.

Backward-compatible usage:
    python monitor_protocol_performance.py --split-type iid --task-id task_iid_001
    python monitor_protocol_performance.py --split-type non_iid --task-id task_non_iid_001

The monitor can be started before M1 and stopped after M7. It polls the
backend, samples system resources, merges JSONL events written by FL clients
and the aggregator, and generates CSV, JSON, plots, LaTeX tables, and a paper
ready Markdown report.

The module also exposes lightweight integration helpers near the bottom of the
file. Client, aggregator, blockchain, and attack-evaluation code can import
those helpers and append richer metric events without coupling to this monitor.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import shutil
import statistics
import threading
import time
from typing import Any, Iterable, Mapping, Sequence

import requests


TERMINAL_STATUSES = {"REWARDED", "CANCELLED"}
DEFAULT_BACKEND_URL = "http://localhost:3000"
DEFAULT_DATASET_NAME = "ChestXRay"
DEFAULT_ETH_PRICE_USD = 3500.0
DEFAULT_USD_INR = 83.0
CONVERGENCE_DELTA = 0.001
CONVERGENCE_STABLE_ROUNDS = 5


# ---------------------------------------------------------------------------
# Paths and CLI
# ---------------------------------------------------------------------------


def default_metrics_dir() -> Path:
    return Path(__file__).resolve().parent / "monitoring_metrics"


def default_output_dir() -> Path:
    return Path(__file__).resolve().parent / "results" / "monitoring"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Monitor a HealChain IID/non-IID protocol run and generate "
            "publication-quality experiment outputs."
        )
    )
    parser.add_argument("--split-type", choices=["iid", "non_iid"], help="Dataset split type")
    parser.add_argument("--task-id", help="Task ID to monitor")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL, help="Backend API URL")
    parser.add_argument("--poll-seconds", type=float, default=5.0, help="Backend polling interval")
    parser.add_argument("--metrics-dir", type=Path, default=default_metrics_dir(), help="JSONL metrics directory")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir(), help="Report output directory")
    parser.add_argument(
        "--stop-at-terminal",
        action="store_true",
        help="Stop automatically when backend status is REWARDED or CANCELLED",
    )

    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME, help="Dataset name for reports")
    parser.add_argument("--dataset-path", default="", help="Dataset path or split folder used in this run")
    parser.add_argument("--num-clients", type=int, default=None, help="Number of FL clients/miners in this run")
    parser.add_argument("--dirichlet-alpha", type=float, default=None, help="Dirichlet alpha for non-IID runs")
    parser.add_argument(
        "--attack-type",
        default="none",
        choices=["none", "label_flipping", "gradient_poisoning", "byzantine", "mixed"],
        help="Attack scenario label for paper tables and plots",
    )
    parser.add_argument(
        "--attack-ratio",
        type=float,
        default=0.0,
        help="Malicious/byzantine client ratio. Accepts 0.3 or 30 for 30%%.",
    )
    parser.add_argument(
        "--byzantine-ratio",
        type=float,
        default=None,
        help="Optional Byzantine ratio if different from attack ratio.",
    )
    parser.add_argument("--eth-price-usd", type=float, default=DEFAULT_ETH_PRICE_USD, help="ETH/USD price")
    parser.add_argument("--usd-inr", type=float, default=DEFAULT_USD_INR, help="USD/INR conversion rate")
    parser.add_argument(
        "--rpc-url",
        default=os.getenv("RPC_URL", ""),
        help="Optional Ethereum JSON-RPC URL for tx receipt/gas enrichment",
    )
    parser.add_argument(
        "--system-sample-seconds",
        type=float,
        default=2.0,
        help="CPU/RAM/GPU sampling interval",
    )
    parser.add_argument(
        "--experiment-id",
        default="",
        help="Optional stable experiment identifier. Defaults to task_id + timestamp.",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Skip polling and generate outputs from existing JSONL metrics only.",
    )
    return parser.parse_args()


def prompt_if_missing(args: argparse.Namespace) -> argparse.Namespace:
    if not args.split_type:
        while True:
            raw = input("Enter split type (iid/non_iid): ").strip().lower().replace("-", "_")
            if raw in {"iid", "non_iid"}:
                args.split_type = raw
                break
            print("Please enter iid or non_iid.")

    if not args.task_id:
        while True:
            raw = input("Enter taskID to monitor: ").strip()
            if raw:
                args.task_id = raw
                break
            print("Please enter a taskID.")
    return args


def configure_logging(run_dir: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("healchain.monitor")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    if run_dir is not None:
        run_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(run_dir / "monitor.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    split_type: str
    task_id: str
    backend_url: str
    poll_seconds: float
    metrics_dir: Path
    output_dir: Path
    stop_at_terminal: bool = False
    dataset_name: str = DEFAULT_DATASET_NAME
    dataset_path: str = ""
    num_clients: int | None = None
    dirichlet_alpha: float | None = None
    attack_type: str = "none"
    attack_ratio: float = 0.0
    byzantine_ratio: float | None = None
    eth_price_usd: float = DEFAULT_ETH_PRICE_USD
    usd_inr: float = DEFAULT_USD_INR
    rpc_url: str = ""
    system_sample_seconds: float = 2.0
    experiment_id: str = ""
    started_at: str = ""

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "ExperimentConfig":
        started_at = utc_now_iso()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        experiment_id = args.experiment_id or f"{args.task_id}_{timestamp}"
        return cls(
            split_type=args.split_type,
            task_id=args.task_id,
            backend_url=args.backend_url.rstrip("/"),
            poll_seconds=max(1.0, float(args.poll_seconds)),
            metrics_dir=args.metrics_dir.expanduser().resolve(),
            output_dir=args.output_dir.expanduser().resolve(),
            stop_at_terminal=bool(args.stop_at_terminal),
            dataset_name=args.dataset_name,
            dataset_path=args.dataset_path,
            num_clients=args.num_clients,
            dirichlet_alpha=args.dirichlet_alpha,
            attack_type=args.attack_type,
            attack_ratio=normalize_ratio_arg(args.attack_ratio),
            byzantine_ratio=normalize_ratio_arg(args.byzantine_ratio)
            if args.byzantine_ratio is not None
            else None,
            eth_price_usd=float(args.eth_price_usd),
            usd_inr=float(args.usd_inr),
            rpc_url=str(args.rpc_url or "").strip(),
            system_sample_seconds=max(1.0, float(args.system_sample_seconds)),
            experiment_id=experiment_id,
            started_at=started_at,
        )


@dataclass
class RoundMetrics:
    round: int = 1
    timestamp: str = ""
    status: str = ""
    client_count: int | None = None
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1_score: float | None = None
    roc_auc: float | None = None
    pr_auc: float | None = None
    specificity: float | None = None
    sensitivity: float | None = None
    tp: int | None = None
    tn: int | None = None
    fp: int | None = None
    fn: int | None = None
    training_loss: float | None = None
    validation_loss: float | None = None
    test_loss: float | None = None
    convergence_reached: bool = False
    aggregation_time_sec: float | None = None
    training_time_sec: float | None = None
    communication_time_sec: float | None = None
    bytes_uploaded: int | None = None
    bytes_downloaded: int | None = None
    total_mb_transmitted: float | None = None
    compression_ratio: float | None = None
    gradient_norm_mean: float | None = None
    gradient_norm_std: float | None = None
    gradient_norm_min: float | None = None
    gradient_norm_max: float | None = None
    cosine_similarity_mean: float | None = None
    cosine_similarity_std: float | None = None
    cosine_similarity_min: float | None = None
    cosine_similarity_max: float | None = None
    gradient_variance_mean: float | None = None
    gradient_divergence_mean: float | None = None
    update_magnitude: float | None = None
    update_distance_from_global: float | None = None
    parameter_drift: float | None = None


@dataclass
class ClientMetrics:
    round: int = 1
    timestamp: str = ""
    client_id: str = ""
    local_accuracy: float | None = None
    local_loss: float | None = None
    samples_used: int | None = None
    training_time_sec: float | None = None
    pipeline_total_sec: float | None = None
    ndd_fe_encrypt_sec: float | None = None
    signature_sec: float | None = None
    upload_bytes: int | None = None
    download_bytes: int | None = None
    communication_time_sec: float | None = None
    gradient_norm_l2: float | None = None
    cosine_similarity_to_global: float | None = None
    gradient_variance: float | None = None
    gradient_divergence: float | None = None
    update_magnitude: float | None = None
    update_distance_from_global: float | None = None
    parameter_drift: float | None = None
    compression_ratio: float | None = None
    sparsity_percent: float | None = None
    contribution_score: float | None = None
    participation_frequency: float | None = None
    reward_received_eth: float | None = None
    suspicion_score: float | None = None
    trust_score: float | None = None
    is_malicious: bool | None = None
    detected_malicious: bool | None = None
    filtered: bool | None = None


@dataclass
class BlockchainMetric:
    round: int = 1
    timestamp: str = ""
    tx_hash: str = ""
    tx_type: str = ""
    transaction_count: int = 1
    success: bool | None = None
    failed: bool | None = None
    gas_used: int | None = None
    gas_price_wei: int | None = None
    eth_cost: float | None = None
    usd_cost: float | None = None
    inr_cost: float | None = None
    confirmation_time_sec: float | None = None
    block_inclusion_delay: int | None = None
    aggregation_completion_time_sec: float | None = None


@dataclass
class AttackMetric:
    round: int = 1
    timestamp: str = ""
    attack_type: str = "none"
    attack_ratio: float = 0.0
    malicious_clients: int | None = None
    detection_tp: int | None = None
    detection_tn: int | None = None
    detection_fp: int | None = None
    detection_fn: int | None = None
    detection_tpr: float | None = None
    detection_fpr: float | None = None
    detection_precision: float | None = None
    detection_recall: float | None = None
    detection_f1: float | None = None
    poisoned_samples: int | None = None
    poisoned_target_success: int | None = None
    attack_success_rate: float | None = None
    clean_accuracy: float | None = None
    robust_accuracy: float | None = None
    accuracy_drop: float | None = None
    malicious_filtered: int | None = None
    benign_incorrectly_filtered: int | None = None


@dataclass
class SystemMetric:
    timestamp: str = ""
    cpu_avg_percent: float | None = None
    cpu_peak_percent: float | None = None
    ram_used_mb: float | None = None
    ram_percent: float | None = None
    disk_used_mb: float | None = None
    disk_growth_mb: float | None = None
    gpu_utilization_percent: float | None = None
    gpu_memory_used_mb: float | None = None
    gpu_temperature_c: float | None = None


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_ratio_arg(value: float | int | None) -> float:
    if value is None:
        return 0.0
    numeric = float(value)
    if numeric > 1.0:
        return numeric / 100.0
    return max(0.0, numeric)


def safe_get_json(url: str, timeout: float = 10.0) -> tuple[int | None, Any | None, str | None]:
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.status_code, response.json(), None
        return response.status_code, None, response.text[:500]
    except Exception as exc:
        return None, None, str(exc)


def append_jsonl(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(obj), sort_keys=True, default=str) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def payload(event: Mapping[str, Any]) -> dict[str, Any]:
    value = event.get("payload")
    return value if isinstance(value, dict) else {}


def event_type(events: Iterable[Mapping[str, Any]], name: str) -> list[dict[str, Any]]:
    return [dict(e) for e in events if e.get("event_type") == name]


def fnum(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        value = value.strip().replace("%", "")
        if value.lower() in {"nan", "none", "null", "n/a", "na"}:
            return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def fint(value: Any) -> int | None:
    numeric = fnum(value)
    if numeric is None:
        return None
    return int(numeric)


def normalize_rate(value: Any) -> float | None:
    numeric = fnum(value)
    if numeric is None:
        return None
    if abs(numeric) > 10_000:
        return numeric / 1_000_000.0
    if abs(numeric) > 1.0:
        return numeric / 100.0
    return numeric


def normalize_accuracy_percent(value: Any) -> float | None:
    rate = normalize_rate(value)
    if rate is None:
        return None
    return rate * 100.0


def first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "success", "succeeded", "ok", "malicious", "detected", "filtered"}:
        return True
    if text in {"0", "false", "no", "n", "fail", "failed", "error", "reverted", "benign", "clean", "not_detected", "unfiltered"}:
        return False
    return None


def mean_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return statistics.mean(clean) if clean else None


def std_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return 0.0 if clean else None
    return statistics.stdev(clean)


def min_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return min(clean) if clean else None


def max_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    return max(clean) if clean else None


def sum_values(values: Iterable[float | int | None]) -> float:
    return float(sum(v for v in values if v is not None))


def safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return float(numerator) / float(denominator)


def fmt_seconds(value: Any) -> str:
    numeric = fnum(value)
    if numeric is None:
        return "N/A"
    return f"{numeric:.3f} s"


def fmt_rate(value: Any) -> str:
    rate = normalize_rate(value)
    if rate is None:
        return "N/A"
    return f"{rate * 100.0:.2f}%"


def fmt_number(value: Any, digits: int = 4) -> str:
    numeric = fnum(value)
    if numeric is None:
        return "N/A"
    return f"{numeric:.{digits}f}"


def short_addr(value: Any) -> str:
    raw = str(value or "")
    if len(raw) > 14 and raw.startswith("0x"):
        return f"{raw[:8]}...{raw[-6:]}"
    return raw or "N/A"


def dataclass_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        if hasattr(row, "__dataclass_fields__"):
            output.append(asdict(row))
        elif isinstance(row, dict):
            output.append(row)
    return output


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], field_order: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = list(field_order or [])
    seen = set(keys)
    for row in rows:
        for key in row.keys():
            if key not in seen:
                keys.append(key)
                seen.add(key)
    if not keys and field_order:
        keys = list(field_order)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in keys})


def dataclass_field_names(cls: Any) -> list[str]:
    return [field.name for field in fields(cls)]


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(out)


def latest_task_snapshot(snapshots: Iterable[Mapping[str, Any]]) -> dict[str, Any] | None:
    latest = None
    for row in snapshots:
        if isinstance(row.get("task"), dict):
            latest = dict(row["task"])
    return latest


def latest_submissions_snapshot(snapshots: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []
    for row in snapshots:
        if isinstance(row.get("submissions"), list):
            latest = [s for s in row["submissions"] if isinstance(s, dict)]
    return latest


def infer_round(event: Mapping[str, Any] | None = None, p: Mapping[str, Any] | None = None) -> int:
    candidates = []
    if p:
        candidates.extend([p.get("round"), p.get("round_id"), p.get("current_round"), p.get("currentRound")])
    if event:
        candidates.extend([event.get("round"), event.get("round_id")])
    for value in candidates:
        numeric = fint(value)
        if numeric is not None and numeric >= 0:
            return numeric
    return 1


def compute_binary_metrics(
    *,
    tp: int | None,
    tn: int | None,
    fp: int | None,
    fn: int | None,
) -> dict[str, float | None]:
    total = sum(v for v in [tp, tn, fp, fn] if v is not None)
    if total <= 0 or None in {tp, tn, fp, fn}:
        return {
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "specificity": None,
            "sensitivity": None,
        }
    tp_i, tn_i, fp_i, fn_i = int(tp), int(tn), int(fp), int(fn)
    accuracy = safe_div(tp_i + tn_i, total)
    precision = safe_div(tp_i, tp_i + fp_i)
    recall = safe_div(tp_i, tp_i + fn_i)
    specificity = safe_div(tn_i, tn_i + fp_i)
    f1 = None
    if precision is not None and recall is not None and precision + recall > 0:
        f1 = 2.0 * precision * recall / (precision + recall)
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "specificity": specificity,
        "sensitivity": recall,
    }


def compute_detection_metrics(tp: int, tn: int, fp: int, fn: int) -> dict[str, float | None]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and precision + recall > 0:
        f1 = 2.0 * precision * recall / (precision + recall)
    return {
        "detection_tpr": safe_div(tp, tp + fn),
        "detection_fpr": safe_div(fp, fp + tn),
        "detection_precision": precision,
        "detection_recall": recall,
        "detection_f1": f1,
    }


def jain_fairness_index(values: Sequence[float]) -> float | None:
    clean = [float(v) for v in values if v is not None and float(v) >= 0]
    if not clean:
        return None
    numerator = sum(clean) ** 2
    denominator = len(clean) * sum(v * v for v in clean)
    if denominator == 0:
        return None
    return numerator / denominator


def convergence_round(round_rows: Sequence[RoundMetrics]) -> int | None:
    ordered = [r for r in sorted(round_rows, key=lambda x: x.round) if r.accuracy is not None]
    if len(ordered) < CONVERGENCE_STABLE_ROUNDS + 1:
        return None

    moving: list[tuple[int, float]] = []
    for idx, row in enumerate(ordered):
        start = max(0, idx - CONVERGENCE_STABLE_ROUNDS + 1)
        window = [r.accuracy for r in ordered[start : idx + 1] if r.accuracy is not None]
        if window:
            moving.append((row.round, statistics.mean(window)))

    stable_count = 0
    previous: float | None = None
    for round_id, value in moving:
        if previous is not None and abs(value - previous) < CONVERGENCE_DELTA:
            stable_count += 1
            if stable_count >= CONVERGENCE_STABLE_ROUNDS:
                return round_id
        else:
            stable_count = 0
        previous = value
    return None


# ---------------------------------------------------------------------------
# Metrics collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Collect backend snapshots and load JSONL instrumentation events."""

    def __init__(self, config: ExperimentConfig, run_dir: Path, logger: logging.Logger):
        self.config = config
        self.run_dir = run_dir
        self.logger = logger
        self.snapshots_path = run_dir / "monitor_snapshots.jsonl"

    def load_metric_events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        if not self.config.metrics_dir.exists():
            return events

        for path in sorted(self.config.metrics_dir.glob("*.jsonl")):
            for event in read_jsonl(path):
                task_id = event.get("task_id")
                if task_id is None or str(task_id) == str(self.config.task_id):
                    events.append(event)

        events.sort(key=lambda e: float(e.get("timestamp_unix") or 0.0))
        return events

    def poll_backend_once(self) -> dict[str, Any]:
        observed_at = utc_now_iso()
        base_url = self.config.backend_url.rstrip("/")
        endpoints = {
            "task": f"{base_url}/tasks/{self.config.task_id}",
            "submissions": f"{base_url}/aggregator/{self.config.task_id}/submissions",
            "aggregator_status": f"{base_url}/aggregator/{self.config.task_id}/status",
        }
        row: dict[str, Any] = {"observed_at": observed_at}

        with ThreadPoolExecutor(max_workers=len(endpoints)) as pool:
            future_map = {pool.submit(safe_get_json, url): name for name, url in endpoints.items()}
            for future in as_completed(future_map):
                name = future_map[future]
                status_code, data, error = future.result()
                row[f"{name}_status_code"] = status_code
                if data is not None:
                    row[name] = data
                if error:
                    row[f"{name}_error"] = error

        append_jsonl(self.snapshots_path, row)
        return row

    def monitor_loop(self) -> list[dict[str, Any]]:
        self.logger.info("Monitoring task %s (%s)", self.config.task_id, self.config.split_type)
        self.logger.info("Run directory: %s", self.run_dir)
        self.logger.info("Press Ctrl+C to stop and generate the report.")

        last_status = None
        try:
            while True:
                row = self.poll_backend_once()
                task = row.get("task")
                if isinstance(task, dict):
                    status = str(task.get("status") or "UNKNOWN")
                    if status != last_status:
                        self.logger.info("status=%s", status)
                        last_status = status
                    if self.config.stop_at_terminal and status in TERMINAL_STATUSES:
                        self.logger.info("Terminal status reached: %s", status)
                        break
                else:
                    if last_status != "WAITING_FOR_TASK":
                        self.logger.info("waiting for task %s", self.config.task_id)
                        last_status = "WAITING_FOR_TASK"
                time.sleep(self.config.poll_seconds)
        except KeyboardInterrupt:
            self.logger.info("Monitor stopped by user. Generating report.")

        return read_jsonl(self.snapshots_path)


# ---------------------------------------------------------------------------
# System monitor
# ---------------------------------------------------------------------------


class SystemMonitor:
    """Low-overhead background CPU/RAM/disk/GPU sampler."""

    def __init__(self, run_dir: Path, sample_seconds: float, logger: logging.Logger):
        self.run_dir = run_dir
        self.sample_seconds = max(1.0, float(sample_seconds))
        self.logger = logger
        self.output_path = run_dir / "system_metrics.jsonl"
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._initial_disk_used_mb: float | None = None
        self._nvml = None
        self._gpu_handle = None

    def start(self) -> None:
        self._initial_disk_used_mb = self._disk_used_mb()
        self._setup_gpu()
        self._thread = threading.Thread(target=self._sample_loop, name="healchain-system-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.sample_seconds + 2.0)
        self._shutdown_gpu()

    def _setup_gpu(self) -> None:
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            self._nvml = pynvml
            self._gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._nvml = None
            self._gpu_handle = None

    def _shutdown_gpu(self) -> None:
        try:
            if self._nvml is not None:
                self._nvml.nvmlShutdown()
        except Exception:
            pass

    def _sample_loop(self) -> None:
        while not self._stop_event.is_set():
            append_jsonl(self.output_path, asdict(self._sample_once()))
            self._stop_event.wait(self.sample_seconds)

    def _sample_once(self) -> SystemMetric:
        cpu_avg = None
        ram_used_mb = None
        ram_percent = None

        try:
            import psutil  # type: ignore

            cpu_avg = fnum(psutil.cpu_percent(interval=None))
            memory = psutil.virtual_memory()
            ram_used_mb = memory.used / (1024 * 1024)
            ram_percent = fnum(memory.percent)
        except Exception:
            pass

        gpu_util = None
        gpu_memory_mb = None
        gpu_temperature = None
        try:
            if self._nvml is not None and self._gpu_handle is not None:
                util = self._nvml.nvmlDeviceGetUtilizationRates(self._gpu_handle)
                memory = self._nvml.nvmlDeviceGetMemoryInfo(self._gpu_handle)
                gpu_util = fnum(util.gpu)
                gpu_memory_mb = memory.used / (1024 * 1024)
                gpu_temperature = fnum(
                    self._nvml.nvmlDeviceGetTemperature(self._gpu_handle, self._nvml.NVML_TEMPERATURE_GPU)
                )
        except Exception:
            pass

        disk_used = self._disk_used_mb()
        disk_growth = None
        if disk_used is not None and self._initial_disk_used_mb is not None:
            disk_growth = disk_used - self._initial_disk_used_mb

        return SystemMetric(
            timestamp=utc_now_iso(),
            cpu_avg_percent=cpu_avg,
            cpu_peak_percent=cpu_avg,
            ram_used_mb=ram_used_mb,
            ram_percent=ram_percent,
            disk_used_mb=disk_used,
            disk_growth_mb=disk_growth,
            gpu_utilization_percent=gpu_util,
            gpu_memory_used_mb=gpu_memory_mb,
            gpu_temperature_c=gpu_temperature,
        )

    def _disk_used_mb(self) -> float | None:
        try:
            total, used, free = shutil.disk_usage(str(self.run_dir.drive or self.run_dir.anchor or self.run_dir))
            return used / (1024 * 1024)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Blockchain and attack monitors
# ---------------------------------------------------------------------------


class BlockchainMonitor:
    """Parse blockchain events and optionally enrich tx hashes through JSON-RPC."""

    def __init__(self, config: ExperimentConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._current_block: int | None = None

    def build_metrics(
        self,
        snapshots: Sequence[Mapping[str, Any]],
        events: Sequence[Mapping[str, Any]],
    ) -> list[BlockchainMetric]:
        rows: list[BlockchainMetric] = []
        seen_hashes: set[str] = set()

        for event in events:
            event_name = str(event.get("event_type") or "")
            p = payload(event)
            if self._looks_like_blockchain_event(event_name, p):
                row = self._row_from_event(event, p)
                if row.tx_hash:
                    seen_hashes.add(row.tx_hash.lower())
                rows.append(self._enrich_cost(row))

        for key_path, tx_hash in self._find_tx_hashes({"snapshots": list(snapshots)}):
            if tx_hash.lower() in seen_hashes:
                continue
            row = BlockchainMetric(
                round=1,
                timestamp=utc_now_iso(),
                tx_hash=tx_hash,
                tx_type=self._infer_tx_type(key_path),
            )
            rows.append(self._enrich_from_rpc(row))
            seen_hashes.add(tx_hash.lower())

        rows.sort(key=lambda r: (r.round, r.timestamp, r.tx_type, r.tx_hash))
        return rows

    def _looks_like_blockchain_event(self, event_name: str, p: Mapping[str, Any]) -> bool:
        name = event_name.lower()
        if any(token in name for token in ["blockchain", "transaction", "gas", "reward_distribution"]):
            return True
        interesting = {
            "tx_hash",
            "transaction_hash",
            "txHash",
            "gas_used",
            "gasUsed",
            "gas_price_wei",
            "effectiveGasPrice",
            "eth_cost",
            "confirmation_time_sec",
        }
        return any(key in p for key in interesting)

    def _row_from_event(self, event: Mapping[str, Any], p: Mapping[str, Any]) -> BlockchainMetric:
        tx_hash = str(first_present(p, ["tx_hash", "transaction_hash", "txHash", "hash"]) or "")
        gas_used = self._int_like(first_present(p, ["gas_used", "gasUsed", "gas"]))
        gas_price_wei = self._int_like(first_present(p, ["gas_price_wei", "effectiveGasPrice", "gasPrice"]))
        success = bool_or_none(first_present(p, ["success", "status", "tx_success"]))
        row = BlockchainMetric(
            round=infer_round(event, p),
            timestamp=str(event.get("timestamp_iso") or p.get("timestamp") or ""),
            tx_hash=tx_hash,
            tx_type=str(first_present(p, ["tx_type", "transaction_type", "operation"]) or event.get("event_type") or ""),
            transaction_count=fint(first_present(p, ["transaction_count", "tx_count"])) or 1,
            success=success,
            failed=(not success) if success is not None else bool_or_none(p.get("failed")),
            gas_used=gas_used,
            gas_price_wei=gas_price_wei,
            eth_cost=fnum(p.get("eth_cost")),
            usd_cost=fnum(p.get("usd_cost")),
            inr_cost=fnum(p.get("inr_cost")),
            confirmation_time_sec=fnum(first_present(p, ["confirmation_time_sec", "latency_sec", "duration_sec"])),
            block_inclusion_delay=fint(first_present(p, ["block_inclusion_delay", "block_delay"])),
            aggregation_completion_time_sec=fnum(first_present(p, ["aggregation_completion_time_sec", "aggregation_latency_sec"])),
        )
        if row.tx_hash and (row.gas_used is None or row.gas_price_wei is None) and self.config.rpc_url:
            row = self._enrich_from_rpc(row)
        return self._enrich_cost(row)

    def _enrich_cost(self, row: BlockchainMetric) -> BlockchainMetric:
        if row.eth_cost is None and row.gas_used is not None and row.gas_price_wei is not None:
            row.eth_cost = (row.gas_used * row.gas_price_wei) / 1e18
        if row.usd_cost is None and row.eth_cost is not None:
            row.usd_cost = row.eth_cost * self.config.eth_price_usd
        if row.inr_cost is None and row.usd_cost is not None:
            row.inr_cost = row.usd_cost * self.config.usd_inr
        if row.failed is None and row.success is not None:
            row.failed = not row.success
        return row

    def _enrich_from_rpc(self, row: BlockchainMetric) -> BlockchainMetric:
        if not self.config.rpc_url or not row.tx_hash:
            return self._enrich_cost(row)
        try:
            receipt = self._rpc("eth_getTransactionReceipt", [row.tx_hash])
            tx = self._rpc("eth_getTransactionByHash", [row.tx_hash])
            if isinstance(receipt, dict):
                row.gas_used = row.gas_used or self._hex_int(receipt.get("gasUsed"))
                row.gas_price_wei = row.gas_price_wei or self._hex_int(receipt.get("effectiveGasPrice"))
                status = self._hex_int(receipt.get("status"))
                if status is not None:
                    row.success = status == 1
                    row.failed = status != 1
                block_number = self._hex_int(receipt.get("blockNumber"))
                if block_number is not None:
                    current = self._get_current_block()
                    if current is not None:
                        row.block_inclusion_delay = max(0, current - block_number)
            if isinstance(tx, dict):
                row.gas_price_wei = row.gas_price_wei or self._hex_int(tx.get("gasPrice"))
        except Exception as exc:
            self.logger.debug("RPC enrichment failed for %s: %s", row.tx_hash, exc)
        return self._enrich_cost(row)

    def _rpc(self, method: str, params: list[Any]) -> Any:
        response = requests.post(
            self.config.rpc_url,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("result")

    def _get_current_block(self) -> int | None:
        if self._current_block is not None:
            return self._current_block
        result = self._rpc("eth_blockNumber", [])
        self._current_block = self._hex_int(result)
        return self._current_block

    @staticmethod
    def _hex_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        text = str(value)
        try:
            return int(text, 16) if text.startswith("0x") else int(text)
        except ValueError:
            return None

    @classmethod
    def _int_like(cls, value: Any) -> int | None:
        parsed = cls._hex_int(value)
        return parsed if parsed is not None else fint(value)

    def _find_tx_hashes(self, obj: Any, path: str = "") -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                child_path = f"{path}.{key}" if path else str(key)
                if isinstance(value, str) and self._is_tx_key(key) and self._looks_like_hash(value):
                    found.append((child_path, value))
                else:
                    found.extend(self._find_tx_hashes(value, child_path))
        elif isinstance(obj, list):
            for idx, value in enumerate(obj):
                found.extend(self._find_tx_hashes(value, f"{path}[{idx}]"))
        return found

    @staticmethod
    def _is_tx_key(key: str) -> bool:
        key_l = key.lower()
        return "tx" in key_l or "transaction" in key_l

    @staticmethod
    def _looks_like_hash(value: str) -> bool:
        text = value.strip()
        return text.startswith("0x") and len(text) >= 66

    @staticmethod
    def _infer_tx_type(key_path: str) -> str:
        lower = key_path.lower()
        if "reward" in lower or "distribute" in lower:
            return "reward_distribution"
        if "gradient" in lower or "submission" in lower:
            return "gradient_submission"
        if "aggregation" in lower or "candidate" in lower or "publish" in lower:
            return "aggregation_publish"
        if "escrow" in lower or "task" in lower:
            return "task_publish_escrow"
        return "transaction"


class AttackMonitor:
    """Compute byzantine detection and attack-success metrics."""

    def __init__(self, config: ExperimentConfig):
        self.config = config

    def build_metrics(
        self,
        events: Sequence[Mapping[str, Any]],
        client_rows: Sequence[ClientMetrics],
        round_rows: Sequence[RoundMetrics],
    ) -> list[AttackMetric]:
        rows: list[AttackMetric] = []

        for event in events:
            event_name = str(event.get("event_type") or "").lower()
            p = payload(event)
            if self._looks_like_attack_event(event_name, p):
                rows.append(self._row_from_event(event, p))

        detection = self._detection_from_clients(client_rows)
        if detection:
            rows.append(detection)

        if not rows:
            final_accuracy = next((r.accuracy for r in reversed(round_rows) if r.accuracy is not None), None)
            rows.append(
                AttackMetric(
                    round=round_rows[-1].round if round_rows else 1,
                    timestamp=utc_now_iso(),
                    attack_type=self.config.attack_type,
                    attack_ratio=self.config.attack_ratio,
                    clean_accuracy=final_accuracy if self.config.attack_ratio == 0 else None,
                    robust_accuracy=final_accuracy if self.config.attack_ratio > 0 else None,
                )
            )

        rows.sort(key=lambda r: (r.round, r.attack_ratio, r.attack_type))
        return rows

    @staticmethod
    def _looks_like_attack_event(event_name: str, p: Mapping[str, Any]) -> bool:
        if any(token in event_name for token in ["attack", "byzantine", "malicious", "poison"]):
            return True
        return any(
            key in p
            for key in [
                "attack_success_rate",
                "asr",
                "poisoned_samples",
                "malicious_clients",
                "detection_tp",
                "is_malicious",
                "detected_malicious",
            ]
        )

    def _row_from_event(self, event: Mapping[str, Any], p: Mapping[str, Any]) -> AttackMetric:
        tp = fint(first_present(p, ["detection_tp", "tp", "true_positive"]))
        tn = fint(first_present(p, ["detection_tn", "tn", "true_negative"]))
        fp = fint(first_present(p, ["detection_fp", "fp", "false_positive"]))
        fn = fint(first_present(p, ["detection_fn", "fn", "false_negative"]))
        detection = compute_detection_metrics(tp or 0, tn or 0, fp or 0, fn or 0) if any(v is not None for v in [tp, tn, fp, fn]) else {}

        poisoned_samples = fint(first_present(p, ["poisoned_samples", "num_poisoned"]))
        poisoned_success = fint(
            first_present(p, ["poisoned_target_success", "poisoned_success", "target_label_success"])
        )
        asr = normalize_rate(first_present(p, ["attack_success_rate", "asr"]))
        if asr is None and poisoned_samples:
            asr = safe_div(poisoned_success, poisoned_samples)

        clean_accuracy = normalize_rate(first_present(p, ["clean_accuracy", "accuracy_no_attack"]))
        robust_accuracy = normalize_rate(first_present(p, ["robust_accuracy", "accuracy_under_attack"]))
        accuracy_drop = normalize_rate(p.get("accuracy_drop"))
        if accuracy_drop is None and clean_accuracy is not None and robust_accuracy is not None:
            accuracy_drop = clean_accuracy - robust_accuracy

        return AttackMetric(
            round=infer_round(event, p),
            timestamp=str(event.get("timestamp_iso") or p.get("timestamp") or ""),
            attack_type=str(p.get("attack_type") or self.config.attack_type),
            attack_ratio=normalize_ratio_arg(fnum(p.get("attack_ratio")) if p.get("attack_ratio") is not None else self.config.attack_ratio),
            malicious_clients=fint(first_present(p, ["malicious_clients", "byzantine_clients"])),
            detection_tp=tp,
            detection_tn=tn,
            detection_fp=fp,
            detection_fn=fn,
            detection_tpr=detection.get("detection_tpr"),
            detection_fpr=detection.get("detection_fpr"),
            detection_precision=detection.get("detection_precision"),
            detection_recall=detection.get("detection_recall"),
            detection_f1=detection.get("detection_f1"),
            poisoned_samples=poisoned_samples,
            poisoned_target_success=poisoned_success,
            attack_success_rate=asr,
            clean_accuracy=clean_accuracy,
            robust_accuracy=robust_accuracy,
            accuracy_drop=accuracy_drop,
            malicious_filtered=fint(p.get("malicious_filtered")),
            benign_incorrectly_filtered=fint(p.get("benign_incorrectly_filtered")),
        )

    def _detection_from_clients(self, client_rows: Sequence[ClientMetrics]) -> AttackMetric | None:
        comparable = [c for c in client_rows if c.is_malicious is not None and c.detected_malicious is not None]
        if not comparable:
            return None
        tp = sum(1 for c in comparable if c.is_malicious and c.detected_malicious)
        tn = sum(1 for c in comparable if not c.is_malicious and not c.detected_malicious)
        fp = sum(1 for c in comparable if not c.is_malicious and c.detected_malicious)
        fn = sum(1 for c in comparable if c.is_malicious and not c.detected_malicious)
        metrics = compute_detection_metrics(tp, tn, fp, fn)
        return AttackMetric(
            round=max((c.round for c in comparable), default=1),
            timestamp=utc_now_iso(),
            attack_type=self.config.attack_type,
            attack_ratio=self.config.attack_ratio,
            malicious_clients=sum(1 for c in comparable if c.is_malicious),
            detection_tp=tp,
            detection_tn=tn,
            detection_fp=fp,
            detection_fn=fn,
            detection_tpr=metrics["detection_tpr"],
            detection_fpr=metrics["detection_fpr"],
            detection_precision=metrics["detection_precision"],
            detection_recall=metrics["detection_recall"],
            detection_f1=metrics["detection_f1"],
            malicious_filtered=sum(1 for c in comparable if c.is_malicious and c.filtered),
            benign_incorrectly_filtered=sum(1 for c in comparable if (not c.is_malicious) and c.filtered),
        )


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------


class ExperimentReporter:
    """Aggregate raw evidence and write paper-ready artifacts."""

    def __init__(self, config: ExperimentConfig, run_dir: Path, logger: logging.Logger):
        self.config = config
        self.run_dir = run_dir
        self.logger = logger
        self.tables_dir = run_dir / "tables"
        self.plots_dir = config.output_dir.parent / "plots" / config.split_type / run_dir.name

    def generate(
        self,
        *,
        snapshots: Sequence[Mapping[str, Any]],
        events: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        client_rows = self.build_client_metrics(events, snapshots)
        round_rows = self.build_round_metrics(events, snapshots, client_rows)
        blockchain_rows = BlockchainMonitor(self.config, self.logger).build_metrics(snapshots, events)
        attack_rows = AttackMonitor(self.config).build_metrics(events, client_rows, round_rows)
        system_rows = self.build_system_metrics()

        summary = self.build_summary(
            snapshots=snapshots,
            events=events,
            round_rows=round_rows,
            client_rows=client_rows,
            blockchain_rows=blockchain_rows,
            attack_rows=attack_rows,
            system_rows=system_rows,
        )

        self.write_outputs(
            summary=summary,
            round_rows=round_rows,
            client_rows=client_rows,
            blockchain_rows=blockchain_rows,
            attack_rows=attack_rows,
            system_rows=system_rows,
        )
        return summary

    # ----------------------- builders -----------------------

    def build_client_metrics(
        self,
        events: Sequence[Mapping[str, Any]],
        snapshots: Sequence[Mapping[str, Any]],
    ) -> list[ClientMetrics]:
        by_key: dict[tuple[int, str], ClientMetrics] = {}

        def row_for(round_id: int, client_id: str, timestamp: str = "") -> ClientMetrics:
            key = (round_id, client_id.lower())
            if key not in by_key:
                by_key[key] = ClientMetrics(round=round_id, client_id=client_id, timestamp=timestamp)
            elif timestamp and not by_key[key].timestamp:
                by_key[key].timestamp = timestamp
            return by_key[key]

        for event in events:
            p = payload(event)
            event_name = str(event.get("event_type") or "")
            round_id = infer_round(event, p)
            client_id = str(
                first_present(p, ["client_id", "miner_address", "minerAddress", "address", "participant"])
                or "unknown"
            ).lower()
            timestamp = str(event.get("timestamp_iso") or p.get("timestamp") or "")
            row = row_for(round_id, client_id, timestamp)

            timings = p.get("timings_sec") if isinstance(p.get("timings_sec"), dict) else {}
            local_training = first_present(
                p,
                ["training_time_sec", "local_training_sec", "local_training_time_sec"],
            )
            if local_training is None:
                local_training = timings.get("local_training_sec")

            row.local_accuracy = row.local_accuracy or normalize_rate(
                first_present(p, ["local_accuracy", "accuracy", "train_accuracy"])
            )
            row.local_loss = row.local_loss or fnum(first_present(p, ["local_loss", "loss", "train_loss"]))
            row.samples_used = row.samples_used or fint(first_present(p, ["samples_used", "sample_count", "n_samples"]))
            row.training_time_sec = row.training_time_sec or fnum(local_training)
            row.pipeline_total_sec = row.pipeline_total_sec or fnum(timings.get("training_pipeline_total_sec"))
            row.ndd_fe_encrypt_sec = row.ndd_fe_encrypt_sec or fnum(timings.get("ndd_fe_encrypt_sec"))
            row.signature_sec = row.signature_sec or fnum(
                first_present(p, ["signature_sec", "submission_signature_sec"])
            )
            if row.signature_sec is None:
                row.signature_sec = fnum(timings.get("submission_signature_sec"))

            if event_name == "gradient_submission_communication":
                row.upload_bytes = row.upload_bytes or fint(p.get("request_size_bytes"))
                row.communication_time_sec = row.communication_time_sec or fnum(p.get("duration_sec"))
            elif event_name == "verification_vote":
                row.upload_bytes = (row.upload_bytes or 0) + (fint(p.get("request_size_bytes")) or 0)
                row.communication_time_sec = (row.communication_time_sec or 0.0) + (fnum(p.get("communication_sec")) or 0.0)

            row.upload_bytes = row.upload_bytes or fint(first_present(p, ["upload_bytes", "bytes_uploaded"]))
            row.download_bytes = row.download_bytes or fint(first_present(p, ["download_bytes", "bytes_downloaded"]))
            row.gradient_norm_l2 = row.gradient_norm_l2 or fnum(
                first_present(p, ["gradient_norm_l2", "gradient_norm", "l2_norm"])
            )
            row.cosine_similarity_to_global = row.cosine_similarity_to_global or fnum(
                first_present(p, ["cosine_similarity_to_global", "cosine_similarity", "cosine_to_global"])
            )
            row.gradient_variance = row.gradient_variance or fnum(p.get("gradient_variance"))
            row.gradient_divergence = row.gradient_divergence or fnum(p.get("gradient_divergence"))
            row.update_magnitude = row.update_magnitude or fnum(p.get("update_magnitude"))
            row.update_distance_from_global = row.update_distance_from_global or fnum(p.get("update_distance_from_global"))
            row.parameter_drift = row.parameter_drift or fnum(p.get("parameter_drift"))
            row.compression_ratio = row.compression_ratio or fnum(p.get("compression_ratio"))
            row.sparsity_percent = row.sparsity_percent or fnum(p.get("sparsity_percent"))
            row.contribution_score = row.contribution_score or fnum(
                first_present(p, ["contribution_score", "score"])
            )
            row.participation_frequency = row.participation_frequency or fnum(p.get("participation_frequency"))
            row.reward_received_eth = row.reward_received_eth or fnum(
                first_present(p, ["reward_received_eth", "reward_eth", "reward"])
            )
            row.suspicion_score = row.suspicion_score or fnum(p.get("suspicion_score"))
            row.trust_score = row.trust_score or fnum(p.get("trust_score"))
            row.is_malicious = row.is_malicious if row.is_malicious is not None else bool_or_none(p.get("is_malicious"))
            row.detected_malicious = (
                row.detected_malicious
                if row.detected_malicious is not None
                else bool_or_none(p.get("detected_malicious"))
            )
            row.filtered = row.filtered if row.filtered is not None else bool_or_none(p.get("filtered"))

        self._merge_rewards_from_backend(by_key, snapshots)
        return sorted(by_key.values(), key=lambda r: (r.round, r.client_id))

    def _merge_rewards_from_backend(
        self,
        by_key: dict[tuple[int, str], ClientMetrics],
        snapshots: Sequence[Mapping[str, Any]],
    ) -> None:
        task = latest_task_snapshot(snapshots)
        if not task:
            return
        rewards = task.get("rewards")
        if not isinstance(rewards, list):
            return
        for reward in rewards:
            if not isinstance(reward, dict):
                continue
            client_id = str(
                first_present(reward, ["minerAddress", "miner_address", "client_id", "address"]) or "unknown"
            ).lower()
            key = (1, client_id)
            row = by_key.setdefault(key, ClientMetrics(round=1, client_id=client_id))
            row.reward_received_eth = row.reward_received_eth or fnum(
                first_present(reward, ["amountETH", "amountEth", "rewardETH", "reward"])
            )

    def build_round_metrics(
        self,
        events: Sequence[Mapping[str, Any]],
        snapshots: Sequence[Mapping[str, Any]],
        client_rows: Sequence[ClientMetrics],
    ) -> list[RoundMetrics]:
        by_round: dict[int, RoundMetrics] = {}
        gradient_norms: dict[int, list[float]] = defaultdict(list)
        cosine_values: dict[int, list[float]] = defaultdict(list)
        variances: dict[int, list[float]] = defaultdict(list)
        divergences: dict[int, list[float]] = defaultdict(list)
        compression_ratios: dict[int, list[float]] = defaultdict(list)

        def row_for(round_id: int, timestamp: str = "") -> RoundMetrics:
            if round_id not in by_round:
                by_round[round_id] = RoundMetrics(round=round_id, timestamp=timestamp)
            elif timestamp and not by_round[round_id].timestamp:
                by_round[round_id].timestamp = timestamp
            return by_round[round_id]

        for snapshot in snapshots:
            task = snapshot.get("task")
            if isinstance(task, dict):
                round_id = fint(first_present(task, ["currentRound", "round"])) or 1
                row = row_for(round_id, str(snapshot.get("observed_at") or ""))
                row.status = str(task.get("status") or row.status or "")
                block = task.get("block")
                if isinstance(block, dict) and block.get("accuracy") is not None:
                    row.accuracy = normalize_rate(block.get("accuracy"))

        for event in events:
            p = payload(event)
            event_name = str(event.get("event_type") or "")
            round_id = infer_round(event, p)
            row = row_for(round_id, str(event.get("timestamp_iso") or p.get("timestamp") or ""))

            classification = self._classification_from_payload(p)
            for key, value in classification.items():
                if value is not None and getattr(row, key) is None:
                    setattr(row, key, value)

            if event_name == "model_update_evaluation":
                row.accuracy = normalize_rate(p.get("accuracy")) or row.accuracy
                row.aggregation_time_sec = (row.aggregation_time_sec or 0.0) + (fnum(p.get("duration_sec")) or 0.0)
            elif event_name in {"secure_aggregation_total", "submission_collection"}:
                row.aggregation_time_sec = (row.aggregation_time_sec or 0.0) + (fnum(p.get("duration_sec")) or 0.0)
            elif event_name in {
                "candidate_broadcast_communication",
                "publish_payload_communication",
                "gradient_submission_communication",
                "verification_vote",
            }:
                duration = fnum(first_present(p, ["duration_sec", "communication_sec"]))
                row.communication_time_sec = (row.communication_time_sec or 0.0) + (duration or 0.0)
                request_bytes = fint(first_present(p, ["request_size_bytes", "upload_bytes", "bytes_uploaded"]))
                row.bytes_uploaded = (row.bytes_uploaded or 0) + (request_bytes or 0)

            row.training_loss = row.training_loss or fnum(first_present(p, ["training_loss", "train_loss"]))
            row.validation_loss = row.validation_loss or fnum(first_present(p, ["validation_loss", "val_loss"]))
            row.test_loss = row.test_loss or fnum(p.get("test_loss"))
            row.update_magnitude = row.update_magnitude or fnum(p.get("update_magnitude"))
            row.update_distance_from_global = row.update_distance_from_global or fnum(p.get("update_distance_from_global"))
            row.parameter_drift = row.parameter_drift or fnum(p.get("parameter_drift"))

            for collection, value in [
                (gradient_norms, fnum(first_present(p, ["gradient_norm_l2", "gradient_norm", "l2_norm"]))),
                (cosine_values, fnum(first_present(p, ["cosine_similarity_to_global", "cosine_similarity"]))),
                (variances, fnum(p.get("gradient_variance"))),
                (divergences, fnum(p.get("gradient_divergence"))),
                (compression_ratios, fnum(p.get("compression_ratio"))),
            ]:
                if value is not None:
                    collection[round_id].append(value)

        clients_by_round: dict[int, list[ClientMetrics]] = defaultdict(list)
        for client in client_rows:
            clients_by_round[client.round].append(client)
            if client.gradient_norm_l2 is not None:
                gradient_norms[client.round].append(client.gradient_norm_l2)
            if client.cosine_similarity_to_global is not None:
                cosine_values[client.round].append(client.cosine_similarity_to_global)
            if client.gradient_variance is not None:
                variances[client.round].append(client.gradient_variance)
            if client.gradient_divergence is not None:
                divergences[client.round].append(client.gradient_divergence)
            if client.compression_ratio is not None:
                compression_ratios[client.round].append(client.compression_ratio)

        for round_id, clients in clients_by_round.items():
            row = row_for(round_id)
            row.client_count = len({c.client_id for c in clients if c.client_id})
            row.training_time_sec = max_values(c.training_time_sec for c in clients)
            row.bytes_uploaded = int(sum_values(c.upload_bytes for c in clients)) or row.bytes_uploaded
            row.bytes_downloaded = int(sum_values(c.download_bytes for c in clients)) or row.bytes_downloaded
            total_bytes = (row.bytes_uploaded or 0) + (row.bytes_downloaded or 0)
            row.total_mb_transmitted = total_bytes / (1024 * 1024) if total_bytes else None

        for round_id, row in by_round.items():
            row.gradient_norm_mean = mean_values(gradient_norms[round_id])
            row.gradient_norm_std = std_values(gradient_norms[round_id])
            row.gradient_norm_min = min_values(gradient_norms[round_id])
            row.gradient_norm_max = max_values(gradient_norms[round_id])
            row.cosine_similarity_mean = mean_values(cosine_values[round_id])
            row.cosine_similarity_std = std_values(cosine_values[round_id])
            row.cosine_similarity_min = min_values(cosine_values[round_id])
            row.cosine_similarity_max = max_values(cosine_values[round_id])
            row.gradient_variance_mean = mean_values(variances[round_id])
            row.gradient_divergence_mean = mean_values(divergences[round_id])
            row.compression_ratio = row.compression_ratio or mean_values(compression_ratios[round_id])

        ordered = sorted(by_round.values(), key=lambda r: r.round)
        conv_round = convergence_round(ordered)
        if conv_round is not None:
            for row in ordered:
                row.convergence_reached = row.round >= conv_round
        return ordered

    def _classification_from_payload(self, p: Mapping[str, Any]) -> dict[str, Any]:
        metrics: dict[str, Any] = {
            "accuracy": normalize_rate(first_present(p, ["accuracy", "test_accuracy", "val_accuracy"])),
            "precision": normalize_rate(p.get("precision")),
            "recall": normalize_rate(p.get("recall")),
            "f1_score": normalize_rate(first_present(p, ["f1_score", "f1"])),
            "roc_auc": normalize_rate(first_present(p, ["roc_auc", "auc"])),
            "pr_auc": normalize_rate(first_present(p, ["pr_auc", "average_precision"])),
            "specificity": normalize_rate(p.get("specificity")),
            "sensitivity": normalize_rate(first_present(p, ["sensitivity", "recall"])),
            "tp": fint(first_present(p, ["tp", "true_positive"])),
            "tn": fint(first_present(p, ["tn", "true_negative"])),
            "fp": fint(first_present(p, ["fp", "false_positive"])),
            "fn": fint(first_present(p, ["fn", "false_negative"])),
        }

        confusion = p.get("confusion_matrix")
        if isinstance(confusion, list) and len(confusion) == 2 and all(isinstance(row, list) for row in confusion):
            try:
                metrics["tn"] = int(confusion[0][0])
                metrics["fp"] = int(confusion[0][1])
                metrics["fn"] = int(confusion[1][0])
                metrics["tp"] = int(confusion[1][1])
            except Exception:
                pass

        derived = compute_binary_metrics(
            tp=metrics.get("tp"),
            tn=metrics.get("tn"),
            fp=metrics.get("fp"),
            fn=metrics.get("fn"),
        )
        for key, value in derived.items():
            metrics[key] = metrics.get(key) if metrics.get(key) is not None else value

        sklearn_metrics = self._classification_from_vectors(p)
        for key, value in sklearn_metrics.items():
            metrics[key] = metrics.get(key) if metrics.get(key) is not None else value
        return metrics

    def _classification_from_vectors(self, p: Mapping[str, Any]) -> dict[str, Any]:
        y_true = first_present(p, ["y_true", "labels", "ground_truth"])
        y_pred = first_present(p, ["y_pred", "predictions"])
        y_score = first_present(p, ["y_score", "probabilities", "scores"])
        if not isinstance(y_true, list) or not isinstance(y_pred, list):
            return {}
        try:
            from sklearn.metrics import (  # type: ignore
                accuracy_score,
                average_precision_score,
                confusion_matrix,
                f1_score,
                precision_score,
                recall_score,
                roc_auc_score,
            )

            tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
            out: dict[str, Any] = {
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
                "tp": int(tp),
                "tn": int(tn),
                "fp": int(fp),
                "fn": int(fn),
            }
            if isinstance(y_score, list) and len(y_score) == len(y_true):
                out["roc_auc"] = float(roc_auc_score(y_true, y_score))
                out["pr_auc"] = float(average_precision_score(y_true, y_score))
            return out
        except Exception:
            return {}

    def build_system_metrics(self) -> list[SystemMetric]:
        rows = []
        for row in read_jsonl(self.run_dir / "system_metrics.jsonl"):
            rows.append(
                SystemMetric(
                    timestamp=str(row.get("timestamp") or ""),
                    cpu_avg_percent=fnum(row.get("cpu_avg_percent")),
                    cpu_peak_percent=fnum(row.get("cpu_peak_percent")),
                    ram_used_mb=fnum(row.get("ram_used_mb")),
                    ram_percent=fnum(row.get("ram_percent")),
                    disk_used_mb=fnum(row.get("disk_used_mb")),
                    disk_growth_mb=fnum(row.get("disk_growth_mb")),
                    gpu_utilization_percent=fnum(row.get("gpu_utilization_percent")),
                    gpu_memory_used_mb=fnum(row.get("gpu_memory_used_mb")),
                    gpu_temperature_c=fnum(row.get("gpu_temperature_c")),
                )
            )
        return rows

    def build_summary(
        self,
        *,
        snapshots: Sequence[Mapping[str, Any]],
        events: Sequence[Mapping[str, Any]],
        round_rows: Sequence[RoundMetrics],
        client_rows: Sequence[ClientMetrics],
        blockchain_rows: Sequence[BlockchainMetric],
        attack_rows: Sequence[AttackMetric],
        system_rows: Sequence[SystemMetric],
    ) -> dict[str, Any]:
        task = latest_task_snapshot(snapshots)
        submissions = latest_submissions_snapshot(snapshots)
        status_counts = Counter(
            (row.get("task") or {}).get("status")
            for row in snapshots
            if isinstance(row.get("task"), dict)
        )

        final_round = next((r for r in reversed(round_rows) if r.accuracy is not None), None)
        best_accuracy = max_values(r.accuracy for r in round_rows)
        worst_accuracy = min_values(r.accuracy for r in round_rows)
        conv_round = convergence_round(round_rows)
        final_attack = attack_rows[-1] if attack_rows else AttackMetric()

        training_times = [c.training_time_sec for c in client_rows]
        pipeline_times = [c.pipeline_total_sec for c in client_rows]
        ndd_encrypt_times = [c.ndd_fe_encrypt_sec for c in client_rows]
        signature_times = [c.signature_sec for c in client_rows]
        verification_signature_times = [
            fnum(payload(e).get("signature_sec")) for e in event_type(events, "verification_vote")
        ]
        aggregator_signature_times = [
            fnum(payload(e).get("duration_sec")) for e in event_type(events, "candidate_signature")
        ]

        aggregation_core = sum_values(
            fnum(payload(e).get("duration_sec"))
            for e in events
            if e.get("event_type")
            in {"secure_aggregation_total", "submission_collection", "model_update_evaluation"}
        )
        aggregation_comm = sum_values(
            fnum(payload(e).get("duration_sec"))
            for e in events
            if e.get("event_type")
            in {"candidate_broadcast_communication", "publish_payload_communication"}
        )
        verification_wait = sum_values(
            fnum(payload(e).get("duration_sec")) for e in event_type(events, "verification_wait")
        )
        ndd_decrypt = sum_values(
            fnum(payload(e).get("duration_sec")) for e in event_type(events, "ndd_fe_decrypt")
        )
        bsgs = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "bsgs_recovery"))

        uploaded_bytes = int(sum_values(c.upload_bytes for c in client_rows))
        downloaded_bytes = int(sum_values(c.download_bytes for c in client_rows))
        total_mb = (uploaded_bytes + downloaded_bytes) / (1024 * 1024)

        rewards = [c.reward_received_eth for c in client_rows if c.reward_received_eth is not None]
        contributions = [c.contribution_score for c in client_rows if c.contribution_score is not None]
        participation = [c.participation_frequency for c in client_rows if c.participation_frequency is not None]
        fairness_base = rewards or contributions or participation

        gas_values = [b.gas_used for b in blockchain_rows if b.gas_used is not None]
        tx_success = sum(1 for b in blockchain_rows if b.success is True)
        tx_failed = sum(1 for b in blockchain_rows if b.failed is True)

        cpu_values = [s.cpu_avg_percent for s in system_rows if s.cpu_avg_percent is not None]
        ram_values = [s.ram_used_mb for s in system_rows if s.ram_used_mb is not None]
        gpu_values = [s.gpu_utilization_percent for s in system_rows if s.gpu_utilization_percent is not None]

        final_status = task.get("status") if task else "UNKNOWN"
        accuracy_percent = final_round.accuracy * 100.0 if final_round and final_round.accuracy is not None else None

        training_pipeline_total = max_values(pipeline_times)
        aggregation_including_comm = aggregation_core + aggregation_comm + verification_wait
        throughput = None
        if self.config.num_clients and training_pipeline_total and training_pipeline_total > 0:
            throughput = self.config.num_clients / training_pipeline_total

        summary: dict[str, Any] = {
            "experiment_id": self.config.experiment_id,
            "split_type": self.config.split_type,
            "task_id": self.config.task_id,
            "backend_url": self.config.backend_url,
            "metrics_dir": str(self.config.metrics_dir),
            "run_dir": str(self.run_dir),
            "generated_at": utc_now_iso(),
            "started_at": self.config.started_at,
            "final_status": final_status,
            "overall_accuracy_percent": accuracy_percent,
            "snapshot_count": len(snapshots),
            "metric_event_count": len(events),
            "status_observations": dict(status_counts),
            "dataset": {
                "name": self.config.dataset_name,
                "path": self.config.dataset_path or "N/A",
                "task": "Binary Chest X-Ray classification",
                "classes": ["NORMAL", "PNEUMONIA"],
                "distribution": self.config.split_type,
                "dirichlet_alpha": self.config.dirichlet_alpha,
                "client_count": self.config.num_clients or len({c.client_id for c in client_rows if c.client_id}),
            },
            "attack_setting": {
                "attack_type": self.config.attack_type,
                "attack_ratio": self.config.attack_ratio,
                "byzantine_ratio": self.config.byzantine_ratio
                if self.config.byzantine_ratio is not None
                else self.config.attack_ratio,
            },
            "classification": {
                "final_accuracy": final_round.accuracy if final_round else None,
                "best_accuracy": best_accuracy,
                "worst_accuracy": worst_accuracy,
                "precision": final_round.precision if final_round else None,
                "recall": final_round.recall if final_round else None,
                "f1_score": final_round.f1_score if final_round else None,
                "roc_auc": final_round.roc_auc if final_round else None,
                "pr_auc": final_round.pr_auc if final_round else None,
                "specificity": final_round.specificity if final_round else None,
                "sensitivity": final_round.sensitivity if final_round else None,
                "tp": final_round.tp if final_round else None,
                "tn": final_round.tn if final_round else None,
                "fp": final_round.fp if final_round else None,
                "fn": final_round.fn if final_round else None,
                "convergence_round": conv_round,
            },
            "training": {
                "miner_count_with_metrics": len({c.client_id for c in client_rows if c.client_id}),
                "mean_local_training_sec": mean_values(training_times),
                "max_local_training_sec": max_values(training_times),
                "sum_local_training_sec": sum_values(training_times),
                "mean_pipeline_total_sec": mean_values(pipeline_times),
                "max_pipeline_total_sec": max_values(pipeline_times),
                "sum_pipeline_total_sec": sum_values(pipeline_times),
                "sum_gradient_submission_comm_sec": sum_values(c.communication_time_sec for c in client_rows),
                "mean_gradient_submission_comm_sec": mean_values(c.communication_time_sec for c in client_rows),
                "rows": dataclass_rows(client_rows),
            },
            "aggregation": {
                "aggregation_core_sec": aggregation_core,
                "candidate_publish_comm_sec": aggregation_comm,
                "verification_wait_sec": verification_wait,
                "aggregation_including_comm_sec": aggregation_including_comm,
            },
            "ndd_fe": {
                "sum_encrypt_sec": sum_values(ndd_encrypt_times),
                "mean_encrypt_sec": mean_values(ndd_encrypt_times),
                "max_encrypt_sec": max_values(ndd_encrypt_times),
                "decrypt_sec": ndd_decrypt,
                "bsgs_recovery_sec": bsgs,
                "encrypt_plus_decrypt_sec": sum_values(ndd_encrypt_times) + ndd_decrypt,
            },
            "digital_signature": {
                "submission_signature_sec": sum_values(signature_times),
                "feedback_signature_sec": sum_values(verification_signature_times),
                "aggregator_candidate_signature_sec": sum_values(aggregator_signature_times),
                "total_signature_sec": sum_values(signature_times)
                + sum_values(verification_signature_times)
                + sum_values(aggregator_signature_times),
            },
            "communication": {
                "bytes_uploaded": uploaded_bytes,
                "bytes_downloaded": downloaded_bytes,
                "total_mb_transmitted": total_mb,
                "average_mb_per_round": safe_div(total_mb, len(round_rows)),
                "average_mb_per_client": safe_div(total_mb, len(client_rows)),
            },
            "blockchain": {
                "transaction_count": sum(b.transaction_count for b in blockchain_rows),
                "successful_transactions": tx_success,
                "failed_transactions": tx_failed,
                "average_gas_used": mean_values(gas_values),
                "min_gas_used": min_values(gas_values),
                "max_gas_used": max_values(gas_values),
                "std_gas_used": std_values(gas_values),
                "total_eth_cost": sum_values(b.eth_cost for b in blockchain_rows),
                "total_usd_cost": sum_values(b.usd_cost for b in blockchain_rows),
                "total_inr_cost": sum_values(b.inr_cost for b in blockchain_rows),
                "mean_confirmation_time_sec": mean_values(b.confirmation_time_sec for b in blockchain_rows),
                "mean_block_inclusion_delay": mean_values(b.block_inclusion_delay for b in blockchain_rows),
            },
            "attack": asdict(final_attack),
            "system": {
                "average_cpu_percent": mean_values(cpu_values),
                "peak_cpu_percent": max_values(cpu_values),
                "average_ram_mb": mean_values(ram_values),
                "peak_ram_mb": max_values(ram_values),
                "disk_growth_mb": max_values(s.disk_growth_mb for s in system_rows),
                "average_gpu_utilization_percent": mean_values(gpu_values),
                "peak_gpu_utilization_percent": max_values(gpu_values),
                "peak_gpu_memory_mb": max_values(s.gpu_memory_used_mb for s in system_rows),
                "peak_gpu_temperature_c": max_values(s.gpu_temperature_c for s in system_rows),
            },
            "fairness": {
                "jain_fairness_index": jain_fairness_index([float(v) for v in fairness_base]),
                "mean_reward_eth": mean_values(rewards),
                "std_reward_eth": std_values(rewards),
                "mean_contribution_score": mean_values(contributions),
                "mean_participation_frequency": mean_values(participation),
            },
            "scalability": {
                "client_count": self.config.num_clients or len({c.client_id for c in client_rows if c.client_id}),
                "training_time_sec": training_pipeline_total,
                "aggregation_time_sec": aggregation_including_comm,
                "blockchain_latency_sec": mean_values(b.confirmation_time_sec for b in blockchain_rows),
                "throughput_clients_per_sec": throughput,
            },
            "timeline": {
                "task_created_at": task.get("createdAt") if task else None,
                "task_updated_at": task.get("updatedAt") if task else None,
                "first_monitor_snapshot_at": snapshots[0].get("observed_at") if snapshots else None,
                "last_monitor_snapshot_at": snapshots[-1].get("observed_at") if snapshots else None,
                "submission_times": [s.get("submitted_at") for s in submissions if s.get("submitted_at")],
            },
            "data_completeness": {
                "has_round_metrics": bool(round_rows),
                "has_client_metrics": bool(client_rows),
                "has_blockchain_metrics": bool(blockchain_rows),
                "has_attack_metrics": bool(attack_rows),
                "has_system_metrics": bool(system_rows),
                "has_final_accuracy": accuracy_percent is not None,
                "backend_submission_count": len(submissions),
            },
        }
        return summary

    # ----------------------- writers -----------------------

    def write_outputs(
        self,
        *,
        summary: Mapping[str, Any],
        round_rows: Sequence[RoundMetrics],
        client_rows: Sequence[ClientMetrics],
        blockchain_rows: Sequence[BlockchainMetric],
        attack_rows: Sequence[AttackMetric],
        system_rows: Sequence[SystemMetric],
    ) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.tables_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir.mkdir(parents=True, exist_ok=True)

        round_dicts = dataclass_rows(round_rows)
        client_dicts = dataclass_rows(client_rows)
        blockchain_dicts = dataclass_rows(blockchain_rows)
        attack_dicts = dataclass_rows(attack_rows)
        system_dicts = dataclass_rows(system_rows)

        write_csv(self.run_dir / "round_metrics.csv", round_dicts, dataclass_field_names(RoundMetrics))
        write_csv(self.run_dir / "client_metrics.csv", client_dicts, dataclass_field_names(ClientMetrics))
        write_csv(self.run_dir / "blockchain_metrics.csv", blockchain_dicts, dataclass_field_names(BlockchainMetric))
        write_csv(self.run_dir / "attack_metrics.csv", attack_dicts, dataclass_field_names(AttackMetric))
        write_csv(self.run_dir / "system_metrics.csv", system_dicts, dataclass_field_names(SystemMetric))

        summary_json = json.dumps(summary, indent=2, default=str)
        (self.run_dir / "experiment_summary.json").write_text(summary_json, encoding="utf-8")
        (self.run_dir / "metrics_summary.json").write_text(summary_json, encoding="utf-8")

        self.write_latex_tables(summary, round_rows, attack_rows, blockchain_rows, client_rows)
        self.write_plots(summary, round_rows, client_rows, blockchain_rows, attack_rows)
        self.write_markdown_report(summary)
        self.write_integration_examples()

    def write_markdown_report(self, summary: Mapping[str, Any]) -> None:
        classification = summary["classification"]
        training = summary["training"]
        aggregation = summary["aggregation"]
        ndd_fe = summary["ndd_fe"]
        signature = summary["digital_signature"]
        communication = summary["communication"]
        blockchain = summary["blockchain"]
        attack = summary["attack"]
        system = summary["system"]
        fairness = summary["fairness"]
        dataset = summary["dataset"]
        scalability = summary["scalability"]

        content = f"""# HealChain Experiment Report

## Experiment Setup

{markdown_table(
    ["Item", "Value"],
    [
        ["Task ID", f"`{summary['task_id']}`"],
        ["Experiment ID", f"`{summary['experiment_id']}`"],
        ["Dataset", dataset["name"]],
        ["Task", dataset["task"]],
        ["Classes", ", ".join(dataset["classes"])],
        ["Distribution", str(dataset["distribution"]).upper()],
        ["Dirichlet alpha", dataset["dirichlet_alpha"] if dataset["dirichlet_alpha"] is not None else "N/A"],
        ["Number of clients", dataset["client_count"] or "N/A"],
        ["Attack type", summary["attack_setting"]["attack_type"]],
        ["Attack ratio", fmt_rate(summary["attack_setting"]["attack_ratio"])],
        ["Final observed status", summary["final_status"]],
    ],
)}

## Key Results

{markdown_table(
    ["Metric", "Value"],
    [
        ["Best accuracy", fmt_rate(classification["best_accuracy"])],
        ["Worst accuracy", fmt_rate(classification["worst_accuracy"])],
        ["Final accuracy", fmt_rate(classification["final_accuracy"])],
        ["Precision", fmt_rate(classification["precision"])],
        ["Recall / sensitivity", fmt_rate(classification["recall"])],
        ["Specificity", fmt_rate(classification["specificity"])],
        ["F1 score", fmt_rate(classification["f1_score"])],
        ["ROC AUC", fmt_number(classification["roc_auc"])],
        ["PR AUC", fmt_number(classification["pr_auc"])],
        ["Convergence round", classification["convergence_round"] or "N/A"],
    ],
)}

## Robustness Under Attack

{markdown_table(
    ["Metric", "Value"],
    [
        ["Attack success rate", fmt_rate(attack.get("attack_success_rate"))],
        ["Clean accuracy", fmt_rate(attack.get("clean_accuracy"))],
        ["Robust accuracy", fmt_rate(attack.get("robust_accuracy"))],
        ["Accuracy drop", fmt_rate(attack.get("accuracy_drop"))],
        ["Detection TPR", fmt_rate(attack.get("detection_tpr"))],
        ["Detection FPR", fmt_rate(attack.get("detection_fpr"))],
        ["Detection F1", fmt_rate(attack.get("detection_f1"))],
        ["Malicious filtered", attack.get("malicious_filtered") if attack.get("malicious_filtered") is not None else "N/A"],
        ["Benign incorrectly filtered", attack.get("benign_incorrectly_filtered") if attack.get("benign_incorrectly_filtered") is not None else "N/A"],
    ],
)}

## Performance And Overheads

{markdown_table(
    ["Metric", "Value"],
    [
        ["Max local training time", fmt_seconds(training["max_local_training_sec"])],
        ["Mean local training time", fmt_seconds(training["mean_local_training_sec"])],
        ["Training pipeline wall proxy", fmt_seconds(training["max_pipeline_total_sec"])],
        ["Aggregation including communication", fmt_seconds(aggregation["aggregation_including_comm_sec"])],
        ["NDD-FE encrypt + decrypt overhead", fmt_seconds(ndd_fe["encrypt_plus_decrypt_sec"])],
        ["Digital signature overhead", fmt_seconds(signature["total_signature_sec"])],
        ["Communication uploaded", f"{communication['bytes_uploaded']} bytes"],
        ["Communication downloaded", f"{communication['bytes_downloaded']} bytes"],
        ["Total communication", f"{communication['total_mb_transmitted']:.4f} MB"],
    ],
)}

## Blockchain Overhead

{markdown_table(
    ["Metric", "Value"],
    [
        ["Transaction count", blockchain["transaction_count"]],
        ["Successful transactions", blockchain["successful_transactions"]],
        ["Failed transactions", blockchain["failed_transactions"]],
        ["Average gas used", fmt_number(blockchain["average_gas_used"], 2)],
        ["Total ETH cost", fmt_number(blockchain["total_eth_cost"], 8)],
        ["Total USD cost", fmt_number(blockchain["total_usd_cost"], 4)],
        ["Total INR cost", fmt_number(blockchain["total_inr_cost"], 2)],
        ["Mean confirmation time", fmt_seconds(blockchain["mean_confirmation_time_sec"])],
        ["Mean block inclusion delay", fmt_number(blockchain["mean_block_inclusion_delay"], 2)],
    ],
)}

## Resource Usage

{markdown_table(
    ["Metric", "Value"],
    [
        ["Average CPU usage", fmt_number(system["average_cpu_percent"], 2) + "%"],
        ["Peak CPU usage", fmt_number(system["peak_cpu_percent"], 2) + "%"],
        ["Average RAM usage", fmt_number(system["average_ram_mb"], 2) + " MB"],
        ["Peak RAM usage", fmt_number(system["peak_ram_mb"], 2) + " MB"],
        ["Disk usage growth", fmt_number(system["disk_growth_mb"], 2) + " MB"],
        ["Average GPU utilization", fmt_number(system["average_gpu_utilization_percent"], 2) + "%"],
        ["Peak GPU memory", fmt_number(system["peak_gpu_memory_mb"], 2) + " MB"],
    ],
)}

## Fairness And Scalability

{markdown_table(
    ["Metric", "Value"],
    [
        ["Jain fairness index", fmt_number(fairness["jain_fairness_index"])],
        ["Mean reward", fmt_number(fairness["mean_reward_eth"], 8) + " ETH"],
        ["Reward std", fmt_number(fairness["std_reward_eth"], 8) + " ETH"],
        ["Scalability clients", scalability["client_count"] or "N/A"],
        ["Throughput", fmt_number(scalability["throughput_clients_per_sec"]) + " clients/s"],
    ],
)}

## Generated Artifacts

- CSV files: `round_metrics.csv`, `client_metrics.csv`, `blockchain_metrics.csv`, `attack_metrics.csv`, `system_metrics.csv`
- JSON summary: `experiment_summary.json`
- LaTeX tables: `tables/`
- Figures: `{self.plots_dir}`

Values shown as `N/A` indicate that the corresponding metric was not emitted by
the running service during this experiment. The included integration examples
show the event payload fields expected by this monitor.
"""
        (self.run_dir / "experiment_report.md").write_text(content, encoding="utf-8")
        legacy_name = f"{self.config.split_type}_{self.config.task_id}_result_analysis.md"
        (self.run_dir / legacy_name).write_text(content, encoding="utf-8")

    def write_latex_tables(
        self,
        summary: Mapping[str, Any],
        round_rows: Sequence[RoundMetrics],
        attack_rows: Sequence[AttackMetric],
        blockchain_rows: Sequence[BlockchainMetric],
        client_rows: Sequence[ClientMetrics],
    ) -> None:
        self._write_tex_table(
            self.tables_dir / "table_accuracy.tex",
            ["Setting", "Clients", "Attack Ratio", "Best Acc.", "Final Acc.", "Precision", "Recall", "F1", "ROC AUC", "Conv. Round"],
            [
                [
                    summary["split_type"].upper(),
                    summary["dataset"]["client_count"] or "N/A",
                    fmt_rate(summary["attack_setting"]["attack_ratio"]),
                    fmt_rate(summary["classification"]["best_accuracy"]),
                    fmt_rate(summary["classification"]["final_accuracy"]),
                    fmt_rate(summary["classification"]["precision"]),
                    fmt_rate(summary["classification"]["recall"]),
                    fmt_rate(summary["classification"]["f1_score"]),
                    fmt_number(summary["classification"]["roc_auc"], 3),
                    summary["classification"]["convergence_round"] or "N/A",
                ]
            ],
            caption="Classification performance of HealChain on ChestXRay.",
            label="tab:accuracy",
        )

        attack = summary["attack"]
        self._write_tex_table(
            self.tables_dir / "table_attack_robustness.tex",
            ["Attack", "Ratio", "ASR", "Clean Acc.", "Robust Acc.", "Drop", "TPR", "FPR", "F1"],
            [
                [
                    attack.get("attack_type", "none"),
                    fmt_rate(attack.get("attack_ratio")),
                    fmt_rate(attack.get("attack_success_rate")),
                    fmt_rate(attack.get("clean_accuracy")),
                    fmt_rate(attack.get("robust_accuracy")),
                    fmt_rate(attack.get("accuracy_drop")),
                    fmt_rate(attack.get("detection_tpr")),
                    fmt_rate(attack.get("detection_fpr")),
                    fmt_rate(attack.get("detection_f1")),
                ]
            ],
            caption="Byzantine and poisoning robustness metrics.",
            label="tab:attack_robustness",
        )

        gas_by_type = self._gas_by_type(blockchain_rows)
        self._write_tex_table(
            self.tables_dir / "table_blockchain_overhead.tex",
            ["Metric", "Value"],
            [
                ["Tx count", summary["blockchain"]["transaction_count"]],
                ["Successful tx", summary["blockchain"]["successful_transactions"]],
                ["Failed tx", summary["blockchain"]["failed_transactions"]],
                ["Avg gradient gas", fmt_number(gas_by_type.get("gradient_submission"), 2)],
                ["Avg aggregation gas", fmt_number(gas_by_type.get("aggregation_publish"), 2)],
                ["Avg reward gas", fmt_number(gas_by_type.get("reward_distribution"), 2)],
                ["Total USD cost", fmt_number(summary["blockchain"]["total_usd_cost"], 4)],
                ["Mean confirmation time", fmt_seconds(summary["blockchain"]["mean_confirmation_time_sec"])],
            ],
            caption="Blockchain transaction overhead.",
            label="tab:blockchain_overhead",
        )

        self._write_tex_table(
            self.tables_dir / "table_scalability.tex",
            ["Clients", "Training Time", "Aggregation Time", "Blockchain Latency", "Throughput"],
            [
                [
                    summary["scalability"]["client_count"] or "N/A",
                    fmt_seconds(summary["scalability"]["training_time_sec"]),
                    fmt_seconds(summary["scalability"]["aggregation_time_sec"]),
                    fmt_seconds(summary["scalability"]["blockchain_latency_sec"]),
                    fmt_number(summary["scalability"]["throughput_clients_per_sec"]),
                ]
            ],
            caption="Scalability metrics across client counts.",
            label="tab:scalability",
        )

        self._write_tex_table(
            self.tables_dir / "table_fairness.tex",
            ["Clients", "Mean Reward", "Reward Std.", "Jain Index", "Mean Contribution"],
            [
                [
                    summary["dataset"]["client_count"] or len(client_rows),
                    fmt_number(summary["fairness"]["mean_reward_eth"], 8),
                    fmt_number(summary["fairness"]["std_reward_eth"], 8),
                    fmt_number(summary["fairness"]["jain_fairness_index"], 4),
                    fmt_number(summary["fairness"]["mean_contribution_score"], 4),
                ]
            ],
            caption="Reward and participation fairness.",
            label="tab:fairness",
        )

    @staticmethod
    def _gas_by_type(blockchain_rows: Sequence[BlockchainMetric]) -> dict[str, float | None]:
        groups: dict[str, list[int]] = defaultdict(list)
        for row in blockchain_rows:
            if row.gas_used is None:
                continue
            tx_type = row.tx_type or "transaction"
            if "gradient" in tx_type:
                groups["gradient_submission"].append(row.gas_used)
            elif "reward" in tx_type:
                groups["reward_distribution"].append(row.gas_used)
            elif "aggreg" in tx_type or "publish" in tx_type or "candidate" in tx_type:
                groups["aggregation_publish"].append(row.gas_used)
            else:
                groups[tx_type].append(row.gas_used)
        return {key: mean_values(values) for key, values in groups.items()}

    @staticmethod
    def _write_tex_table(
        path: Path,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]],
        *,
        caption: str,
        label: str,
    ) -> None:
        def esc(value: Any) -> str:
            text = str(value)
            return (
                text.replace("\\", "\\textbackslash{}")
                .replace("&", "\\&")
                .replace("%", "\\%")
                .replace("_", "\\_")
                .replace("#", "\\#")
            )

        column_spec = "l" * len(headers)
        lines = [
            "\\begin{table}[t]",
            "\\centering",
            f"\\caption{{{esc(caption)}}}",
            f"\\label{{{label}}}",
            f"\\begin{{tabular}}{{{column_spec}}}",
            "\\hline",
            " & ".join(esc(h) for h in headers) + " \\\\",
            "\\hline",
        ]
        for row in rows:
            lines.append(" & ".join(esc(v) for v in row) + " \\\\")
        lines.extend(["\\hline", "\\end{tabular}", "\\end{table}", ""])
        path.write_text("\n".join(lines), encoding="utf-8")

    # ----------------------- plotting -----------------------

    def write_plots(
        self,
        summary: Mapping[str, Any],
        round_rows: Sequence[RoundMetrics],
        client_rows: Sequence[ClientMetrics],
        blockchain_rows: Sequence[BlockchainMetric],
        attack_rows: Sequence[AttackMetric],
    ) -> None:
        self._plot_accuracy_vs_round(round_rows)
        self._plot_loss_vs_round(round_rows)
        self._plot_asr_vs_attack_ratio(summary, attack_rows)
        self._plot_accuracy_vs_attack_ratio(summary)
        self._plot_gas_usage_vs_round(blockchain_rows)
        self._plot_communication_cost_vs_round(round_rows)
        self._plot_client_fairness(client_rows)
        self._plot_gradient_similarity_histogram(client_rows)
        self._plot_blockchain_latency_distribution(blockchain_rows)
        self._plot_scalability_curves(summary)
        self._plot_confusion_matrices(round_rows)

    def _setup_plotting(self) -> Any:
        import matplotlib.pyplot as plt  # type: ignore

        try:
            import seaborn as sns  # type: ignore

            sns.set_theme(style="whitegrid", context="paper")
        except Exception:
            plt.style.use("seaborn-v0_8-whitegrid")
        plt.rcParams.update(
            {
                "figure.dpi": 120,
                "savefig.dpi": 300,
                "font.size": 10,
                "axes.labelsize": 10,
                "axes.titlesize": 11,
                "legend.fontsize": 9,
            }
        )
        return plt

    def _placeholder_plot(self, path: Path, title: str, message: str = "No data available") -> None:
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        ax.axis("off")
        ax.text(0.5, 0.55, title, ha="center", va="center", fontsize=12, fontweight="bold")
        ax.text(0.5, 0.42, message, ha="center", va="center", fontsize=10)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_accuracy_vs_round(self, rows: Sequence[RoundMetrics]) -> None:
        path = self.plots_dir / "accuracy_vs_round.png"
        usable = [r for r in rows if r.accuracy is not None]
        if not usable:
            self._placeholder_plot(path, "Accuracy vs Round")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.plot([r.round for r in usable], [r.accuracy * 100 for r in usable], marker="o", linewidth=2)
        ax.set_xlabel("Round")
        ax.set_ylabel("Accuracy (%)")
        ax.set_title("Accuracy vs Round")
        ax.set_ylim(0, 100)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_loss_vs_round(self, rows: Sequence[RoundMetrics]) -> None:
        path = self.plots_dir / "loss_vs_round.png"
        series = [
            ("Training Loss", "training_loss"),
            ("Validation Loss", "validation_loss"),
            ("Test Loss", "test_loss"),
        ]
        if not any(getattr(r, field) is not None for _, field in series for r in rows):
            self._placeholder_plot(path, "Loss vs Round")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        for label, field in series:
            usable = [r for r in rows if getattr(r, field) is not None]
            if usable:
                ax.plot([r.round for r in usable], [getattr(r, field) for r in usable], marker="o", label=label)
        ax.set_xlabel("Round")
        ax.set_ylabel("Loss")
        ax.set_title("Loss vs Round")
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_asr_vs_attack_ratio(self, summary: Mapping[str, Any], attack_rows: Sequence[AttackMetric]) -> None:
        path = self.plots_dir / "asr_vs_attack_ratio.png"
        points = self._peer_attack_points(summary)
        for row in attack_rows:
            if row.attack_success_rate is not None:
                points.append((row.attack_ratio * 100, row.attack_success_rate * 100))
        if not points:
            self._placeholder_plot(path, "ASR vs Attack Ratio")
            return
        points = sorted(set(points))
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.plot([p[0] for p in points], [p[1] for p in points], marker="o", linewidth=2)
        ax.set_xlabel("Attack Ratio (%)")
        ax.set_ylabel("Attack Success Rate (%)")
        ax.set_title("ASR vs Attack Ratio")
        ax.set_ylim(0, 100)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_accuracy_vs_attack_ratio(self, summary: Mapping[str, Any]) -> None:
        path = self.plots_dir / "accuracy_vs_attack_ratio.png"
        points = self._peer_accuracy_attack_points(summary)
        attack = summary["attack"]
        accuracy = attack.get("robust_accuracy") or summary["classification"].get("final_accuracy")
        if accuracy is not None:
            points.append((summary["attack_setting"]["attack_ratio"] * 100, accuracy * 100))
        if not points:
            self._placeholder_plot(path, "Accuracy vs Attack Ratio")
            return
        points = sorted(set(points))
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.plot([p[0] for p in points], [p[1] for p in points], marker="o", linewidth=2)
        ax.set_xlabel("Attack Ratio (%)")
        ax.set_ylabel("Accuracy (%)")
        ax.set_title("Accuracy vs Attack Ratio")
        ax.set_ylim(0, 100)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_gas_usage_vs_round(self, rows: Sequence[BlockchainMetric]) -> None:
        path = self.plots_dir / "gas_usage_vs_round.png"
        usable = [r for r in rows if r.gas_used is not None]
        if not usable:
            self._placeholder_plot(path, "Gas Usage vs Round")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        for tx_type in sorted({r.tx_type or "transaction" for r in usable}):
            typed = [r for r in usable if (r.tx_type or "transaction") == tx_type]
            ax.scatter([r.round for r in typed], [r.gas_used for r in typed], label=tx_type, s=36)
        ax.set_xlabel("Round")
        ax.set_ylabel("Gas Used")
        ax.set_title("Gas Usage vs Round")
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_communication_cost_vs_round(self, rows: Sequence[RoundMetrics]) -> None:
        path = self.plots_dir / "communication_cost_vs_round.png"
        usable = [r for r in rows if r.total_mb_transmitted is not None]
        if not usable:
            self._placeholder_plot(path, "Communication Cost vs Round")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.bar([r.round for r in usable], [r.total_mb_transmitted for r in usable])
        ax.set_xlabel("Round")
        ax.set_ylabel("MB Transmitted")
        ax.set_title("Communication Cost vs Round")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_client_fairness(self, rows: Sequence[ClientMetrics]) -> None:
        path = self.plots_dir / "client_fairness_distribution.png"
        values = [
            (short_addr(r.client_id), r.reward_received_eth if r.reward_received_eth is not None else r.contribution_score)
            for r in rows
            if r.reward_received_eth is not None or r.contribution_score is not None
        ]
        if not values:
            self._placeholder_plot(path, "Client Fairness Distribution")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.bar([v[0] for v in values], [v[1] for v in values])
        ax.set_xlabel("Client")
        ax.set_ylabel("Reward ETH / Contribution Score")
        ax.set_title("Client Fairness Distribution")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_gradient_similarity_histogram(self, rows: Sequence[ClientMetrics]) -> None:
        path = self.plots_dir / "gradient_similarity_histogram.png"
        values = [r.cosine_similarity_to_global for r in rows if r.cosine_similarity_to_global is not None]
        if not values:
            self._placeholder_plot(path, "Gradient Similarity Histogram")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.hist(values, bins=min(20, max(5, len(values))), edgecolor="black")
        ax.set_xlabel("Cosine Similarity to Global Gradient")
        ax.set_ylabel("Client Count")
        ax.set_title("Gradient Similarity Histogram")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_blockchain_latency_distribution(self, rows: Sequence[BlockchainMetric]) -> None:
        path = self.plots_dir / "blockchain_latency_distribution.png"
        values = [
            r.confirmation_time_sec
            for r in rows
            if r.confirmation_time_sec is not None
        ] or [
            r.aggregation_completion_time_sec
            for r in rows
            if r.aggregation_completion_time_sec is not None
        ]
        if not values:
            self._placeholder_plot(path, "Blockchain Latency Distribution")
            return
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.hist(values, bins=min(20, max(5, len(values))), edgecolor="black")
        ax.set_xlabel("Latency (s)")
        ax.set_ylabel("Frequency")
        ax.set_title("Blockchain Latency Distribution")
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_scalability_curves(self, summary: Mapping[str, Any]) -> None:
        path = self.plots_dir / "scalability_curves.png"
        points = self._peer_scalability_points(summary)
        current = summary["scalability"]
        if current.get("client_count"):
            points.append(
                {
                    "clients": current.get("client_count"),
                    "training": current.get("training_time_sec"),
                    "aggregation": current.get("aggregation_time_sec"),
                    "latency": current.get("blockchain_latency_sec"),
                }
            )
        points = [p for p in points if p.get("clients")]
        if not points:
            self._placeholder_plot(path, "Scalability Curves")
            return
        points = sorted(points, key=lambda p: p["clients"])
        plt = self._setup_plotting()
        fig, ax = plt.subplots(figsize=(6, 3.6))
        for label, key in [
            ("Training", "training"),
            ("Aggregation", "aggregation"),
            ("Blockchain Latency", "latency"),
        ]:
            usable = [p for p in points if p.get(key) is not None]
            if usable:
                ax.plot([p["clients"] for p in usable], [p[key] for p in usable], marker="o", label=label)
        ax.set_xlabel("Number of Clients")
        ax.set_ylabel("Time (s)")
        ax.set_title("Scalability Curves")
        ax.legend()
        fig.tight_layout()
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def _plot_confusion_matrices(self, rows: Sequence[RoundMetrics]) -> None:
        usable = [r for r in rows if None not in {r.tp, r.tn, r.fp, r.fn}]
        if not usable:
            self._placeholder_plot(self.plots_dir / "confusion_matrix_unavailable.png", "Confusion Matrix")
            return
        plt = self._setup_plotting()
        try:
            import seaborn as sns  # type: ignore
        except Exception:
            sns = None

        for row in usable:
            matrix = [[row.tn, row.fp], [row.fn, row.tp]]
            fig, ax = plt.subplots(figsize=(4.2, 3.8))
            if sns is not None:
                sns.heatmap(
                    matrix,
                    annot=True,
                    fmt="d",
                    cmap="Blues",
                    xticklabels=["Normal", "Pneumonia"],
                    yticklabels=["Normal", "Pneumonia"],
                    ax=ax,
                )
            else:
                ax.imshow(matrix, cmap="Blues")
                for i in range(2):
                    for j in range(2):
                        ax.text(j, i, str(matrix[i][j]), ha="center", va="center")
                ax.set_xticks([0, 1], ["Normal", "Pneumonia"])
                ax.set_yticks([0, 1], ["Normal", "Pneumonia"])
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")
            ax.set_title(f"Confusion Matrix - Round {row.round}")
            fig.tight_layout()
            fig.savefig(self.plots_dir / f"confusion_matrix_round_{row.round}.png", bbox_inches="tight")
            plt.close(fig)

    # ----------------------- peer summaries -----------------------

    def _peer_summaries(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        root = self.config.output_dir
        if not root.exists():
            return summaries
        for path in root.rglob("experiment_summary.json"):
            if path.resolve() == (self.run_dir / "experiment_summary.json").resolve():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                summaries.append(data)
        return summaries

    def _peer_attack_points(self, summary: Mapping[str, Any]) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for data in self._peer_summaries():
            if data.get("split_type") != summary.get("split_type"):
                continue
            attack = data.get("attack") if isinstance(data.get("attack"), dict) else {}
            asr = normalize_rate(attack.get("attack_success_rate"))
            ratio = normalize_rate((data.get("attack_setting") or {}).get("attack_ratio"))
            if asr is not None and ratio is not None:
                points.append((ratio * 100, asr * 100))
        return points

    def _peer_accuracy_attack_points(self, summary: Mapping[str, Any]) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for data in self._peer_summaries():
            if data.get("split_type") != summary.get("split_type"):
                continue
            attack_setting = data.get("attack_setting") if isinstance(data.get("attack_setting"), dict) else {}
            classification = data.get("classification") if isinstance(data.get("classification"), dict) else {}
            ratio = normalize_rate(attack_setting.get("attack_ratio"))
            accuracy = normalize_rate(classification.get("final_accuracy"))
            if ratio is not None and accuracy is not None:
                points.append((ratio * 100, accuracy * 100))
        return points

    def _peer_scalability_points(self, summary: Mapping[str, Any]) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for data in self._peer_summaries():
            if data.get("split_type") != summary.get("split_type"):
                continue
            scalability = data.get("scalability") if isinstance(data.get("scalability"), dict) else {}
            if scalability.get("client_count"):
                points.append(
                    {
                        "clients": scalability.get("client_count"),
                        "training": scalability.get("training_time_sec"),
                        "aggregation": scalability.get("aggregation_time_sec"),
                        "latency": scalability.get("blockchain_latency_sec"),
                    }
                )
        return points

    def write_integration_examples(self) -> None:
        content = f"""# HealChain Monitor Integration Examples

Use these lightweight hooks when you add richer instrumentation to M1-M7.
All events are JSONL rows in `{self.config.metrics_dir}` and are best-effort.

```python
from experimentation_and_result_Analysis.monitor_protocol_performance import (
    record_client_training_metric,
    record_gradient_submission_metric,
    record_aggregation_metric,
    record_blockchain_transaction_metric,
    record_attack_metric,
)

record_client_training_metric(
    metrics_dir="{self.config.metrics_dir}",
    task_id="{self.config.task_id}",
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
    metrics_dir="{self.config.metrics_dir}",
    task_id="{self.config.task_id}",
    client_id="0xMiner",
    round_id=1,
    bytes_uploaded=1048576,
    bytes_downloaded=2048,
    compression_ratio=0.12,
    duration_sec=1.4,
)

record_aggregation_metric(
    metrics_dir="{self.config.metrics_dir}",
    task_id="{self.config.task_id}",
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
    metrics_dir="{self.config.metrics_dir}",
    task_id="{self.config.task_id}",
    round_id=1,
    tx_hash="0x...",
    tx_type="gradient_submission",
    gas_used=95000,
    gas_price_wei=20_000_000_000,
    success=True,
    confirmation_time_sec=3.2,
)

record_attack_metric(
    metrics_dir="{self.config.metrics_dir}",
    task_id="{self.config.task_id}",
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
"""
        (self.run_dir / "integration_examples.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Backward-compatible analysis functions
# ---------------------------------------------------------------------------


def load_metric_events(metrics_dir: Path, task_id: str) -> list[dict[str, Any]]:
    config = ExperimentConfig(
        split_type="iid",
        task_id=task_id,
        backend_url=DEFAULT_BACKEND_URL,
        poll_seconds=5.0,
        metrics_dir=metrics_dir.expanduser().resolve(),
        output_dir=default_output_dir(),
    )
    logger = logging.getLogger("healchain.monitor.loader")
    return MetricsCollector(config, default_output_dir(), logger).load_metric_events()


def extract_accuracy_percent(task: dict[str, Any] | None, events: list[dict[str, Any]]) -> float | None:
    if task:
        block = task.get("block")
        if isinstance(block, dict) and block.get("accuracy") is not None:
            return normalize_accuracy_percent(block.get("accuracy"))

    for event in reversed(events):
        p = payload(event)
        acc = normalize_accuracy_percent(first_present(p, ["accuracy", "test_accuracy", "val_accuracy"]))
        if acc is not None:
            return acc
    return None


def build_analysis(
    *,
    split_type: str,
    task_id: str,
    backend_url: str,
    metrics_dir: Path,
    run_dir: Path,
    snapshots: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    config = ExperimentConfig(
        split_type=split_type,
        task_id=task_id,
        backend_url=backend_url.rstrip("/"),
        poll_seconds=5.0,
        metrics_dir=metrics_dir.expanduser().resolve(),
        output_dir=run_dir.parent.parent if run_dir.parent.name in {"iid", "non_iid"} else default_output_dir(),
        started_at=utc_now_iso(),
        experiment_id=run_dir.name,
    )
    logger = logging.getLogger("healchain.monitor.analysis")
    reporter = ExperimentReporter(config, run_dir, logger)
    client_rows = reporter.build_client_metrics(events, snapshots)
    round_rows = reporter.build_round_metrics(events, snapshots, client_rows)
    blockchain_rows = BlockchainMonitor(config, logger).build_metrics(snapshots, events)
    attack_rows = AttackMonitor(config).build_metrics(events, client_rows, round_rows)
    system_rows = reporter.build_system_metrics()
    return reporter.build_summary(
        snapshots=snapshots,
        events=events,
        round_rows=round_rows,
        client_rows=client_rows,
        blockchain_rows=blockchain_rows,
        attack_rows=attack_rows,
        system_rows=system_rows,
    )


def write_markdown_report(path: Path, analysis: dict[str, Any]) -> None:
    config = ExperimentConfig(
        split_type=str(analysis.get("split_type") or "iid"),
        task_id=str(analysis.get("task_id") or "unknown"),
        backend_url=str(analysis.get("backend_url") or DEFAULT_BACKEND_URL),
        poll_seconds=5.0,
        metrics_dir=Path(str(analysis.get("metrics_dir") or default_metrics_dir())),
        output_dir=default_output_dir(),
        experiment_id=str(analysis.get("experiment_id") or analysis.get("task_id") or "experiment"),
    )
    reporter = ExperimentReporter(config, path.parent, logging.getLogger("healchain.monitor.markdown"))
    reporter.write_markdown_report(analysis)
    legacy = path.parent / "experiment_report.md"
    if legacy.exists() and legacy.resolve() != path.resolve():
        path.write_text(legacy.read_text(encoding="utf-8"), encoding="utf-8")


def write_outputs(run_dir: Path, analysis: dict[str, Any]) -> tuple[Path, Path]:
    json_path = run_dir / "metrics_summary.json"
    md_path = run_dir / f"{analysis['split_type']}_{analysis['task_id']}_result_analysis.md"
    json_path.write_text(json.dumps(analysis, indent=2, default=str), encoding="utf-8")
    write_markdown_report(md_path, analysis)
    return json_path, md_path


# ---------------------------------------------------------------------------
# Integration helper API
# ---------------------------------------------------------------------------


def record_experiment_event(
    *,
    metrics_dir: str | Path,
    task_id: str,
    component: str,
    event_type: str,
    payload_data: Mapping[str, Any],
) -> Path:
    metrics_path = Path(metrics_dir).expanduser().resolve()
    event = {
        "timestamp_unix": time.time(),
        "timestamp_iso": datetime.now().isoformat(timespec="milliseconds"),
        "component": component,
        "task_id": str(task_id),
        "event_type": event_type,
        "payload": dict(payload_data),
    }
    out_path = metrics_path / f"{component}_metrics.jsonl"
    append_jsonl(out_path, event)
    return out_path


def record_client_training_metric(
    *,
    metrics_dir: str | Path,
    task_id: str,
    client_id: str,
    round_id: int,
    **metrics: Any,
) -> Path:
    payload_data = {"client_id": client_id, "round": round_id, **metrics}
    return record_experiment_event(
        metrics_dir=metrics_dir,
        task_id=task_id,
        component="fl_client",
        event_type="client_training_metrics",
        payload_data=payload_data,
    )


def record_gradient_submission_metric(
    *,
    metrics_dir: str | Path,
    task_id: str,
    client_id: str,
    round_id: int,
    **metrics: Any,
) -> Path:
    payload_data = {"client_id": client_id, "round": round_id, **metrics}
    return record_experiment_event(
        metrics_dir=metrics_dir,
        task_id=task_id,
        component="fl_client",
        event_type="gradient_submission_metrics",
        payload_data=payload_data,
    )


def record_aggregation_metric(
    *,
    metrics_dir: str | Path,
    task_id: str,
    round_id: int,
    **metrics: Any,
) -> Path:
    payload_data = {"round": round_id, **metrics}
    return record_experiment_event(
        metrics_dir=metrics_dir,
        task_id=task_id,
        component="aggregator",
        event_type="round_metrics",
        payload_data=payload_data,
    )


def record_blockchain_transaction_metric(
    *,
    metrics_dir: str | Path,
    task_id: str,
    round_id: int,
    tx_hash: str,
    tx_type: str,
    **metrics: Any,
) -> Path:
    payload_data = {"round": round_id, "tx_hash": tx_hash, "tx_type": tx_type, **metrics}
    return record_experiment_event(
        metrics_dir=metrics_dir,
        task_id=task_id,
        component="blockchain",
        event_type="blockchain_transaction",
        payload_data=payload_data,
    )


def record_attack_metric(
    *,
    metrics_dir: str | Path,
    task_id: str,
    round_id: int,
    attack_type: str,
    attack_ratio: float,
    **metrics: Any,
) -> Path:
    payload_data = {
        "round": round_id,
        "attack_type": attack_type,
        "attack_ratio": attack_ratio,
        **metrics,
    }
    return record_experiment_event(
        metrics_dir=metrics_dir,
        task_id=task_id,
        component="attack",
        event_type="attack_metrics",
        payload_data=payload_data,
    )


# ---------------------------------------------------------------------------
# Main monitor command
# ---------------------------------------------------------------------------


def monitor(args: argparse.Namespace) -> None:
    config = ExperimentConfig.from_args(args)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = config.output_dir / config.split_type / f"{config.task_id}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)

    logger = configure_logging(run_dir)
    collector = MetricsCollector(config, run_dir, logger)
    system_monitor = SystemMonitor(run_dir, config.system_sample_seconds, logger)

    config_payload = asdict(config)
    config_payload["metrics_dir"] = str(config.metrics_dir)
    config_payload["output_dir"] = str(config.output_dir)
    config_payload["run_dir"] = str(run_dir)
    (run_dir / "monitor_config.json").write_text(json.dumps(config_payload, indent=2, default=str), encoding="utf-8")

    if args.generate_only:
        snapshots = read_jsonl(collector.snapshots_path)
    else:
        system_monitor.start()
        try:
            snapshots = collector.monitor_loop()
        finally:
            system_monitor.stop()

    events = collector.load_metric_events()
    reporter = ExperimentReporter(config, run_dir, logger)
    summary = reporter.generate(snapshots=snapshots, events=events)

    logger.info("Metrics summary: %s", run_dir / "experiment_summary.json")
    logger.info("Markdown report: %s", run_dir / "experiment_report.md")
    logger.info("Plots: %s", reporter.plots_dir)
    logger.info("Final accuracy: %s", fmt_rate(summary["classification"]["final_accuracy"]))


def main() -> None:
    args = prompt_if_missing(parse_args())
    monitor(args)


if __name__ == "__main__":
    main()
