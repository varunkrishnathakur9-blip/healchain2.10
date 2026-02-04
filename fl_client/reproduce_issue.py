
import sys
import os
from tinyec import registry
from tinyec.ec import Point

# Load values from .env (simulated)
# TP_PUBLIC_KEY from .env
PROBABLE_DECIMAL_PK = "97874679282846974519650999519501889643142020566680933017436168048037707254816,49216227484323797341479210933320237369501001304559437289395602564378693623295"

curve = registry.get_curve("secp256r1")

def test_load(pk_str, name):
    print(f"Testing {name}: {pk_str[:50]}...")
    x_str, y_str = pk_str.split(",")
    
    # Try Hex (Current implementation)
    try:
        x_hex = int(x_str, 16)
        y_hex = int(y_str, 16)
        pt = Point(curve, x_hex, y_hex)
        print(f"  [HEX parsing] Result: {pt}")
    except Exception as e:
        print(f"  [HEX parsing] Failed/Warned: {e}")

    # Try Decimal
    try:
        x_dec = int(x_str)
        y_dec = int(y_str)
        pt = Point(curve, x_dec, y_dec)
        print(f"  [DEC parsing] Result: {pt}")
        # Validate - tinyec usually checks on init? 
        # Actually tinyec Point init DOES NOT enforce on-curve check strictness unless operations strictly fail,
        # but the USER WARNINGS come from tinyec library internals during operations.
        # Let's perform a check manually
        is_on_curve = curve.is_on_curve(x_dec, y_dec)
        print(f"  [DEC parsing] On Curve? {is_on_curve}")
    except Exception as e:
        print(f"  [DEC parsing] Failed: {e}")

if __name__ == "__main__":
    test_load(PROBABLE_DECIMAL_PK, "TP_PUBLIC_KEY")
