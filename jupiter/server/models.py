"""Pydantic models for Jupiter API requests and responses."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    """Request model for POST /scan endpoint."""

    show_hidden: bool = Field(
        default=False, description="Include hidden files in the scan."
    )
    ignore_globs: Optional[List[str]] = Field(
        default=None, description="Glob patterns to ignore."
    )
    incremental: bool = Field(
        default=False, description="Use incremental scanning (cache)."
    )
    backend_name: Optional[str] = Field(
        default=None, description="Name of the backend to use (optional)."
    )
    capture_snapshot: bool = Field(
        default=True, description="Persist a snapshot once the scan finishes."
    )
    snapshot_label: Optional[str] = Field(
        default=None, description="Optional human label stored with the snapshot."
    )


class FileAnalysis(BaseModel):
    """Represents analysis data for a single file."""

    path: str
    size_bytes: int
    modified_timestamp: float
    file_type: str
    language_analysis: Optional[Dict[str, Any]] = None


class ScanReport(BaseModel):
    """Response model for scan operations."""

    report_schema_version: str = Field(
        default="1.0", description="Version of the report schema."
    )
    root: str
    files: List[FileAnalysis]
    dynamic: Optional[Dict[str, Any]] = Field(
        default=None, description="Dynamic analysis data (e.g., runtime call counts)."
    )
    plugins: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List of active plugins and their status."
    )
    api: Optional[Dict[str, Any]] = Field(
        default=None, description="API inspection data."
    )
    quality: Optional[Dict[str, Any]] = Field(
        default=None, description="Code quality metrics (complexity, duplication)."
    )
    refactoring: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Refactoring recommendations derived from quality analysis."
    )
    pylance: Optional[Dict[str, Any]] = Field(
        default=None, description="Static type analysis results from Pyright/Pylance."
    )
    code_quality: Optional[Dict[str, Any]] = Field(
        default=None, description="Code quality plugin analysis results."
    )


class RunRequest(BaseModel):
    """Request model for POST /run endpoint."""

    command: List[str] = Field(
        ..., description="The command to execute as a list of strings."
    )
    with_dynamic: bool = Field(
        default=False, description="Enable dynamic analysis (tracing) for this run."
    )
    backend_name: Optional[str] = Field(
        default=None, description="Name of the backend to use (optional)."
    )
    cwd: Optional[str] = Field(
        default=None, description="Working directory for command execution (optional, defaults to project root)."
    )


class RunResponse(BaseModel):
    """Response model for command execution results."""

    stdout: str
    stderr: str
    returncode: int
    dynamic_analysis: Optional[Dict[str, Any]] = None


class PythonProjectSummary(BaseModel):
    """Summary statistics for Python code in a project."""

    total_files: int
    total_functions: int
    total_potentially_unused_functions: int
    avg_functions_per_file: float
    quality_score: Optional[float] = None


class JsTsProjectSummary(BaseModel):
    """Summary statistics for JS/TS code in a project."""

    total_files: int
    total_functions: int
    avg_functions_per_file: float


class Hotspot(BaseModel):
    """Represents a hotspot (area of interest) in the project."""

    path: str
    details: str


class UserModel(BaseModel):
    """Model for a Jupiter user."""
    name: str
    token: str
    role: str = "viewer"


class RefactoringRecommendation(BaseModel):
    """Represents a code refactoring recommendation."""

    path: str
    type: str
    details: str
    severity: str
    locations: Optional[List[Dict[str, Any]]] = None
    code_excerpt: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response model for GET /analyze endpoint."""

    file_count: int
    total_size_bytes: int
    average_size_bytes: float
    by_extension: Dict[str, int]
    hotspots: Dict[str, List[Hotspot]]
    python_summary: Optional[PythonProjectSummary] = None
    js_ts_summary: Optional[JsTsProjectSummary] = None
    plugins: Optional[List[Dict[str, Any]]] = None
    refactoring: List[RefactoringRecommendation] = Field(default_factory=list)
    api: Optional[Dict[str, Any]] = None
    # Plugin data fields
    code_quality: Optional[Dict[str, Any]] = None
    pylance: Optional[Dict[str, Any]] = None
    # Generic field for any other plugin data
    plugin_data: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MeetingStatus(BaseModel):
    """Response model for GET /meeting/status endpoint."""

    device_key: Optional[str] = Field(
        None, description="Device key registered with Meeting service."
    )
    is_licensed: bool = Field(
        description="Whether the device has a valid license."
    )
    session_active: bool = Field(
        description="Whether an active session is running."
    )
    session_remaining_seconds: Optional[int] = Field(
        None, description="Remaining seconds in session (if limited)."
    )
    status: str = Field(
        description="Overall status: 'active', 'limited', 'expired', or 'unlicensed'."
    )
    message: Optional[str] = Field(None, description="Status message or error.")


class LicenseStatus(BaseModel):
    """Response model for GET /license/status endpoint with detailed Meeting verification."""

    status: str = Field(
        description="License status: 'valid', 'invalid', 'network_error', or 'config_error'."
    )
    message: str = Field(
        description="Human-readable message explaining the license status."
    )
    device_key: Optional[str] = Field(
        None, description="The device key that was checked."
    )
    http_status: Optional[int] = Field(
        None, description="HTTP status code from Meeting API (if applicable)."
    )
    authorized: Optional[bool] = Field(
        None, description="Whether the device is authorized in Meeting."
    )
    device_type: Optional[str] = Field(
        None, description="The device type reported by Meeting."
    )
    token_count: Optional[int] = Field(
        None, description="The number of tokens remaining for this device."
    )
    checked_at: Optional[str] = Field(
        None, description="ISO timestamp when the license was last checked."
    )
    meeting_base_url: Optional[str] = Field(
        None, description="The Meeting API base URL that was used."
    )
    device_type_expected: Optional[str] = Field(
        None, description="The expected device type for Jupiter."
    )


class HealthStatus(BaseModel):
    """Response model for GET /health endpoint."""

    status: str
    root: str


class RootUpdate(BaseModel):
    """Request model for POST /config/root endpoint."""

    path: str


class RootUpdateResponse(BaseModel):
    """Response model for POST /config/root endpoint."""

    status: str
    root: str


class FSListEntry(BaseModel):
    """Represents a single filesystem entry."""

    name: str
    path: str
    is_dir: bool


class FSListResponse(BaseModel):
    """Response model for GET /fs/list endpoint."""

    current: str
    entries: List[FSListEntry]


class ErrorDetail(BaseModel):
    """Standard error detail model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: ErrorDetail


class ConfigModel(BaseModel):
    """Model for full configuration."""
    server_host: str
    server_port: int
    gui_host: str
    gui_port: int
    meeting_device_key: Optional[str]
    meeting_auth_token: Optional[str] = None
    meeting_heartbeat_interval: int = 60
    ui_theme: str
    ui_language: str
    log_level: str = "INFO"
    log_path: Optional[str] = None
    plugins_enabled: List[str]
    plugins_disabled: List[str]
    # Performance
    perf_parallel_scan: bool = True
    perf_max_workers: Optional[int] = None
    perf_scan_timeout: int = 300
    perf_graph_simplification: bool = False
    perf_max_graph_nodes: int = 1000
    # Security
    sec_allow_run: bool = True
    # API Inspection
    api_connector: Optional[str] = None
    api_app_var: Optional[str] = None
    api_path: Optional[str] = None


class RawConfigModel(BaseModel):
    """Model for raw configuration file content."""
    content: str


class UpdateRequest(BaseModel):
    """Request model for POST /update endpoint."""
    source: str
    force: bool = False


class SnapshotMetadataModel(BaseModel):
    """Metadata describing a stored snapshot.
    
    Note: This Pydantic model mirrors SnapshotMetadata dataclass in jupiter.core.history
    to avoid circular imports. Keep both in sync when modifying fields.
    """

    id: str
    timestamp: float
    label: str
    jupiter_version: str
    backend_name: Optional[str]
    project_root: str
    project_name: str
    file_count: int
    total_size_bytes: int
    function_count: int
    unused_function_count: int


class SnapshotListResponse(BaseModel):
    snapshots: List[SnapshotMetadataModel]


class SnapshotResponse(BaseModel):
    metadata: SnapshotMetadataModel
    report: Dict[str, Any]


class SnapshotDiffResponse(BaseModel):
    snapshot_a: SnapshotMetadataModel
    snapshot_b: SnapshotMetadataModel
    diff: Dict[str, Any]


class SimulateRequest(BaseModel):
    """Request model for POST /simulate/remove endpoint."""
    target_type: str = Field(..., description="Type of target: 'file' or 'function'")
    path: str = Field(..., description="Path to the file")
    function_name: Optional[str] = Field(None, description="Name of the function (if target_type is 'function')")


class ImpactModel(BaseModel):
    """Represents a single impact detected during simulation."""
    target: str
    impact_type: str
    details: str
    severity: str


class SimulateResponse(BaseModel):
    """Response model for simulation results."""
    target: str
    impacts: List[ImpactModel]
    risk_score: str

class LoginRequest(BaseModel):
    username: str
    password: str

