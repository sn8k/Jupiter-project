"""Exception classes for the Jupiter Plugin Bridge.

Version: 0.1.0

This module defines all exception types used by the Bridge system.
Each exception provides context about what went wrong and where.
"""

from __future__ import annotations

from typing import Any, Optional


class BridgeError(Exception):
    """Base exception for all Bridge-related errors.
    
    Attributes:
        message: Human-readable error description
        details: Additional context (dict, plugin_id, etc.)
    """
    
    def __init__(
        self, 
        message: str, 
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message
    
    def to_dict(self) -> dict[str, Any]:
        """Convert exception to a serializable dict."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class PluginError(BridgeError):
    """Error related to a specific plugin.
    
    Attributes:
        plugin_id: The ID of the plugin that caused the error
    """
    
    def __init__(
        self, 
        message: str, 
        plugin_id: str,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, details)
        self.plugin_id = plugin_id
        self.details["plugin_id"] = plugin_id
    
    def __str__(self) -> str:
        return f"[{self.plugin_id}] {self.message}"


class ManifestError(PluginError):
    """Error parsing or validating a plugin manifest (plugin.yaml).
    
    Raised when:
    - Manifest file is missing or unreadable
    - YAML syntax is invalid
    - Required fields are missing
    - Field values are invalid
    - Version constraints are not met
    """
    
    def __init__(
        self, 
        message: str, 
        plugin_id: str,
        field: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, plugin_id, details)
        self.field = field
        if field:
            self.details["field"] = field


class DependencyError(PluginError):
    """Error related to plugin dependencies.
    
    Raised when:
    - A required dependency is missing
    - A dependency version is incompatible
    - A circular dependency is detected
    - A dependency failed to load
    """
    
    def __init__(
        self, 
        message: str, 
        plugin_id: str,
        dependency: Optional[str] = None,
        required_version: Optional[str] = None,
        actual_version: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, plugin_id, details)
        self.dependency = dependency
        self.required_version = required_version
        self.actual_version = actual_version
        
        if dependency:
            self.details["dependency"] = dependency
        if required_version:
            self.details["required_version"] = required_version
        if actual_version:
            self.details["actual_version"] = actual_version


class ServiceNotFoundError(BridgeError):
    """Error when a requested service is not registered in the Bridge.
    
    Raised when:
    - Plugin requests a service that doesn't exist
    - Service was not initialized
    - Service was disabled
    """
    
    def __init__(
        self, 
        service_name: str,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        message = f"Service '{service_name}' not found in Bridge registry"
        super().__init__(message, details)
        self.service_name = service_name
        self.details["service_name"] = service_name


class PermissionDeniedError(PluginError):
    """Error when a plugin attempts an operation without required permission.
    
    Raised when:
    - Plugin tries to access filesystem without fs_read/fs_write
    - Plugin tries to run commands without run_commands
    - Plugin tries network calls without network_outbound
    - Plugin tries to access Meeting without access_meeting
    """
    
    def __init__(
        self, 
        message: str,
        plugin_id: str,
        permission: str,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, plugin_id, details)
        self.permission = permission
        self.details["permission"] = permission


class LifecycleError(PluginError):
    """Error during plugin lifecycle transitions.
    
    Raised when:
    - Plugin fails to initialize
    - Plugin fails to register contributions
    - Plugin fails health check
    - Invalid state transition attempted
    """
    
    def __init__(
        self, 
        message: str,
        plugin_id: str,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, plugin_id, details)
        self.current_state = current_state
        self.target_state = target_state
        
        if current_state:
            self.details["current_state"] = current_state
        if target_state:
            self.details["target_state"] = target_state


class CircularDependencyError(DependencyError):
    """Error when circular dependencies are detected between plugins.
    
    Includes the cycle path for debugging.
    """
    
    def __init__(
        self, 
        plugin_id: str,
        cycle: list[str],
        details: Optional[dict[str, Any]] = None
    ) -> None:
        cycle_str = " -> ".join(cycle)
        message = f"Circular dependency detected: {cycle_str}"
        super().__init__(message, plugin_id, details=details)
        self.cycle = cycle
        self.details["cycle"] = cycle


class ValidationError(BridgeError):
    """Error validating configuration or input data.
    
    Raised when:
    - JSON Schema validation fails
    - Configuration values are out of range
    - Required configuration is missing
    """
    
    def __init__(
        self, 
        message: str,
        schema_path: Optional[str] = None,
        validation_errors: Optional[list[str]] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, details)
        self.schema_path = schema_path
        self.validation_errors = validation_errors or []
        
        if schema_path:
            self.details["schema_path"] = schema_path
        if validation_errors:
            self.details["validation_errors"] = validation_errors


class SignatureError(PluginError):
    """Error related to plugin signature verification.
    
    Raised when:
    - Signature file is missing (in strict mode)
    - Signature verification fails
    - Certificate is invalid or expired
    """
    
    def __init__(
        self, 
        message: str,
        plugin_id: str,
        signature_path: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ) -> None:
        super().__init__(message, plugin_id, details)
        self.signature_path = signature_path
        
        if signature_path:
            self.details["signature_path"] = signature_path
