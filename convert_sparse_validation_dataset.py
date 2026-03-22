#!/usr/bin/env python3
"""
Convert local FL image dataset into Aggregator sparse validation JSONL.

Expected source dataset structure (either direct root or nested under --dataset-type):
  <dataset_root>/
    images/*.npy
    labels.json

Example:
  python convert_sparse_validation_dataset.py ^
    --dataset-root fl_client/local_data/chestxray ^
    --output artifacts/validation/chestxray_sparse_validation.jsonl ^
    --epsilon 1e-6 --top-k 4096

The output JSONL format is compatible with:
  aggregator/src/model/runtime_evaluator.py
which expects each line to include:
  {"label": 0|1, "indices": [...], "values": [...]}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

try:
    from PIL import Image
except Exception as e:  # pragma: no cover
    raise RuntimeError(
        "Pillow is required for conversion (missing PIL). "
        "Install with: pip install pillow"
    ) from e


def _resolve_dataset_dir(dataset_root: Path, dataset_type: str) -> Path:
    direct_images = dataset_root / "images"
    direct_labels = dataset_root / "labels.json"
    if direct_images.exists() and direct_labels.exists():
        return dataset_root

    nested = dataset_root / dataset_type
    nested_images = nested / "images"
    nested_labels = nested / "labels.json"
    if nested_images.exists() and nested_labels.exists():
        return nested

    raise FileNotFoundError(
        f"Could not find dataset structure in '{dataset_root}'. Expected either:\n"
        f"  1) {dataset_root / 'images'} + {dataset_root / 'labels.json'}\n"
        f"  2) {nested_images} + {nested_labels}"
    )


def _resize_single_channel(arr: np.ndarray, size_hw: Tuple[int, int]) -> np.ndarray:
    h, w = size_hw
    img = Image.fromarray(arr.astype(np.float32), mode="F")
    resized = img.resize((w, h), resample=Image.Resampling.BILINEAR)
    return np.asarray(resized, dtype=np.float32)


def _preprocess_like_fl_client(raw: np.ndarray, size_hw: Tuple[int, int]) -> np.ndarray:
    """
    Mirror fl_client/src/dataset/loader.py behavior as closely as possible:
    - If (1, 64, 64), transpose to (64, 64, 1)
    - If (64, 64, 1), repeat to 3 channels
    - Resize to (224, 224, 3) by default
    """
    img = raw.astype(np.float32)

    if img.shape == (1, 64, 64):
        img = np.transpose(img, (1, 2, 0))

    if img.ndim == 2:
        img = img[..., None]

    if img.ndim != 3:
        raise ValueError(f"Unsupported image shape after normalization: {img.shape}")

    if img.shape[2] == 1:
        img = np.repeat(img, 3, axis=2)
    elif img.shape[2] > 3:
        img = img[..., :3]

    channels = []
    for c in range(img.shape[2]):
        channels.append(_resize_single_channel(img[..., c], size_hw))
    resized = np.stack(channels, axis=-1).astype(np.float32)
    return resized


def _to_sparse(
    flat: np.ndarray,
    *,
    epsilon: float,
    top_k: int | None,
    round_digits: int | None,
) -> Tuple[List[int], List[float]]:
    mask = np.abs(flat) > epsilon
    if not np.any(mask):
        return [], []

    indices = np.nonzero(mask)[0]
    values = flat[indices]

    if top_k is not None and top_k > 0 and len(indices) > top_k:
        # Keep largest-magnitude coordinates.
        keep = np.argpartition(np.abs(values), -top_k)[-top_k:]
        indices = indices[keep]
        values = values[keep]

    # Stable ordering by index (helps reproducibility/diffability).
    order = np.argsort(indices)
    indices = indices[order]
    values = values[order]

    if round_digits is not None and round_digits >= 0:
        values = np.round(values, decimals=round_digits)

    return indices.astype(np.int64).tolist(), values.astype(np.float32).tolist()


def _iter_samples(images_dir: Path) -> Iterable[Path]:
    for p in sorted(images_dir.glob("*.npy")):
        if p.is_file():
            yield p


def convert(
    dataset_dir: Path,
    output_path: Path,
    *,
    epsilon: float,
    top_k: int | None,
    max_samples: int | None,
    round_digits: int | None,
    resize_hw: Tuple[int, int],
) -> None:
    labels_path = dataset_dir / "labels.json"
    images_dir = dataset_dir / "images"

    if not labels_path.exists():
        raise FileNotFoundError(f"Missing labels file: {labels_path}")
    if not images_dir.exists():
        raise FileNotFoundError(f"Missing images directory: {images_dir}")

    with labels_path.open("r", encoding="utf-8") as f:
        labels: Dict[str, int] = json.load(f)

    image_files = list(_iter_samples(images_dir))
    if max_samples is not None and max_samples > 0:
        image_files = image_files[:max_samples]

    if not image_files:
        raise ValueError(f"No .npy images found in {images_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    total_nnz = 0

    with output_path.open("w", encoding="utf-8") as out:
        for i, img_path in enumerate(image_files, start=1):
            stem = img_path.stem
            if stem not in labels:
                skipped += 1
                print(f"[WARN] label missing for {stem}; skipping")
                continue

            label = int(labels[stem])
            if label not in (0, 1):
                raise ValueError(f"Label for {stem} must be 0/1, got {label}")

            raw = np.load(img_path).astype(np.float32)
            img = _preprocess_like_fl_client(raw, resize_hw)
            flat = img.reshape(-1)

            indices, values = _to_sparse(
                flat,
                epsilon=epsilon,
                top_k=top_k,
                round_digits=round_digits,
            )
            if not indices:
                skipped += 1
                print(f"[WARN] empty sparse sample for {stem}; skipping")
                continue

            row = {
                "label": label,
                "indices": indices,
                "values": values,
                "id": stem,
            }
            out.write(json.dumps(row, separators=(",", ":")))
            out.write("\n")

            converted += 1
            total_nnz += len(indices)
            if i % 100 == 0:
                avg_nnz = total_nnz / max(converted, 1)
                print(
                    f"[INFO] progress: {i}/{len(image_files)} files scanned, "
                    f"converted={converted}, skipped={skipped}, avg_nnz={avg_nnz:.1f}"
                )

    if converted == 0:
        raise RuntimeError("No samples converted. Check labels or sparsification settings.")

    avg_nnz = total_nnz / converted
    print("------------------------------------------------------------")
    print(f"[DONE] Sparse validation file written: {output_path}")
    print(f"[DONE] converted={converted}, skipped={skipped}, avg_nnz={avg_nnz:.2f}")
    print(f"[DONE] vector_dim={resize_hw[0] * resize_hw[1] * 3}")
    print("------------------------------------------------------------")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert FL local dataset to Aggregator sparse validation JSONL."
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("fl_client/local_data/chestxray"),
        help=(
            "Dataset root directory. Can be either direct dataset dir "
            "(images/ + labels.json) or parent containing --dataset-type subdir."
        ),
    )
    parser.add_argument(
        "--dataset-type",
        type=str,
        default="chestxray",
        help="Dataset type subfolder name when dataset-root is parent directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/validation/chestxray_sparse_validation.jsonl"),
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0.0,
        help="Drop coordinates with abs(value) <= epsilon.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Keep only top-k absolute coordinates per sample (after epsilon filter).",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Convert only first N samples (for quick testing).",
    )
    parser.add_argument(
        "--round-digits",
        type=int,
        default=6,
        help="Round values to N decimal digits. Use -1 to disable rounding.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=224,
        help="Resize target height.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=224,
        help="Resize target width.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.height <= 0 or args.width <= 0:
        raise ValueError("height/width must be positive")
    if args.round_digits is not None and args.round_digits < -1:
        raise ValueError("round-digits must be >= -1")

    round_digits = None if args.round_digits == -1 else args.round_digits
    dataset_dir = _resolve_dataset_dir(args.dataset_root, args.dataset_type)

    print(f"[INFO] dataset_dir={dataset_dir}")
    print(f"[INFO] output={args.output}")
    print(
        f"[INFO] settings: epsilon={args.epsilon}, top_k={args.top_k}, "
        f"max_samples={args.max_samples}, round_digits={round_digits}, "
        f"resize={args.height}x{args.width}"
    )

    convert(
        dataset_dir=dataset_dir,
        output_path=args.output,
        epsilon=args.epsilon,
        top_k=args.top_k,
        max_samples=args.max_samples,
        round_digits=round_digits,
        resize_hw=(args.height, args.width),
    )


if __name__ == "__main__":
    main()

