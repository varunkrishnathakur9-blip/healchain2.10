import json
import re
import sys
from pathlib import Path


def stream_extract_from_miner_state(
    miner_state_path: Path,
    task_id: str,
    expected_miner_address: str,
):
    if not miner_state_path.exists():
        return None

    task_pat = re.compile(r'^\s*"' + re.escape(task_id) + r'"\s*:\s*\{\s*$')
    score_pat = re.compile(r'"score"\s*:\s*([0-9eE.+-]+)')
    nonce_pat = re.compile(r'"nonce"\s*:\s*"([0-9a-fA-F]+)"')
    commit_pat = re.compile(r'"commit"\s*:\s*"([0-9a-fA-F]+)"')
    miner_pat = re.compile(r'"minerAddress"\s*:\s*"([^"]+)"')

    in_task = False
    depth = 0
    score = None
    nonce = None
    commit = None
    miner_address = None

    with miner_state_path.open("r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            if not in_task:
                if task_pat.match(line):
                    in_task = True
                    depth = 1
                continue

            m = score_pat.search(line)
            if m:
                score = m.group(1)

            m = nonce_pat.search(line)
            if m:
                nonce = "0x" + m.group(1).lower()

            m = commit_pat.search(line)
            if m:
                commit = "0x" + m.group(1).lower()

            m = miner_pat.search(line)
            if m:
                miner_address = m.group(1).strip().lower()

            depth += line.count("{")
            depth -= line.count("}")

            if depth <= 0:
                break

    if not in_task:
        return None

    if miner_address and miner_address != expected_miner_address:
        return {
            "taskID": task_id,
            "minerAddress": miner_address,
            "score": score,
            "nonce": nonce,
            "commit": commit,
            "warning": (
                f"Task found but minerAddress mismatch "
                f"(expected={expected_miner_address}, found={miner_address})"
            ),
        }

    return {
        "taskID": task_id,
        "minerAddress": expected_miner_address,
        "score": score,
        "nonce": nonce,
        "commit": commit,
    }


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/show_reveal_data.py <task_id> <miner_address>")
        print("Example: python scripts/show_reveal_data.py task_037 0xaeb1b0ab57ebc91ff0fcc1cd35ff314653ebe529")
        raise SystemExit(1)

    task_id = sys.argv[1].strip()
    miner_address = sys.argv[2].strip().lower()

    fl_client_root = Path(__file__).resolve().parent.parent
    reveal_dir = fl_client_root / "reveal_exports"
    reveal_file = reveal_dir / f"{task_id}__{miner_address}.json"
    miner_state_file = fl_client_root / "miner_state.json"

    if not reveal_file.exists():
        print(f"Reveal artifact not found: {reveal_file}")
        print("Falling back to streaming parse from miner_state.json ...")
        data = stream_extract_from_miner_state(miner_state_file, task_id, miner_address)
        if not data:
            print(f"Task not found in {miner_state_file}")
            raise SystemExit(2)
    else:
        try:
            data = json.loads(reveal_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Failed to read reveal artifact: {e}")
            raise SystemExit(3)

    print(f"taskID={data.get('taskID')}")
    print(f"minerAddress={data.get('minerAddress')}")
    print(f"score={data.get('score')}")
    if "scoreUint" in data:
        print(f"scoreUint={data.get('scoreUint')}")
    print(f"nonce={data.get('nonce')}")
    print(f"commit={data.get('commit')}")
    if "createdAt" in data:
        print(f"createdAt={data.get('createdAt')}")
    if data.get("warning"):
        print(f"warning={data.get('warning')}")


if __name__ == "__main__":
    main()
