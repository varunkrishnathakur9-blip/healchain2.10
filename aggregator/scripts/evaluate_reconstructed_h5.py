#!/usr/bin/env python3
"""
Evaluate a reconstructed HealChain Keras H5 model on an image test dataset.

Supported dataset layouts:
  dataset/
    images/
      sample_001.npy
    labels.json

  dataset/
    NORMAL/
      image_001.jpeg
    PNEUMONIA/
      image_002.jpeg
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np


AGGREGATOR_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECONSTRUCTED_DIR = AGGREGATOR_ROOT / "artifacts" / "reconstructed"
DEFAULT_EVALUATION_DIR = AGGREGATOR_ROOT / "artifacts" / "evaluation"
SUPPORTED_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".npy", ".png", ".tif", ".tiff"}
LABEL_MAP = {"NORMAL": 0, "PNEUMONIA": 1}


def _import_tensorflow():
    try:
        import tensorflow as tf  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "TensorFlow is required to run a reconstructed Keras H5 model. "
            "Install it in this venv before evaluation."
        ) from e
    return tf


def _default_model_path(task_id: str, round_no: int) -> Path:
    return DEFAULT_RECONSTRUCTED_DIR / f"{task_id}_round{round_no}_global.h5"


def _default_output_path(model_path: Path, dataset_path: Path) -> Path:
    dataset_name = dataset_path.name or "dataset"
    return DEFAULT_EVALUATION_DIR / f"{model_path.stem}__{dataset_name}_metrics.json"


def _label_to_int(value: Any) -> int:
    if isinstance(value, str):
        key = value.strip().upper()
        if key in LABEL_MAP:
            return LABEL_MAP[key]
        return int(value)
    return int(value)


def _discover_images_labels_dataset(dataset_path: Path) -> list[tuple[Path, int]]:
    images_dir = dataset_path / "images"
    labels_path = dataset_path / "labels.json"
    if not images_dir.is_dir() or not labels_path.is_file():
        return []

    with labels_path.open("r", encoding="utf-8") as f:
        labels = json.load(f)

    samples: list[tuple[Path, int]] = []
    for image_path in sorted(images_dir.iterdir()):
        if not image_path.is_file() or image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        label_key = image_path.stem
        if label_key not in labels and image_path.name in labels:
            label_key = image_path.name
        if label_key not in labels:
            raise ValueError(f"Missing label for {image_path.name} in {labels_path}")

        samples.append((image_path, _label_to_int(labels[label_key])))

    return samples


def _discover_class_folder_dataset(dataset_path: Path) -> list[tuple[Path, int]]:
    samples: list[tuple[Path, int]] = []
    for class_dir in sorted(path for path in dataset_path.iterdir() if path.is_dir()):
        label = LABEL_MAP.get(class_dir.name.upper())
        if label is None:
            try:
                label = int(class_dir.name)
            except ValueError:
                continue

        for image_path in sorted(class_dir.rglob("*")):
            if image_path.is_file() and image_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                samples.append((image_path, label))

    return samples


def discover_samples(dataset_path: Path) -> list[tuple[Path, int]]:
    samples = _discover_images_labels_dataset(dataset_path)
    if samples:
        return samples

    samples = _discover_class_folder_dataset(dataset_path)
    if samples:
        return samples

    raise ValueError(
        "Could not find test samples. Expected either images/ + labels.json "
        "or class folders such as NORMAL/ and PNEUMONIA/."
    )


def _resolve_input_spec(model) -> tuple[str, tuple[int, int, int] | int]:
    input_shape = model.input_shape
    if isinstance(input_shape, list):
        input_shape = input_shape[0]

    if len(input_shape) == 4:
        _, height, width, channels = input_shape
        return "image", (
            int(height or 224),
            int(width or 224),
            int(channels or 3),
        )

    if len(input_shape) == 2:
        _, features = input_shape
        if features is None:
            raise ValueError(f"Cannot infer flat input size from model.input_shape={input_shape}")
        return "flat", int(features)

    raise ValueError(f"Unsupported model input shape: {input_shape}")


def _load_npy(path: Path) -> np.ndarray:
    return np.load(path).astype(np.float32)


def _load_image(path: Path, *, channels: int, tf) -> np.ndarray:
    raw = tf.io.read_file(str(path))
    decoded = tf.image.decode_image(raw, channels=channels, expand_animations=False)
    return decoded.numpy().astype(np.float32)


def _to_hwc(array: np.ndarray) -> np.ndarray:
    if array.ndim == 1:
        return array
    if array.ndim == 2:
        return array[..., np.newaxis]
    if array.ndim == 3 and array.shape[0] in {1, 3} and array.shape[-1] not in {1, 3}:
        return np.transpose(array, (1, 2, 0))
    return array


def _match_channels(array: np.ndarray, channels: int) -> np.ndarray:
    if array.ndim != 3:
        return array

    current = array.shape[-1]
    if current == channels:
        return array
    if current == 1 and channels == 3:
        return np.repeat(array, 3, axis=-1)
    if current == 3 and channels == 1:
        return np.mean(array, axis=-1, keepdims=True)
    if current > channels:
        return array[..., :channels]

    repeats = int(np.ceil(channels / current))
    return np.repeat(array, repeats, axis=-1)[..., :channels]


def _preprocess_sample(
    path: Path,
    *,
    input_mode: str,
    input_spec: tuple[int, int, int] | int,
    tf,
) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        array = _load_npy(path)
    else:
        channels = input_spec[2] if input_mode == "image" else 3
        array = _load_image(path, channels=channels, tf=tf)

    array = _to_hwc(array)
    if array.size and float(np.nanmax(array)) > 1.5:
        array = array / 255.0

    if input_mode == "flat":
        flat_size = int(input_spec)
        flat = array.reshape(-1).astype(np.float32)
        if flat.size != flat_size:
            raise ValueError(
                f"{path} flattens to {flat.size} values, but model expects {flat_size}"
            )
        return flat

    height, width, channels = input_spec
    array = _match_channels(array, channels)
    array = tf.image.resize(array, (height, width)).numpy()
    return array.astype(np.float32)


def _batched(samples: list[tuple[Path, int]], batch_size: int) -> Iterable[list[tuple[Path, int]]]:
    for start in range(0, len(samples), batch_size):
        yield samples[start : start + batch_size]


def _binary_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    specificity = tn / (tn + fp) if (tn + fp) else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and (precision + recall)
        else None
    )

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "sensitivity": recall,
        "specificity": specificity,
        "f1_score": f1,
        "confusion_matrix": [[tn, fp], [fn, tp]],
    }


def _predictions_from_output(output: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    scores = np.asarray(output)
    if scores.ndim == 1:
        positive_scores = scores
        return (positive_scores >= threshold).astype(int), positive_scores

    if scores.ndim == 2 and scores.shape[-1] == 1:
        positive_scores = scores[:, 0]
        return (positive_scores >= threshold).astype(int), positive_scores

    if scores.ndim == 2 and scores.shape[-1] == 2:
        return np.argmax(scores, axis=1).astype(int), scores[:, 1]

    raise ValueError(f"Unsupported model output shape: {scores.shape}")


def evaluate_model(
    *,
    model_path: Path,
    dataset_path: Path,
    output_path: Path,
    batch_size: int,
    threshold: float,
) -> dict[str, Any]:
    tf = _import_tensorflow()

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not dataset_path.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_path}")

    model = tf.keras.models.load_model(model_path, compile=False)
    input_mode, input_spec = _resolve_input_spec(model)
    samples = discover_samples(dataset_path)

    y_true_chunks: list[np.ndarray] = []
    y_pred_chunks: list[np.ndarray] = []
    score_chunks: list[np.ndarray] = []

    for batch in _batched(samples, batch_size):
        x_batch = np.stack(
            [
                _preprocess_sample(path, input_mode=input_mode, input_spec=input_spec, tf=tf)
                for path, _label in batch
            ],
            axis=0,
        )
        y_batch = np.asarray([label for _path, label in batch], dtype=int)

        output = model.predict(x_batch, verbose=0)
        y_pred, scores = _predictions_from_output(output, threshold)

        y_true_chunks.append(y_batch)
        y_pred_chunks.append(y_pred)
        score_chunks.append(scores)

    y_true = np.concatenate(y_true_chunks)
    y_pred = np.concatenate(y_pred_chunks)
    scores = np.concatenate(score_chunks)

    report: dict[str, Any] = {
        "model_path": str(model_path),
        "dataset_path": str(dataset_path),
        "samples_used": int(y_true.size),
        "input_mode": input_mode,
        "input_shape": list(model.input_shape if not isinstance(model.input_shape, list) else model.input_shape[0]),
        "threshold": threshold,
        "accuracy": float(np.mean(y_true == y_pred)),
        "labels": y_true.astype(int).tolist(),
        "predictions": y_pred.astype(int).tolist(),
        "positive_scores": scores.astype(float).tolist(),
    }

    if set(np.unique(y_true)).issubset({0, 1}) and set(np.unique(y_pred)).issubset({0, 1}):
        report.update(_binary_metrics(y_true, y_pred))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a reconstructed HealChain Keras H5 model on a test dataset."
    )
    parser.add_argument("--task-id", help="Task id used for default reconstructed model path")
    parser.add_argument("--round", dest="round_no", type=int, default=2, help="FL round number")
    parser.add_argument("--model", type=Path, help="Path to reconstructed .h5 model")
    parser.add_argument("--dataset", type=Path, required=True, help="Path to test dataset folder")
    parser.add_argument("--output", type=Path, help="Path to write JSON metrics")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--threshold", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.model:
        model_path = args.model
    else:
        if not args.task_id:
            raise SystemExit("Either --model or --task-id is required.")
        model_path = _default_model_path(args.task_id, args.round_no)

    dataset_path = args.dataset
    output_path = args.output or _default_output_path(model_path, dataset_path)

    report = evaluate_model(
        model_path=model_path.resolve(),
        dataset_path=dataset_path.resolve(),
        output_path=output_path.resolve(),
        batch_size=args.batch_size,
        threshold=args.threshold,
    )

    print("Evaluation complete")
    print(f"  model:    {report['model_path']}")
    print(f"  dataset:  {report['dataset_path']}")
    print(f"  output:   {output_path.resolve()}")
    print(f"  samples:  {report['samples_used']}")
    print(f"  accuracy: {report['accuracy']:.6f}")
    if "confusion_matrix" in report:
        print(f"  cm:       {report['confusion_matrix']}")


if __name__ == "__main__":
    main()
