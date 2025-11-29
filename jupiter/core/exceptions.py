"""Jupiter project exceptions."""

class JupiterError(Exception):
    """Base exception for all Jupiter errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

class ScanError(JupiterError):
    """Raised when a scan fails."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="SCAN_FAILED", details=details)

class AnalyzeError(JupiterError):
    """Raised when analysis fails."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="ANALYZE_FAILED", details=details)

class RunError(JupiterError):
    """Raised when command execution fails."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="RUN_FAILED", details=details)

class MeetingError(JupiterError):
    """Raised when Meeting service interaction fails."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="MEETING_ERROR", details=details)
