"""CLI command handlers for plugin management.

Version: 0.5.0 - Added update, check-updates, install-deps and dry-run

Provides handlers for:
- jupiter plugins list
- jupiter plugins info <id>
- jupiter plugins enable <id>
- jupiter plugins disable <id>
- jupiter plugins status
- jupiter plugins install <source> [--install-deps] [--dry-run]
- jupiter plugins uninstall <id>
- jupiter plugins update <id> [--source] [--install-deps] [--no-backup]
- jupiter plugins check-updates
- jupiter plugins scaffold <id>
- jupiter plugins reload <id>
- jupiter plugins sign <path>
- jupiter plugins verify <path>
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from jupiter.core.bridge.manifest import PluginManifest

logger = logging.getLogger(__name__)


def get_bridge():
    """Get the Bridge singleton."""
    try:
        from jupiter.core.bridge import Bridge
        return Bridge()
    except ImportError:
        logger.error("Bridge module not available")
        return None


def get_cli_registry():
    """Get the CLI registry."""
    try:
        from jupiter.core.bridge import get_cli_registry
        return get_cli_registry()
    except ImportError:
        return None


def get_api_registry():
    """Get the API registry."""
    try:
        from jupiter.core.bridge import get_api_registry
        return get_api_registry()
    except ImportError:
        return None


def get_ui_registry():
    """Get the UI registry."""
    try:
        from jupiter.core.bridge import get_ui_registry
        return get_ui_registry()
    except ImportError:
        return None


def format_state_emoji(state: str) -> str:
    """Get emoji for plugin state."""
    state_emojis = {
        "discovered": "🔍",
        "loading": "⏳",
        "ready": "✅",
        "error": "❌",
        "disabled": "⏸️",
    }
    return state_emojis.get(state, "❓")


def format_type_emoji(plugin_type: str) -> str:
    """Get emoji for plugin type."""
    type_emojis = {
        "core": "🔧",
        "system": "⚙️",
        "external": "📦",
        "legacy": "📜",
    }
    return type_emojis.get(plugin_type, "🔌")


def handle_plugins_list(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins list` command."""
    import json
    
    bridge = get_bridge()
    cli_registry = get_cli_registry()
    api_registry = get_api_registry()
    ui_registry = get_ui_registry()
    
    if not bridge:
        print("❌ Bridge v2 not available", file=sys.stderr)
        sys.exit(1)
    
    plugins = bridge.get_all_plugins()
    
    if args.json:
        # JSON output
        output = {
            "plugins": [],
            "total": len(plugins),
            "by_state": {},
            "by_type": {},
        }
        
        for info in plugins:
            plugin_type = info.manifest.plugin_type.value
            plugin_state = info.state.value
            
            output["by_state"][plugin_state] = output["by_state"].get(plugin_state, 0) + 1
            output["by_type"][plugin_type] = output["by_type"].get(plugin_type, 0) + 1
            
            output["plugins"].append({
                "id": info.manifest.id,
                "name": info.manifest.name,
                "version": info.manifest.version,
                "type": plugin_type,
                "state": plugin_state,
                "description": info.manifest.description,
            })
        
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        if not plugins:
            print("No plugins registered.")
            return
        
        print(f"\n{'='*60}")
        print(f"  📦 Jupiter Plugins ({len(plugins)} total)")
        print(f"{'='*60}\n")
        
        # Group by type
        by_type: Dict[str, List] = {}
        for info in plugins:
            plugin_type = info.manifest.plugin_type.value
            if plugin_type not in by_type:
                by_type[plugin_type] = []
            by_type[plugin_type].append(info)
        
        for plugin_type in ["core", "system", "external", "legacy"]:
            if plugin_type not in by_type:
                continue
            
            type_plugins = by_type[plugin_type]
            print(f"{format_type_emoji(plugin_type)} {plugin_type.upper()} ({len(type_plugins)})")
            print("-" * 40)
            
            for info in type_plugins:
                state_emoji = format_state_emoji(info.state.value)
                name = info.manifest.name
                version = info.manifest.version
                plugin_id = info.manifest.id
                
                # Count contributions
                cli_count = len(cli_registry.get_plugin_commands(plugin_id)) if cli_registry else 0
                api_count = len(api_registry.get_plugin_routes(plugin_id)) if api_registry else 0
                ui_count = len(ui_registry.get_plugin_panels(plugin_id)) if ui_registry else 0
                
                contrib_str = ""
                if cli_count or api_count or ui_count:
                    parts = []
                    if cli_count:
                        parts.append(f"CLI:{cli_count}")
                    if api_count:
                        parts.append(f"API:{api_count}")
                    if ui_count:
                        parts.append(f"UI:{ui_count}")
                    contrib_str = f" [{', '.join(parts)}]"
                
                print(f"  {state_emoji} {name} v{version} ({plugin_id}){contrib_str}")
            
            print()
        
        # Summary
        ready = sum(1 for p in plugins if p.state.value == "ready")
        error = sum(1 for p in plugins if p.state.value == "error")
        disabled = sum(1 for p in plugins if p.state.value == "disabled")
        
        print(f"Summary: ✅ {ready} ready, ❌ {error} errors, ⏸️ {disabled} disabled")


def handle_plugins_info(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins info <id>` command."""
    import json
    
    bridge = get_bridge()
    cli_registry = get_cli_registry()
    api_registry = get_api_registry()
    ui_registry = get_ui_registry()
    
    if not bridge:
        print("❌ Bridge v2 not available", file=sys.stderr)
        sys.exit(1)
    
    plugin_id = args.plugin_id
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    manifest = info.manifest
    
    # Count contributions
    cli_commands = cli_registry.get_plugin_commands(plugin_id) if cli_registry else []
    api_routes = api_registry.get_plugin_routes(plugin_id) if api_registry else []
    ui_panels = ui_registry.get_plugin_panels(plugin_id) if ui_registry else []
    
    if args.json:
        output = info.to_dict()
        output["cli_commands"] = [c.to_dict() for c in cli_commands]
        output["api_routes"] = [r.to_dict() for r in api_routes]
        output["ui_panels"] = [p.to_dict() for p in ui_panels]
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'='*60}")
        icon = getattr(manifest, 'icon', '🔌')
        print(f"  {icon} {manifest.name}")
        print(f"{'='*60}\n")
        
        print(f"ID:          {manifest.id}")
        print(f"Version:     {manifest.version}")
        print(f"Type:        {format_type_emoji(manifest.plugin_type.value)} {manifest.plugin_type.value}")
        print(f"State:       {format_state_emoji(info.state.value)} {info.state.value}")
        
        if manifest.description:
            print(f"\nDescription: {manifest.description}")
        
        author = getattr(manifest, 'author', None)
        if author:
            print(f"Author:      {author}")
        
        homepage = getattr(manifest, 'homepage', None)
        if homepage:
            print(f"Homepage:    {homepage}")
        
        license_info = getattr(manifest, 'license', None)
        if license_info:
            print(f"License:     {license_info}")
        
        # Permissions
        if manifest.permissions:
            print(f"\nPermissions: {', '.join(p.value for p in manifest.permissions)}")
        
        # Dependencies
        if manifest.dependencies:
            deps = manifest.dependencies
            if isinstance(deps, dict):
                deps_str = ", ".join(f"{k}:{v}" for k, v in deps.items())
            else:
                deps_str = ", ".join(deps)
            print(f"Dependencies: {deps_str}")
        
        # Error
        if info.error:
            print(f"\n❌ Error: {info.error}")
        
        # Contributions
        print(f"\n📋 Contributions:")
        print(f"  CLI Commands: {len(cli_commands)}")
        for cmd in cli_commands:
            print(f"    - {cmd.full_name}: {cmd.description}")
        
        print(f"  API Routes: {len(api_routes)}")
        for route in api_routes:
            print(f"    - {route.method.value} {route.full_path}")
        
        print(f"  UI Panels: {len(ui_panels)}")
        for panel in ui_panels:
            print(f"    - {panel.panel_id}: {panel.title_key}")


def handle_plugins_enable(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins enable <id>` command."""
    bridge = get_bridge()
    
    if not bridge:
        print("❌ Bridge v2 not available", file=sys.stderr)
        sys.exit(1)
    
    plugin_id = args.plugin_id
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    if info.state.value == "ready":
        print(f"ℹ️ Plugin '{plugin_id}' is already enabled and ready")
        return
    
    try:
        # Note: enable_plugin may not exist yet, this is future-proof
        if hasattr(bridge, 'enable_plugin'):
            getattr(bridge, 'enable_plugin')(plugin_id)
            print(f"✅ Plugin '{plugin_id}' enabled")
        else:
            print(f"⚠️ Plugin enable not yet implemented in Bridge")
            print(f"   To enable, edit your jupiter config and restart the server")
    except Exception as e:
        print(f"❌ Failed to enable plugin: {e}", file=sys.stderr)
        sys.exit(1)


def handle_plugins_disable(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins disable <id>` command."""
    bridge = get_bridge()
    
    if not bridge:
        print("❌ Bridge v2 not available", file=sys.stderr)
        sys.exit(1)
    
    plugin_id = args.plugin_id
    info = bridge.get_plugin(plugin_id)
    
    if not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    if info.state.value == "disabled":
        print(f"ℹ️ Plugin '{plugin_id}' is already disabled")
        return
    
    # Check if it's a core plugin
    if info.manifest.plugin_type.value == "core":
        print(f"❌ Cannot disable core plugin '{plugin_id}'", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Note: disable_plugin may not exist yet, this is future-proof
        if hasattr(bridge, 'disable_plugin'):
            getattr(bridge, 'disable_plugin')(plugin_id)
            print(f"✅ Plugin '{plugin_id}' disabled")
        else:
            print(f"⚠️ Plugin disable not yet implemented in Bridge")
            print(f"   To disable, edit your jupiter config and restart the server")
    except Exception as e:
        print(f"❌ Failed to disable plugin: {e}", file=sys.stderr)
        sys.exit(1)


def handle_plugins_status(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins status` command - show Bridge status."""
    import json
    
    bridge = get_bridge()
    cli_registry = get_cli_registry()
    api_registry = get_api_registry()
    ui_registry = get_ui_registry()
    
    from jupiter.core.bridge import __version__ as bridge_version
    
    if not bridge:
        status = {
            "initialized": False,
            "version": bridge_version,
            "plugins_loaded": 0,
            "plugins_ready": 0,
            "plugins_error": 0,
            "cli_commands": 0,
            "api_routes": 0,
            "ui_panels": 0,
        }
    else:
        plugins = bridge.get_all_plugins()
        status = {
            "initialized": True,
            "version": bridge_version,
            "plugins_loaded": len(plugins),
            "plugins_ready": sum(1 for p in plugins if p.state.value == "ready"),
            "plugins_error": sum(1 for p in plugins if p.state.value == "error"),
            "cli_commands": len(cli_registry.get_all_commands()) if cli_registry else 0,
            "api_routes": len(api_registry.get_all_routes()) if api_registry else 0,
            "ui_panels": (
                len(ui_registry.get_sidebar_panels()) + 
                len(ui_registry.get_settings_panels())
            ) if ui_registry else 0,
        }
    
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print(f"\n🔌 Jupiter Bridge v{status['version']}")
        print(f"{'='*40}")
        
        if status["initialized"]:
            print(f"Status:       ✅ Initialized")
        else:
            print(f"Status:       ❌ Not initialized")
        
        print(f"\nPlugins:      {status['plugins_loaded']} loaded")
        print(f"  ✅ Ready:   {status['plugins_ready']}")
        print(f"  ❌ Errors:  {status['plugins_error']}")
        
        print(f"\nContributions:")
        print(f"  CLI Commands: {status['cli_commands']}")
        print(f"  API Routes:   {status['api_routes']}")
        print(f"  UI Panels:    {status['ui_panels']}")


def _get_plugins_dir() -> Path:
    """Get the plugins directory from Bridge or default."""
    bridge = get_bridge()
    if bridge and bridge.plugins_dir:
        return Path(bridge.plugins_dir)
    # Default to jupiter/plugins
    return Path(__file__).parent.parent / "plugins"


def _download_from_url(url: str, dest: Path) -> Path:
    """Download a file from URL."""
    import urllib.request
    from urllib.parse import urlparse
    
    logger.info("Downloading from %s", url)
    
    # Determine filename from URL
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path) or "plugin.zip"
    dest_file = dest / filename
    
    try:
        urllib.request.urlretrieve(url, dest_file)
        logger.info("Downloaded to %s", dest_file)
        return dest_file
    except Exception as e:
        raise RuntimeError(f"Download failed: {e}") from e


def _extract_zip(zip_path: Path, dest_dir: Path) -> Path:
    """Extract ZIP file and return the plugin directory."""
    logger.info("Extracting %s", zip_path)
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Check for manifest in root or in a single subdirectory
        namelist = zf.namelist()
        
        # Look for manifest.json
        manifest_paths = [n for n in namelist if n.endswith('manifest.json')]
        
        if not manifest_paths:
            raise RuntimeError("No manifest.json found in ZIP archive")
        
        # Get the plugin directory name from manifest path
        manifest_path = manifest_paths[0]
        if '/' in manifest_path:
            plugin_dir_name = manifest_path.split('/')[0]
        else:
            # manifest.json at root, use ZIP filename as dir name
            plugin_dir_name = zip_path.stem
        
        # Extract all files
        zf.extractall(dest_dir)
        
        # Return path to plugin directory
        if '/' in manifest_path:
            return dest_dir / plugin_dir_name
        else:
            # Files extracted to dest_dir itself
            return dest_dir


def _clone_git_repo(git_url: str, dest: Path) -> Path:
    """Clone a Git repository."""
    import subprocess
    
    # Parse git URL to get repo name
    if git_url.endswith('.git'):
        repo_name = os.path.basename(git_url)[:-4]
    else:
        repo_name = os.path.basename(git_url)
    
    dest_path = dest / repo_name
    
    logger.info("Cloning %s to %s", git_url, dest_path)
    
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", git_url, str(dest_path)],
            capture_output=True,
            text=True,
            check=True
        )
        return dest_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git clone failed: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError("Git is not installed or not in PATH")


def _validate_plugin_manifest(plugin_dir: Path) -> dict:
    """Validate that plugin directory contains a valid manifest."""
    import json
    
    manifest_path = plugin_dir / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError(f"No manifest.json found in {plugin_dir}")
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid manifest.json: {e}") from e
    
    # Check required fields
    required_fields = ['id', 'name', 'version']
    for field in required_fields:
        if field not in manifest:
            raise RuntimeError(f"Manifest missing required field: {field}")
    
    return manifest


def _verify_plugin_signature(plugin_path: Path, force: bool = False) -> bool:
    """Verify plugin signature and prompt user if needed.
    
    Args:
        plugin_path: Path to plugin directory
        force: If True, skip confirmation prompts
        
    Returns:
        True if installation should proceed, False if cancelled
    """
    try:
        from jupiter.core.bridge.signature import (
            verify_plugin,
            TrustLevel,
        )
        from jupiter.core.bridge.dev_mode import is_dev_mode
    except ImportError:
        # Signature module not available, allow installation
        print("  ⚠️ Signature verification unavailable")
        return True
    
    # Check if dev mode allows unsigned plugins
    dev_mode_active = False
    try:
        dev_mode_active = is_dev_mode()
    except Exception:
        pass
    
    # Verify the plugin
    result = verify_plugin(plugin_path)
    
    # Trust level emojis and descriptions
    trust_info = {
        TrustLevel.OFFICIAL: ("🏆", "Official Jupiter plugin"),
        TrustLevel.VERIFIED: ("✅", "Verified third-party plugin"),
        TrustLevel.COMMUNITY: ("👥", "Community-signed plugin"),
        TrustLevel.UNSIGNED: ("⚠️", "Unsigned plugin"),
    }
    
    emoji, desc = trust_info.get(result.trust_level, ("❓", "Unknown trust level"))
    print(f"  {emoji} Trust level: {result.trust_level.value} ({desc})")
    
    if result.signature_info:
        print(f"     Signed by: {result.signature_info.signer_name}")
    
    # Handle based on trust level
    if result.trust_level == TrustLevel.UNSIGNED:
        if dev_mode_active:
            print("  ℹ️ Dev mode: allowing unsigned plugin")
            return True
        
        if force:
            print("  ⚠️ Installing unsigned plugin (--force)")
            return True
        
        # Ask for confirmation
        print("\n  ⚠️ WARNING: This plugin is not signed.")
        print("     Installing unsigned plugins may pose security risks.")
        confirm = input("     Do you want to proceed? [y/N] ")
        if confirm.lower() not in ('y', 'yes'):
            return False
        return True
    
    elif result.trust_level == TrustLevel.COMMUNITY:
        # Community plugins are OK but show a note
        if not result.valid:
            print(f"  ⚠️ Signature validation issue: {result.error}")
            if not force:
                confirm = input("     Do you want to proceed anyway? [y/N] ")
                if confirm.lower() not in ('y', 'yes'):
                    return False
        return True
    
    else:
        # VERIFIED or OFFICIAL - proceed
        if not result.valid:
            print(f"  ⚠️ Warning: {result.error}")
        return True


def _install_plugin_dependencies(plugin_path: Path) -> bool:
    """Install Python dependencies from plugin's requirements.txt.
    
    Args:
        plugin_path: Path to the plugin directory
        
    Returns:
        True if dependencies were installed, False otherwise
    """
    import subprocess
    
    requirements_file = plugin_path / "requirements.txt"
    if not requirements_file.exists():
        return False
    
    print("  📦 Installing dependencies from requirements.txt...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            check=True
        )
        print("  ✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ⚠️ Warning: Failed to install dependencies: {e.stderr}")
        logger.warning("Failed to install plugin dependencies: %s", e.stderr)
        return False


def handle_plugins_install(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins install <source>` command.
    
    Supports:
    - Local path (directory or ZIP file)
    - HTTP/HTTPS URL to ZIP file
    - Git repository URL
    
    Options:
    - --install-deps: Install Python dependencies from requirements.txt
    - --dry-run: Simulate installation without making changes
    """
    source = args.source
    force = getattr(args, 'force', False)
    install_deps = getattr(args, 'install_deps', False)
    dry_run = getattr(args, 'dry_run', False)
    
    plugins_dir = _get_plugins_dir()
    
    if not plugins_dir.exists() and not dry_run:
        plugins_dir.mkdir(parents=True, exist_ok=True)
    
    mode_str = "[DRY RUN] " if dry_run else ""
    print(f"{mode_str}📦 Installing plugin from: {source}")
    
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            
            # Determine source type and get plugin directory
            if source.startswith(('http://', 'https://')):
                # URL - download
                if source.endswith('.git'):
                    # Git URL
                    plugin_path = _clone_git_repo(source, tmp_path)
                else:
                    # ZIP URL
                    zip_file = _download_from_url(source, tmp_path)
                    plugin_path = _extract_zip(zip_file, tmp_path)
            elif Path(source).exists():
                local_path = Path(source)
                if local_path.is_dir():
                    # Local directory - copy
                    plugin_path = local_path
                elif local_path.suffix == '.zip':
                    # Local ZIP file
                    plugin_path = _extract_zip(local_path, tmp_path)
                else:
                    raise RuntimeError(f"Unsupported source type: {source}")
            else:
                raise RuntimeError(f"Source not found: {source}")
            
            # Validate manifest
            manifest = _validate_plugin_manifest(plugin_path)
            plugin_id = manifest['id']
            plugin_name = manifest['name']
            plugin_version = manifest['version']
            
            print(f"  Plugin ID: {plugin_id}")
            print(f"  Name: {plugin_name}")
            print(f"  Version: {plugin_version}")
            
            # Check for dependencies
            requirements_file = plugin_path / "requirements.txt"
            if requirements_file.exists():
                print(f"  📋 Found requirements.txt")
                if install_deps:
                    if dry_run:
                        print(f"  {mode_str}Would install dependencies")
                    else:
                        _install_plugin_dependencies(plugin_path)
                else:
                    print(f"     Use --install-deps to install dependencies")
            
            # Verify signature
            signature_result = _verify_plugin_signature(plugin_path, force)
            if signature_result is False:
                # User declined to install unsigned/untrusted plugin
                print("Installation cancelled")
                sys.exit(1)
            
            # Check if already installed
            dest_path = plugins_dir / plugin_id
            if dest_path.exists():
                if force:
                    print(f"  ⚠️ Plugin already exists, {'would overwrite' if dry_run else 'overwriting'} (--force)")
                    if not dry_run:
                        shutil.rmtree(dest_path)
                else:
                    print(f"❌ Plugin '{plugin_id}' already installed at {dest_path}")
                    print(f"   Use --force to overwrite")
                    sys.exit(1)
            
            if dry_run:
                print(f"\n{mode_str}✅ Plugin '{plugin_id}' would be installed to {dest_path}")
                print(f"   Run without --dry-run to install")
                return
            
            # Copy to plugins directory
            if plugin_path.resolve() != dest_path.resolve():
                shutil.copytree(plugin_path, dest_path)
            
            # Install dependencies after copying (if --install-deps)
            if install_deps:
                _install_plugin_dependencies(dest_path)
            
            print(f"✅ Plugin '{plugin_id}' installed to {dest_path}")
            print(f"   Restart Jupiter to load the plugin")
            
    except Exception as e:
        print(f"❌ Installation failed: {e}", file=sys.stderr)
        logger.exception("Plugin installation failed")
        sys.exit(1)


def handle_plugins_uninstall(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins uninstall <id>` command."""
    plugin_id = args.plugin_id
    force = getattr(args, 'force', False)
    
    bridge = get_bridge()
    plugins_dir = _get_plugins_dir()
    
    # Check if plugin exists
    info = bridge.get_plugin(plugin_id) if bridge else None
    plugin_path = plugins_dir / plugin_id
    
    if not plugin_path.exists() and not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Prevent uninstalling core plugins
    if info and info.manifest.plugin_type.value == "core":
        print(f"❌ Cannot uninstall core plugin '{plugin_id}'", file=sys.stderr)
        sys.exit(1)
    
    # Confirm uninstall
    if not force:
        confirm = input(f"⚠️ Are you sure you want to uninstall '{plugin_id}'? [y/N] ")
        if confirm.lower() not in ('y', 'yes'):
            print("Cancelled")
            return
    
    try:
        if plugin_path.exists():
            shutil.rmtree(plugin_path)
            print(f"✅ Plugin '{plugin_id}' uninstalled from {plugin_path}")
            print(f"   Restart Jupiter to complete removal")
        else:
            print(f"⚠️ Plugin directory not found at {plugin_path}")
            print(f"   The plugin may be a built-in or installed elsewhere")
    except Exception as e:
        print(f"❌ Uninstall failed: {e}", file=sys.stderr)
        sys.exit(1)


def handle_plugins_scaffold(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins scaffold <id>` command.
    
    Generates a new plugin skeleton with:
    - manifest.json
    - plugin.py (main plugin file)
    - README.md
    """
    plugin_id = args.plugin_id
    output_dir = Path(getattr(args, 'output', '.'))
    
    # Validate plugin ID
    if not plugin_id.replace('_', '').replace('-', '').isalnum():
        print(f"❌ Invalid plugin ID: {plugin_id}", file=sys.stderr)
        print(f"   Use only letters, numbers, underscores, and hyphens")
        sys.exit(1)
    
    plugin_dir = output_dir / plugin_id
    
    if plugin_dir.exists():
        print(f"❌ Directory already exists: {plugin_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Create plugin directory
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    # Create manifest.json
    import json
    manifest = {
        "id": plugin_id,
        "name": plugin_id.replace('_', ' ').replace('-', ' ').title(),
        "version": "0.1.0",
        "description": f"A Jupiter plugin: {plugin_id}",
        "author": "",
        "homepage": "",
        "license": "MIT",
        "plugin_type": "external",
        "permissions": ["api"],
        "capabilities": {
            "hooks": ["on_scan", "on_analyze"]
        },
        "entry_point": "plugin.py"
    }
    
    (plugin_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    
    # Create plugin.py
    class_name = plugin_id.replace("_", " ").replace("-", " ").title().replace(" ", "")
    plugin_template = f'''"""
Jupiter Plugin: {plugin_id}

Version: 0.1.0
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    PluginType,
    Permission,
    CLIContribution,
    APIContribution,
    UIContribution,
)

logger = logging.getLogger(__name__)


class {class_name}Plugin(IPlugin):
    """Main plugin class."""
    
    def __init__(self, manifest: IPluginManifest):
        self._manifest = manifest
        self._enabled = True
        self._logger = logging.getLogger(f"jupiter.plugins.{{manifest.id}}")
    
    @property
    def manifest(self) -> IPluginManifest:
        return self._manifest
    
    def initialize(self) -> None:
        """Called when the plugin is loaded."""
        self._logger.info("[%s] Initializing", self._manifest.id)
    
    def shutdown(self) -> None:
        """Called when the plugin is unloaded."""
        self._logger.info("[%s] Shutting down", self._manifest.id)
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Apply configuration."""
        self._enabled = config.get("enabled", True)
        self._logger.info("[%s] Configured: enabled=%s", self._manifest.id, self._enabled)
    
    def get_cli_contribution(self) -> Optional[CLIContribution]:
        """Return CLI contribution (optional)."""
        return None
    
    def get_api_contribution(self) -> Optional[APIContribution]:
        """Return API contribution (optional)."""
        return None
    
    def get_ui_contribution(self) -> Optional[UIContribution]:
        """Return UI contribution (optional)."""
        return None
    
    # Plugin hooks
    def on_scan(self, report: Dict[str, Any], **kwargs) -> None:
        """Called after a scan completes."""
        pass
    
    def on_analyze(self, report: Dict[str, Any], **kwargs) -> None:
        """Called after an analysis completes."""
        pass
'''
    
    (plugin_dir / "plugin.py").write_text(plugin_template, encoding='utf-8')
    
    # Create README.md
    readme_template = f'''# {plugin_id.replace("_", " ").replace("-", " ").title()}

A Jupiter plugin.

## Installation

Copy this directory to your Jupiter plugins folder.

## Configuration

No configuration required.

## Usage

This plugin will be loaded automatically when Jupiter starts.

## Development

Edit `plugin.py` to add your plugin logic.

See the [Jupiter Plugin Development Guide](https://github.com/your-repo/jupiter/docs/dev_guide.md) for more information.
'''
    
    (plugin_dir / "README.md").write_text(readme_template, encoding='utf-8')
    
    print(f"✅ Plugin scaffold created at: {plugin_dir}")
    print(f"\nFiles created:")
    print(f"  📄 manifest.json - Plugin metadata")
    print(f"  📄 plugin.py     - Main plugin code")
    print(f"  📄 README.md     - Documentation")
    print(f"\nNext steps:")
    print(f"  1. Edit manifest.json with your plugin details")
    print(f"  2. Implement your plugin logic in plugin.py")
    print(f"  3. Copy the plugin to your plugins directory")
    print(f"  4. Restart Jupiter to load the plugin")


def handle_plugins_reload(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins reload <id>` command.
    
    Hot-reloads a plugin in development mode.
    Only works when the server is running in dev mode.
    """
    plugin_id = args.plugin_id
    
    bridge = get_bridge()
    
    if not bridge:
        print("❌ Bridge not available", file=sys.stderr)
        sys.exit(1)
    
    # Check if plugin exists
    info = bridge.get_plugin(plugin_id)
    if not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Check if developer mode is enabled
    if not bridge.developer_mode:
        print(f"❌ Hot reload requires developer mode", file=sys.stderr)
        print(f"   Set developer_mode: true in your jupiter config")
        sys.exit(1)
    
    # Attempt reload
    try:
        if hasattr(bridge, 'reload_plugin'):
            result = getattr(bridge, 'reload_plugin')(plugin_id)
            if result:
                print(f"✅ Plugin '{plugin_id}' reloaded successfully")
            else:
                print(f"⚠️ Plugin '{plugin_id}' reload returned no result")
        else:
            # Fallback: emit reload event via event bus
            from jupiter.core.bridge import get_event_bus
            get_event_bus().emit("plugin.reload", {"plugin_id": plugin_id})
            print(f"✅ Reload signal sent for plugin '{plugin_id}'")
            print(f"   Check server logs for reload result")
    except Exception as e:
        print(f"❌ Reload failed: {e}", file=sys.stderr)
        logger.exception("Plugin reload failed")
        sys.exit(1)


def handle_plugins_sign(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins sign <path>` command.
    
    Signs a plugin with a cryptographic signature.
    Creates a plugin.sig file in the plugin directory.
    """
    plugin_path = Path(args.path).resolve()
    
    # Validate plugin directory
    if not plugin_path.exists():
        print(f"❌ Path not found: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    
    if not plugin_path.is_dir():
        print(f"❌ Not a directory: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    
    # Check for manifest
    manifest_path = plugin_path / "plugin.yaml"
    if not manifest_path.exists():
        # Try JSON manifest
        manifest_path = plugin_path / "plugin.json"
    if not manifest_path.exists():
        manifest_path = plugin_path / "manifest.json"
    
    if not manifest_path.exists():
        print(f"❌ Plugin manifest not found in: {plugin_path}", file=sys.stderr)
        print(f"   Expected: plugin.yaml, plugin.json, or manifest.json")
        sys.exit(1)
    
    # Get signer info
    signer_id = getattr(args, 'signer_id', None) or os.getenv("JUPITER_SIGNER_ID", "local-developer")
    signer_name = getattr(args, 'signer_name', None) or os.getenv("JUPITER_SIGNER_NAME", "Local Developer")
    
    # Get trust level
    trust_level_str = getattr(args, 'trust_level', None) or "community"
    
    try:
        from jupiter.core.bridge.signature import TrustLevel, sign_plugin, SigningResult
        
        trust_level = TrustLevel(trust_level_str.lower())
    except ValueError:
        print(f"❌ Invalid trust level: {trust_level_str}", file=sys.stderr)
        print(f"   Valid levels: official, verified, community, unsigned")
        sys.exit(1)
    except ImportError:
        print(f"❌ Signature module not available", file=sys.stderr)
        sys.exit(1)
    
    # Get private key path (optional)
    private_key_path = None
    if hasattr(args, 'key') and args.key:
        private_key_path = Path(args.key).resolve()
        if not private_key_path.exists():
            print(f"❌ Private key not found: {private_key_path}", file=sys.stderr)
            sys.exit(1)
    
    # Sign the plugin
    print(f"🔏 Signing plugin at: {plugin_path}")
    print(f"   Signer: {signer_name} ({signer_id})")
    print(f"   Trust level: {trust_level.value}")
    
    try:
        result = sign_plugin(
            plugin_path=plugin_path,
            signer_id=signer_id,
            signer_name=signer_name,
            private_key_path=private_key_path,
            trust_level=trust_level,
        )
        
        if result.success:
            print(f"✅ Plugin signed successfully")
            print(f"   Signature file: {plugin_path / 'plugin.sig'}")
            if result.signature_path:
                print(f"   Path: {result.signature_path}")
        else:
            print(f"❌ Signing failed: {result.error}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Signing failed: {e}", file=sys.stderr)
        logger.exception("Plugin signing failed")
        sys.exit(1)


def handle_plugins_verify(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins verify <path>` command.
    
    Verifies a plugin's signature.
    """
    plugin_path = Path(args.path).resolve()
    
    # Validate plugin directory
    if not plugin_path.exists():
        print(f"❌ Path not found: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    
    if not plugin_path.is_dir():
        print(f"❌ Not a directory: {plugin_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        from jupiter.core.bridge.signature import verify_plugin, TrustLevel
        
        print(f"🔍 Verifying plugin at: {plugin_path}")
        
        result = verify_plugin(plugin_path)
        
        # Trust level emojis
        trust_emojis = {
            TrustLevel.OFFICIAL: "🏆",
            TrustLevel.VERIFIED: "✅",
            TrustLevel.COMMUNITY: "👥",
            TrustLevel.UNSIGNED: "⚠️",
        }
        
        emoji = trust_emojis.get(result.trust_level, "❓")
        
        print(f"\nResults:")
        print(f"   Trust level: {emoji} {result.trust_level.value}")
        print(f"   Valid: {'✅ Yes' if result.valid else '❌ No'}")
        
        if result.signature_info:
            info = result.signature_info
            print(f"\nSignature info:")
            print(f"   Signer: {info.signer_name} ({info.signer_id})")
            print(f"   Algorithm: {info.algorithm.value}")
            print(f"   Plugin: {info.plugin_id} v{info.plugin_version}")
            if info.timestamp:
                from datetime import datetime
                signed_at = datetime.fromtimestamp(info.timestamp)
                print(f"   Signed at: {signed_at.isoformat()}")
        
        if result.warnings:
            print(f"\n⚠️ Warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")
        
        if result.error:
            print(f"\n❌ Error: {result.error}")
        
        # Exit code based on trust level
        if hasattr(args, 'require_level') and args.require_level:
            try:
                required = TrustLevel(args.require_level.lower())
                if result.trust_level >= required:
                    print(f"\n✅ Plugin meets required trust level ({required.value})")
                else:
                    print(f"\n❌ Plugin does not meet required trust level ({required.value})", file=sys.stderr)
                    sys.exit(1)
            except ValueError:
                pass
                
    except ImportError:
        print(f"❌ Signature module not available", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification failed: {e}", file=sys.stderr)
        logger.exception("Plugin verification failed")
        sys.exit(1)


def handle_plugins_update(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins update <id>` command.
    
    Updates a plugin to a new version. If --source is provided, uses that as
    the update source. Otherwise, looks for update source in plugin metadata.
    
    Features:
    - Creates backup before update (unless --no-backup)
    - Supports rollback on failure
    - Optional dependency installation (--install-deps)
    """
    import json
    from datetime import datetime
    
    plugin_id = args.plugin_id
    source = getattr(args, 'source', None)
    force = getattr(args, 'force', False)
    install_deps = getattr(args, 'install_deps', False)
    no_backup = getattr(args, 'no_backup', False)
    
    bridge = get_bridge()
    plugins_dir = _get_plugins_dir()
    
    # Check if plugin exists
    info = bridge.get_plugin(plugin_id) if bridge else None
    plugin_path = plugins_dir / plugin_id
    
    if not plugin_path.exists() and not info:
        print(f"❌ Plugin '{plugin_id}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Prevent updating core plugins
    if info and info.manifest.plugin_type.value == "core":
        print(f"❌ Cannot update core plugin '{plugin_id}'", file=sys.stderr)
        sys.exit(1)
    
    # Get current version
    current_version = "unknown"
    if info:
        current_version = info.manifest.version
    elif plugin_path.exists():
        manifest_path = plugin_path / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                current_version = manifest.get('version', 'unknown')
            except Exception:
                pass
    
    print(f"🔄 Updating plugin '{plugin_id}' (current: v{current_version})")
    
    # If no source provided, try to get from manifest metadata
    if not source:
        if plugin_path.exists():
            manifest_path = plugin_path / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    source = manifest.get('repository') or manifest.get('homepage')
                except Exception:
                    pass
        
        if not source:
            print(f"❌ No update source provided and none found in manifest", file=sys.stderr)
            print(f"   Use --source <url|path> to specify update source")
            sys.exit(1)
    
    print(f"  Source: {source}")
    
    # Create backup
    backup_path = None
    if not no_backup and plugin_path.exists():
        backup_dir = plugins_dir / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{plugin_id}_{timestamp}"
        print(f"  💾 Creating backup at {backup_path}")
        try:
            shutil.copytree(plugin_path, backup_path)
        except Exception as e:
            print(f"  ⚠️ Warning: Failed to create backup: {e}")
            backup_path = None
    
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            
            # Determine source type and get plugin directory
            if source.startswith(('http://', 'https://')):
                if source.endswith('.git'):
                    new_plugin_path = _clone_git_repo(source, tmp_path)
                else:
                    zip_file = _download_from_url(source, tmp_path)
                    new_plugin_path = _extract_zip(zip_file, tmp_path)
            elif Path(source).exists():
                local_path = Path(source)
                if local_path.is_dir():
                    new_plugin_path = local_path
                elif local_path.suffix == '.zip':
                    new_plugin_path = _extract_zip(local_path, tmp_path)
                else:
                    raise RuntimeError(f"Unsupported source type: {source}")
            else:
                raise RuntimeError(f"Source not found: {source}")
            
            # Validate new manifest
            new_manifest = _validate_plugin_manifest(new_plugin_path)
            new_version = new_manifest['version']
            
            # Check version
            if new_version == current_version and not force:
                print(f"  ℹ️ Already at version {current_version}")
                print(f"     Use --force to reinstall")
                return
            
            print(f"  New version: v{new_version}")
            
            # Verify signature
            signature_result = _verify_plugin_signature(new_plugin_path, force)
            if signature_result is False:
                print("Update cancelled")
                sys.exit(1)
            
            # Remove old version
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
            
            # Install new version
            shutil.copytree(new_plugin_path, plugin_path)
            
            # Install dependencies if requested
            if install_deps:
                _install_plugin_dependencies(plugin_path)
            
            print(f"✅ Plugin '{plugin_id}' updated to v{new_version}")
            print(f"   Restart Jupiter to load the updated plugin")
            
            # Clean up backup on success (optional)
            # Keep backup for now for safety
            if backup_path:
                print(f"   Backup saved at {backup_path}")
            
    except Exception as e:
        print(f"❌ Update failed: {e}", file=sys.stderr)
        logger.exception("Plugin update failed")
        
        # Rollback on failure
        if backup_path and backup_path.exists():
            print(f"  🔄 Rolling back to previous version...")
            try:
                if plugin_path.exists():
                    shutil.rmtree(plugin_path)
                shutil.copytree(backup_path, plugin_path)
                print(f"  ✅ Rollback successful")
            except Exception as rollback_error:
                print(f"  ❌ Rollback failed: {rollback_error}", file=sys.stderr)
        
        sys.exit(1)


def handle_plugins_check_updates(args: argparse.Namespace) -> None:
    """Handle `jupiter plugins check-updates` command.
    
    Checks for available updates for all installed plugins.
    This is a placeholder - actual implementation would need a registry/marketplace.
    """
    import json
    
    as_json = getattr(args, 'json', False)
    
    bridge = get_bridge()
    plugins_dir = _get_plugins_dir()
    
    if not bridge:
        print("❌ Bridge not available", file=sys.stderr)
        sys.exit(1)
    
    plugins = bridge.get_all_plugins()
    results = []
    
    print("🔍 Checking for plugin updates...")
    print()
    
    for info in plugins:
        plugin_id = info.manifest.id
        current_version = info.manifest.version
        
        # Get repository/homepage from manifest
        update_source = None
        manifest_path = plugins_dir / plugin_id / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                update_source = manifest.get('repository') or manifest.get('homepage')
            except Exception:
                pass
        
        # For now, we just report what we know
        # In the future, this would query a registry/marketplace
        result = {
            "plugin_id": plugin_id,
            "current_version": current_version,
            "update_source": update_source,
            "update_available": None,  # Unknown without registry
            "latest_version": None,
        }
        results.append(result)
        
        if not as_json:
            print(f"  {plugin_id}: v{current_version}")
            if update_source:
                print(f"     Source: {update_source}")
            else:
                print(f"     ⚠️ No update source configured")
    
    if as_json:
        print(json.dumps({"plugins": results}, indent=2))
    else:
        print()
        print("ℹ️ Automatic update checking requires a plugin registry.")
        print("   Use 'jupiter plugins update <id> --source <url>' to update manually.")
