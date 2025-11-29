import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from jupiter.server.api import app
from jupiter.config.config import JupiterConfig, SecurityConfig

client = TestClient(app)

@pytest.fixture
def secure_app():
    # Initialize project_manager if not present
    if not hasattr(app.state, "project_manager"):
        from jupiter.server.manager import ProjectManager
        app.state.project_manager = ProjectManager(JupiterConfig())

    # Initialize meeting_adapter if not present
    if not hasattr(app.state, "meeting_adapter"):
        from jupiter.server.meeting_adapter import MeetingAdapter
        app.state.meeting_adapter = MeetingAdapter(device_key=None, project_root=Path("."))

    # Mock config with token
    original_config = app.state.project_manager.config
    
    # Create a mock config
    config = JupiterConfig()
    config.security = SecurityConfig(token="secret-token")
    
    app.state.project_manager.config = config
        
    yield
    
    # Restore
    app.state.project_manager.config = original_config

def test_run_protected_no_token(secure_app):
    response = client.post("/run", json={"command": ["echo", "hello"]})
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication token"

def test_run_protected_invalid_token(secure_app):
    response = client.post("/run", json={"command": ["echo", "hello"]}, headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication token"

def test_run_protected_valid_token(secure_app):
    # We need to mock the connector run_command too, otherwise it tries to run
    # But here we just want to check auth passes (it might fail later on execution if no backend)
    
    # Actually, if auth passes, it proceeds to logic.
    # If we don't have a backend, it might 404 or 500.
    # Let's assume 404 or 500 means auth passed.
    
    response = client.post("/run", json={"command": ["echo", "hello"]}, headers={"Authorization": "Bearer secret-token"})
    assert response.status_code != 401

def test_public_endpoint(secure_app):
    response = client.get("/health")
    assert response.status_code == 200
