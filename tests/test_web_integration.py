import os
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from dataclasses import dataclass, asdict

from jupiter.web.app import JupiterWebUI, WebUISettings
from jupiter.server.api import app
from jupiter.server.manager import ProjectManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.config import JupiterConfig
from jupiter.core.history import SnapshotMetadata

# --- Fixtures ---

@pytest.fixture
def web_ui_settings(tmp_path):
    return WebUISettings(root=tmp_path, port=8050)

@pytest.fixture
def web_ui(web_ui_settings):
    return JupiterWebUI(web_ui_settings)

@pytest.fixture
def api_client(tmp_path):
    # Setup app state
    app.state.root_path = tmp_path
    app.state.project_manager = ProjectManager(JupiterConfig())
    app.state.plugin_manager = PluginManager()
    app.state.history_manager = MagicMock()
    
    return TestClient(app)

# --- WebUI Server Tests ---

def test_web_ui_handler_context(web_ui, tmp_path):
    """Test the do_GET method for /context.json."""
    handler_partial = web_ui._build_handler()
    HandlerClass = handler_partial.func
    directory = handler_partial.keywords['directory']
    
    # Mock the socket and request
    mock_wfile = MagicMock()
    
    # Create a subclass that mocks wfile and prevents super().__init__ from running network code
    class MockHandler(HandlerClass):
        def __init__(self):
            self.wfile = mock_wfile
            self.path = "/context.json"
            self.directory = directory
            # We don't call super().__init__ to avoid socket usage
            
        def send_response(self, code, message=None):
            self.response_code = code
            
        def send_header(self, keyword, value):
            pass
            
        def end_headers(self):
            pass
            
    handler = MockHandler()
    handler.do_GET()
    
    # Check response code
    assert handler.response_code == 200
    
    # Check output
    # wfile.write is called with bytes
    args, _ = mock_wfile.write.call_args
    response_data = json.loads(args[0].decode('utf-8'))
    
    assert response_data['root'] == str(tmp_path)
    assert response_data['api_base_url'] == "http://127.0.0.1:8000" # Default if env var not set in this scope

# --- WebUI API Integration Tests ---

def test_api_config_endpoint(api_client):
    """Test /config endpoint used by WebUI."""
    response = api_client.get("/config")
    assert response.status_code == 200
    data = response.json()
    # The response is a ConfigModel, so it has keys like 'server_host', 'gui_host', etc.
    assert "server_host" in data
    assert "gui_host" in data
    assert "ui_theme" in data

def test_api_plugins_endpoint(api_client):
    """Test /plugins endpoint used by WebUI."""
    response = api_client.get("/plugins")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_reports_last_endpoint(api_client, tmp_path):
    """Test /reports/last endpoint used by WebUI."""
    # First, ensure there is a report
    # We can mock the return of ProjectManager.get_last_report or just create a file
    
    # Let's create a dummy report file
    cache_dir = tmp_path / ".jupiter" / "cache"
    cache_dir.mkdir(parents=True)
    report_path = cache_dir / "last_scan.json"
    report_data = {"files": [], "root": str(tmp_path)}
    report_path.write_text(json.dumps(report_data))
    
    response = api_client.get("/reports/last")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == str(tmp_path)

def test_api_snapshots_endpoints(api_client):
    """Test /snapshots endpoints used by WebUI."""
    # Mock history manager response
    # We need to return SnapshotMetadata objects because api.py uses asdict() on them
    
    snap1 = SnapshotMetadata(
        id="snap1", timestamp=1000.0, label="test1", jupiter_version="1.0",
        backend_name="local", project_root="/tmp", project_name="test",
        file_count=10, total_size_bytes=100, function_count=5, unused_function_count=1
    )
    snap2 = SnapshotMetadata(
        id="snap2", timestamp=2000.0, label="test2", jupiter_version="1.0",
        backend_name="local", project_root="/tmp", project_name="test",
        file_count=12, total_size_bytes=120, function_count=6, unused_function_count=2
    )
    
    app.state.history_manager.list_snapshots.return_value = [snap1, snap2]
    
    response = api_client.get("/snapshots")
    assert response.status_code == 200
    data = response.json()
    assert len(data["snapshots"]) == 2
    assert data["snapshots"][0]["id"] == "snap1"
    
    # Test diff
    mock_diff = MagicMock()
    mock_diff.to_dict.return_value = {
        "snapshot_a": asdict(snap1),
        "snapshot_b": asdict(snap2),
        "diff": {
            "files_added": [],
            "files_removed": [],
            "files_modified": [],
            "functions_added": [],
            "functions_removed": [],
            "metrics_delta": {}
        }
    }
    app.state.history_manager.compare_snapshots.return_value = mock_diff
    # We also need get_snapshot to return the metadata for the diff response
    def get_snapshot_side_effect(snap_id):
        if snap_id == "snap1": return snap1
        if snap_id == "snap2": return snap2
        return None
        
    app.state.history_manager.get_snapshot.side_effect = get_snapshot_side_effect
    
    response = api_client.get("/snapshots/diff?id_a=snap1&id_b=snap2")
    assert response.status_code == 200
    data = response.json()
    assert "diff" in data
    assert data["snapshot_a"]["id"] == "snap1"

