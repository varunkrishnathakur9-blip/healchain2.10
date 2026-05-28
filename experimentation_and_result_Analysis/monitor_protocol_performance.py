"""
Monitor one HealChain protocol run from M1 to M7 and generate a result report.

Run once for IID and once for non-IID:
    python monitor_protocol_performance.py --split-type iid --task-id task_iid_001
    python monitor_protocol_performance.py --split-type non_iid --task-id task_non_iid_001

The monitor polls the backend while the protocol runs and combines those
snapshots with JSONL timing events written by the FL client and aggregator.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import time
from typing import Any, Iterable

import requests


TERMINAL_STATUSES = {"REWARDED", "CANCELLED"}
DEFAULT_BACKEND_URL = "http://localhost:3000"


def default_metrics_dir() -> Path:
    return Path(__file__).resolve().parent / "monitoring_metrics"


def default_output_dir() -> Path:
    return Path(__file__).resolve().parent / "results" / "monitoring"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor a HealChain IID/non-IID protocol run and generate markdown analysis."
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


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_get_json(url: str, timeout: float = 10.0) -> tuple[int | None, Any | None, str | None]:
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.status_code, response.json(), None
        return response.status_code, None, response.text[:500]
    except Exception as exc:
        return None, None, str(exc)


def append_jsonl(path: Path, obj: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, default=str) + "\n")


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
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def load_metric_events(metrics_dir: Path, task_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not metrics_dir.exists():
        return events
    for path in sorted(metrics_dir.glob("*_metrics.jsonl")):
        for event in read_jsonl(path):
            if str(event.get("task_id")) == str(task_id):
                events.append(event)
    events.sort(key=lambda e: float(e.get("timestamp_unix") or 0.0))
    return events


def latest_task_snapshot(snapshots: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    latest = None
    for row in snapshots:
        if isinstance(row.get("task"), dict):
            latest = row["task"]
    return latest


def latest_submissions_snapshot(snapshots: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: list[dict[str, Any]] = []
    for row in snapshots:
        if isinstance(row.get("submissions"), list):
            latest = row["submissions"]
    return latest


def payload(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("payload")
    return value if isinstance(value, dict) else {}


def event_type(events: Iterable[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event_type") == name]


def fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def sum_values(values: Iterable[float | None]) -> float:
    return sum(v for v in values if v is not None)


def mean_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return statistics.mean(clean)


def max_values(values: Iterable[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return max(clean)


def fmt_seconds(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f} s"


def fmt_percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"


def normalize_accuracy_percent(value: Any) -> float | None:
    numeric = fnum(value)
    if numeric is None:
        return None
    if numeric > 1000:
        return numeric / 10_000.0
    if 0.0 <= numeric <= 1.0:
        return numeric * 100.0
    return numeric


def extract_accuracy_percent(task: dict[str, Any] | None, events: list[dict[str, Any]]) -> float | None:
    if task:
        block = task.get("block")
        if isinstance(block, dict) and block.get("accuracy") is not None:
            return normalize_accuracy_percent(block.get("accuracy"))
        if task.get("targetAccuracy") is not None:
            pass

    eval_events = event_type(events, "model_update_evaluation")
    for event in reversed(eval_events):
        acc = payload(event).get("accuracy")
        pct = normalize_accuracy_percent(acc)
        if pct is not None:
            return pct
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
    task = latest_task_snapshot(snapshots)
    submissions = latest_submissions_snapshot(snapshots)

    training_events = event_type(events, "training_pipeline")
    submission_comm_events = event_type(events, "gradient_submission_communication")
    verification_vote_events = event_type(events, "verification_vote")

    training_by_miner: dict[str, dict[str, Any]] = {}
    for event in training_events:
        p = payload(event)
        miner = str(p.get("miner_address") or "unknown").lower()
        timings = p.get("timings_sec") if isinstance(p.get("timings_sec"), dict) else {}
        training_by_miner[miner] = {
            "miner_address": miner,
            "local_training_sec": fnum(timings.get("local_training_sec")),
            "training_pipeline_total_sec": fnum(timings.get("training_pipeline_total_sec")),
            "ndd_fe_encrypt_sec": fnum(timings.get("ndd_fe_encrypt_sec")),
            "submission_signature_sec": fnum(timings.get("submission_signature_sec")),
            "gradient_compress_score_commit_sec": fnum(timings.get("gradient_compress_score_commit_sec")),
            "sparsity_percent": fnum(p.get("sparsity_percent")),
            "total_parameters": p.get("total_parameters"),
            "nonzero_parameters": p.get("nonzero_parameters"),
        }

    for event in submission_comm_events:
        p = payload(event)
        miner = str(p.get("miner_address") or "unknown").lower()
        row = training_by_miner.setdefault(miner, {"miner_address": miner})
        row["gradient_submission_comm_sec"] = fnum(p.get("duration_sec"))
        row["gradient_submission_request_bytes"] = p.get("request_size_bytes")
        row["gradient_submission_success"] = p.get("success")

    training_rows = list(training_by_miner.values())
    training_pipeline_totals = [fnum(r.get("training_pipeline_total_sec")) for r in training_rows]
    local_training_times = [fnum(r.get("local_training_sec")) for r in training_rows]
    submission_comm_times = [fnum(r.get("gradient_submission_comm_sec")) for r in training_rows]

    secure_agg_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "secure_aggregation_total"))
    collection_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "submission_collection"))
    model_update_eval_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "model_update_evaluation"))
    candidate_broadcast_total = sum_values(
        fnum(payload(e).get("duration_sec")) for e in event_type(events, "candidate_broadcast_communication")
    )
    publish_comm_total = sum_values(
        fnum(payload(e).get("duration_sec")) for e in event_type(events, "publish_payload_communication")
    )
    verification_wait_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "verification_wait"))

    ndd_encrypt_times = [fnum(r.get("ndd_fe_encrypt_sec")) for r in training_rows]
    ndd_decrypt_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "ndd_fe_decrypt"))
    bsgs_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "bsgs_recovery"))

    submission_sig_total = sum_values(fnum(r.get("submission_signature_sec")) for r in training_rows)
    feedback_sig_total = sum_values(fnum(payload(e).get("signature_sec")) for e in verification_vote_events)
    aggregator_sig_total = sum_values(fnum(payload(e).get("duration_sec")) for e in event_type(events, "candidate_signature"))

    status_counts = Counter(
        (row.get("task") or {}).get("status")
        for row in snapshots
        if isinstance(row.get("task"), dict)
    )

    created_at = task.get("createdAt") if task else None
    updated_at = task.get("updatedAt") if task else None
    first_snapshot_at = snapshots[0]["observed_at"] if snapshots else None
    last_snapshot_at = snapshots[-1]["observed_at"] if snapshots else None

    accuracy_percent = extract_accuracy_percent(task, events)
    final_status = task.get("status") if task else "UNKNOWN"

    aggregation_including_comm = (
        collection_total
        + secure_agg_total
        + model_update_eval_total
        + candidate_broadcast_total
        + verification_wait_total
        + publish_comm_total
    )

    analysis = {
        "split_type": split_type,
        "task_id": task_id,
        "backend_url": backend_url,
        "metrics_dir": str(metrics_dir),
        "run_dir": str(run_dir),
        "generated_at": utc_now_iso(),
        "final_status": final_status,
        "overall_accuracy_percent": accuracy_percent,
        "snapshot_count": len(snapshots),
        "metric_event_count": len(events),
        "status_observations": dict(status_counts),
        "timeline": {
            "task_created_at": created_at,
            "task_updated_at": updated_at,
            "first_monitor_snapshot_at": first_snapshot_at,
            "last_monitor_snapshot_at": last_snapshot_at,
            "submission_times": [s.get("submitted_at") for s in submissions if s.get("submitted_at")],
        },
        "training": {
            "miner_count_with_metrics": len(training_rows),
            "mean_local_training_sec": mean_values(local_training_times),
            "max_local_training_sec": max_values(local_training_times),
            "sum_local_training_sec": sum_values(local_training_times),
            "mean_pipeline_total_sec": mean_values(training_pipeline_totals),
            "max_pipeline_total_sec": max_values(training_pipeline_totals),
            "sum_pipeline_total_sec": sum_values(training_pipeline_totals),
            "sum_gradient_submission_comm_sec": sum_values(submission_comm_times),
            "mean_gradient_submission_comm_sec": mean_values(submission_comm_times),
            "rows": training_rows,
        },
        "aggregation": {
            "submission_collection_sec": collection_total,
            "secure_aggregation_sec": secure_agg_total,
            "model_update_evaluation_sec": model_update_eval_total,
            "candidate_broadcast_comm_sec": candidate_broadcast_total,
            "verification_wait_sec": verification_wait_total,
            "publish_comm_sec": publish_comm_total,
            "aggregation_including_comm_sec": aggregation_including_comm,
        },
        "ndd_fe": {
            "sum_encrypt_sec": sum_values(ndd_encrypt_times),
            "mean_encrypt_sec": mean_values(ndd_encrypt_times),
            "max_encrypt_sec": max_values(ndd_encrypt_times),
            "decrypt_sec": ndd_decrypt_total,
            "bsgs_recovery_sec": bsgs_total,
            "encrypt_plus_decrypt_sec": sum_values(ndd_encrypt_times) + ndd_decrypt_total,
        },
        "digital_signature": {
            "submission_signature_sec": submission_sig_total,
            "feedback_signature_sec": feedback_sig_total,
            "aggregator_candidate_signature_sec": aggregator_sig_total,
            "total_signature_sec": submission_sig_total + feedback_sig_total + aggregator_sig_total,
        },
        "data_completeness": {
            "has_training_metrics": bool(training_rows),
            "has_aggregator_metrics": any(e.get("component") == "aggregator" for e in events),
            "has_final_accuracy": accuracy_percent is not None,
            "backend_submission_count": len(submissions),
        },
    }
    return analysis


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(out)


def write_markdown_report(path: Path, analysis: dict[str, Any]) -> None:
    training = analysis["training"]
    aggregation = analysis["aggregation"]
    ndd_fe = analysis["ndd_fe"]
    signature = analysis["digital_signature"]
    timeline = analysis["timeline"]
    completeness = analysis["data_completeness"]

    training_rows = []
    for row in training["rows"]:
        training_rows.append(
            [
                short_addr(row.get("miner_address")),
                fmt_seconds(row.get("local_training_sec")),
                fmt_seconds(row.get("training_pipeline_total_sec")),
                fmt_seconds(row.get("ndd_fe_encrypt_sec")),
                fmt_seconds(row.get("submission_signature_sec")),
                fmt_seconds(row.get("gradient_submission_comm_sec")),
                fmt_percent(row.get("sparsity_percent")),
            ]
        )

    if not training_rows:
        training_rows = [["N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"]]

    content = f"""# HealChain Experimentation Result Analysis: {analysis['split_type'].upper()}

**Task ID:** `{analysis['task_id']}`  
**Generated At:** {analysis['generated_at']}  
**Backend URL:** {analysis['backend_url']}  
**Final Observed Status:** {analysis['final_status']}

## Executive Summary

{markdown_table(
    ["Metric", "Value"],
    [
        ["Overall model accuracy", fmt_percent(analysis["overall_accuracy_percent"])],
        ["Max local training time", fmt_seconds(training["max_local_training_sec"])],
        ["Training pipeline wall proxy", fmt_seconds(training["max_pipeline_total_sec"])],
        ["Aggregation including communication", fmt_seconds(aggregation["aggregation_including_comm_sec"])],
        ["NDD-FE encrypt + decrypt overhead", fmt_seconds(ndd_fe["encrypt_plus_decrypt_sec"])],
        ["Digital signature overhead", fmt_seconds(signature["total_signature_sec"])],
    ],
)}

The training pipeline wall proxy uses the maximum miner pipeline duration, which is the right approximation when miners run in parallel. The cumulative training time is also reported below for compute-cost accounting.

## Model Training And Communication

{markdown_table(
    ["Miner", "Local Training", "Pipeline Total", "NDD-FE Encrypt", "Submission Signature", "Submit Communication", "Sparsity"],
    training_rows,
)}

{markdown_table(
    ["Aggregate Training Metric", "Value"],
    [
        ["Mean local training time", fmt_seconds(training["mean_local_training_sec"])],
        ["Max local training time", fmt_seconds(training["max_local_training_sec"])],
        ["Cumulative local training time", fmt_seconds(training["sum_local_training_sec"])],
        ["Mean full miner pipeline time", fmt_seconds(training["mean_pipeline_total_sec"])],
        ["Max full miner pipeline time", fmt_seconds(training["max_pipeline_total_sec"])],
        ["Cumulative full miner pipeline time", fmt_seconds(training["sum_pipeline_total_sec"])],
        ["Cumulative gradient submission communication", fmt_seconds(training["sum_gradient_submission_comm_sec"])],
    ],
)}

## Aggregation And Communication

{markdown_table(
    ["Aggregation Metric", "Value"],
    [
        ["Submission collection and backend fetch wait", fmt_seconds(aggregation["submission_collection_sec"])],
        ["Secure aggregation core", fmt_seconds(aggregation["secure_aggregation_sec"])],
        ["Model update and evaluation", fmt_seconds(aggregation["model_update_evaluation_sec"])],
        ["Candidate broadcast communication", fmt_seconds(aggregation["candidate_broadcast_comm_sec"])],
        ["M5 verification wait", fmt_seconds(aggregation["verification_wait_sec"])],
        ["M6 publish communication", fmt_seconds(aggregation["publish_comm_sec"])],
        ["Total aggregation including communication", fmt_seconds(aggregation["aggregation_including_comm_sec"])],
    ],
)}

## NDD-FE Overhead

{markdown_table(
    ["NDD-FE Metric", "Value"],
    [
        ["Cumulative miner encryption time", fmt_seconds(ndd_fe["sum_encrypt_sec"])],
        ["Mean miner encryption time", fmt_seconds(ndd_fe["mean_encrypt_sec"])],
        ["Max miner encryption time", fmt_seconds(ndd_fe["max_encrypt_sec"])],
        ["Aggregator NDD-FE decrypt time", fmt_seconds(ndd_fe["decrypt_sec"])],
        ["BSGS recovery time", fmt_seconds(ndd_fe["bsgs_recovery_sec"])],
        ["Encryption + decrypt overhead", fmt_seconds(ndd_fe["encrypt_plus_decrypt_sec"])],
    ],
)}

## Digital Signature Overhead

{markdown_table(
    ["Signature Metric", "Value"],
    [
        ["Miner M3 submission signatures", fmt_seconds(signature["submission_signature_sec"])],
        ["Miner M5 feedback signatures", fmt_seconds(signature["feedback_signature_sec"])],
        ["Aggregator candidate signature", fmt_seconds(signature["aggregator_candidate_signature_sec"])],
        ["Total measured signature overhead", fmt_seconds(signature["total_signature_sec"])],
    ],
)}

## Accuracy

Final candidate accuracy observed for this run: **{fmt_percent(analysis["overall_accuracy_percent"])}**.

## Timeline

{markdown_table(
    ["Event", "Timestamp"],
    [
        ["Task created at", timeline["task_created_at"] or "N/A"],
        ["First monitor snapshot", timeline["first_monitor_snapshot_at"] or "N/A"],
        ["Last monitor snapshot", timeline["last_monitor_snapshot_at"] or "N/A"],
        ["Task updated at", timeline["task_updated_at"] or "N/A"],
        ["Submission timestamps", ", ".join(timeline["submission_times"]) if timeline["submission_times"] else "N/A"],
    ],
)}

## Data Completeness Notes

{markdown_table(
    ["Check", "Value"],
    [
        ["Training metrics found", completeness["has_training_metrics"]],
        ["Aggregator metrics found", completeness["has_aggregator_metrics"]],
        ["Final accuracy found", completeness["has_final_accuracy"]],
        ["Backend submission count", completeness["backend_submission_count"]],
        ["Backend snapshots recorded", analysis["snapshot_count"]],
        ["Metric events recorded", analysis["metric_event_count"]],
    ],
)}

If any value is `N/A`, the most common cause is that the monitor was started after that stage or one of the instrumented services was not restarted after adding the probes.
"""
    path.write_text(content, encoding="utf-8")


def short_addr(value: Any) -> str:
    raw = str(value or "")
    if len(raw) > 14 and raw.startswith("0x"):
        return f"{raw[:8]}...{raw[-6:]}"
    return raw or "N/A"


def write_outputs(run_dir: Path, analysis: dict[str, Any]) -> tuple[Path, Path]:
    json_path = run_dir / "metrics_summary.json"
    md_path = run_dir / f"{analysis['split_type']}_{analysis['task_id']}_result_analysis.md"
    json_path.write_text(json.dumps(analysis, indent=2, default=str), encoding="utf-8")
    write_markdown_report(md_path, analysis)
    return json_path, md_path


def monitor(args: argparse.Namespace) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = args.output_dir.expanduser().resolve() / args.split_type / f"{args.task_id}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshots_path = run_dir / "monitor_snapshots.jsonl"

    config = {
        "split_type": args.split_type,
        "task_id": args.task_id,
        "backend_url": args.backend_url,
        "poll_seconds": args.poll_seconds,
        "metrics_dir": str(args.metrics_dir.expanduser().resolve()),
        "started_at": utc_now_iso(),
    }
    (run_dir / "monitor_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    print(f"Monitoring task {args.task_id} ({args.split_type})")
    print(f"Run directory: {run_dir}")
    print("Press Ctrl+C to stop and generate the report.")

    last_status = None
    try:
        while True:
            observed_at = utc_now_iso()
            task_url = f"{args.backend_url.rstrip('/')}/tasks/{args.task_id}"
            status_code, task_data, task_error = safe_get_json(task_url)

            row: dict[str, Any] = {
                "observed_at": observed_at,
                "task_status_code": status_code,
            }

            if isinstance(task_data, dict):
                row["task"] = task_data
                status = str(task_data.get("status") or "UNKNOWN")
                if status != last_status:
                    print(f"[{observed_at}] status={status}")
                    last_status = status

                submissions_url = f"{args.backend_url.rstrip('/')}/aggregator/{args.task_id}/submissions"
                sub_status, submissions, sub_error = safe_get_json(submissions_url)
                row["submissions_status_code"] = sub_status
                if isinstance(submissions, list):
                    row["submissions"] = submissions
                elif sub_error:
                    row["submissions_error"] = sub_error

                append_jsonl(snapshots_path, row)

                if args.stop_at_terminal and status in TERMINAL_STATUSES:
                    print(f"Terminal status reached: {status}")
                    break
            else:
                row["task_error"] = task_error or "Task not available yet"
                append_jsonl(snapshots_path, row)
                if last_status != "WAITING_FOR_TASK":
                    print(f"[{observed_at}] waiting for task {args.task_id}")
                    last_status = "WAITING_FOR_TASK"

            time.sleep(max(1.0, args.poll_seconds))
    except KeyboardInterrupt:
        print("\nMonitor stopped by user. Generating report...")

    snapshots = read_jsonl(snapshots_path)
    events = load_metric_events(args.metrics_dir.expanduser().resolve(), args.task_id)
    analysis = build_analysis(
        split_type=args.split_type,
        task_id=args.task_id,
        backend_url=args.backend_url,
        metrics_dir=args.metrics_dir.expanduser().resolve(),
        run_dir=run_dir,
        snapshots=snapshots,
        events=events,
    )
    json_path, md_path = write_outputs(run_dir, analysis)
    print(f"Metrics summary: {json_path}")
    print(f"Markdown report: {md_path}")


def main() -> None:
    args = prompt_if_missing(parse_args())
    monitor(args)


if __name__ == "__main__":
    main()
