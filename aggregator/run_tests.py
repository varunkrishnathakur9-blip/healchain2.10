#!/usr/bin/env python3
"""
HealChain Aggregator - Test Runner
=================================

Simple test runner that handles Python path automatically.
"""

import os
import sys
import subprocess

def run_test(test_path, test_name):
    """Run a specific test with proper Python path."""
    print(f"🧪 Running {test_name}...")
    
    # Add src/ to Python path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(root_dir, "src")
    env = os.environ.copy()
    env['PYTHONPATH'] = src_dir
    
    try:
        result = subprocess.run([
            sys.executable, test_path
        ], env=env, capture_output=True, text=True, cwd=root_dir)
        
        if result.returncode == 0:
            print(f"✅ {test_name} PASSED")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {test_name} FAILED")
            if result.stderr:
                print(result.stderr)
                
    except Exception as e:
        print(f"❌ {test_name} ERROR: {e}")

def main():
    """Run all aggregator tests."""
    print("🔍 HealChain Aggregator Test Runner")
    print("=" * 50)
    
    # Test categories
    tests = [
        ("tests/test_crypto/test_ec_utils.py", "EC Utils Tests"),
        ("tests/test_crypto/test_bsgs.py", "BSGS Tests"),
        ("tests/test_crypto/test_ndd_fe.py", "NDD-FE Tests"),
        ("tests/test_aggregation/test_aggregator.py", "Aggregation Tests"),
        ("tests/integration/test_end_to_end.py", "Integration Tests"),
    ]
    
    results = []
    
    for test_path, test_name in tests:
        run_test(test_path, test_name)
    
    print("\n" + "=" * 50)
    print("🎯 TEST RUNNER COMPLETE")
    print("🚀 All tests can now be run individually or with pytest")

if __name__ == "__main__":
    main()
