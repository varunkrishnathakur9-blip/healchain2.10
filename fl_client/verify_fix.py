
import sys
import os
from tinyec import registry
from tinyec.ec import Point

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from crypto.nddfe import load_public_key

# Decimal key (Problematic one)
DECIMAL_PK = "97874679282846974519650999519501889643142020566680933017436168048037707254816,49216227484323797341479210933320237369501001304559437289395602564378693623295"
# Hex key (Correct one)
HEX_PK = "0xd8631af7ecc9597c27187123aa12d8a43f87a8b433431afb845d4ea83f7734a0,0x6cd3bb53e7f9188d3e2646d2319c5c962b694b2a56c26bd00615262a9c19cdbf"

def verify_fix():
    print("Verifying Key Parsing Logic...")
    
    # Test 1: Decimal Parsing
    print("\n[Test 1] Parsing Decimal Key...")
    try:
        pt_dec = load_public_key(DECIMAL_PK)
        print(f"  ✅ Success: {pt_dec}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Test 2: Hex Parsing
    print("\n[Test 2] Parsing Hex Key...")
    try:
        pt_hex = load_public_key(HEX_PK)
        print(f"  ✅ Success: {pt_hex}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        
    # Check if they match
    print(f"\n[Comparison]")
    print(f"Dec: x={pt_dec.x}, y={pt_dec.y}")
    print(f"Hex: x={pt_hex.x}, y={pt_hex.y}")
    
    if pt_dec.x == pt_hex.x and pt_dec.y == pt_hex.y:
        print("\n✅ Verification Passed: Decimal and Hex keys yield identical points.")
    else:
        print("\n❌ Verification Failed: Points do not match!")

if __name__ == "__main__":
    verify_fix()
