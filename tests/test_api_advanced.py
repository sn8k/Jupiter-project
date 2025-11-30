from fastapi.testclient import TestClient
from jupiter.server.api import app
from jupiter.server.manager import ProjectManager
from jupiter.config import load_config
from jupiter.core.plugin_manager import PluginManager as JupiterPluginManager
from pathlib import Path
import pytest
import time

@pytest.fixture
def client(tmp_path):
    # Setup app state
    app.state.root_path = tmp_path
    config = load_config(tmp_path)
    app.state.project_manager = ProjectManager(config)
    app.state.plugin_manager = JupiterPluginManager(config.plugins)
    # Initialize history manager
    app.state.history_manager = None # Reset
    
    # Create dummy files
    (tmp_path / "main.py").write_text("def foo(): pass")
    
    return TestClient(app)

def test_scan_endpoint(client):
    response = client.post("/scan", json={"incremental": False})
    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) == 1
    assert "files" in data

def test_analyze_endpoint(client):
    # Scan first to populate cache/files
    client.post("/scan", json={"incremental": False})
    
    response = client.get("/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["file_count"] == 1
    assert "python_summary" in data

def test_simulate_remove_endpoint(client):
    # Scan first
    client.post("/scan", json={"incremental": False})
    
    response = client.post("/simulate/remove", json={"target_type": "file", "path": "main.py"})
    assert response.status_code == 200
    data = response.json()
    # The target string format depends on simulator implementation
    assert "main.py" in data["target"]
    assert "risk_score" in data

def test_snapshots_endpoints(client):
    # Create snapshot via scan
    client.post("/scan", json={"incremental": False})
    
    # List snapshots
    response = client.get("/snapshots")
    assert response.status_code == 200
    snapshots = response.json()["snapshots"]
    assert len(snapshots) == 1
    snap_id = snapshots[0]["id"]
    
    # Get snapshot details
    response = client.get(f"/snapshots/{snap_id}")
    assert response.status_code == 200
    
    # Create another snapshot
    time.sleep(0.01) # Ensure different timestamp
    client.post("/scan", json={"incremental": False})
    response = client.get("/snapshots")
    snapshots = response.json()["snapshots"]
    assert len(snapshots) == 2
    snap_id_2 = snapshots[0]["id"] # Newest first
    
    # Diff
    response = client.get(f"/snapshots/diff?id_a={snapshots[1]['id']}&id_b={snap_id_2}")
    assert response.status_code == 200
    diff = response.json()
    assert "metrics_delta" in diff["diff"]
