#!/usr/bin/env python3
"""
Simple test validation for HealChain aggregator tests.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def validate_test_structure():
    """Validate test file structure and imports."""
    print("🔍 HealChain Aggregator Test Validation")
    print("=" * 50)
    
    test_files = [
        "tests/test_crypto/test_ec_utils.py",
        "tests/test_crypto/test_bsgs.py", 
        "tests/test_crypto/test_ndd_fe.py",
        "tests/test_aggregation/test_aggregator.py",
        "tests/integration/test_end_to_end.py",
    ]
    
    all_valid = True
    
    for test_file in test_files:
        print(f"\n📁 Validating {test_file}...")
        print("-" * 30)
        
        file_path = os.path.join(os.path.dirname(__file__), test_file)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {test_file}")
            all_valid = False
            continue
        
        # Read and validate the file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for test functions
        test_functions = [line.strip() for line in content.split('\n') 
                         if line.strip().startswith('def test_')]
        
        if not test_functions:
            print(f"⚠️  No test functions found in {test_file}")
            all_valid = False
        else:
            print(f"✅ Found {len(test_functions)} test functions")
            for func in test_functions[:3]:  # Show first 3
                print(f"   - {func}")
            if len(test_functions) > 3:
                print(f"   - ... and {len(test_functions) - 3} more")
        
        # Check for proper imports
        if 'from crypto' in content or 'from aggregation' in content or 'from consensus' in content:
            print("✅ Has proper module imports")
        else:
            print("⚠️  May be missing module imports")
        
        # Check for assertions
        if 'assert ' in content:
            print("✅ Has test assertions")
        else:
            print("⚠️  May be missing test assertions")
    
    print("\n" + "=" * 50)
    if all_valid:
        print("🎉 ALL TEST FILES VALIDATED!")
        print("✅ Test structure is correct")
        print("✅ Ready for pytest execution")
        return 0
    else:
        print("❌ SOME VALIDATION ISSUES FOUND!")
        print("⚠️  Please fix issues before running tests")
        return 1

if __name__ == "__main__":
    sys.exit(validate_test_structure())
