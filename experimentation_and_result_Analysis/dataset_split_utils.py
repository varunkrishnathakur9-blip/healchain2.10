"""
Utilities for splitting Chest X-ray training datasets into client datasets.

Supported source layouts:
1. HealChain converted format:
   dataset/
     images/
       sample_0001.npy
     labels.json

2. Class-folder format:
   train/
     NORMAL/
       image_001.jpeg
     PNEUMONIA/
       image_002.jpeg
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import random
import shutil
from typing import Any, DefaultDict, Iterable, List, Sequence


SUPPORTED_IMAGE_EXTENSIONS = {
    ".bmp",
    ".jpeg",
    ".jpg",
    ".npy",
    ".png",
    ".tif",
    ".tiff",
}


@dataclass(frozen=True)
class DatasetSample:
    source_path: Path
    target_relative_path: Path
    label_key: str
    label_value: Any
    label_json_key: str | None = None


@dataclass(frozen=True)
class DatasetInfo:
    source_path: Path
    format_name: str
    samples: List[DatasetSample]


def prompt_for_path(prompt: str) -> Path:
    while True:
        raw = input(prompt).strip().strip('"')
        if not raw:
            print("Please enter a dataset path.")
            continue
        path = Path(raw).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            print(f"Dataset directory not found: {path}")
            continue
        return path


def prompt_for_client_count(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value <= 0:
            print("Number of clients must be greater than zero.")
            continue
        return value


def discover_dataset(source_path: Path) -> DatasetInfo:
    source_path = source_path.resolve()
    project_format = _try_discover_project_format(source_path)
    if project_format is not None:
        return project_format

    class_folder_format = _try_discover_class_folder_format(source_path)
    if class_folder_format is not None:
        return class_folder_format

    raise ValueError(
        "Could not recognize dataset layout. Expected either "
        "'images/ + labels.json' or class subfolders like NORMAL/PNEUMONIA."
    )


def stratified_iid_split(
    samples: Sequence[DatasetSample],
    num_clients: int,
    seed: int,
) -> List[List[DatasetSample]]:
    rng = random.Random(seed)
    by_label = _samples_by_label(samples)
    splits: List[List[DatasetSample]] = [[] for _ in range(num_clients)]

    for label in sorted(by_label):
        group = list(by_label[label])
        rng.shuffle(group)
        for idx, sample in enumerate(group):
            splits[idx % num_clients].append(sample)

    _shuffle_each_client(splits, rng)
    return splits


def label_skew_non_iid_split(
    samples: Sequence[DatasetSample],
    num_clients: int,
    seed: int,
    dominant_fraction: float = 0.8,
) -> List[List[DatasetSample]]:
    """
    Produce a deterministic label-skew non-IID split.

    For each label, most samples go to clients whose index is assigned that
    label, and the remaining samples are spread across the other clients. This
    keeps every sample exactly once while making client label distributions
    visibly different.
    """
    if not 0.0 <= dominant_fraction <= 1.0:
        raise ValueError("dominant_fraction must be in [0.0, 1.0]")

    rng = random.Random(seed)
    by_label = _samples_by_label(samples)
    labels = sorted(by_label)
    splits: List[List[DatasetSample]] = [[] for _ in range(num_clients)]

    if len(labels) <= 1 or num_clients == 1:
        return stratified_iid_split(samples, num_clients, seed)

    for label_index, label in enumerate(labels):
        group = list(by_label[label])
        rng.shuffle(group)

        primary_clients = [
            client_idx
            for client_idx in range(num_clients)
            if client_idx % len(labels) == label_index
        ]
        secondary_clients = [
            client_idx
            for client_idx in range(num_clients)
            if client_idx not in primary_clients
        ]

        if not primary_clients:
            primary_clients = list(range(num_clients))
        if not secondary_clients:
            secondary_clients = primary_clients

        dominant_count = int(round(len(group) * dominant_fraction))
        dominant_samples = group[:dominant_count]
        spillover_samples = group[dominant_count:]

        _round_robin_assign(dominant_samples, primary_clients, splits)
        _round_robin_assign(spillover_samples, secondary_clients, splits)

    _shuffle_each_client(splits, rng)
    return splits


def make_output_root(
    source_path: Path,
    split_name: str,
    num_clients: int,
    output_dir: Path | None = None,
) -> Path:
    if output_dir is not None:
        base = output_dir.expanduser().resolve()
    else:
        base = source_path.parent / f"{source_path.name}_{split_name}_{num_clients}_clients"

    if not base.exists():
        return base

    suffix = 2
    while True:
        candidate = base.parent / f"{base.name}_{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def write_client_datasets(
    dataset_info: DatasetInfo,
    splits: Sequence[Sequence[DatasetSample]],
    output_root: Path,
    split_type: str,
    strategy: str,
    seed: int,
) -> Path:
    output_root.mkdir(parents=True, exist_ok=False)

    for client_index, client_samples in enumerate(splits, start=1):
        client_dir = output_root / f"client_{client_index:02d}"
        client_dir.mkdir(parents=True, exist_ok=True)

        labels_for_json: dict[str, Any] = {}
        for sample in client_samples:
            destination = client_dir / sample.target_relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sample.source_path, destination)

            if sample.label_json_key is not None:
                labels_for_json[sample.label_json_key] = sample.label_value

        if dataset_info.format_name == "images_labels_json":
            labels_path = client_dir / "labels.json"
            with labels_path.open("w", encoding="utf-8") as f:
                json.dump(labels_for_json, f, indent=2, sort_keys=True)

    summary_path = output_root / "split_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            build_summary(
                dataset_info=dataset_info,
                splits=splits,
                split_type=split_type,
                strategy=strategy,
                output_root=output_root,
                seed=seed,
            ),
            f,
            indent=2,
        )

    return summary_path


def print_split_report(summary_path: Path) -> None:
    with summary_path.open("r", encoding="utf-8") as f:
        summary = json.load(f)

    print("\nSplit complete.")
    print(f"Output: {summary['output_root']}")
    print(f"Dataset format: {summary['dataset_format']}")
    print(f"Total samples: {summary['total_samples']}")
    print("Original class counts:")
    for label, count in summary["class_counts"].items():
        print(f"  {label}: {count}")
    print("Client class counts:")
    for client in summary["clients"]:
        counts = ", ".join(f"{label}={count}" for label, count in client["class_counts"].items())
        print(f"  {client['client']}: total={client['total_samples']} ({counts})")
    print(f"Summary: {summary_path}")


def build_summary(
    dataset_info: DatasetInfo,
    splits: Sequence[Sequence[DatasetSample]],
    split_type: str,
    strategy: str,
    output_root: Path,
    seed: int,
) -> dict[str, Any]:
    total_counts = Counter(sample.label_key for sample in dataset_info.samples)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_path": str(dataset_info.source_path),
        "output_root": str(output_root),
        "dataset_format": dataset_info.format_name,
        "split_type": split_type,
        "strategy": strategy,
        "seed": seed,
        "num_clients": len(splits),
        "total_samples": len(dataset_info.samples),
        "class_counts": dict(sorted(total_counts.items())),
        "clients": [
            {
                "client": f"client_{client_index:02d}",
                "total_samples": len(client_samples),
                "class_counts": dict(
                    sorted(Counter(sample.label_key for sample in client_samples).items())
                ),
            }
            for client_index, client_samples in enumerate(splits, start=1)
        ],
    }


def _try_discover_project_format(source_path: Path) -> DatasetInfo | None:
    images_dir = source_path / "images"
    labels_path = source_path / "labels.json"
    if not images_dir.is_dir() or not labels_path.is_file():
        return None

    with labels_path.open("r", encoding="utf-8") as f:
        labels = json.load(f)

    samples: List[DatasetSample] = []
    for file_path in sorted(images_dir.iterdir()):
        if not file_path.is_file():
            continue

        label_key = file_path.stem
        if label_key not in labels and file_path.name in labels:
            label_key = file_path.name
        if label_key not in labels:
            raise ValueError(f"Missing label for image file: {file_path.name}")

        label_value = labels[label_key]
        samples.append(
            DatasetSample(
                source_path=file_path,
                target_relative_path=Path("images") / file_path.name,
                label_key=str(label_value),
                label_value=label_value,
                label_json_key=label_key,
            )
        )

    if not samples:
        raise ValueError(f"No files found in {images_dir}")

    return DatasetInfo(
        source_path=source_path,
        format_name="images_labels_json",
        samples=samples,
    )


def _try_discover_class_folder_format(source_path: Path) -> DatasetInfo | None:
    class_dirs = [path for path in sorted(source_path.iterdir()) if path.is_dir()]
    samples: List[DatasetSample] = []

    for class_dir in class_dirs:
        files = [
            file_path
            for file_path in sorted(class_dir.rglob("*"))
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ]
        for file_path in files:
            samples.append(
                DatasetSample(
                    source_path=file_path,
                    target_relative_path=file_path.relative_to(source_path),
                    label_key=class_dir.name,
                    label_value=class_dir.name,
                )
            )

    if not samples:
        return None

    return DatasetInfo(
        source_path=source_path,
        format_name="class_folders",
        samples=samples,
    )


def _samples_by_label(
    samples: Sequence[DatasetSample],
) -> DefaultDict[str, List[DatasetSample]]:
    by_label: DefaultDict[str, List[DatasetSample]] = defaultdict(list)
    for sample in samples:
        by_label[sample.label_key].append(sample)
    return by_label


def _round_robin_assign(
    samples: Iterable[DatasetSample],
    client_indices: Sequence[int],
    splits: List[List[DatasetSample]],
) -> None:
    if not client_indices:
        raise ValueError("client_indices must not be empty")
    for sample_index, sample in enumerate(samples):
        splits[client_indices[sample_index % len(client_indices)]].append(sample)


def _shuffle_each_client(splits: Sequence[List[DatasetSample]], rng: random.Random) -> None:
    for client_samples in splits:
        rng.shuffle(client_samples)
