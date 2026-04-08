"""
Run real-data HealChain experimentation analysis for specific tasks.

This runner:
1. Clears previous generated outputs.
2. Extracts real metrics from backend DB + Ganache chain data.
3. Regenerates benchmark markdown + JSON reports.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from benchmark_report_generator import BenchmarkReportGenerator


def _clear_dir_contents(path: Path) -> None:
    """Delete all files/subdirs inside a directory but keep the directory itself."""
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    base = Path(__file__).resolve().parent

    # Output locations used by the experimentation suite.
    clear_targets = [
        base / "results",
        base / "experimentation_results",
    ]
    for target in clear_targets:
        _clear_dir_contents(target)

    print("[*] Cleared output directories:")
    for target in clear_targets:
        print(f"    - {target}")

    generator = BenchmarkReportGenerator(output_dir=base / "results")
    md_file, json_file = generator.create_full_report(
        output_prefix="healchain_benchmark_report",
        include_actual_metrics=True,
        task_ids=["task_037", "task_038"],
    )

    print("\n[+] Real-data benchmark reports generated:")
    print(f"    - Markdown: {md_file}")
    print(f"    - JSON: {json_file}")


if __name__ == "__main__":
    main()

