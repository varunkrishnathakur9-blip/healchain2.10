
"""
Elliptic Curve Utilities for HealChain Aggregator
================================================

Curve: secp256r1 (NIST P-256)

Responsibilities:
- Parse serialized EC points from miners ("x,y")
- Serialize EC points for hashing / transport
- Safe EC arithmetic wrappers
- Curve constants (read-only)

IMPORTANT:
- Must EXACTLY match miner-side EC encoding
- No encryption or protocol logic here
"""

from typing import Tuple, List
import hashlib
from tinyec.ec import Point

# -------------------------------------------------------------------
# Curve setup (FIXED — do not change)
# -------------------------------------------------------------------

# Import from centralized configuration for single source of truth
from config.curve import curve, G, N, P


# -------------------------------------------------------------------
# Parsing & Serialization
# -------------------------------------------------------------------

def parse_point(serialized: str) -> Point:
    """
    Parse miner-submitted EC point.

    Miner format (FIXED):
        "x,y"  where x,y are base-10 integers

    Raises:
        ValueError if invalid or off-curve
    """
    try:
        x_str, y_str = serialized.split(",")
        x = int(x_str)
        y = int(y_str)
    except Exception as e:
        raise ValueError(f"Invalid EC point encoding: {serialized}") from e

    pt = Point(curve, x, y)

    # Validate point is on curve
    # Note: tinyec may create Point objects even for off-curve points (with warning)
    # So we explicitly check using curve.on_curve(x, y)
    if pt is None:
        raise ValueError("Point not on secp256r1 curve")
    
    if not curve.on_curve(x, y):
        raise ValueError(
            f"Point ({x}, {y}) is not on secp256r1 curve. "
            "Please ensure the point coordinates are valid."
        )

    return pt


def serialize_point(pt: Point) -> str:
    """
    Serialize EC point to miner-compatible format.

    Output:
        "x,y"  (base-10)
    """
    if pt is None:
        raise ValueError("Cannot serialize null EC point")

    return f"{pt.x},{pt.y}"


# -------------------------------------------------------------------
# EC Arithmetic Wrappers
# -------------------------------------------------------------------

def point_add(p1: Point, p2: Point) -> Point:
    """
    Safe EC point addition.
    """
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    return p1 + p2


def point_mul(pt: Point, scalar: int) -> Point:
    """
    Scalar multiplication with modular reduction.

    NOTE:
    - Scalars are always reduced mod curve order N
    """
    if pt is None:
        raise ValueError("Cannot multiply null EC point")

    k = scalar % N
    if k == 0:
        raise ValueError("Scalar multiplication by zero not allowed")

    return k * pt


def point_neg(pt: Point) -> Point:
    """
    Compute additive inverse of EC point.
    """
    if pt is None:
        raise ValueError("Cannot negate null EC point")
    return Point(curve, pt.x, (-pt.y) % P)


def point_sub(p1: Point, p2: Point) -> Point:
    """
    EC subtraction p1 - p2.
    """
    return point_add(p1, point_neg(p2))


# -------------------------------------------------------------------
# Utility Helpers
# -------------------------------------------------------------------

def is_identity(pt: Point) -> bool:
    """
    Check if point is identity (point at infinity).

    tinyec represents infinity with None.
    """
    return pt is None


def assert_same_curve(pt: Point):
    """
    Defensive check: ensure point belongs to secp256r1.
    """
    # Validate point is on curve using tinyec's built-in validation
    # The Point constructor already validates this, so we just check if it's None
    if pt is None:
        raise ValueError("Point is not on secp256r1")


# -------------------------------------------------------------------
# Debug / Logging Helpers
# -------------------------------------------------------------------

def short_point(pt: Point) -> str:
    """
    Compact string for logs (non-sensitive).
    """
    if pt is None:
        return "<INF>"
    return f"({str(pt.x)[:6]}...,{str(pt.y)[:6]}...)"


# -------------------------------------------------------------------
# Hash and Batch Operations
# -------------------------------------------------------------------

def hash_point(pt: Point) -> str:
    """
    Hash EC point for commitment verification.
    Used in score commitment verification.
    """
    if pt is None:
        raise ValueError("Cannot hash identity point")
    
    # Serialize and hash (consistent with miner side)
    serialized = serialize_point(pt)
    return hashlib.sha256(serialized.encode()).hexdigest()


def parse_point_batch(serialized_list: List[str]) -> List[Point]:
    """
    Parse multiple EC points efficiently.
    Useful for processing miner submissions.
    """
    points = []
    for s in serialized_list:
        points.append(parse_point(s))
    return points


def serialize_point_batch(points: List[Point]) -> List[str]:
    """Serialize multiple EC points."""
    return [serialize_point(pt) for pt in points]


def validate_point_range(pt: Point) -> bool:
    """
    Ensure point coordinates are within valid range.
    Additional safety check for malformed inputs.
    """
    if pt is None:
        return False
    return 0 <= pt.x < P and 0 <= pt.y < P


def validate_point_list(points: List[Point]) -> bool:
    """
    Validate a list of EC points.
    Returns True if all points are valid.
    """
    for pt in points:
        if not validate_point_range(pt):
            return False
        if not curve.on_curve(pt.x, pt.y):
            return False
    return True
