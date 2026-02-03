# HealChain Aggregator - Key Management
# FE key handling


"""
HealChain Aggregator – Key Manager
=================================

Responsibilities:
-----------------
- Load and store cryptographic keys for a single task
- Provide safe access to:
    - skA  (Aggregator private key)
    - pkA  (Aggregator public key)
    - pkTP (Task Publisher public key)
    - skFE (Functional Encryption key)
- Provide EC point parsing helpers for verifier

NON-RESPONSIBILITIES:
---------------------
- No cryptographic operations
- No backend access
- No smart contract logic
"""

import os
from typing import Optional, Dict

from tinyec import registry
from tinyec.ec import Point

from crypto.ec_utils import (
    curve,
    G,
    parse_point,
    parse_hex_point,
    serialize_point,
)

from utils.logging import get_logger

logger = get_logger("state.key_manager")


class KeyManager:
    """
    Task-scoped cryptographic key container.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id

        # --- Core keys ---
        self.skA: Optional[int] = None
        self.pkA: Optional[Point] = None

        self.pkTP: Optional[Point] = None
        self.skFE: Optional[int] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, backend_receiver=None, aggregator_address: str = None, metadata: Optional[Dict] = None):
        """
        Load all required keys from environment / secure storage.
        
        Algorithm 2.2: skFE is derived deterministically from task metadata.

        REQUIRED ENV VARIABLES:
        -----------------------
        AGGREGATOR_SK        : int
        AGGREGATOR_PK        : "x,y"
        TP_PUBLIC_KEY        : "x,y"
        FE_FUNCTION_KEY      : int (fallback only, not used if backend derivation succeeds)

        Parameters:
        -----------
        backend_receiver : BackendReceiver, optional
            Backend receiver instance for fetching key derivation metadata (Algorithm 2.2)
        aggregator_address : str, optional
            Aggregator's wallet address (for verification)
        metadata : Dict, optional
            Pre-fetched metadata to avoid redundant backend calls
        """

        logger.info(f"[KeyManager] Loading keys for task {self.task_id}")

        # Aggregator private key
        self.skA = self._load_int_env("AGGREGATOR_SK")

        # Aggregator public key
        # Try to load from environment, but we'll validate it matches skA in sanity check
        self.pkA = self._load_point_env("AGGREGATOR_PK")

        # Task Publisher public key
        self.pkTP = self._load_point_env("TP_PUBLIC_KEY")

        # Functional Encryption key (Algorithm 2.2)
        # Derive from backend metadata (deterministic)
        if backend_receiver or metadata:
            try:
                if not metadata and backend_receiver:
                    metadata = backend_receiver.fetch_key_derivation_metadata()
                
                if metadata:
                    # Verify aggregator address matches (if provided)
                    backend_agg = metadata.get("aggregatorAddress", "").lower()
                    if aggregator_address:
                        if backend_agg != aggregator_address.lower():
                            raise ValueError(
                                f"Aggregator address mismatch: "
                                f"expected {aggregator_address}, got {backend_agg}"
                            )
                    else:
                        # Use aggregator address from backend if not in env
                        aggregator_address = backend_agg
                        logger.info(
                            f"[KeyManager] Using aggregator address from backend: {aggregator_address}"
                        )
                    
                    # Derive skFE using same method as backend (Algorithm 2.2)
                    self.skFE = self.derive_skfe_from_task(
                        publisher_address=metadata["publisher"],
                        miner_public_keys=metadata["minerPublicKeys"],
                        nonce_tp=metadata["nonceTP"]
                    )
                    logger.info(
                        f"[KeyManager] skFE derived from backend metadata "
                        f"(Algorithm 2.2): {metadata.get('minerCount', 0)} miners, "
                        f"aggregator: {aggregator_address}"
                    )
                else:
                    raise ValueError("Failed to fetch key derivation metadata")
            except Exception as e:
                logger.warning(
                    f"[KeyManager] Failed to derive skFE from backend: {e}. "
                    "Falling back to FE_FUNCTION_KEY environment variable."
                )
                self.skFE = self._load_int_env("FE_FUNCTION_KEY")
        else:
            # Fallback: use environment variable (for development/testing)
            logger.warning(
                "[KeyManager] Using FE_FUNCTION_KEY from env (not Algorithm 2.2 compliant). "
                "Provide backend_receiver for proper key derivation."
            )
            self.skFE = self._load_int_env("FE_FUNCTION_KEY")

        self._sanity_check()

        logger.info("[KeyManager] All keys loaded successfully")

    # ------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------

    def parse_ciphertext_point(self, hex_point: str) -> Point:
        """
        Parse EC point from miner ciphertext.

        Format (FL-client):
            "x_hex,y_hex"
        """
        return parse_hex_point(hex_point)

    # ------------------------------------------------------------------
    # Internal Loaders
    # ------------------------------------------------------------------

    def _load_int_env(self, name: str) -> int:
        val = os.getenv(name)
        if val is None:
            raise EnvironmentError(f"Missing environment variable: {name}")
        try:
            return int(val)
        except ValueError as e:
            raise ValueError(f"Invalid integer for {name}") from e

    def _load_point_env(self, name: str) -> Point:
        val = os.getenv(name)
        if val is None:
            raise EnvironmentError(f"Missing environment variable: {name}")
        try:
            pt = parse_point(val)
            # Explicitly validate point is on curve (parse_point already does this, but double-check)
            if not curve.on_curve(pt.x, pt.y):
                raise ValueError(
                    f"Point from {name} is not on secp256r1 curve. "
                    f"Please generate new keys using: python scripts/generate_keys.py"
                )
            return pt
        except ValueError as e:
            # Re-raise with more context
            raise ValueError(f"Invalid EC point for {name}: {e}") from e
        except Exception as e:
            raise ValueError(f"Invalid EC point for {name}: {e}") from e

    # ------------------------------------------------------------------
    # Sanity Checks
    # ------------------------------------------------------------------


    def derive_skfe_from_task(
        self,
        publisher_address: str,
        miner_public_keys: list,
        nonce_tp: str
    ) -> int:
        """
        Derive skFE using the same method as backend (Algorithm 2.2).
        
        This is deterministic: same inputs = same skFE.
        Matches backend implementation in keyDerivation.ts:
        skFE = H(publisherAddr || minerPKs || taskID || nonceTP)
        
        Parameters:
        -----------
        publisher_address : str
            Task publisher's wallet address
        miner_public_keys : list[str]
            List of miner public keys (should be sorted)
        nonce_tp : str
            Nonce from M1 task creation (64 hex chars)
        
        Returns:
        --------
        skFE : int
            Functional encryption key
        """
        # Build input string (same as backend: keyDerivation.ts line 69)
        # Format: publisher || pk1 || pk2 || ... || taskID || nonce
        input_parts = [
            publisher_address.lower(),  # Normalize like backend
            *sorted(miner_public_keys),  # Sort for deterministic order
            self.task_id,
            nonce_tp
        ]
        input_string = "||".join(input_parts)
        
        # Hash using keccak256 (same as backend uses ethers.keccak256)
        # Python equivalent: use pycryptodome's keccak (has Windows wheels)
        try:
            from Crypto.Hash import keccak
            k = keccak.new(digest_bits=256)
            k.update(input_string.encode('utf-8'))
            hash_hex = k.hexdigest()
        except ImportError:
            # Fallback: try pysha3 (requires compilation on Windows)
            try:
                import sha3
                k = sha3.keccak_256()
                k.update(input_string.encode('utf-8'))
                hash_hex = k.hexdigest()
            except ImportError:
                raise ImportError(
                    "keccak256 not available. Install pycryptodome: pip install pycryptodome"
                )
        
        # Convert to int and reduce modulo curve order (same as backend)
        # secp256r1 curve order (from keyDerivation.ts line 77)
        CURVE_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
        skFE = int(hash_hex, 16) % CURVE_ORDER
        
        # Ensure non-zero (same check as backend line 81)
        if skFE == 0:
            raise ValueError("Derived skFE is zero (extremely unlikely)")
        
        logger.info(f"[KeyManager] skFE derived: {skFE} (from {len(miner_public_keys)} miners)")
        return skFE

    def _sanity_check(self):
        """
        Ensure keys are internally consistent.
        """

        if self.skA <= 0:
            raise ValueError("Invalid aggregator private key")

        # Verify pkA = skA * G
        derived_pkA = self.skA * G
        if derived_pkA != self.pkA:
            # Provide detailed error message with guidance
            logger.warning(
                f"[KeyManager] Public key mismatch detected:\n"
                f"  Derived from SK: ({derived_pkA.x}, {derived_pkA.y})\n"
                f"  From AGGREGATOR_PK: ({self.pkA.x}, {self.pkA.y})\n"
                f"  Auto-correcting: Using derived public key from AGGREGATOR_SK"
            )
            # Auto-correct: use the derived public key (pkA is public anyway, so deriving from skA is safe)
            self.pkA = derived_pkA
            logger.info(
                "[KeyManager] Using derived public key. "
                "Consider updating AGGREGATOR_PK environment variable to match: "
                f"{serialize_point(derived_pkA)}"
            )

        if self.skFE <= 0:
            raise ValueError("Invalid FE function key")

        if not curve.on_curve(self.pkTP.x, self.pkTP.y):
            raise ValueError(
                "TP public key not on curve. "
                "Please check TP_PUBLIC_KEY environment variable."
            )

        logger.info("[KeyManager] Key sanity check passed")
