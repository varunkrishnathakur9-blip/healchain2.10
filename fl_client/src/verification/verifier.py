"""
HealChain FL-Client - Miner Verification
Implements Algorithm 5 from BTP Report Section 4.6

M5: Miner Verification Feedback (Consensus)
"""

import os
import json
import math
import hashlib
import binascii
import time
from typing import Dict, Optional, Tuple

import requests
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256

from crypto.signature import sign_message
from state.local_store import load_state


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://localhost:3000")


def _normalize_pk(pk: str) -> str:
    parts = pk.split(",")
    if len(parts) != 2:
        raise ValueError("public key must be x_hex,y_hex")
    norm = []
    for p in parts:
        t = p.strip().lower()
        if t.startswith("0x"):
            t = t[2:]
        if not t:
            raise ValueError("invalid empty public key coordinate")
        norm.append(t)
    return ",".join(norm)


def _canonical_candidate_block(
    *,
    task_id: str,
    round_no: int,
    model_hash: str,
    model_link: str,
    accuracy: float,
    participants: list[str],
    score_commits: list[str],
    aggregator_pk: str,
    timestamp: int,
) -> bytes:
    fields = [
        str(task_id),
        str(round_no),
        str(model_hash),
        str(model_link),
        f"{float(accuracy):.8f}",
        ",".join(str(v) for v in participants),
        ",".join(str(v) for v in score_commits),
        str(aggregator_pk),
        str(timestamp),
    ]
    return "|".join(fields).encode("utf-8")


def _verify_aggregator_signature(
    *,
    aggregator_pk: str,
    signature_hex: str,
    candidate_hash_hex: str,
) -> bool:
    """
    Verify aggregator signature over candidate hash bytes (double-hashed with SHA-256
    inside ECDSA, matching aggregator signing path).
    """
    try:
        x_hex, y_hex = aggregator_pk.split(",")
        x = int(x_hex, 16)
        y = int(y_hex, 16)
        pub = ECC.construct(curve="P-256", point_x=x, point_y=y)

        sig = signature_hex.strip()
        if sig.startswith("0x") or sig.startswith("0X"):
            sig = sig[2:]
        sig_bytes = binascii.unhexlify(sig)

        digest = candidate_hash_hex.strip()
        if digest.startswith("0x") or digest.startswith("0X"):
            digest = digest[2:]
        msg = bytes.fromhex(digest)

        verifier = DSS.new(pub, "fips-186-3")
        verifier.verify(SHA256.new(msg), sig_bytes)
        return True
    except Exception:
        return False


def _canonical_feedback_message(
    *,
    task_id: str,
    candidate_hash: str,
    verdict: str,
    reason: str,
    miner_pk: str,
) -> bytes:
    parts = [
        task_id,
        candidate_hash,
        verdict,
        reason,
        miner_pk,
    ]
    return "|".join(parts).encode("utf-8")


def _normalize_commit_hex(value: object) -> str:
    commit = str(value or "").strip().lower()
    if commit.startswith("0x"):
        commit = commit[2:]
    return commit


def _extract_score_commit_for_miner(task: Dict, miner_address: str) -> str:
    if not isinstance(task, dict):
        return ""
    by_miner = task.get("scoreCommitsByMiner")
    if isinstance(by_miner, dict):
        v = by_miner.get(str(miner_address).lower(), "")
        if v:
            return str(v)

    gradients = task.get("gradients")
    if isinstance(gradients, list):
        for g in gradients:
            if not isinstance(g, dict):
                continue
            if str(g.get("minerAddress", "")).lower() != str(miner_address).lower():
                continue
            score_commit = g.get("scoreCommit")
            if score_commit:
                return str(score_commit)
    return ""


def _fetch_task_details(task_id: str, timeout_sec: float) -> Optional[Dict]:
    try:
        resp = requests.get(
            f"{_backend_url()}/tasks/{task_id}",
            timeout=timeout_sec,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data if isinstance(data, dict) else None
    except Exception:
        return None
    return None


def _resolve_score_commit_with_retries(
    *,
    task_id: str,
    miner_address: str,
    initial_task: Dict,
) -> str:
    retries = max(1, int(os.getenv("FL_VERIFY_SCORECOMMIT_FETCH_RETRIES", "5")))
    delay_sec = max(0.0, float(os.getenv("FL_VERIFY_SCORECOMMIT_FETCH_DELAY_SEC", "1.0")))
    timeout_sec = max(1.0, float(os.getenv("FL_VERIFY_SCORECOMMIT_FETCH_TIMEOUT_SEC", "8")))

    for attempt in range(retries):
        task_snapshot = initial_task if attempt == 0 else _fetch_task_details(task_id, timeout_sec)
        if isinstance(task_snapshot, dict):
            commit = _extract_score_commit_for_miner(task_snapshot, miner_address)
            if commit:
                return commit
        if attempt < retries - 1:
            time.sleep(delay_sec * (attempt + 1))

    return ""


def _optional_model_sanity_check(
    *,
    model_link: str,
    artifact_hash: Optional[str],
) -> bool:
    if not model_link:
        return False

    resp = requests.get(model_link, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict):
        return False

    weights = payload.get("weights")
    if not isinstance(weights, list) or len(weights) == 0:
        return False

    if artifact_hash:
        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        actual = hashlib.sha256(serialized).hexdigest()
        token = str(artifact_hash).lower().replace("0x", "")
        if actual != token:
            return False

    for v in weights[: min(2048, len(weights))]:
        try:
            fv = float(v)
        except Exception:
            return False
        if not math.isfinite(fv):
            return False

    return True


def verify_candidate_block(
    task_id: str,
    miner_address: str,
    candidate_block: Dict,
    miner_pk: str,
    score_commit: str,
    task_round: Optional[int] = None,
    perform_local_sanity: bool = False,
) -> Tuple[bool, str]:
    """
    Verify candidate block according to Algorithm 5:
      1. Verify aggregator signature over HASH(B)
      2. Check score commitment presence
      3. Optional local sanity check

    Returns:
      (is_valid, reason)
    """
    try:
        participants = candidate_block.get("participants", []) or []
        score_commits = candidate_block.get("scoreCommits", []) or []
        model_hash = candidate_block.get("modelHash", "")
        model_link = candidate_block.get("modelLink", "")
        aggregator_pk = candidate_block.get("aggregatorPK", "")
        signature_a = candidate_block.get("signatureA", "")
        candidate_hash = candidate_block.get("candidateHash", "")
        candidate_ts_raw = candidate_block.get("candidateTimestamp") or candidate_block.get("timestamp")
        round_no = candidate_block.get("round", task_round if task_round is not None else 1)
        acc_raw = candidate_block.get("accuracy", 0)
        artifact_hash = candidate_block.get("artifactHash")

        accuracy = float(acc_raw) / 1_000_000.0 if isinstance(acc_raw, (int, str)) else float(acc_raw)
        timestamp = int(candidate_ts_raw)

        canonical = _canonical_candidate_block(
            task_id=task_id,
            round_no=int(round_no),
            model_hash=str(model_hash),
            model_link=str(model_link),
            accuracy=float(accuracy),
            participants=[str(p) for p in participants],
            score_commits=[str(c) for c in score_commits],
            aggregator_pk=str(aggregator_pk),
            timestamp=timestamp,
        )
        recomputed_hash = hashlib.sha256(canonical).hexdigest()
        if recomputed_hash != str(candidate_hash):
            return False, "bad candidate hash"

        if not _verify_aggregator_signature(
            aggregator_pk=str(aggregator_pk),
            signature_hex=str(signature_a),
            candidate_hash_hex=str(candidate_hash),
        ):
            return False, "bad aggregator sig"

        miner_score_commit = _normalize_commit_hex(score_commit)
        block_score_commits = {
            _normalize_commit_hex(v) for v in score_commits if _normalize_commit_hex(v)
        }
        if not miner_score_commit or miner_score_commit not in block_score_commits:
            return False, "missing scoreCommit"

        normalized_self_pk = _normalize_pk(miner_pk)
        normalized_parts = {_normalize_pk(str(p)) for p in participants}
        if normalized_parts and normalized_self_pk not in normalized_parts:
            return False, "miner not in participants"

        if perform_local_sanity:
            ok = _optional_model_sanity_check(
                model_link=str(model_link),
                artifact_hash=str(artifact_hash) if artifact_hash is not None else None,
            )
            if not ok:
                return False, "model fails local sanity"

        return True, ""
    except Exception as e:
        return False, f"verification_error:{e}"


def submit_verification_vote(
    task_id: str,
    miner_address: str,
    miner_pk: str,
    candidate_hash: str,
    verdict: str,
    reason: str,
    miner_private_key: str,
) -> Dict:
    """
    Submit protocol-format verification vote to backend (M5).
    """
    if verdict not in ["VALID", "INVALID"]:
        raise ValueError("Verdict must be VALID or INVALID")

    message_bytes = _canonical_feedback_message(
        task_id=task_id,
        candidate_hash=candidate_hash,
        verdict=verdict,
        reason=reason,
        miner_pk=miner_pk,
    )
    message = message_bytes.decode("utf-8")
    signature = sign_message(private_key=miner_private_key, message=message_bytes)

    payload = {
        "taskID": task_id,
        "minerAddress": miner_address,
        "miner_pk": miner_pk,
        "candidateHash": candidate_hash,
        "verdict": verdict,
        "reason": reason,
        "message": message,
        "signature": signature,
    }

    response = requests.post(
        f"{_backend_url()}/verification/submit",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=20,
    )

    response.raise_for_status()
    return response.json()


def get_consensus_result(task_id: str) -> Dict:
    response = requests.get(
        f"{_backend_url()}/verification/consensus/{task_id}",
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def verify_and_submit_for_task(
    *,
    task: Dict,
    miner_address: str,
    miner_pk: str,
    miner_private_key: str,
    perform_local_sanity: bool = False,
) -> Dict:
    """
    End-to-end Algorithm-5 flow for a miner:
      verify candidate -> submit signed feedback.
    """
    task_id = str(task.get("taskID"))
    block = task.get("block")
    if not isinstance(block, dict):
        raise ValueError("Task has no candidate block to verify")

    state = load_state()
    score_commit = ""
    if task_id in state:
        score_commit = str(state[task_id].get("commit", ""))

    if not score_commit:
        score_commit = _extract_score_commit_for_miner(task, miner_address)

    if not score_commit:
        score_commit = _resolve_score_commit_with_retries(
            task_id=task_id,
            miner_address=miner_address,
            initial_task=task,
        )

    is_valid, reason = verify_candidate_block(
        task_id=task_id,
        miner_address=miner_address,
        candidate_block=block,
        miner_pk=miner_pk,
        score_commit=score_commit,
        task_round=int(task.get("currentRound", 1)),
        perform_local_sanity=perform_local_sanity,
    )
    verdict = "VALID" if is_valid else "INVALID"
    if is_valid:
        reason = ""

    return submit_verification_vote(
        task_id=task_id,
        miner_address=miner_address,
        miner_pk=miner_pk,
        candidate_hash=str(block.get("candidateHash") or block.get("hash") or ""),
        verdict=verdict,
        reason=reason,
        miner_private_key=miner_private_key,
    )
