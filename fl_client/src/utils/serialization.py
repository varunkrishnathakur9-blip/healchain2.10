from config.settings import SCORE_PRECISION

def encode_score_uint(score: float) -> int:
    """
    Converts float score to uint256-compatible integer.
    MUST be used before commit and reveal.
    """
    if score < 0:
        raise ValueError("Score cannot be negative")
    return int(score * SCORE_PRECISION)
