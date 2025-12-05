"""Tests for Jupiter Plugin manifest parsing.

Version: 0.1.0

This module tests the manifest loading and validation in
jupiter/core/bridge/manifest.py.
"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict

from jupiter.core.bridge.manifest import (
    PluginManifest,
    generate_manifest_for_legacy,
    _validate_with_schema,
)
from jupiter.core.bridge.interfaces import (
    PluginType,
    Permission,
    UILocation,
)
from jupiter.core.bridge.exceptions import ManifestError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def minimal_manifest_data() -> Dict[str, Any]:
    """Minimal valid manifest data."""
    return {
        "id": "test_plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "type": "tool",
        "jupiter_version": ">=1.0.0",
    }


@pytest.fixture
def full_manifest_data() -> Dict[str, Any]:
    """Complete manifest data with all fields."""
    return {
        "id": "full_plugin",
        "name": "Full Test Plugin",
        "version": "2.0.0",
        "description": "A complete test plugin with all features",
        "type": "system",
        "jupiter_version": ">=1.5.0",
        "author": {
            "name": "Test Author",
            "email": "test@example.com",
        },
        "license": "MIT",
        "trust_level": "verified",
        "extends": False,
        "permissions": [
            "fs_read",
            "fs_write",
            "emit_events",
            "register_api",
        ],
        "dependencies": {
            "other_plugin": ">=1.0.0",
        },
        "python_dependencies": [
            "httpx>=0.24.0",
        ],
        "capabilities": {
            "metrics": {
                "enabled": True,
                "export_format": "prometheus",
            },
            "jobs": {
                "enabled": True,
                "max_concurrent": 3,
            },
            "health_check": {
                "enabled": True,
            },
        },
        "entrypoints": {
            "init": "__init__:Plugin.init",
            "shutdown": "__init__:Plugin.shutdown",
        },
        "cli": {
            "commands": [
                {
                    "name": "test-cmd",
                    "description": "A test command",
                    "entrypoint": "cli.commands:run",
                    "aliases": ["tc"],
                },
            ],
        },
        "api": {
            "routes": [
                {
                    "path": "/status",
                    "method": "GET",
                    "entrypoint": "server.api:get_status",
                    "tags": ["status"],
                },
            ],
        },
        "ui": {
            "panels": [
                {
                    "id": "main",
                    "location": "sidebar",
                    "route": "/plugins/full_plugin",
                    "title_key": "plugin.full_plugin.title",
                    "icon": "🔧",
                    "order": 50,
                },
                {
                    "id": "settings",
                    "location": "settings",
                    "route": "/plugins/full_plugin/settings",
                    "title_key": "plugin.full_plugin.settings",
                    "settings_section": "Full Plugin Settings",
                },
            ],
        },
        "config": {
            "schema": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                },
            },
            "defaults": {
                "enabled": True,
            },
        },
    }


@pytest.fixture
def temp_manifest_file(minimal_manifest_data):
    """Create a temporary manifest YAML file."""
    import yaml
    
    with tempfile.NamedTemporaryFile(
        mode="w", 
        suffix=".yaml", 
        delete=False,
        encoding="utf-8"
    ) as f:
        yaml.safe_dump(minimal_manifest_data, f)
        return Path(f.name)


# =============================================================================
# BASIC PARSING TESTS
# =============================================================================

class TestManifestFromDict:
    """Tests for PluginManifest.from_dict()."""
    
    def test_minimal_manifest(self, minimal_manifest_data):
        """Should parse minimal manifest data."""
        manifest = PluginManifest.from_dict(minimal_manifest_data, validate=False)
        
        assert manifest.id == "test_plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.description == "A test plugin"
        assert manifest.plugin_type == PluginType.TOOL
        assert manifest.jupiter_version == ">=1.0.0"
    
    def test_full_manifest(self, full_manifest_data):
        """Should parse complete manifest data."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert manifest.id == "full_plugin"
        assert manifest.plugin_type == PluginType.SYSTEM
        assert manifest.trust_level == "verified"
        assert manifest.author is not None
        assert manifest.author["name"] == "Test Author"
        assert manifest.license == "MIT"
    
    def test_parses_permissions(self, full_manifest_data):
        """Should parse permissions list."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert Permission.FS_READ in manifest.permissions
        assert Permission.FS_WRITE in manifest.permissions
        assert Permission.EMIT_EVENTS in manifest.permissions
        assert Permission.REGISTER_API in manifest.permissions
        assert len(manifest.permissions) == 4
    
    def test_ignores_unknown_permissions(self):
        """Should skip unknown permissions with warning."""
        data = {
            "id": "test",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "type": "tool",
            "jupiter_version": ">=1.0.0",
            "permissions": ["fs_read", "unknown_perm", "emit_events"],
        }
        
        manifest = PluginManifest.from_dict(data, validate=False)
        
        assert len(manifest.permissions) == 2
        assert Permission.FS_READ in manifest.permissions
        assert Permission.EMIT_EVENTS in manifest.permissions
    
    def test_parses_capabilities(self, full_manifest_data):
        """Should parse capabilities."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert manifest.capabilities.metrics_enabled is True
        assert manifest.capabilities.metrics_export_format == "prometheus"
        assert manifest.capabilities.jobs_enabled is True
        assert manifest.capabilities.jobs_max_concurrent == 3
        assert manifest.capabilities.health_check_enabled is True
    
    def test_parses_cli_contributions(self, full_manifest_data):
        """Should parse CLI contributions."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert len(manifest.cli_contributions) == 1
        cmd = manifest.cli_contributions[0]
        assert cmd.name == "test-cmd"
        assert cmd.entrypoint == "cli.commands:run"
        assert cmd.aliases == ["tc"]
    
    def test_parses_api_contributions(self, full_manifest_data):
        """Should parse API contributions."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert len(manifest.api_contributions) == 1
        route = manifest.api_contributions[0]
        assert route.path == "/status"
        assert route.method == "GET"
        assert route.tags == ["status"]
    
    def test_parses_ui_contributions(self, full_manifest_data):
        """Should parse UI contributions."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert len(manifest.ui_contributions) == 2
        
        main_panel = manifest.ui_contributions[0]
        assert main_panel.id == "main"
        assert main_panel.location == UILocation.SIDEBAR
        assert main_panel.icon == "🔧"
        assert main_panel.order == 50
        
        settings_panel = manifest.ui_contributions[1]
        assert settings_panel.location == UILocation.SETTINGS
        assert settings_panel.settings_section == "Full Plugin Settings"
    
    def test_parses_config(self, full_manifest_data):
        """Should parse config schema and defaults."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        
        assert manifest.config_schema is not None
        assert manifest.config_schema["type"] == "object"
        assert manifest.config_defaults["enabled"] is True


class TestManifestFromYaml:
    """Tests for PluginManifest.from_yaml()."""
    
    def test_load_from_file(self, temp_manifest_file):
        """Should load manifest from YAML file."""
        manifest = PluginManifest.from_yaml(temp_manifest_file, validate=False)
        
        assert manifest.id == "test_plugin"
        # source_path is now the plugin directory (parent of yaml file), not the yaml file itself
        assert manifest.source_path == temp_manifest_file.parent
    
    def test_file_not_found(self):
        """Should raise ManifestError for missing file."""
        with pytest.raises(ManifestError) as exc_info:
            PluginManifest.from_yaml("/nonexistent/path/plugin.yaml")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_invalid_yaml(self):
        """Should raise ManifestError for invalid YAML."""
        with tempfile.NamedTemporaryFile(
            mode="w", 
            suffix=".yaml", 
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write("invalid: yaml: syntax: [")
            path = Path(f.name)
        
        with pytest.raises(ManifestError) as exc_info:
            PluginManifest.from_yaml(path)
        
        assert "yaml" in str(exc_info.value).lower()


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestManifestValidation:
    """Tests for manifest validation."""
    
    def test_missing_required_field(self):
        """Should raise ManifestError for missing required field."""
        data = {
            "id": "test",
            "name": "Test",
            # missing version
            "description": "Test",
            "type": "tool",
            "jupiter_version": ">=1.0.0",
        }
        
        with pytest.raises(ManifestError) as exc_info:
            PluginManifest.from_dict(data, validate=False)
        
        assert "version" in str(exc_info.value).lower()
    
    def test_invalid_plugin_type(self):
        """Should raise ManifestError for invalid type."""
        data = {
            "id": "test",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "type": "invalid_type",
            "jupiter_version": ">=1.0.0",
        }
        
        with pytest.raises(ManifestError) as exc_info:
            PluginManifest.from_dict(data, validate=False)
        
        assert "type" in str(exc_info.value).lower()
    
    def test_schema_validation_errors(self, minimal_manifest_data):
        """Should collect validation errors."""
        # Remove required field to trigger validation
        del minimal_manifest_data["version"]
        
        errors = _validate_with_schema(minimal_manifest_data, "test")
        
        assert len(errors) > 0
        assert any("version" in e.lower() for e in errors)


# =============================================================================
# SERIALIZATION TESTS
# =============================================================================

class TestManifestSerialization:
    """Tests for manifest serialization."""
    
    def test_to_dict(self, full_manifest_data):
        """Should serialize manifest to dict."""
        manifest = PluginManifest.from_dict(full_manifest_data, validate=False)
        d = manifest.to_dict()
        
        assert d["id"] == "full_plugin"
        assert d["type"] == "system"
        assert d["permissions"] == ["fs_read", "fs_write", "emit_events", "register_api"]
        assert len(d["cli"]) == 1
        assert len(d["api"]) == 1
        assert len(d["ui"]) == 2
    
    def test_round_trip(self, minimal_manifest_data):
        """Should support round-trip serialization."""
        manifest1 = PluginManifest.from_dict(minimal_manifest_data, validate=False)
        d = manifest1.to_dict()
        
        # to_dict produces a flattened format (cli/api/ui are lists)
        # Restructure for re-parsing
        reparseable = {
            "id": d["id"],
            "name": d["name"],
            "version": d["version"],
            "description": d["description"],
            "type": d["type"],
            "jupiter_version": d["jupiter_version"],
        }
        manifest2 = PluginManifest.from_dict(reparseable, validate=False)
        
        assert manifest1.id == manifest2.id
        assert manifest1.version == manifest2.version


# =============================================================================
# LEGACY MANIFEST GENERATION TESTS
# =============================================================================

class TestLegacyManifestGeneration:
    """Tests for generate_manifest_for_legacy()."""
    
    def test_generates_minimal_manifest(self):
        """Should generate manifest for legacy plugin."""
        manifest = generate_manifest_for_legacy(
            plugin_id="legacy_plugin",
            name="Legacy Plugin",
            version="0.5.0",
            description="A legacy v1 plugin",
        )
        
        assert manifest.id == "legacy_plugin"
        assert manifest.name == "Legacy Plugin"
        assert manifest.version == "0.5.0"
        assert manifest.plugin_type == PluginType.TOOL
        assert manifest.trust_level == "experimental"
        assert len(manifest.permissions) == 0  # Restricted by default
    
    def test_generates_ui_contribution(self):
        """Should generate UI contribution if has_ui is True."""
        manifest = generate_manifest_for_legacy(
            plugin_id="ui_plugin",
            name="UI Plugin",
            version="1.0.0",
            description="Plugin with UI",
            has_ui=True,
            ui_type="sidebar",
        )
        
        assert len(manifest.ui_contributions) == 1
        ui = manifest.ui_contributions[0]
        assert ui.location == UILocation.SIDEBAR
        assert ui.route == "/plugins/ui_plugin"
    
    def test_no_ui_for_none_type(self):
        """Should not generate UI contribution for 'none' type."""
        manifest = generate_manifest_for_legacy(
            plugin_id="no_ui",
            name="No UI Plugin",
            version="1.0.0",
            description="Plugin without UI",
            has_ui=True,
            ui_type="none",
        )
        
        assert len(manifest.ui_contributions) == 0
    
    def test_handles_both_ui_type(self):
        """Should handle 'both' UI type."""
        manifest = generate_manifest_for_legacy(
            plugin_id="both_plugin",
            name="Both Plugin",
            version="1.0.0",
            description="Plugin in both locations",
            has_ui=True,
            ui_type="both",
        )
        
        assert len(manifest.ui_contributions) == 1
        assert manifest.ui_contributions[0].location == UILocation.BOTH


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_contributions(self, minimal_manifest_data):
        """Should handle empty contribution lists."""
        manifest = PluginManifest.from_dict(minimal_manifest_data, validate=False)
        
        assert manifest.cli_contributions == []
        assert manifest.api_contributions == []
        assert manifest.ui_contributions == []
    
    def test_default_capabilities(self, minimal_manifest_data):
        """Should use default capabilities when not specified."""
        manifest = PluginManifest.from_dict(minimal_manifest_data, validate=False)
        
        assert manifest.capabilities.metrics_enabled is False
        assert manifest.capabilities.jobs_enabled is False
        assert manifest.capabilities.health_check_enabled is True
    
    def test_unknown_ui_location_defaults_to_none(self):
        """Should default to NONE for unknown UI location."""
        data = {
            "id": "test",
            "name": "Test",
            "version": "1.0.0",
            "description": "Test",
            "type": "tool",
            "jupiter_version": ">=1.0.0",
            "ui": {
                "panels": [
                    {
                        "id": "main",
                        "location": "invalid_location",
                        "route": "/test",
                        "title_key": "test",
                    },
                ],
            },
        }
        
        manifest = PluginManifest.from_dict(data, validate=False)
        
        assert manifest.ui_contributions[0].location == UILocation.NONE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
