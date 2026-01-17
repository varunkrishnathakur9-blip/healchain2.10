# HealChain Aggregator - Serialization Utilities
# data encoding/decoding


"""
HealChain Aggregator – Serialization Utilities
==============================================

Responsibilities:
-----------------
- Deterministic serialization of common data structures
- Canonical byte encoding for hashing and signing
- Safe EC point serialization helpers

Design Principles:
------------------
- Same input -> same bytes
- Explicit ordering
- No implicit randomness
- JSON where possible, bytes where required
"""

import json
from typing import Any, Dict, List

from crypto.ec_utils import serialize_point, parse_point


# -------------------------------------------------------------------
# JSON Serialization (Deterministic)
# -------------------------------------------------------------------

def canonical_json(obj: Any) -> bytes:
    """
    Deterministically serialize an object to JSON bytes.

    Properties:
    -----------
    - Sorted keys
    - No whitespace
    - UTF-8 encoded

    Suitable for:
    - hashing
    - signing
    - storage
    """

    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


# -------------------------------------------------------------------
# EC Point Serialization
# -------------------------------------------------------------------

def serialize_point_list(points: List) -> List[str]:
    """
    Serialize list of EC points to ["x,y", ...] format.

    Used when:
    - Sending data to backend
    - Hashing aggregated results
    """
    return [serialize_point(p) for p in points]


def deserialize_point_list(serialized: List[str]) -> List:
    """
    Deserialize list of EC points from ["x,y", ...] format.
    """
    return [parse_point(s) for s in serialized]


# -------------------------------------------------------------------
# Ciphertext Serialization
# -------------------------------------------------------------------

def serialize_ciphertext(ciphertext: List[str]) -> str:
    """
    Deterministically serialize ciphertext vector.

    Input:
        ["x1,y1", "x2,y2", ...]

    Output:
        "x1,y1|x2,y2|..."
    """
    return "|".join(ciphertext)


def deserialize_ciphertext(data: str) -> List[str]:
    """
    Reverse of serialize_ciphertext().
    """
    if not data:
        return []
    return data.split("|")


# -------------------------------------------------------------------
# Submission / Feedback Canonicalization
# -------------------------------------------------------------------

def canonical_submission_message(
    *,
    task_id: str,
    ciphertext: List[str],
    score_commit: str,
    miner_pk: str,
) -> bytes:
    """
    Canonical message used for miner submission signatures.

    MUST match collector.py logic exactly.
    """

    parts = [
        task_id,
        serialize_ciphertext(ciphertext),
        score_commit,
        miner_pk,
    ]

    return "|".join(parts).encode("utf-8")


def canonical_feedback_message(
    *,
    task_id: str,
    candidate_hash: str,
    verdict: str,
    reason: str,
    miner_pk: str,
) -> bytes:
    """
    Canonical message used for miner feedback signatures.

    MUST match consensus/feedback.py logic exactly.
    """

    parts = [
        task_id,
        candidate_hash,
        verdict,
        reason,
        miner_pk,
    ]

    return "|".join(parts).encode("utf-8")


# -------------------------------------------------------------------
# Candidate Block Canonicalization
# -------------------------------------------------------------------

def canonical_candidate_block(block: Dict) -> bytes:
    """
    Deterministic byte encoding of candidate block.

    Used for:
    - hashing
    - signing (if added later)

    Required fields (must already be present):
    -----------------------------------------
    task_id, round, model_hash, model_link,
    accuracy, participants, score_commits,
    aggregator_pk, timestamp
    """

    fields = [
        block["task_id"],
        str(block["round"]),
        block["model_hash"],
        block["model_link"],
        f"{block['accuracy']:.8f}",
        ",".join(block["participants"]),
        ",".join(block["score_commits"]),
        block["aggregator_pk"],
        str(block["timestamp"]),
    ]

    return "|".join(fields).encode("utf-8")
