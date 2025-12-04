"""Tests for jupiter.core.bridge.ui_registry module.

Version: 0.1.0

Tests for the UI Registry functionality.
"""

import pytest
from typing import Any

from jupiter.core.bridge.ui_registry import (
    UIRegistry,
    RegisteredPanel,
    RegisteredMenuItem,
    SettingsSchema,
    PluginUIManifest,
    get_ui_registry,
    reset_ui_registry,
)
from jupiter.core.bridge.interfaces import (
    UIContribution,
    UILocation,
    Permission,
)
from jupiter.core.bridge.exceptions import (
    PermissionDeniedError,
    ValidationError,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset the global UI registry before and after each test."""
    reset_ui_registry()
    yield
    reset_ui_registry()


@pytest.fixture
def registry() -> UIRegistry:
    """Create a fresh UI registry."""
    return UIRegistry()


# =============================================================================
# RegisteredPanel Tests
# =============================================================================

class TestRegisteredPanel:
    """Tests for RegisteredPanel dataclass."""
    
    def test_creates_with_required_fields(self):
        """Should create panel with required fields."""
        panel = RegisteredPanel(
            plugin_id="test_plugin",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="panel_title",
        )
        
        assert panel.plugin_id == "test_plugin"
        assert panel.panel_id == "main"
        assert panel.location == UILocation.SIDEBAR
        assert panel.route == "/"
        assert panel.title_key == "panel_title"
    
    def test_full_route_includes_prefix(self):
        """full_route should include plugin prefix."""
        panel = RegisteredPanel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/dashboard",
            title_key="title",
        )
        
        assert panel.full_route == "/plugins/test/dashboard"
    
    def test_full_route_handles_leading_slash(self):
        """full_route should handle routes with/without leading slash."""
        panel1 = RegisteredPanel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="dashboard",
            title_key="title",
        )
        
        panel2 = RegisteredPanel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/dashboard",
            title_key="title",
        )
        
        assert panel1.full_route == "/plugins/test/dashboard"
        assert panel2.full_route == "/plugins/test/dashboard"
    
    def test_i18n_title_key_adds_prefix(self):
        """i18n_title_key should add plugin prefix."""
        panel = RegisteredPanel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="panel_title",
        )
        
        assert panel.i18n_title_key == "plugin.test.panel_title"
    
    def test_i18n_title_key_keeps_existing_prefix(self):
        """i18n_title_key should keep existing prefix."""
        panel = RegisteredPanel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="plugin.other.panel_title",
        )
        
        assert panel.i18n_title_key == "plugin.other.panel_title"
    
    def test_to_dict_serializes_all_fields(self):
        """to_dict should serialize all fields."""
        panel = RegisteredPanel(
            plugin_id="test_plugin",
            panel_id="main",
            location=UILocation.BOTH,
            route="/dashboard",
            title_key="title",
            icon="📊",
            order=50,
            description_key="desc",
            component_path="js/panel.js",
            lazy_load=False,
            visible=True,
            requires_auth=True,
        )
        
        data = panel.to_dict()
        
        assert data["plugin_id"] == "test_plugin"
        assert data["panel_id"] == "main"
        assert data["location"] == "both"
        assert data["route"] == "/dashboard"
        assert data["icon"] == "📊"
        assert data["order"] == 50
        assert data["component_path"] == "js/panel.js"
        assert data["lazy_load"] is False
        assert data["requires_auth"] is True


# =============================================================================
# RegisteredMenuItem Tests
# =============================================================================

class TestRegisteredMenuItem:
    """Tests for RegisteredMenuItem dataclass."""
    
    def test_creates_with_required_fields(self):
        """Should create menu item with required fields."""
        item = RegisteredMenuItem(
            plugin_id="test",
            item_id="analyze",
            label_key="menu_analyze",
            action="/plugins/test/analyze",
        )
        
        assert item.plugin_id == "test"
        assert item.item_id == "analyze"
        assert item.label_key == "menu_analyze"
        assert item.action == "/plugins/test/analyze"
    
    def test_i18n_label_key_adds_prefix(self):
        """i18n_label_key should add plugin prefix."""
        item = RegisteredMenuItem(
            plugin_id="test",
            item_id="analyze",
            label_key="menu_label",
            action="/",
        )
        
        assert item.i18n_label_key == "plugin.test.menu_label"
    
    def test_to_dict(self):
        """to_dict should serialize all fields."""
        item = RegisteredMenuItem(
            plugin_id="test",
            item_id="analyze",
            label_key="label",
            action="/analyze",
            icon="🔍",
            order=10,
            parent="tools",
            separator_before=True,
            separator_after=False,
            visible=True,
        )
        
        data = item.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["item_id"] == "analyze"
        assert data["icon"] == "🔍"
        assert data["parent"] == "tools"
        assert data["separator_before"] is True


# =============================================================================
# SettingsSchema Tests
# =============================================================================

class TestSettingsSchema:
    """Tests for SettingsSchema dataclass."""
    
    def test_creates_with_required_fields(self):
        """Should create schema with required fields."""
        schema = SettingsSchema(
            plugin_id="test",
            schema={"type": "object", "properties": {}},
        )
        
        assert schema.plugin_id == "test"
        assert schema.schema == {"type": "object", "properties": {}}
        assert schema.ui_schema is None
        assert schema.defaults == {}
    
    def test_to_dict(self):
        """to_dict should serialize fields."""
        schema = SettingsSchema(
            plugin_id="test",
            schema={"type": "object"},
            ui_schema={"field1": {"widget": "textarea"}},
            defaults={"field1": "default"},
        )
        
        data = schema.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["schema"] == {"type": "object"}
        assert data["ui_schema"] == {"field1": {"widget": "textarea"}}
        assert data["defaults"] == {"field1": "default"}


# =============================================================================
# PluginUIManifest Tests
# =============================================================================

class TestPluginUIManifest:
    """Tests for PluginUIManifest dataclass."""
    
    def test_creates_with_defaults(self):
        """Should create manifest with defaults."""
        manifest = PluginUIManifest(plugin_id="test")
        
        assert manifest.plugin_id == "test"
        assert manifest.panels == []
        assert manifest.menu_items == []
        assert manifest.settings_schema is None
        assert manifest.i18n_namespace == "plugin.test"
    
    def test_has_sidebar_with_sidebar_panel(self):
        """has_sidebar should be True with sidebar panel."""
        manifest = PluginUIManifest(
            plugin_id="test",
            panels=[
                RegisteredPanel(
                    plugin_id="test",
                    panel_id="main",
                    location=UILocation.SIDEBAR,
                    route="/",
                    title_key="title",
                )
            ]
        )
        
        assert manifest.has_sidebar is True
    
    def test_has_sidebar_with_both_panel(self):
        """has_sidebar should be True with 'both' location."""
        manifest = PluginUIManifest(
            plugin_id="test",
            panels=[
                RegisteredPanel(
                    plugin_id="test",
                    panel_id="main",
                    location=UILocation.BOTH,
                    route="/",
                    title_key="title",
                )
            ]
        )
        
        assert manifest.has_sidebar is True
    
    def test_has_settings_with_settings_panel(self):
        """has_settings should be True with settings panel."""
        manifest = PluginUIManifest(
            plugin_id="test",
            panels=[
                RegisteredPanel(
                    plugin_id="test",
                    panel_id="settings",
                    location=UILocation.SETTINGS,
                    route="/settings",
                    title_key="title",
                )
            ]
        )
        
        assert manifest.has_settings is True
    
    def test_has_settings_with_schema(self):
        """has_settings should be True with settings schema."""
        manifest = PluginUIManifest(
            plugin_id="test",
            settings_schema=SettingsSchema(
                plugin_id="test",
                schema={"type": "object"},
            )
        )
        
        assert manifest.has_settings is True


# =============================================================================
# UIRegistry Permission Tests
# =============================================================================

class TestUIRegistryPermissions:
    """Tests for UI Registry permission checks."""
    
    def test_register_requires_permission(self, registry):
        """Registration should require REGISTER_UI permission."""
        with pytest.raises(PermissionDeniedError) as exc:
            registry.register_panel(
                plugin_id="test",
                panel_id="main",
                location=UILocation.SIDEBAR,
                route="/",
                title_key="title",
            )
        
        assert "REGISTER_UI" in str(exc.value) or "permission" in str(exc.value).lower()
    
    def test_register_with_permission_succeeds(self, registry):
        """Registration should succeed with permission."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        panel = registry.register_panel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
        )
        
        assert panel is not None
        assert panel.panel_id == "main"
    
    def test_check_permissions_can_be_bypassed(self, registry):
        """check_permissions=False should bypass check."""
        panel = registry.register_panel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
            check_permissions=False,
        )
        
        assert panel is not None
    
    def test_register_menu_item_requires_permission(self, registry):
        """Menu item registration should require permission."""
        with pytest.raises(PermissionDeniedError):
            registry.register_menu_item(
                plugin_id="test",
                item_id="analyze",
                label_key="label",
                action="/analyze",
            )
    
    def test_register_settings_schema_requires_permission(self, registry):
        """Settings schema registration should require permission."""
        with pytest.raises(PermissionDeniedError):
            registry.register_settings_schema(
                plugin_id="test",
                schema={"type": "object"},
            )


# =============================================================================
# UIRegistry Panel Registration Tests
# =============================================================================

class TestUIRegistryRegisterPanel:
    """Tests for panel registration."""
    
    def test_register_basic_panel(self, registry):
        """Should register a basic panel."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        panel = registry.register_panel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="panel_title",
        )
        
        assert panel.plugin_id == "test"
        assert panel.panel_id == "main"
        assert panel.location == UILocation.SIDEBAR
    
    def test_register_panel_with_all_options(self, registry):
        """Should register panel with all options."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        panel = registry.register_panel(
            plugin_id="test",
            panel_id="dashboard",
            location=UILocation.BOTH,
            route="/dashboard",
            title_key="title",
            icon="📊",
            order=10,
            description_key="desc",
            component_path="js/dashboard.js",
            lazy_load=False,
            visible=True,
            requires_auth=True,
        )
        
        assert panel.icon == "📊"
        assert panel.order == 10
        assert panel.component_path == "js/dashboard.js"
        assert panel.requires_auth is True
    
    def test_register_from_contribution(self, registry):
        """Should register from UIContribution."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        contribution = UIContribution(
            id="main",
            location=UILocation.SIDEBAR,
            route="/main",
            title_key="main_title",
            icon="🔌",
            order=50,
        )
        
        panel = registry.register_from_contribution(
            plugin_id="test",
            contribution=contribution,
        )
        
        assert panel.panel_id == "main"
        assert panel.location == UILocation.SIDEBAR
        assert panel.icon == "🔌"


# =============================================================================
# UIRegistry Validation Tests
# =============================================================================

class TestUIRegistryValidation:
    """Tests for panel ID validation."""
    
    def test_empty_panel_id_rejected(self, registry):
        """Empty panel ID should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        with pytest.raises(ValidationError):
            registry.register_panel(
                plugin_id="test",
                panel_id="",
                location=UILocation.SIDEBAR,
                route="/",
                title_key="title",
            )
    
    def test_invalid_characters_rejected(self, registry):
        """Invalid characters should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        with pytest.raises(ValidationError):
            registry.register_panel(
                plugin_id="test",
                panel_id="panel@name",
                location=UILocation.SIDEBAR,
                route="/",
                title_key="title",
            )
    
    def test_hyphens_and_underscores_allowed(self, registry):
        """Hyphens and underscores should be allowed."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        panel = registry.register_panel(
            plugin_id="test",
            panel_id="my-panel_name",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
        )
        
        assert panel.panel_id == "my-panel_name"
    
    def test_duplicate_panel_id_rejected(self, registry):
        """Duplicate panel ID should be rejected."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        registry.register_panel(
            plugin_id="test",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
        )
        
        with pytest.raises(ValidationError):
            registry.register_panel(
                plugin_id="test",
                panel_id="main",
                location=UILocation.SETTINGS,
                route="/settings",
                title_key="title2",
            )
    
    def test_same_panel_id_different_plugins_allowed(self, registry):
        """Same panel ID in different plugins should be allowed."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_UI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_UI})
        
        panel1 = registry.register_panel(
            plugin_id="p1",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
        )
        
        panel2 = registry.register_panel(
            plugin_id="p2",
            panel_id="main",
            location=UILocation.SIDEBAR,
            route="/",
            title_key="title",
        )
        
        assert panel1.plugin_id == "p1"
        assert panel2.plugin_id == "p2"


# =============================================================================
# UIRegistry Menu Item Tests
# =============================================================================

class TestUIRegistryMenuItems:
    """Tests for menu item registration."""
    
    def test_register_menu_item(self, registry):
        """Should register a menu item."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        item = registry.register_menu_item(
            plugin_id="test",
            item_id="analyze",
            label_key="menu_analyze",
            action="/plugins/test/analyze",
            icon="🔍",
        )
        
        assert item.plugin_id == "test"
        assert item.item_id == "analyze"
        assert item.icon == "🔍"
    
    def test_register_submenu_item(self, registry):
        """Should register a submenu item."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        item = registry.register_menu_item(
            plugin_id="test",
            item_id="sub_action",
            label_key="sub_label",
            action="/action",
            parent="tools",
        )
        
        assert item.parent == "tools"
    
    def test_get_menu_items_filters_by_parent(self, registry):
        """get_menu_items should filter by parent."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        registry.register_menu_item("test", "root1", "l1", "/a")
        registry.register_menu_item("test", "root2", "l2", "/b")
        registry.register_menu_item("test", "child1", "l3", "/c", parent="tools")
        
        root_items = registry.get_menu_items(parent=None)
        child_items = registry.get_menu_items(parent="tools")
        
        assert len(root_items) == 2
        assert len(child_items) == 1
        assert child_items[0].item_id == "child1"


# =============================================================================
# UIRegistry Settings Schema Tests
# =============================================================================

class TestUIRegistrySettingsSchema:
    """Tests for settings schema registration."""
    
    def test_register_settings_schema(self, registry):
        """Should register a settings schema."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        
        schema = registry.register_settings_schema(
            plugin_id="test",
            schema={
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "default": True},
                }
            },
            defaults={"enabled": True},
        )
        
        assert schema.plugin_id == "test"
        assert schema.defaults == {"enabled": True}
    
    def test_get_settings_schema(self, registry):
        """get_settings_schema should return registered schema."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_settings_schema("test", {"type": "object"})
        
        schema = registry.get_settings_schema("test")
        
        assert schema is not None
        assert schema.schema == {"type": "object"}
    
    def test_get_all_settings_schemas(self, registry):
        """get_all_settings_schemas should return all schemas."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_UI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_UI})
        
        registry.register_settings_schema("p1", {"type": "object"})
        registry.register_settings_schema("p2", {"type": "object"})
        
        schemas = registry.get_all_settings_schemas()
        
        assert len(schemas) == 2


# =============================================================================
# UIRegistry Query Tests
# =============================================================================

class TestUIRegistryQueries:
    """Tests for querying registered UI elements."""
    
    def test_get_panel_returns_registered(self, registry):
        """get_panel should return registered panel."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "main", UILocation.SIDEBAR, "/", "title")
        
        panel = registry.get_panel("test", "main")
        
        assert panel is not None
        assert panel.panel_id == "main"
    
    def test_get_panel_returns_none_for_unknown(self, registry):
        """get_panel should return None for unknown."""
        assert registry.get_panel("test", "unknown") is None
    
    def test_get_plugin_panels(self, registry):
        """get_plugin_panels should return all for plugin."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "p1", UILocation.SIDEBAR, "/a", "t1")
        registry.register_panel("test", "p2", UILocation.SETTINGS, "/b", "t2")
        
        panels = registry.get_plugin_panels("test")
        
        assert len(panels) == 2
    
    def test_get_sidebar_panels(self, registry):
        """get_sidebar_panels should return sidebar and both panels."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "sidebar", UILocation.SIDEBAR, "/a", "t1")
        registry.register_panel("test", "settings", UILocation.SETTINGS, "/b", "t2")
        registry.register_panel("test", "both", UILocation.BOTH, "/c", "t3")
        
        sidebar_panels = registry.get_sidebar_panels()
        
        assert len(sidebar_panels) == 2
        panel_ids = {p.panel_id for p in sidebar_panels}
        assert panel_ids == {"sidebar", "both"}
    
    def test_get_settings_panels(self, registry):
        """get_settings_panels should return settings and both panels."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "sidebar", UILocation.SIDEBAR, "/a", "t1")
        registry.register_panel("test", "settings", UILocation.SETTINGS, "/b", "t2")
        registry.register_panel("test", "both", UILocation.BOTH, "/c", "t3")
        
        settings_panels = registry.get_settings_panels()
        
        assert len(settings_panels) == 2
        panel_ids = {p.panel_id for p in settings_panels}
        assert panel_ids == {"settings", "both"}
    
    def test_panels_sorted_by_order(self, registry):
        """Panels should be sorted by order."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "p3", UILocation.SIDEBAR, "/c", "t3", order=300)
        registry.register_panel("test", "p1", UILocation.SIDEBAR, "/a", "t1", order=100)
        registry.register_panel("test", "p2", UILocation.SIDEBAR, "/b", "t2", order=200)
        
        panels = registry.get_sidebar_panels()
        
        assert [p.panel_id for p in panels] == ["p1", "p2", "p3"]
    
    def test_get_plugins_with_ui(self, registry):
        """get_plugins_with_ui should return plugin IDs."""
        registry.set_plugin_permissions("p1", {Permission.REGISTER_UI})
        registry.set_plugin_permissions("p2", {Permission.REGISTER_UI})
        
        registry.register_panel("p1", "main", UILocation.SIDEBAR, "/", "t")
        registry.register_panel("p2", "main", UILocation.SIDEBAR, "/", "t")
        
        plugins = registry.get_plugins_with_ui()
        
        assert set(plugins) == {"p1", "p2"}
    
    def test_get_plugin_manifest(self, registry):
        """get_plugin_manifest should return manifest."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "main", UILocation.SIDEBAR, "/", "t")
        
        manifest = registry.get_plugin_manifest("test")
        
        assert manifest is not None
        assert manifest.plugin_id == "test"
        assert len(manifest.panels) == 1


# =============================================================================
# UIRegistry Unregister Tests
# =============================================================================

class TestUIRegistryUnregister:
    """Tests for unregistering UI elements."""
    
    def test_unregister_panel(self, registry):
        """unregister_panel should remove panel."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "main", UILocation.SIDEBAR, "/", "t")
        
        result = registry.unregister_panel("test", "main")
        
        assert result is True
        assert registry.get_panel("test", "main") is None
    
    def test_unregister_panel_returns_false_if_not_found(self, registry):
        """unregister_panel should return False if not found."""
        result = registry.unregister_panel("unknown", "main")
        assert result is False
    
    def test_unregister_menu_item(self, registry):
        """unregister_menu_item should remove item."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_menu_item("test", "analyze", "label", "/a")
        
        result = registry.unregister_menu_item("test", "analyze")
        
        assert result is True
    
    def test_unregister_plugin_removes_all(self, registry):
        """unregister_plugin should remove all UI contributions."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "p1", UILocation.SIDEBAR, "/a", "t1")
        registry.register_panel("test", "p2", UILocation.SETTINGS, "/b", "t2")
        registry.register_menu_item("test", "m1", "label", "/c")
        registry.register_settings_schema("test", {"type": "object"})
        
        count = registry.unregister_plugin("test")
        
        assert count == 4  # 2 panels + 1 menu item + 1 schema
        assert registry.get_plugin_panels("test") == []
        assert registry.get_settings_schema("test") is None
    
    def test_unregister_plugin_returns_zero_if_none(self, registry):
        """unregister_plugin should return 0 if no UI."""
        count = registry.unregister_plugin("unknown")
        assert count == 0


# =============================================================================
# UIRegistry UI Manifest Tests
# =============================================================================

class TestUIRegistryManifest:
    """Tests for UI manifest generation."""
    
    def test_get_ui_manifest_empty(self, registry):
        """get_ui_manifest should work with empty registry."""
        manifest = registry.get_ui_manifest()
        
        assert manifest["plugins"] == {}
        assert manifest["sidebar_panels"] == []
        assert manifest["settings_panels"] == []
        assert manifest["menu_items"] == []
        assert manifest["plugin_count"] == 0
    
    def test_get_ui_manifest_with_data(self, registry):
        """get_ui_manifest should include all data."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "sidebar", UILocation.SIDEBAR, "/", "t")
        registry.register_panel("test", "settings", UILocation.SETTINGS, "/s", "t")
        registry.register_menu_item("test", "action", "label", "/a")
        
        manifest = registry.get_ui_manifest()
        
        assert "test" in manifest["plugins"]
        assert len(manifest["sidebar_panels"]) == 1
        assert len(manifest["settings_panels"]) == 1
        assert len(manifest["menu_items"]) == 1
        assert manifest["plugin_count"] == 1


# =============================================================================
# UIRegistry Serialization Tests
# =============================================================================

class TestUIRegistrySerialization:
    """Tests for registry serialization."""
    
    def test_to_dict_empty(self, registry):
        """to_dict should work with empty registry."""
        data = registry.to_dict()
        
        assert data["manifests"] == {}
        assert data["total_panels"] == 0
        assert data["total_menu_items"] == 0
        assert data["plugins_with_settings"] == 0
    
    def test_to_dict_with_data(self, registry):
        """to_dict should serialize data."""
        registry.set_plugin_permissions("test", {Permission.REGISTER_UI})
        registry.register_panel("test", "main", UILocation.SIDEBAR, "/", "t")
        registry.register_menu_item("test", "action", "label", "/a")
        registry.register_settings_schema("test", {"type": "object"})
        
        data = registry.to_dict()
        
        assert "test" in data["manifests"]
        assert data["total_panels"] == 1
        assert data["total_menu_items"] == 1
        assert data["plugins_with_settings"] == 1


# =============================================================================
# Global Registry Tests
# =============================================================================

class TestGlobalUIRegistry:
    """Tests for global UI registry functions."""
    
    def test_get_ui_registry_returns_singleton(self):
        """get_ui_registry should return same instance."""
        r1 = get_ui_registry()
        r2 = get_ui_registry()
        
        assert r1 is r2
    
    def test_reset_ui_registry_creates_new(self):
        """reset_ui_registry should create new instance."""
        r1 = get_ui_registry()
        reset_ui_registry()
        r2 = get_ui_registry()
        
        assert r1 is not r2
