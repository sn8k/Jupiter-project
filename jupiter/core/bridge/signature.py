"""Jupiter Plugin Bridge - Plugin Signature System.

Version: 0.1.0

Provides cryptographic signing and verification for plugins.
Ensures trust and integrity of plugin packages.

Trust Levels:
- OFFICIAL: Signed by Jupiter core team (highest trust)
- VERIFIED: Signed by verified third-party developers
- COMMUNITY: Signed by community members
- UNSIGNED: No signature or invalid signature (lowest trust)

Usage:
    from jupiter.core.bridge.signature import (
        sign_plugin,
        verify_plugin,
        get_signature_verifier,
    )
    
    # Sign a plugin
    result = sign_plugin("/path/to/plugin", private_key_path)
    
    # Verify a plugin
    result = verify_plugin("/path/to/plugin")
    print(f"Trust level: {result.trust_level}")
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class TrustLevel(Enum):
    """Trust level for plugin signatures."""
    
    OFFICIAL = "official"      # Signed by Jupiter core team
    VERIFIED = "verified"      # Signed by verified third-party
    COMMUNITY = "community"    # Signed by community member
    UNSIGNED = "unsigned"      # No signature or invalid
    
    @property
    def numeric_level(self) -> int:
        """Get numeric trust level for comparisons."""
        levels = {
            TrustLevel.OFFICIAL: 3,
            TrustLevel.VERIFIED: 2,
            TrustLevel.COMMUNITY: 1,
            TrustLevel.UNSIGNED: 0,
        }
        return levels.get(self, 0)
    
    def __ge__(self, other: "TrustLevel") -> bool:
        return self.numeric_level >= other.numeric_level
    
    def __gt__(self, other: "TrustLevel") -> bool:
        return self.numeric_level > other.numeric_level
    
    def __le__(self, other: "TrustLevel") -> bool:
        return self.numeric_level <= other.numeric_level
    
    def __lt__(self, other: "TrustLevel") -> bool:
        return self.numeric_level < other.numeric_level


class SignatureAlgorithm(Enum):
    """Supported signature algorithms."""
    
    SHA256_RSA = "sha256-rsa"
    SHA512_RSA = "sha512-rsa"
    ED25519 = "ed25519"


# Signature file name
SIGNATURE_FILENAME = "plugin.sig"

# Manifest file to sign
MANIFEST_FILENAME = "plugin.yaml"

# Files to include in hash (in order)
HASH_INCLUDE_PATTERNS = [
    "plugin.yaml",
    "*.py",
    "**/*.py",
]

# Files to exclude from hash
HASH_EXCLUDE_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".git",
    ".venv",
    "plugin.sig",
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SignatureInfo:
    """Information about a plugin signature."""
    
    algorithm: SignatureAlgorithm
    signature: str  # Base64 encoded
    signer_id: str
    signer_name: str
    trust_level: TrustLevel
    timestamp: float
    plugin_id: str
    plugin_version: str
    content_hash: str  # SHA256 of signed content
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "algorithm": self.algorithm.value,
            "signature": self.signature,
            "signer_id": self.signer_id,
            "signer_name": self.signer_name,
            "trust_level": self.trust_level.value,
            "timestamp": self.timestamp,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "content_hash": self.content_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignatureInfo":
        """Deserialize from dictionary."""
        return cls(
            algorithm=SignatureAlgorithm(data["algorithm"]),
            signature=data["signature"],
            signer_id=data["signer_id"],
            signer_name=data["signer_name"],
            trust_level=TrustLevel(data["trust_level"]),
            timestamp=data["timestamp"],
            plugin_id=data["plugin_id"],
            plugin_version=data["plugin_version"],
            content_hash=data["content_hash"],
        )


@dataclass
class VerificationResult:
    """Result of plugin signature verification."""
    
    valid: bool
    trust_level: TrustLevel
    signature_info: Optional[SignatureInfo] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    # Verification details
    content_hash_match: bool = False
    signature_valid: bool = False
    signer_trusted: bool = False
    not_expired: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "valid": self.valid,
            "trust_level": self.trust_level.value,
            "signature_info": self.signature_info.to_dict() if self.signature_info else None,
            "error": self.error,
            "warnings": self.warnings,
            "details": {
                "content_hash_match": self.content_hash_match,
                "signature_valid": self.signature_valid,
                "signer_trusted": self.signer_trusted,
                "not_expired": self.not_expired,
            },
        }


@dataclass
class SigningResult:
    """Result of plugin signing operation."""
    
    success: bool
    signature_path: Optional[Path] = None
    signature_info: Optional[SignatureInfo] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "signature_path": str(self.signature_path) if self.signature_path else None,
            "signature_info": self.signature_info.to_dict() if self.signature_info else None,
            "error": self.error,
        }


@dataclass
class TrustedSigner:
    """A trusted signer entry."""
    
    signer_id: str
    name: str
    public_key: str  # Base64 encoded
    trust_level: TrustLevel
    added_at: float
    expires_at: Optional[float] = None
    revoked: bool = False
    
    def is_valid(self) -> bool:
        """Check if signer is currently valid."""
        if self.revoked:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "signer_id": self.signer_id,
            "name": self.name,
            "public_key": self.public_key,
            "trust_level": self.trust_level.value,
            "added_at": self.added_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustedSigner":
        """Deserialize from dictionary."""
        return cls(
            signer_id=data["signer_id"],
            name=data["name"],
            public_key=data["public_key"],
            trust_level=TrustLevel(data["trust_level"]),
            added_at=data["added_at"],
            expires_at=data.get("expires_at"),
            revoked=data.get("revoked", False),
        )


# =============================================================================
# SIGNATURE VERIFIER
# =============================================================================

class SignatureVerifier:
    """Verifies plugin signatures and manages trusted signers.
    
    The verifier maintains a list of trusted signers and can verify
    plugin signatures against their public keys.
    
    Thread Safety:
        Uses locks for thread-safe signer management.
    """
    
    def __init__(self, trust_store_path: Optional[Path] = None) -> None:
        """Initialize the signature verifier.
        
        Args:
            trust_store_path: Path to trust store file (JSON)
        """
        self._lock = Lock()
        self._trust_store_path = trust_store_path
        self._trusted_signers: Dict[str, TrustedSigner] = {}
        self._verification_log: List[Dict[str, Any]] = []
        self._max_log_entries = 1000
        
        # Configuration
        self._allow_unsigned = False
        self._minimum_trust_level = TrustLevel.UNSIGNED
        self._signature_max_age_days: Optional[int] = None
        
        # Load trust store if exists
        if trust_store_path and trust_store_path.exists():
            self._load_trust_store()
    
    def _load_trust_store(self) -> None:
        """Load trusted signers from file."""
        if not self._trust_store_path:
            return
        
        try:
            with open(self._trust_store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for signer_data in data.get("signers", []):
                signer = TrustedSigner.from_dict(signer_data)
                self._trusted_signers[signer.signer_id] = signer
            
            logger.info("Loaded %d trusted signers", len(self._trusted_signers))
        except Exception as e:
            logger.error("Failed to load trust store: %s", e)
    
    def _save_trust_store(self) -> None:
        """Save trusted signers to file."""
        if not self._trust_store_path:
            return
        
        try:
            data = {
                "signers": [s.to_dict() for s in self._trusted_signers.values()],
            }
            
            self._trust_store_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._trust_store_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save trust store: %s", e)
    
    # -------------------------------------------------------------------------
    # CONFIGURATION
    # -------------------------------------------------------------------------
    
    def set_allow_unsigned(self, allow: bool) -> None:
        """Set whether unsigned plugins are allowed."""
        self._allow_unsigned = allow
    
    def set_minimum_trust_level(self, level: TrustLevel) -> None:
        """Set minimum required trust level."""
        self._minimum_trust_level = level
    
    def set_signature_max_age(self, days: Optional[int]) -> None:
        """Set maximum signature age in days (None for no limit)."""
        self._signature_max_age_days = days
    
    # -------------------------------------------------------------------------
    # SIGNER MANAGEMENT
    # -------------------------------------------------------------------------
    
    def add_trusted_signer(self, signer: TrustedSigner) -> None:
        """Add a trusted signer.
        
        Args:
            signer: Signer to add
        """
        with self._lock:
            self._trusted_signers[signer.signer_id] = signer
            self._save_trust_store()
            logger.info("Added trusted signer: %s (%s)", signer.name, signer.signer_id)
    
    def remove_trusted_signer(self, signer_id: str) -> bool:
        """Remove a trusted signer.
        
        Args:
            signer_id: ID of signer to remove
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if signer_id in self._trusted_signers:
                del self._trusted_signers[signer_id]
                self._save_trust_store()
                logger.info("Removed trusted signer: %s", signer_id)
                return True
            return False
    
    def revoke_signer(self, signer_id: str) -> bool:
        """Revoke a trusted signer (marks as revoked but keeps record).
        
        Args:
            signer_id: ID of signer to revoke
            
        Returns:
            True if revoked, False if not found
        """
        with self._lock:
            if signer_id in self._trusted_signers:
                self._trusted_signers[signer_id].revoked = True
                self._save_trust_store()
                logger.warning("Revoked trusted signer: %s", signer_id)
                return True
            return False
    
    def get_trusted_signer(self, signer_id: str) -> Optional[TrustedSigner]:
        """Get a trusted signer by ID."""
        return self._trusted_signers.get(signer_id)
    
    def list_trusted_signers(self, include_revoked: bool = False) -> List[TrustedSigner]:
        """List all trusted signers.
        
        Args:
            include_revoked: Include revoked signers
            
        Returns:
            List of trusted signers
        """
        signers = list(self._trusted_signers.values())
        if not include_revoked:
            signers = [s for s in signers if not s.revoked]
        return signers
    
    # -------------------------------------------------------------------------
    # VERIFICATION
    # -------------------------------------------------------------------------
    
    def verify_plugin(self, plugin_path: Path) -> VerificationResult:
        """Verify a plugin's signature.
        
        Args:
            plugin_path: Path to plugin directory
            
        Returns:
            VerificationResult with details
        """
        plugin_path = Path(plugin_path)
        warnings: List[str] = []
        
        # Check plugin directory exists
        if not plugin_path.is_dir():
            return VerificationResult(
                valid=False,
                trust_level=TrustLevel.UNSIGNED,
                error=f"Plugin directory not found: {plugin_path}",
            )
        
        # Check for signature file
        sig_path = plugin_path / SIGNATURE_FILENAME
        if not sig_path.exists():
            if self._allow_unsigned:
                self._log_verification(plugin_path, True, TrustLevel.UNSIGNED)
                return VerificationResult(
                    valid=True,
                    trust_level=TrustLevel.UNSIGNED,
                    warnings=["Plugin is unsigned"],
                )
            self._log_verification(plugin_path, False, TrustLevel.UNSIGNED)
            return VerificationResult(
                valid=False,
                trust_level=TrustLevel.UNSIGNED,
                error="Plugin is not signed (no plugin.sig found)",
            )
        
        # Load signature
        try:
            with open(sig_path, "r", encoding="utf-8") as f:
                sig_data = json.load(f)
            sig_info = SignatureInfo.from_dict(sig_data)
        except Exception as e:
            return VerificationResult(
                valid=False,
                trust_level=TrustLevel.UNSIGNED,
                error=f"Failed to load signature: {e}",
            )
        
        # Calculate content hash
        current_hash = self._calculate_plugin_hash(plugin_path)
        content_hash_match = (current_hash == sig_info.content_hash)
        
        if not content_hash_match:
            return VerificationResult(
                valid=False,
                trust_level=TrustLevel.UNSIGNED,
                signature_info=sig_info,
                error="Content hash mismatch - plugin may have been modified",
                content_hash_match=False,
            )
        
        # Check signer
        signer = self._trusted_signers.get(sig_info.signer_id)
        signer_trusted = signer is not None and signer.is_valid()
        
        if not signer_trusted:
            if signer and signer.revoked:
                return VerificationResult(
                    valid=False,
                    trust_level=TrustLevel.UNSIGNED,
                    signature_info=sig_info,
                    error="Signer has been revoked",
                    content_hash_match=True,
                    signer_trusted=False,
                )
            warnings.append("Signer is not in trusted list")
        
        # Verify cryptographic signature
        signature_valid = self._verify_cryptographic_signature(
            plugin_path, sig_info, signer
        )
        
        if not signature_valid:
            return VerificationResult(
                valid=False,
                trust_level=TrustLevel.UNSIGNED,
                signature_info=sig_info,
                error="Cryptographic signature verification failed",
                content_hash_match=True,
                signature_valid=False,
                signer_trusted=signer_trusted,
            )
        
        # Check signature age
        not_expired = True
        if self._signature_max_age_days:
            age_days = (time.time() - sig_info.timestamp) / (24 * 60 * 60)
            if age_days > self._signature_max_age_days:
                not_expired = False
                warnings.append(f"Signature is {int(age_days)} days old (max: {self._signature_max_age_days})")
        
        # Determine trust level
        if signer_trusted and signer:
            trust_level = signer.trust_level
        else:
            trust_level = TrustLevel.COMMUNITY
            warnings.append("Signer not verified - assigned COMMUNITY trust level")
        
        # Check minimum trust level
        if trust_level < self._minimum_trust_level:
            return VerificationResult(
                valid=False,
                trust_level=trust_level,
                signature_info=sig_info,
                error=f"Trust level {trust_level.value} is below minimum {self._minimum_trust_level.value}",
                content_hash_match=True,
                signature_valid=True,
                signer_trusted=signer_trusted,
                not_expired=not_expired,
            )
        
        # Log verification
        self._log_verification(plugin_path, True, trust_level)
        
        return VerificationResult(
            valid=True,
            trust_level=trust_level,
            signature_info=sig_info,
            warnings=warnings,
            content_hash_match=True,
            signature_valid=True,
            signer_trusted=signer_trusted,
            not_expired=not_expired,
        )
    
    def _calculate_plugin_hash(self, plugin_path: Path) -> str:
        """Calculate hash of plugin content.
        
        Hashes all relevant files in deterministic order.
        """
        hasher = hashlib.sha256()
        
        # Get all files to hash
        files_to_hash: List[Path] = []
        
        for pattern in HASH_INCLUDE_PATTERNS:
            if "**" in pattern:
                files_to_hash.extend(plugin_path.glob(pattern))
            else:
                match = plugin_path / pattern
                if match.exists():
                    files_to_hash.append(match)
        
        # Filter out excluded patterns
        def should_exclude(p: Path) -> bool:
            for excl in HASH_EXCLUDE_PATTERNS:
                if excl in str(p):
                    return True
            return False
        
        files_to_hash = [f for f in files_to_hash if f.is_file() and not should_exclude(f)]
        
        # Sort for deterministic ordering
        files_to_hash.sort(key=lambda p: str(p.relative_to(plugin_path)))
        
        # Hash each file
        for file_path in files_to_hash:
            # Include relative path in hash
            rel_path = str(file_path.relative_to(plugin_path))
            hasher.update(rel_path.encode("utf-8"))
            
            # Hash file content
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def _verify_cryptographic_signature(
        self,
        plugin_path: Path,
        sig_info: SignatureInfo,
        signer: Optional[TrustedSigner],
    ) -> bool:
        """Verify the cryptographic signature.
        
        Note: This is a simplified implementation. In production,
        use proper cryptographic libraries (cryptography, nacl).
        """
        # For now, we do a simplified verification based on hash matching
        # A full implementation would use RSA/Ed25519 signature verification
        
        if not signer:
            # Can't verify without public key, but hash matched
            # This is acceptable for community-level trust
            return True
        
        try:
            # Decode signature
            sig_bytes = base64.b64decode(sig_info.signature)
            
            # In a real implementation:
            # 1. Load signer's public key
            # 2. Verify signature against content_hash
            # 3. Use cryptography.hazmat.primitives.asymmetric
            
            # Simplified: signature should contain hash signed with private key
            # For demo, we just check that signature is not empty
            return len(sig_bytes) > 0
            
        except Exception as e:
            logger.error("Signature verification failed: %s", e)
            return False
    
    def _log_verification(
        self,
        plugin_path: Path,
        valid: bool,
        trust_level: TrustLevel,
    ) -> None:
        """Log a verification result."""
        entry = {
            "plugin_path": str(plugin_path),
            "valid": valid,
            "trust_level": trust_level.value,
            "timestamp": time.time(),
        }
        
        self._verification_log.append(entry)
        
        # Trim log if needed
        if len(self._verification_log) > self._max_log_entries:
            self._verification_log = self._verification_log[-self._max_log_entries:]
    
    def get_verification_log(
        self,
        limit: int = 100,
        plugin_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get verification log entries.
        
        Args:
            limit: Maximum entries to return
            plugin_path: Filter by plugin path
            
        Returns:
            List of log entries
        """
        entries = self._verification_log
        
        if plugin_path:
            entries = [e for e in entries if plugin_path in e["plugin_path"]]
        
        return list(reversed(entries[-limit:]))


# =============================================================================
# PLUGIN SIGNER
# =============================================================================

class PluginSigner:
    """Signs plugins with cryptographic signatures.
    
    Creates plugin.sig files containing signature information.
    """
    
    def __init__(
        self,
        signer_id: str,
        signer_name: str,
        private_key_path: Optional[Path] = None,
        trust_level: TrustLevel = TrustLevel.COMMUNITY,
    ) -> None:
        """Initialize the plugin signer.
        
        Args:
            signer_id: Unique identifier for this signer
            signer_name: Human-readable name
            private_key_path: Path to private key file
            trust_level: Trust level to assign to signatures
        """
        self._signer_id = signer_id
        self._signer_name = signer_name
        self._private_key_path = private_key_path
        self._trust_level = trust_level
        self._algorithm = SignatureAlgorithm.SHA256_RSA
    
    def sign_plugin(self, plugin_path: Path) -> SigningResult:
        """Sign a plugin.
        
        Creates a plugin.sig file in the plugin directory.
        
        Args:
            plugin_path: Path to plugin directory
            
        Returns:
            SigningResult with details
        """
        plugin_path = Path(plugin_path)
        
        # Validate plugin directory
        if not plugin_path.is_dir():
            return SigningResult(
                success=False,
                error=f"Plugin directory not found: {plugin_path}",
            )
        
        # Check for manifest
        manifest_path = plugin_path / MANIFEST_FILENAME
        if not manifest_path.exists():
            return SigningResult(
                success=False,
                error=f"Plugin manifest not found: {manifest_path}",
            )
        
        # Load manifest for plugin info
        try:
            import yaml
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
            plugin_id = manifest.get("id", plugin_path.name)
            plugin_version = manifest.get("version", "0.0.0")
        except Exception as e:
            return SigningResult(
                success=False,
                error=f"Failed to load manifest: {e}",
            )
        
        # Calculate content hash
        verifier = SignatureVerifier()
        content_hash = verifier._calculate_plugin_hash(plugin_path)
        
        # Create signature
        signature = self._create_signature(content_hash)
        
        # Create signature info
        sig_info = SignatureInfo(
            algorithm=self._algorithm,
            signature=signature,
            signer_id=self._signer_id,
            signer_name=self._signer_name,
            trust_level=self._trust_level,
            timestamp=time.time(),
            plugin_id=plugin_id,
            plugin_version=plugin_version,
            content_hash=content_hash,
        )
        
        # Write signature file
        sig_path = plugin_path / SIGNATURE_FILENAME
        try:
            with open(sig_path, "w", encoding="utf-8") as f:
                json.dump(sig_info.to_dict(), f, indent=2)
        except Exception as e:
            return SigningResult(
                success=False,
                error=f"Failed to write signature: {e}",
            )
        
        logger.info(
            "Signed plugin %s v%s (hash: %s...)",
            plugin_id, plugin_version, content_hash[:16]
        )
        
        return SigningResult(
            success=True,
            signature_path=sig_path,
            signature_info=sig_info,
        )
    
    def _create_signature(self, content_hash: str) -> str:
        """Create cryptographic signature of content hash.
        
        Note: Simplified implementation. In production, use proper
        cryptographic libraries.
        """
        # In a real implementation:
        # 1. Load private key from self._private_key_path
        # 2. Sign the content_hash using RSA/Ed25519
        # 3. Return base64-encoded signature
        
        # Simplified: Create a pseudo-signature for demo
        # This includes signer_id and hash for basic verification
        pseudo_sig = f"{self._signer_id}:{content_hash}:{time.time()}"
        return base64.b64encode(pseudo_sig.encode()).decode()
    
    def get_public_key(self) -> str:
        """Get the public key for this signer.
        
        Returns:
            Base64-encoded public key
        """
        # In a real implementation, derive from private key
        # Simplified: Return a placeholder
        return base64.b64encode(f"pubkey:{self._signer_id}".encode()).decode()


# =============================================================================
# SINGLETON AND MODULE FUNCTIONS
# =============================================================================

_signature_verifier: Optional[SignatureVerifier] = None
_lock = Lock()


def get_signature_verifier() -> SignatureVerifier:
    """Get the singleton SignatureVerifier.
    
    Returns:
        SignatureVerifier instance
    """
    global _signature_verifier
    if _signature_verifier is None:
        with _lock:
            if _signature_verifier is None:
                _signature_verifier = SignatureVerifier()
    return _signature_verifier


def init_signature_verifier(
    trust_store_path: Optional[Path] = None,
    allow_unsigned: bool = False,
    minimum_trust_level: TrustLevel = TrustLevel.UNSIGNED,
) -> SignatureVerifier:
    """Initialize the signature verifier with configuration.
    
    Args:
        trust_store_path: Path to trust store file
        allow_unsigned: Whether to allow unsigned plugins
        minimum_trust_level: Minimum required trust level
        
    Returns:
        Configured SignatureVerifier
    """
    global _signature_verifier
    with _lock:
        _signature_verifier = SignatureVerifier(trust_store_path)
        _signature_verifier.set_allow_unsigned(allow_unsigned)
        _signature_verifier.set_minimum_trust_level(minimum_trust_level)
    return _signature_verifier


def reset_signature_verifier() -> None:
    """Reset the singleton (for testing)."""
    global _signature_verifier
    with _lock:
        _signature_verifier = None


def verify_plugin(plugin_path: Path) -> VerificationResult:
    """Verify a plugin's signature.
    
    Convenience function using the singleton verifier.
    
    Args:
        plugin_path: Path to plugin directory
        
    Returns:
        VerificationResult
    """
    return get_signature_verifier().verify_plugin(plugin_path)


def sign_plugin(
    plugin_path: Path,
    signer_id: str,
    signer_name: str,
    private_key_path: Optional[Path] = None,
    trust_level: TrustLevel = TrustLevel.COMMUNITY,
) -> SigningResult:
    """Sign a plugin.
    
    Convenience function for signing plugins.
    
    Args:
        plugin_path: Path to plugin directory
        signer_id: Signer identifier
        signer_name: Signer name
        private_key_path: Path to private key
        trust_level: Trust level to assign
        
    Returns:
        SigningResult
    """
    signer = PluginSigner(
        signer_id=signer_id,
        signer_name=signer_name,
        private_key_path=private_key_path,
        trust_level=trust_level,
    )
    return signer.sign_plugin(plugin_path)


def is_plugin_trusted(
    plugin_path: Path,
    minimum_level: TrustLevel = TrustLevel.COMMUNITY,
) -> bool:
    """Quick check if a plugin meets minimum trust level.
    
    Args:
        plugin_path: Path to plugin directory
        minimum_level: Minimum acceptable trust level
        
    Returns:
        True if plugin meets minimum trust level
    """
    result = verify_plugin(plugin_path)
    return result.valid and result.trust_level >= minimum_level
