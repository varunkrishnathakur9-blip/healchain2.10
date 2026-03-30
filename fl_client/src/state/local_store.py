import json
from datetime import datetime, timezone
from pathlib import Path


def get_fl_client_root() -> Path:
    # This file is in fl_client/src/state/local_store.py
    # Go up from src/state/ to fl_client/
    return Path(__file__).resolve().parent.parent.parent


def get_store_path() -> Path:
    # miner_state.json lives in fl_client root
    return get_fl_client_root() / "miner_state.json"


def get_reveal_exports_dir() -> Path:
    return get_fl_client_root() / "reveal_exports"


STORE = get_store_path()


def load_state():
    if STORE.exists():
        try:
            return json.loads(STORE.read_text())
        except Exception as e:
            print(f"[local_store] Warning: Could not load state from {STORE}: {e}")
            return {}
    return {}


def save_state(state):
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(f"[local_store] Warning: Could not save state to {STORE}: {e}")


def save_reveal_record(
    task_id: str,
    miner_address: str,
    score: float,
    nonce_hex: str,
    commit_hex: str,
    score_precision: int = 10**6,
) -> Path | None:
    """
    Persist a compact reveal artifact for M7b.
    This avoids reading large miner_state.json just to recover score/nonce/commit.
    """
    try:
        miner_norm = str(miner_address or "").strip().lower()
        nonce_norm = str(nonce_hex or "").strip().lower().replace("0x", "")
        commit_norm = str(commit_hex or "").strip().lower().replace("0x", "")
        score_float = float(score)
        score_uint = int(score_float * int(score_precision))

        artifact = {
            "taskID": str(task_id),
            "minerAddress": miner_norm,
            "score": score_float,
            "scoreUint": score_uint,
            "nonce": f"0x{nonce_norm}",
            "commit": f"0x{commit_norm}",
            "scorePrecision": int(score_precision),
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        export_dir = get_reveal_exports_dir()
        export_dir.mkdir(parents=True, exist_ok=True)

        # Deterministic per-task/per-miner artifact.
        file_name = f"{artifact['taskID']}__{miner_norm}.json"
        artifact_path = export_dir / file_name
        artifact_path.write_text(json.dumps(artifact, indent=2))

        # Convenience pointer to latest generated reveal artifact.
        latest_path = export_dir / "latest.json"
        latest_path.write_text(json.dumps(artifact, indent=2))

        return artifact_path
    except Exception as e:
        print(f"[local_store] Warning: Could not save reveal artifact: {e}")
        return None
