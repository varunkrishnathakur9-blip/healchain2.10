#!/usr/bin/env python3
"""
Reconstruct a Keras H5 checkpoint from a HealChain global model artifact.

The aggregator publishes global models as flat JSON vectors:
  {"weights": [...], "num_parameters": N}

This script uses a cached base H5/Keras checkpoint as the architecture
template, copies it, and replaces its model weight datasets with the global
flat weights.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable


AGGREGATOR_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT_DIR = AGGREGATOR_ROOT / "artifacts"
DEFAULT_CACHE_DIR = DEFAULT_ARTIFACT_DIR / "cache"
DEFAULT_OUTPUT_DIR = DEFAULT_ARTIFACT_DIR / "reconstructed"


def _decode_attr_value(value) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return str(value)


def _iter_keras_weight_datasets(h5_file) -> Iterable:
    """
    Yield HDF5 datasets in the same deterministic order used by
    aggregator/src/model/loader.py when it flattens H5 checkpoints.
    """
    import h5py  # type: ignore

    root = h5_file["model_weights"] if "model_weights" in h5_file else h5_file
    layer_names = root.attrs.get("layer_names")

    if layer_names is not None:
        for layer_name_raw in layer_names:
            layer_name = _decode_attr_value(layer_name_raw)
            if layer_name not in root:
                continue

            layer_group = root[layer_name]
            weight_names = layer_group.attrs.get("weight_names", [])
            for weight_name_raw in weight_names:
                weight_name = _decode_attr_value(weight_name_raw)
                if weight_name not in layer_group:
                    continue

                obj = layer_group[weight_name]
                if isinstance(obj, h5py.Dataset):
                    yield obj
        return

    def _visit(_name, obj):
        if isinstance(obj, h5py.Dataset):
            datasets.append(obj)

    datasets = []
    root.visititems(_visit)
    for dataset in datasets:
        yield dataset


def _load_flat_weights(artifact_path: Path) -> tuple[list[float], int | None]:
    with artifact_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError(f"Artifact must be a JSON object: {artifact_path}")

    weights = payload.get("weights")
    if not isinstance(weights, list):
        raise ValueError(f"Artifact missing list field 'weights': {artifact_path}")

    num_parameters = payload.get("num_parameters")
    if num_parameters is not None:
        num_parameters = int(num_parameters)

    return weights, num_parameters


def _default_artifact_path(task_id: str, round_no: int) -> Path:
    return DEFAULT_ARTIFACT_DIR / f"{task_id}_round{round_no}.json"


def _default_base_model_path(task_id: str) -> Path:
    return DEFAULT_CACHE_DIR / f"{task_id}_base_model.bin"


def _default_output_path(task_id: str, round_no: int) -> Path:
    return DEFAULT_OUTPUT_DIR / f"{task_id}_round{round_no}_global.h5"


def reconstruct_h5(
    *,
    artifact_path: Path,
    base_model_path: Path,
    output_path: Path,
    overwrite: bool,
) -> None:
    import h5py  # type: ignore
    import numpy as np

    if not artifact_path.exists():
        raise FileNotFoundError(f"Global artifact not found: {artifact_path}")
    if not base_model_path.exists():
        raise FileNotFoundError(f"Base H5 template not found: {base_model_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists; pass --overwrite to replace it: {output_path}")
    if output_path.resolve() == base_model_path.resolve():
        raise ValueError("Output path must not be the same as the base model path")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base_model_path, output_path)

    weights, declared_num_parameters = _load_flat_weights(artifact_path)
    weight_count = len(weights)
    if declared_num_parameters is not None and declared_num_parameters != weight_count:
        raise ValueError(
            "Artifact num_parameters does not match weights length: "
            f"{declared_num_parameters} != {weight_count}"
        )

    offset = 0
    dataset_count = 0
    expected_parameters = 0

    with h5py.File(output_path, "r+") as h5_file:
        for dataset in _iter_keras_weight_datasets(h5_file):
            size = int(np.prod(dataset.shape))
            next_offset = offset + size
            if next_offset > weight_count:
                raise ValueError(
                    "Artifact has fewer weights than the H5 template expects: "
                    f"needed at least {next_offset}, got {weight_count}"
                )

            reshaped = np.asarray(weights[offset:next_offset], dtype=dataset.dtype).reshape(
                dataset.shape
            )
            dataset[...] = reshaped

            offset = next_offset
            expected_parameters += size
            dataset_count += 1

    if offset != weight_count:
        raise ValueError(
            "Artifact has extra weights after filling the H5 template: "
            f"used {offset}, got {weight_count}"
        )

    print("Reconstruction complete")
    print(f"  artifact: {artifact_path}")
    print(f"  base H5:  {base_model_path}")
    print(f"  output:   {output_path}")
    print(f"  tensors:  {dataset_count}")
    print(f"  params:   {expected_parameters}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconstruct a Keras H5 checkpoint from an aggregator JSON model artifact."
    )
    parser.add_argument("--task-id", required=True, help="HealChain task id, e.g. task_iid_5c_clean_0")
    parser.add_argument("--round", dest="round_no", type=int, default=2, help="FL round number")
    parser.add_argument("--artifact", type=Path, help="Path to global JSON artifact")
    parser.add_argument("--base-model", type=Path, help="Path to cached base H5 template")
    parser.add_argument("--output", type=Path, help="Output reconstructed H5 path")
    parser.add_argument("--overwrite", action="store_true", help="Replace output if it already exists")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    artifact_path = args.artifact or _default_artifact_path(args.task_id, args.round_no)
    base_model_path = args.base_model or _default_base_model_path(args.task_id)
    output_path = args.output or _default_output_path(args.task_id, args.round_no)

    reconstruct_h5(
        artifact_path=artifact_path.resolve(),
        base_model_path=base_model_path.resolve(),
        output_path=output_path.resolve(),
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
