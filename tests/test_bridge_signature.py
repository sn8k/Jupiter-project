"""Tests for Plugin Signature System.

Tests cryptographic signing and verification of plugins.
"""

from __future__ import annotations

import json
import pytest
import tempfile
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.signature import (
    TrustLevel,
    SignatureAlgorithm,
    SignatureInfo,
    VerificationResult,
    SigningResult,
    TrustedSigner,
    SignatureVerifier,
    PluginSigner,
    get_signature_verifier,
    init_signature_verifier,
    reset_signature_verifier,
    verify_plugin,
    sign_plugin,
    is_plugin_trusted,
    SIGNATURE_FILENAME,
    MANIFEST_FILENAME,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_plugin_dir(tmp_path):
    """Create a temporary plugin directory with manifest."""
    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()
    
    # Create manifest
    manifest = {
        "id": "test_plugin",
        "version": "1.0.0",
        "name": "Test Plugin",
    }
    manifest_path = plugin_dir / MANIFEST_FILENAME
    
    import yaml
    with open(manifest_path, "w", encoding="utf-8") as f:
        yaml.dump(manifest, f)
    
    # Create a Python file
    (plugin_dir / "__init__.py").write_text("# Test plugin\n")
    
    return plugin_dir


@pytest.fixture
def verifier():
    """Create a fresh SignatureVerifier."""
    return SignatureVerifier()


@pytest.fixture
def signer():
    """Create a PluginSigner."""
    return PluginSigner(
        signer_id="test-signer",
        signer_name="Test Signer",
        trust_level=TrustLevel.COMMUNITY,
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton after each test."""
    yield
    reset_signature_verifier()


# =============================================================================
# TESTS: TRUST LEVEL
# =============================================================================

class TestTrustLevel:
    """Tests for TrustLevel enum."""
    
    def test_numeric_levels(self):
        """Test numeric level values."""
        assert TrustLevel.UNSIGNED.numeric_level == 0
        assert TrustLevel.COMMUNITY.numeric_level == 1
        assert TrustLevel.VERIFIED.numeric_level == 2
        assert TrustLevel.OFFICIAL.numeric_level == 3
    
    def test_comparison_operators(self):
        """Test trust level comparisons."""
        assert TrustLevel.OFFICIAL > TrustLevel.VERIFIED
        assert TrustLevel.VERIFIED > TrustLevel.COMMUNITY
        assert TrustLevel.COMMUNITY > TrustLevel.UNSIGNED
        
        assert TrustLevel.UNSIGNED < TrustLevel.COMMUNITY
        assert TrustLevel.COMMUNITY <= TrustLevel.COMMUNITY
        assert TrustLevel.OFFICIAL >= TrustLevel.VERIFIED
    
    def test_values(self):
        """Test enum values."""
        assert TrustLevel.OFFICIAL.value == "official"
        assert TrustLevel.VERIFIED.value == "verified"
        assert TrustLevel.COMMUNITY.value == "community"
        assert TrustLevel.UNSIGNED.value == "unsigned"


class TestSignatureAlgorithm:
    """Tests for SignatureAlgorithm enum."""
    
    def test_values(self):
        """Test algorithm values."""
        assert SignatureAlgorithm.SHA256_RSA.value == "sha256-rsa"
        assert SignatureAlgorithm.SHA512_RSA.value == "sha512-rsa"
        assert SignatureAlgorithm.ED25519.value == "ed25519"


# =============================================================================
# TESTS: SIGNATURE INFO
# =============================================================================

class TestSignatureInfo:
    """Tests for SignatureInfo dataclass."""
    
    def test_create(self):
        """Test creating SignatureInfo."""
        info = SignatureInfo(
            algorithm=SignatureAlgorithm.SHA256_RSA,
            signature="c2lnbmF0dXJl",
            signer_id="test-signer",
            signer_name="Test Signer",
            trust_level=TrustLevel.COMMUNITY,
            timestamp=1234567890.0,
            plugin_id="test_plugin",
            plugin_version="1.0.0",
            content_hash="abc123",
        )
        
        assert info.algorithm == SignatureAlgorithm.SHA256_RSA
        assert info.signer_id == "test-signer"
        assert info.trust_level == TrustLevel.COMMUNITY
    
    def test_to_dict(self):
        """Test serialization to dict."""
        info = SignatureInfo(
            algorithm=SignatureAlgorithm.SHA256_RSA,
            signature="c2lnbmF0dXJl",
            signer_id="test-signer",
            signer_name="Test Signer",
            trust_level=TrustLevel.COMMUNITY,
            timestamp=1234567890.0,
            plugin_id="test_plugin",
            plugin_version="1.0.0",
            content_hash="abc123",
        )
        
        data = info.to_dict()
        
        assert data["algorithm"] == "sha256-rsa"
        assert data["trust_level"] == "community"
        assert data["plugin_id"] == "test_plugin"
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "algorithm": "sha256-rsa",
            "signature": "c2lnbmF0dXJl",
            "signer_id": "test-signer",
            "signer_name": "Test Signer",
            "trust_level": "verified",
            "timestamp": 1234567890.0,
            "plugin_id": "test_plugin",
            "plugin_version": "1.0.0",
            "content_hash": "abc123",
        }
        
        info = SignatureInfo.from_dict(data)
        
        assert info.algorithm == SignatureAlgorithm.SHA256_RSA
        assert info.trust_level == TrustLevel.VERIFIED
        assert info.plugin_id == "test_plugin"
    
    def test_roundtrip(self):
        """Test serialization roundtrip."""
        original = SignatureInfo(
            algorithm=SignatureAlgorithm.ED25519,
            signature="c2lnbmF0dXJl",
            signer_id="test-signer",
            signer_name="Test Signer",
            trust_level=TrustLevel.OFFICIAL,
            timestamp=time.time(),
            plugin_id="test_plugin",
            plugin_version="2.0.0",
            content_hash="def456",
        )
        
        data = original.to_dict()
        restored = SignatureInfo.from_dict(data)
        
        assert restored.algorithm == original.algorithm
        assert restored.trust_level == original.trust_level
        assert restored.content_hash == original.content_hash


# =============================================================================
# TESTS: VERIFICATION RESULT
# =============================================================================

class TestVerificationResult:
    """Tests for VerificationResult dataclass."""
    
    def test_valid_result(self):
        """Test valid verification result."""
        result = VerificationResult(
            valid=True,
            trust_level=TrustLevel.VERIFIED,
            content_hash_match=True,
            signature_valid=True,
            signer_trusted=True,
        )
        
        assert result.valid is True
        assert result.trust_level == TrustLevel.VERIFIED
        assert result.error is None
    
    def test_invalid_result(self):
        """Test invalid verification result."""
        result = VerificationResult(
            valid=False,
            trust_level=TrustLevel.UNSIGNED,
            error="Signature verification failed",
            content_hash_match=False,
        )
        
        assert result.valid is False
        assert result.error == "Signature verification failed"
    
    def test_to_dict(self):
        """Test serialization."""
        result = VerificationResult(
            valid=True,
            trust_level=TrustLevel.COMMUNITY,
            warnings=["Test warning"],
        )
        
        data = result.to_dict()
        
        assert data["valid"] is True
        assert data["trust_level"] == "community"
        assert "Test warning" in data["warnings"]


# =============================================================================
# TESTS: SIGNING RESULT
# =============================================================================

class TestSigningResult:
    """Tests for SigningResult dataclass."""
    
    def test_success_result(self):
        """Test successful signing result."""
        result = SigningResult(
            success=True,
            signature_path=Path("/path/to/plugin.sig"),
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_failure_result(self):
        """Test failed signing result."""
        result = SigningResult(
            success=False,
            error="Failed to sign plugin",
        )
        
        assert result.success is False
        assert result.error == "Failed to sign plugin"
    
    def test_to_dict(self):
        """Test serialization."""
        result = SigningResult(
            success=True,
            signature_path=Path("/path/to/plugin.sig"),
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        # Path may use backslashes on Windows
        assert Path(data["signature_path"]) == Path("/path/to/plugin.sig")


# =============================================================================
# TESTS: TRUSTED SIGNER
# =============================================================================

class TestTrustedSigner:
    """Tests for TrustedSigner dataclass."""
    
    def test_create(self):
        """Test creating a trusted signer."""
        signer = TrustedSigner(
            signer_id="jupiter-official",
            name="Jupiter Official",
            public_key="cHVia2V5",
            trust_level=TrustLevel.OFFICIAL,
            added_at=time.time(),
        )
        
        assert signer.signer_id == "jupiter-official"
        assert signer.trust_level == TrustLevel.OFFICIAL
        assert signer.revoked is False
    
    def test_is_valid_normal(self):
        """Test validity of normal signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        
        assert signer.is_valid() is True
    
    def test_is_valid_revoked(self):
        """Test validity of revoked signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
            revoked=True,
        )
        
        assert signer.is_valid() is False
    
    def test_is_valid_expired(self):
        """Test validity of expired signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time() - 1000,
            expires_at=time.time() - 100,  # Expired 100 seconds ago
        )
        
        assert signer.is_valid() is False
    
    def test_to_dict(self):
        """Test serialization."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.COMMUNITY,
            added_at=1234567890.0,
        )
        
        data = signer.to_dict()
        
        assert data["signer_id"] == "test"
        assert data["trust_level"] == "community"
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "signer_id": "test",
            "name": "Test",
            "public_key": "key",
            "trust_level": "official",
            "added_at": 1234567890.0,
        }
        
        signer = TrustedSigner.from_dict(data)
        
        assert signer.trust_level == TrustLevel.OFFICIAL


# =============================================================================
# TESTS: SIGNATURE VERIFIER
# =============================================================================

class TestSignatureVerifierInit:
    """Tests for SignatureVerifier initialization."""
    
    def test_create_default(self):
        """Test creating with defaults."""
        verifier = SignatureVerifier()
        
        assert verifier._allow_unsigned is False
        assert verifier._minimum_trust_level == TrustLevel.UNSIGNED
    
    def test_create_with_trust_store(self, tmp_path):
        """Test creating with trust store."""
        trust_store = tmp_path / "trust_store.json"
        trust_store.write_text('{"signers": []}')
        
        verifier = SignatureVerifier(trust_store_path=trust_store)
        
        assert verifier._trust_store_path == trust_store


class TestSignatureVerifierConfig:
    """Tests for SignatureVerifier configuration."""
    
    def test_set_allow_unsigned(self, verifier):
        """Test setting allow_unsigned."""
        verifier.set_allow_unsigned(True)
        assert verifier._allow_unsigned is True
    
    def test_set_minimum_trust_level(self, verifier):
        """Test setting minimum trust level."""
        verifier.set_minimum_trust_level(TrustLevel.VERIFIED)
        assert verifier._minimum_trust_level == TrustLevel.VERIFIED
    
    def test_set_signature_max_age(self, verifier):
        """Test setting max signature age."""
        verifier.set_signature_max_age(30)
        assert verifier._signature_max_age_days == 30


class TestSignatureVerifierSigners:
    """Tests for signer management."""
    
    def test_add_trusted_signer(self, verifier):
        """Test adding a trusted signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        
        verifier.add_trusted_signer(signer)
        
        assert verifier.get_trusted_signer("test") is not None
    
    def test_remove_trusted_signer(self, verifier):
        """Test removing a trusted signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        
        verifier.add_trusted_signer(signer)
        result = verifier.remove_trusted_signer("test")
        
        assert result is True
        assert verifier.get_trusted_signer("test") is None
    
    def test_remove_nonexistent_signer(self, verifier):
        """Test removing nonexistent signer."""
        result = verifier.remove_trusted_signer("nonexistent")
        assert result is False
    
    def test_revoke_signer(self, verifier):
        """Test revoking a signer."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        
        verifier.add_trusted_signer(signer)
        result = verifier.revoke_signer("test")
        
        assert result is True
        assert verifier.get_trusted_signer("test").revoked is True
    
    def test_list_trusted_signers(self, verifier):
        """Test listing signers."""
        for i in range(3):
            signer = TrustedSigner(
                signer_id=f"signer-{i}",
                name=f"Signer {i}",
                public_key="key",
                trust_level=TrustLevel.COMMUNITY,
                added_at=time.time(),
            )
            verifier.add_trusted_signer(signer)
        
        signers = verifier.list_trusted_signers()
        assert len(signers) == 3
    
    def test_list_excludes_revoked(self, verifier):
        """Test that list excludes revoked by default."""
        signer = TrustedSigner(
            signer_id="test",
            name="Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        
        verifier.add_trusted_signer(signer)
        verifier.revoke_signer("test")
        
        signers = verifier.list_trusted_signers(include_revoked=False)
        assert len(signers) == 0
        
        signers = verifier.list_trusted_signers(include_revoked=True)
        assert len(signers) == 1


class TestSignatureVerifierVerify:
    """Tests for plugin verification."""
    
    def test_verify_nonexistent_plugin(self, verifier):
        """Test verifying nonexistent plugin."""
        result = verifier.verify_plugin(Path("/nonexistent"))
        
        assert result.valid is False
        assert "not found" in result.error
    
    def test_verify_unsigned_plugin_not_allowed(self, verifier, temp_plugin_dir):
        """Test verifying unsigned plugin when not allowed."""
        verifier.set_allow_unsigned(False)
        
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is False
        assert result.trust_level == TrustLevel.UNSIGNED
        assert "not signed" in result.error
    
    def test_verify_unsigned_plugin_allowed(self, verifier, temp_plugin_dir):
        """Test verifying unsigned plugin when allowed."""
        verifier.set_allow_unsigned(True)
        
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is True
        assert result.trust_level == TrustLevel.UNSIGNED
        assert "unsigned" in result.warnings[0].lower()
    
    def test_verify_signed_plugin(self, verifier, temp_plugin_dir, signer):
        """Test verifying a signed plugin."""
        # Sign the plugin first
        sign_result = signer.sign_plugin(temp_plugin_dir)
        assert sign_result.success is True
        
        # Verify
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is True
        assert result.content_hash_match is True
        assert result.signature_info is not None
    
    def test_verify_modified_plugin(self, verifier, temp_plugin_dir, signer):
        """Test verifying a plugin modified after signing."""
        # Sign the plugin
        signer.sign_plugin(temp_plugin_dir)
        
        # Modify the plugin
        (temp_plugin_dir / "__init__.py").write_text("# Modified content\n")
        
        # Verify
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is False
        assert result.content_hash_match is False
        assert "modified" in result.error.lower()
    
    def test_verify_below_minimum_trust(self, verifier, temp_plugin_dir, signer):
        """Test verifying plugin below minimum trust level."""
        # Sign with community level
        signer.sign_plugin(temp_plugin_dir)
        
        # Require verified level
        verifier.set_minimum_trust_level(TrustLevel.VERIFIED)
        
        # Verify
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is False
        assert "below minimum" in result.error


class TestSignatureVerifierHash:
    """Tests for content hashing."""
    
    def test_hash_deterministic(self, verifier, temp_plugin_dir):
        """Test that hashing is deterministic."""
        hash1 = verifier._calculate_plugin_hash(temp_plugin_dir)
        hash2 = verifier._calculate_plugin_hash(temp_plugin_dir)
        
        assert hash1 == hash2
    
    def test_hash_changes_with_content(self, verifier, temp_plugin_dir):
        """Test that hash changes when content changes."""
        hash1 = verifier._calculate_plugin_hash(temp_plugin_dir)
        
        # Modify content
        (temp_plugin_dir / "__init__.py").write_text("# Changed\n")
        
        hash2 = verifier._calculate_plugin_hash(temp_plugin_dir)
        
        assert hash1 != hash2


class TestSignatureVerifierLog:
    """Tests for verification logging."""
    
    def test_get_verification_log_empty(self, verifier):
        """Test getting empty log."""
        log = verifier.get_verification_log()
        assert log == []
    
    def test_verification_logged(self, verifier, temp_plugin_dir):
        """Test that verifications are logged."""
        verifier.set_allow_unsigned(True)
        verifier.verify_plugin(temp_plugin_dir)
        
        log = verifier.get_verification_log()
        
        assert len(log) == 1
        assert log[0]["valid"] is True
    
    def test_log_limit(self, verifier, temp_plugin_dir):
        """Test log limit."""
        verifier.set_allow_unsigned(True)
        
        for _ in range(5):
            verifier.verify_plugin(temp_plugin_dir)
        
        log = verifier.get_verification_log(limit=3)
        
        assert len(log) == 3


# =============================================================================
# TESTS: PLUGIN SIGNER
# =============================================================================

class TestPluginSignerInit:
    """Tests for PluginSigner initialization."""
    
    def test_create(self):
        """Test creating a signer."""
        signer = PluginSigner(
            signer_id="test",
            signer_name="Test",
            trust_level=TrustLevel.VERIFIED,
        )
        
        assert signer._signer_id == "test"
        assert signer._trust_level == TrustLevel.VERIFIED


class TestPluginSignerSign:
    """Tests for plugin signing."""
    
    def test_sign_plugin(self, signer, temp_plugin_dir):
        """Test signing a plugin."""
        result = signer.sign_plugin(temp_plugin_dir)
        
        assert result.success is True
        assert result.signature_path == temp_plugin_dir / SIGNATURE_FILENAME
        assert result.signature_info is not None
        assert result.signature_info.signer_id == "test-signer"
    
    def test_sign_nonexistent_plugin(self, signer):
        """Test signing nonexistent plugin."""
        result = signer.sign_plugin(Path("/nonexistent"))
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_sign_plugin_without_manifest(self, signer, tmp_path):
        """Test signing plugin without manifest."""
        plugin_dir = tmp_path / "no_manifest"
        plugin_dir.mkdir()
        
        result = signer.sign_plugin(plugin_dir)
        
        assert result.success is False
        assert "manifest" in result.error.lower()
    
    def test_signature_file_created(self, signer, temp_plugin_dir):
        """Test that signature file is created."""
        signer.sign_plugin(temp_plugin_dir)
        
        sig_path = temp_plugin_dir / SIGNATURE_FILENAME
        assert sig_path.exists()
    
    def test_signature_file_content(self, signer, temp_plugin_dir):
        """Test signature file content."""
        signer.sign_plugin(temp_plugin_dir)
        
        sig_path = temp_plugin_dir / SIGNATURE_FILENAME
        with open(sig_path, "r") as f:
            data = json.load(f)
        
        assert "algorithm" in data
        assert "signature" in data
        assert "signer_id" in data
        assert data["plugin_id"] == "test_plugin"


class TestPluginSignerPublicKey:
    """Tests for public key generation."""
    
    def test_get_public_key(self, signer):
        """Test getting public key."""
        public_key = signer.get_public_key()
        
        assert public_key is not None
        assert len(public_key) > 0


# =============================================================================
# TESTS: MODULE FUNCTIONS
# =============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""
    
    def test_get_signature_verifier_singleton(self):
        """Test singleton access."""
        v1 = get_signature_verifier()
        v2 = get_signature_verifier()
        
        assert v1 is v2
    
    def test_init_signature_verifier(self):
        """Test initialization function."""
        verifier = init_signature_verifier(
            allow_unsigned=True,
            minimum_trust_level=TrustLevel.COMMUNITY,
        )
        
        assert verifier._allow_unsigned is True
        assert verifier._minimum_trust_level == TrustLevel.COMMUNITY
    
    def test_reset_signature_verifier(self):
        """Test singleton reset."""
        v1 = get_signature_verifier()
        reset_signature_verifier()
        v2 = get_signature_verifier()
        
        assert v1 is not v2
    
    def test_verify_plugin_function(self, temp_plugin_dir):
        """Test convenience verify function."""
        init_signature_verifier(allow_unsigned=True)
        
        result = verify_plugin(temp_plugin_dir)
        
        assert result.valid is True
    
    def test_sign_plugin_function(self, temp_plugin_dir):
        """Test convenience sign function."""
        result = sign_plugin(
            temp_plugin_dir,
            signer_id="cli-signer",
            signer_name="CLI Signer",
        )
        
        assert result.success is True
    
    def test_is_plugin_trusted(self, temp_plugin_dir, signer):
        """Test trust check function."""
        init_signature_verifier(allow_unsigned=True)
        
        # Unsigned plugin with UNSIGNED minimum
        trusted = is_plugin_trusted(temp_plugin_dir, TrustLevel.UNSIGNED)
        assert trusted is True
        
        # Unsigned plugin with COMMUNITY minimum
        trusted = is_plugin_trusted(temp_plugin_dir, TrustLevel.COMMUNITY)
        assert trusted is False


# =============================================================================
# TESTS: TRUST STORE PERSISTENCE
# =============================================================================

class TestTrustStorePersistence:
    """Tests for trust store file operations."""
    
    def test_save_and_load_trust_store(self, tmp_path):
        """Test saving and loading trust store."""
        trust_store = tmp_path / "trust_store.json"
        
        # Create verifier and add signer
        v1 = SignatureVerifier(trust_store_path=trust_store)
        signer = TrustedSigner(
            signer_id="persist-test",
            name="Persist Test",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        v1.add_trusted_signer(signer)
        
        # Create new verifier and load
        v2 = SignatureVerifier(trust_store_path=trust_store)
        
        loaded = v2.get_trusted_signer("persist-test")
        assert loaded is not None
        assert loaded.name == "Persist Test"
    
    def test_load_nonexistent_trust_store(self, tmp_path):
        """Test loading nonexistent trust store."""
        trust_store = tmp_path / "nonexistent.json"
        
        verifier = SignatureVerifier(trust_store_path=trust_store)
        
        assert len(verifier.list_trusted_signers()) == 0


# =============================================================================
# TESTS: REVOKED SIGNER VERIFICATION
# =============================================================================

class TestRevokedSignerVerification:
    """Tests for handling revoked signers during verification."""
    
    def test_verify_with_revoked_signer(self, verifier, temp_plugin_dir):
        """Test that verification fails if signer was revoked."""
        # Add and then revoke signer
        signer = TrustedSigner(
            signer_id="test-signer",
            name="Test Signer",
            public_key="key",
            trust_level=TrustLevel.VERIFIED,
            added_at=time.time(),
        )
        verifier.add_trusted_signer(signer)
        
        # Sign plugin
        plugin_signer = PluginSigner(
            signer_id="test-signer",
            signer_name="Test Signer",
            trust_level=TrustLevel.VERIFIED,
        )
        plugin_signer.sign_plugin(temp_plugin_dir)
        
        # Revoke signer
        verifier.revoke_signer("test-signer")
        
        # Verify should fail
        result = verifier.verify_plugin(temp_plugin_dir)
        
        assert result.valid is False
        assert "revoked" in result.error.lower()
