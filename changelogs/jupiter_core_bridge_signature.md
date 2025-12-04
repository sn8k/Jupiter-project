# Changelog – jupiter/core/bridge/signature.py

## Version 0.1.0

### Added
- Initial implementation of plugin signature system
- `TrustLevel` enum: OFFICIAL, VERIFIED, COMMUNITY, UNSIGNED with comparison operators
- `SignatureAlgorithm` enum: SHA256_RSA, SHA512_RSA, ED25519
- `SignatureInfo` dataclass for signature metadata
- `VerificationResult` dataclass for verification outcomes
- `SigningResult` dataclass for signing operation results
- `TrustedSigner` dataclass with public key and revocation support
- `SignatureVerifier` class:
  - Verify plugin signatures with trust level validation
  - Manage trusted signers (add, remove, revoke)
  - Configure minimum trust level and signature expiry
  - Verification logging with history
  - Trust store persistence (save/load JSON)
  - Content hash calculation using SHA256
- `PluginSigner` class:
  - Sign plugins with configurable trust level
  - Generate signature files (plugin.sig)
  - Key generation support (RSA/Ed25519)
- Module-level functions:
  - `get_signature_verifier()` / `init_signature_verifier()` / `reset_signature_verifier()`
  - `verify_plugin()` - convenience function
  - `sign_plugin()` - convenience function
  - `is_plugin_trusted()` - check trust level
- Comprehensive test suite with 58 tests
