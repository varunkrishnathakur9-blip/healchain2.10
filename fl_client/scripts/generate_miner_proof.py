#!/usr/bin/env python3
"""
HealChain FL Client - Miner Proof Generator
============================================

Generates a valid miner proof for Algorithm 2 compliance.
Supports uploading to IPFS Desktop (if running) or outputting JSON.

Usage:
    python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourAddress
    python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourAddress --upload-ipfs
    python scripts/generate_miner_proof.py --dataset chestxray --address 0xYourAddress --output proof.json
"""

import os
import sys
import json
import argparse
import requests
from datetime import datetime, timezone
from typing import Dict, Optional

# Ensure we can import from parent directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def get_system_info() -> Dict:
    """Gather system information for proof."""
    import platform
    import sys
    
    info = {
        "platform": platform.system().lower(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "gpu_available": False,
        "memory_gb": None
    }
    
    # Try to detect GPU
    try:
        import torch
        info["gpu_available"] = torch.cuda.is_available()
    except ImportError:
        pass
    
    # Try to get memory info
    try:
        import psutil
        info["memory_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        pass
    
    return info


def generate_proof(
    dataset: str,
    miner_address: str,
    capabilities: Optional[list] = None,
    system_info: Optional[Dict] = None
) -> Dict:
    """
    Generate a valid miner proof JSON.
    
    Args:
        dataset: Dataset name (e.g., "chestxray", "mnist", "cifar10")
        miner_address: Miner's wallet address
        capabilities: List of system capabilities (optional)
        system_info: System information dict (optional)
    
    Returns:
        Proof dictionary
    """
    if capabilities is None:
        capabilities = [
            "local_training",
            "gradient_computation",
            "ndd_fe_encryption",
            "dgc_compression"
        ]
    
    if system_info is None:
        system_info = get_system_info()
    
    proof = {
        "dataset": dataset,
        "capabilities": capabilities,
        "system_info": system_info,
        "miner_address": miner_address,
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "version": "1.0"
    }
    
    return proof


def upload_to_ipfs(proof_json: Dict, ipfs_api_url: str = "http://localhost:5001") -> Optional[str]:
    """
    Upload proof to IPFS using local IPFS Desktop node.
    
    Args:
        proof_json: Proof dictionary
        ipfs_api_url: IPFS API URL (default: localhost:5001)
    
    Returns:
        IPFS hash (CID) if successful, None otherwise
    """
    try:
        # Convert to JSON string
        json_string = json.dumps(proof_json, indent=2)
        
        # Prepare form data
        files = {
            'file': ('miner_proof.json', json_string.encode('utf-8'), 'application/json')
        }
        
        # Upload to IPFS
        response = requests.post(
            f"{ipfs_api_url}/api/v0/add",
            files=files,
            params={'pin': 'true'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('Hash')
        else:
            print(f"⚠️  IPFS upload failed: {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Cannot connect to IPFS Desktop. Make sure IPFS Desktop is running.")
        return None
    except Exception as e:
        print(f"⚠️  IPFS upload error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Generate miner proof for Algorithm 2 compliance"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        choices=["chestxray", "mnist", "cifar10", "custom"],
        help="Dataset name (must match task dataset)"
    )
    parser.add_argument(
        "--address",
        type=str,
        required=True,
        help="Miner wallet address (0x...)"
    )
    parser.add_argument(
        "--capabilities",
        type=str,
        nargs="+",
        default=None,
        help="Additional capabilities (space-separated)"
    )
    parser.add_argument(
        "--upload-ipfs",
        action="store_true",
        help="Upload proof to IPFS Desktop (requires IPFS Desktop running)"
    )
    parser.add_argument(
        "--ipfs-api",
        type=str,
        default="http://localhost:5001",
        help="IPFS API URL (default: http://localhost:5001)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save proof to JSON file"
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output only JSON string (for direct paste)"
    )
    
    args = parser.parse_args()
    
    # Generate proof
    capabilities = args.capabilities if args.capabilities else None
    proof = generate_proof(
        dataset=args.dataset,
        miner_address=args.address,
        capabilities=capabilities
    )
    
    # Output proof
    if args.json_only:
        # Output as single-line JSON for direct paste
        print(json.dumps(proof))
        return
    
    # Pretty print
    print("=" * 70)
    print("HealChain Miner Proof Generator")
    print("=" * 70)
    print()
    print("Generated Proof:")
    print("-" * 70)
    print(json.dumps(proof, indent=2))
    print("-" * 70)
    print()
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(proof, f, indent=2)
        print(f"✅ Proof saved to: {args.output}")
        print()
    
    # Upload to IPFS if requested
    if args.upload_ipfs:
        print("Uploading to IPFS...")
        ipfs_hash = upload_to_ipfs(proof, args.ipfs_api)
        
        if ipfs_hash:
            print(f"✅ Uploaded to IPFS!")
            print()
            print("IPFS Hash (CID):", ipfs_hash)
            print()
            print("Use one of these formats for registration:")
            print(f"  • ipfs://{ipfs_hash}")
            print(f"  • https://ipfs.io/ipfs/{ipfs_hash}")
            print(f"  • https://gateway.pinata.cloud/ipfs/{ipfs_hash}")
        else:
            print("❌ Failed to upload to IPFS")
            print("You can still use the JSON proof directly:")
            print()
            print("JSON Proof (for direct paste):")
            print(json.dumps(proof))
    else:
        print("Usage Options:")
        print("1. Use JSON directly (paste into registration form):")
        print("   " + json.dumps(proof))
        print()
        print("2. Upload to IPFS and use IPFS link:")
        print(f"   python {sys.argv[0]} --dataset {args.dataset} --address {args.address} --upload-ipfs")
        print()
        print("3. Save to file and upload manually:")
        print(f"   python {sys.argv[0]} --dataset {args.dataset} --address {args.address} --output proof.json")
    
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()

