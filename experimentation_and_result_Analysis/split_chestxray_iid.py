"""
Create stratified IID client splits for a Chest X-ray training dataset.

Run:
    python split_chestxray_iid.py

The script prompts for:
1. Original training dataset path
2. Number of clients

Output is written beside the original dataset as:
    <original_name>_iid_<n>_clients/client_01
    <original_name>_iid_<n>_clients/client_02
    ...
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_split_utils import (
    discover_dataset,
    make_output_root,
    print_split_report,
    prompt_for_client_count,
    prompt_for_path,
    stratified_iid_split,
    write_client_datasets,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a Chest X-ray dataset into stratified IID client datasets."
    )
    parser.add_argument("--dataset", type=Path, help="Path to the original training dataset")
    parser.add_argument("--clients", type=int, help="Number of clients to create")
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed")
    parser.add_argument("--output-dir", type=Path, help="Optional output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_path = args.dataset.expanduser().resolve() if args.dataset else prompt_for_path(
        "Enter original training dataset path: "
    )
    if not source_path.exists() or not source_path.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {source_path}")

    num_clients = args.clients if args.clients is not None else prompt_for_client_count(
        "Enter number of clients: "
    )
    if num_clients <= 0:
        raise ValueError("Number of clients must be greater than zero")

    dataset_info = discover_dataset(source_path)
    splits = stratified_iid_split(dataset_info.samples, num_clients, args.seed)
    output_root = make_output_root(source_path, "iid", num_clients, args.output_dir)
    summary_path = write_client_datasets(
        dataset_info=dataset_info,
        splits=splits,
        output_root=output_root,
        split_type="stratified_iid",
        strategy="Per-class shuffle followed by round-robin allocation to clients.",
        seed=args.seed,
    )
    print_split_report(summary_path)


if __name__ == "__main__":
    main()
