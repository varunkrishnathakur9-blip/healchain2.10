# HealChain Aggregator - Collection Module
# submission validation

"""
HealChain Aggregator – Submission Collector & Validator
=======================================================

Implements:
- Miner submission validation (Module M4 – pre-aggregation)

Responsibilities:
-----------------
- Validate miner signatures
- Ensure required submission fields exist
- Enforce task binding (task_id)
- Filter malformed or malicious submissions

NON-RESPONSIBILITIES:
---------------------
- No cryptographic aggregation
- No FE decryption
- No BSGS
- No backend communication
"""

import json
import re
from typing import Dict, List

from utils.validation import verify_signature
from utils.logging import get_logger

logger = get_logger("aggregation.collector")

_HEX_POINT_RE = re.compile(r"^(0x)?[0-9a-fA-F]+,(0x)?[0-9a-fA-F]+$")


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def collect_and_validate_submissions(
    *,
    submissions: List[Dict],
    task_id: str,
    min_participants: int,
    max_participants: int = None,  # Optional: cap submissions at max
) -> List[Dict]:
    """
    Validate miner submissions and return only valid ones.

    Parameters:
    -----------
    submissions : List[Dict]
        Raw submissions received from backend (FL client format)

    task_id : str
        Current HealChain task ID

    min_participants : int
        Minimum number of valid submissions required

    Expected submission format (FL client):
    ------------------------------------
    {
        "taskID": str,                    # FL client uses camelCase
        "miner_pk": str,
        "ciphertext": str or [str],       # Can be string or list
        "scoreCommit": str,               # FL client uses camelCase
        "signature": str,                 # Required for security
        "quantization_scale": int         # Optional FL client field
    }

    Returns:
    --------
    valid_submissions : List[Dict]
        Normalized submissions ready for aggregation
    """

    logger.info(
        f"[M4] Validating {len(submissions)} miner submissions"
    )

    valid: List[Dict] = []
    seen_identities = set()

    for idx, sub in enumerate(submissions):
        try:
            # Normalize FL client format to aggregator format
            normalized = _normalize_submission(sub)
            _validate_submission_structure(normalized, task_id)
            # Identity should be miner address when available.
            # Some local/dev setups reuse the same signing key across miners.
            identity = normalized.get("miner_address") or normalized["miner_pk"]
            if identity in seen_identities:
                raise ValueError("Duplicate miner submission")
            _verify_submission_signature(normalized)
            seen_identities.add(identity)
            valid.append(normalized)
        except Exception as e:
            logger.warning(
                f"[M4] Rejected submission {idx}: {str(e)}"
            )

    if len(valid) < min_participants:
        raise RuntimeError(
            f"Insufficient valid submissions "
            f"({len(valid)} < {min_participants})"
        )

    # Cap submissions at max_participants if specified
    if max_participants is not None and len(valid) > max_participants:
        logger.warning(
            f"[M4] Capping submissions from {len(valid)} to {max_participants} "
            f"(task maxMiners limit)"
        )
        valid = valid[:max_participants]

    logger.info(
        f"[M4] {len(valid)} submissions accepted"
    )

    return valid


# -------------------------------------------------------------------
# Normalization Helper
# -------------------------------------------------------------------

def _normalize_submission(sub: Dict) -> Dict:
    """
    Normalize FL client submission format to aggregator format.
    
    Handles:
    - Field name mapping (camelCase → snake_case)
    - Ciphertext format (string → list)
    - Sparse format normalization (without dense reconstruction)
    - Optional field preservation
    """
    
    normalized = {}
    
    # Map FL client fields to aggregator fields
    normalized["task_id"] = sub.get("taskID", sub.get("task_id"))
    normalized["miner_address"] = sub.get("miner_address", sub.get("minerAddress"))
    normalized["miner_pk"] = sub.get("miner_pk")
    normalized["score_commit"] = sub.get("scoreCommit", sub.get("score_commit"))
    normalized["signature"] = sub.get("signature")
    # Optional canonical-signature helpers from FL client payload.
    normalized["signed_message"] = sub.get("message")
    normalized["signed_ciphertext_concat"] = sub.get("ciphertext_concat")
    
    # Handle ciphertext format (sparse or dense)
    raw_cipher = sub.get("ciphertext")
    sparse_format = sub.get("format") == "sparse"
    if not sparse_format and isinstance(raw_cipher, dict):
        sparse_format = raw_cipher.get("format") == "sparse"
    if not sparse_format and isinstance(raw_cipher, str):
        try:
            parsed_cipher = json.loads(raw_cipher)
        except Exception:
            parsed_cipher = None
        if isinstance(parsed_cipher, dict):
            sparse_format = parsed_cipher.get("format") == "sparse"
    if sparse_format:
        # Sparse format: keep sparse representation end-to-end.
        # Do NOT reconstruct dense ciphertext: it is both expensive and incorrect without
        # per-miner base masks.
        sparse_payload = _extract_sparse_payload(sub)
        total_size = sparse_payload["total_size"]
        nonzero_indices = sparse_payload["nonzero_indices"]
        ciphertext_sparse = sparse_payload["ciphertext"]
        base_mask = sparse_payload["base_mask"]

        # Keep the exact sparse concatenation that miners sign over.
        if not normalized.get("signed_ciphertext_concat"):
            normalized["signed_ciphertext_concat"] = ",".join(ciphertext_sparse)

        normalized["format"] = "sparse"
        normalized["total_size"] = total_size
        normalized["nonzero_indices"] = nonzero_indices
        normalized["base_mask"] = base_mask
        normalized["ciphertext"] = ciphertext_sparse
        logger.info(
            f"[M4] Accepted sparse tensor: {total_size:,} total, "
            f"{len(nonzero_indices):,} non-zero "
            f"({100 * len(nonzero_indices) / max(total_size, 1):.2f}%)"
        )
    else:
        # Legacy dense format
        normalized["format"] = "dense"
        normalized["ciphertext"] = _coerce_ciphertext_list(sub.get("ciphertext", []))
    
    # Preserve optional FL client fields
    if "quantization_scale" in sub:
        normalized["quantization_scale"] = sub["quantization_scale"]
    
    return normalized


# -------------------------------------------------------------------
# Internal Validators
# -------------------------------------------------------------------

def _validate_submission_structure(sub: Dict, task_id: str):
    """
    Structural and semantic validation (after normalization).
    """

    required_fields = {
        "task_id",
        "miner_pk",
        "ciphertext",
        "score_commit",
        "signature",
    }

    missing = required_fields - sub.keys()
    if missing:
        raise ValueError(
            f"Missing fields: {','.join(missing)}"
        )

    if sub["task_id"] != task_id:
        raise ValueError("Task ID mismatch")

    # After normalization, ciphertext should always be a list.
    if not isinstance(sub["ciphertext"], list):
        raise ValueError("Ciphertext must be list")
    if sub.get("format") != "sparse" and not sub["ciphertext"]:
        raise ValueError("Dense ciphertext must be non-empty list")

    if not isinstance(sub["score_commit"], str):
        raise ValueError("Invalid score_commit")

    if not isinstance(sub["miner_pk"], str):
        raise ValueError("Invalid miner_pk")

    if not isinstance(sub["signature"], str):
        raise ValueError("Invalid signature")

    if sub.get("format") == "sparse":
        if "total_size" not in sub or "nonzero_indices" not in sub or "base_mask" not in sub:
            raise ValueError("Sparse submission missing total_size/nonzero_indices/base_mask")
        total_size = sub["total_size"]
        if not isinstance(total_size, int) or total_size <= 0:
            raise ValueError("Invalid sparse total_size")
        nonzero_indices = sub["nonzero_indices"]
        if not isinstance(nonzero_indices, list):
            raise ValueError("Invalid sparse nonzero_indices")
        if len(nonzero_indices) != len(sub["ciphertext"]):
            raise ValueError("Sparse indices/ciphertext length mismatch")
        if len(set(nonzero_indices)) != len(nonzero_indices):
            raise ValueError("Sparse nonzero_indices contain duplicates")
        for idx in nonzero_indices:
            if not isinstance(idx, int) or idx < 0 or idx >= total_size:
                raise ValueError("Sparse nonzero_indices out of bounds")
        if not isinstance(sub["base_mask"], str) or not _is_hex_point_encoding(sub["base_mask"]):
            raise ValueError("Sparse base_mask format invalid")

    # Validate ciphertext point format (should be hex points)
    for ct in sub["ciphertext"]:
        if not isinstance(ct, str):
            raise ValueError("Ciphertext entries must be strings")
        if not _is_hex_point_encoding(ct):
            raise ValueError("Invalid ciphertext point encoding")


def _is_hex_point_encoding(value: str) -> bool:
    """
    Fast format guard for EC point strings expected as "x_hex,y_hex".
    """
    return isinstance(value, str) and bool(_HEX_POINT_RE.fullmatch(value.strip()))


def _verify_submission_signature(sub: Dict):
    """
    Verify miner signature.

    Signature covers:
        HASH(task_id || ciphertext_hash || score_commit || miner_pk)
    """

    # Fast path: verify exact client-supplied canonical message first.
    # This avoids expensive dense ciphertext string reconstruction.
    signed_message = sub.get("signed_message")
    if isinstance(signed_message, str) and signed_message:
        if verify_signature(
            public_key=sub["miner_pk"],
            message=signed_message.encode("utf-8"),
            signature=sub["signature"],
        ):
            return

    # Build fallback variants only if fast path did not verify.
    message_variants = []
    ciphertext_variants = []
    signed_ciphertext_concat = sub.get("signed_ciphertext_concat")
    if isinstance(signed_ciphertext_concat, str) and signed_ciphertext_concat:
        ciphertext_variants.append(signed_ciphertext_concat)

    # If no explicit ciphertext concat exists, fall back to joined ciphertext list.
    if not ciphertext_variants:
        ciphertext_variants.append(",".join(sub["ciphertext"]))

    pk_no_prefix = _normalize_pk_for_message(sub["miner_pk"], with_prefix=False)
    pk_with_prefix = _normalize_pk_for_message(sub["miner_pk"], with_prefix=True)
    pk_variants = _dedupe_preserve_order([sub["miner_pk"], pk_no_prefix, pk_with_prefix])
    score_variants = _score_commit_variants(sub["score_commit"])

    for ciphertext_concat in ciphertext_variants:
        for pk_variant in pk_variants:
            for score_variant in score_variants:
                sub_variant = dict(sub)
                sub_variant["miner_pk"] = pk_variant
                sub_variant["score_commit"] = score_variant
                message_variants.append(
                    _canonical_message(sub_variant, ciphertext_concat=ciphertext_concat)
                )

    for msg in _dedupe_preserve_order(message_variants):
        if verify_signature(
            public_key=sub["miner_pk"],
            message=msg,
            signature=sub["signature"],
        ):
            return

    raise ValueError("Invalid miner signature")


def _score_commit_variants(score_commit: str) -> List[str]:
    """
    Generate score_commit formatting variants for canonical-message matching.
    """
    raw = score_commit.strip()
    if not raw:
        return [score_commit]

    lowered = raw.lower()
    if lowered.startswith("0x"):
        no_prefix = lowered[2:]
    else:
        no_prefix = lowered
    with_prefix = f"0x{no_prefix}"

    return _dedupe_preserve_order([score_commit, raw, no_prefix, with_prefix, lowered])


def _dedupe_preserve_order(items: List):
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _canonical_message(sub: Dict, *, ciphertext_concat: str = None) -> bytes:
    """
    Deterministic message encoding for signature verification.
    """

    if ciphertext_concat is None:
        ciphertext_concat = ",".join(sub["ciphertext"])

    parts = [
        sub["task_id"],
        ciphertext_concat,
        sub["score_commit"],
        sub["miner_pk"],
    ]

    return "|".join(parts).encode("utf-8")


def _normalize_pk_for_message(pk: str, *, with_prefix: bool) -> str:
    """
    Normalize miner_pk string formatting for canonical-message compatibility.
    Input/output format: "x,y" where each coordinate may have or omit 0x.
    """
    try:
        x, y = pk.split(",")
    except Exception:
        return pk

    def norm(part: str) -> str:
        raw = part.strip().lower()
        if raw.startswith("0x"):
            raw = raw[2:]
        return f"0x{raw}" if with_prefix else raw

    return f"{norm(x)},{norm(y)}"


def _coerce_ciphertext_list(raw_ciphertext) -> List[str]:
    """
    Parse ciphertext payload into a list of "x_hex,y_hex" strings.
    """
    if isinstance(raw_ciphertext, list):
        return raw_ciphertext
    if isinstance(raw_ciphertext, str):
        text = raw_ciphertext.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except Exception:
            return [raw_ciphertext]
        if isinstance(parsed, list):
            return parsed
        raise ValueError("Ciphertext JSON must decode to a list for dense format")
    raise ValueError("Invalid ciphertext format")


def _extract_sparse_payload(sub: Dict) -> Dict:
    """
    Extract sparse payload from submission.

    Supported source layouts:
    1) sub["ciphertext"] is dict payload (preferred):
       {"format":"sparse","totalSize":...,"nonzeroIndices":[...],"values":[...],"baseMask":"..."}
    2) legacy top-level sparse fields:
       sub["format"]="sparse", sub["totalSize"], sub["nonzeroIndices"], sub["ciphertext"]=[...], sub["baseMask"]
    """
    payload = None
    raw_cipher = sub.get("ciphertext")
    if isinstance(raw_cipher, dict):
        payload = raw_cipher
    elif isinstance(raw_cipher, str):
        text = raw_cipher.strip()
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            payload = parsed
        elif isinstance(parsed, list):
            payload = {
                "format": sub.get("format"),
                "totalSize": sub.get("totalSize"),
                "nonzeroIndices": sub.get("nonzeroIndices"),
                "values": parsed,
                "baseMask": sub.get("baseMask"),
            }
    elif isinstance(raw_cipher, list):
        payload = {
            "format": sub.get("format"),
            "totalSize": sub.get("totalSize"),
            "nonzeroIndices": sub.get("nonzeroIndices"),
            "values": raw_cipher,
            "baseMask": sub.get("baseMask"),
        }

    if not isinstance(payload, dict):
        raise ValueError("Invalid sparse format: ciphertext payload missing")

    if (payload.get("format") or sub.get("format")) != "sparse":
        raise ValueError("Sparse format payload has invalid format tag")

    total_size = payload.get("totalSize")
    nonzero_indices = payload.get("nonzeroIndices")
    ciphertext_sparse = payload.get("values", payload.get("ciphertext"))
    base_mask = payload.get("baseMask")

    if not isinstance(total_size, int) or total_size <= 0:
        raise ValueError("Invalid sparse format: totalSize is required and must be > 0")
    if not isinstance(nonzero_indices, list):
        raise ValueError("Invalid sparse format: nonzeroIndices must be a list")
    if not isinstance(ciphertext_sparse, list):
        raise ValueError("Invalid sparse format: values/ciphertext must be a list")
    if not isinstance(base_mask, str) or "," not in base_mask:
        raise ValueError("Invalid sparse format: baseMask is required")

    # Coerce indices to int strictly.
    coerced_indices = []
    for idx in nonzero_indices:
        if not isinstance(idx, int):
            raise ValueError("Invalid sparse format: nonzeroIndices must contain integers")
        coerced_indices.append(idx)

    if len(coerced_indices) != len(ciphertext_sparse):
        raise ValueError(
            f"Sparse format mismatch: {len(coerced_indices)} indices but "
            f"{len(ciphertext_sparse)} ciphertext values"
        )

    return {
        "total_size": total_size,
        "nonzero_indices": coerced_indices,
        "ciphertext": ciphertext_sparse,
        "base_mask": base_mask,
    }
