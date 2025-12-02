"""Meeting integration and license verification.

This module provides the MeetingAdapter class for verifying Jupiter licenses
against the Meeting backend API. It checks device authorization, device type,
and token availability to determine license validity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

from jupiter.core.exceptions import MeetingError


class MeetingLicenseStatus(str, Enum):
    """Status of a Meeting license check."""
    
    VALID = "valid"
    INVALID = "invalid"
    NETWORK_ERROR = "network_error"
    CONFIG_ERROR = "config_error"


@dataclass
class MeetingLicenseCheckResult:
    """Result of a Meeting license verification.
    
    Attributes:
        status: The overall license status (valid, invalid, network_error, config_error).
        message: Human-readable message explaining the status.
        device_key: The device key that was checked (if any).
        http_status: The HTTP status code from the Meeting API (if applicable).
        authorized: Whether the device is authorized in Meeting.
        device_type: The device type reported by Meeting.
        token_count: The number of tokens remaining for this device.
        checked_at: Timestamp when the check was performed.
        meeting_base_url: The Meeting API base URL that was used.
        device_type_expected: The expected device type for Jupiter.
    """
    
    status: MeetingLicenseStatus
    message: str
    device_key: Optional[str] = None
    http_status: Optional[int] = None
    authorized: Optional[bool] = None
    device_type: Optional[str] = None
    token_count: Optional[int] = None
    checked_at: Optional[str] = None
    meeting_base_url: Optional[str] = None
    device_type_expected: Optional[str] = None
    
    def to_dict(self) -> dict[str, object]:
        """Convert the result to a dictionary for JSON serialization."""
        return {
            "status": self.status.value,
            "message": self.message,
            "device_key": self.device_key,
            "http_status": self.http_status,
            "authorized": self.authorized,
            "device_type": self.device_type,
            "token_count": self.token_count,
            "checked_at": self.checked_at,
            "meeting_base_url": self.meeting_base_url,
            "device_type_expected": self.device_type_expected,
        }


@dataclass
class MeetingAdapter:
    """Handle communication with the Meeting service.

    This adapter verifies Jupiter licenses against the Meeting backend API.
    It checks that the device is:
    - Authorized (authorized == true)
    - Of the correct type (device_type == "Jupiter")
    - Has tokens remaining (token_count > 0)

    If Meeting is unavailable or no device_key is configured, Jupiter runs
    in a restricted/trial mode with a time limit.
    
    Attributes:
        device_key: The Jupiter device key to verify.
        project_root: The root path of the current project.
        base_url: The Meeting API base URL.
        device_type_expected: The expected device type (default: "Jupiter").
        timeout_seconds: HTTP request timeout.
        auth_token: Optional authentication token for Meeting API.
    """

    device_key: str | None
    project_root: Path
    base_url: str = "https://meeting.ygsoft.fr/api"
    device_type_expected: str = "Jupiter"
    timeout_seconds: float = 5.0
    auth_token: Optional[str] = None
    _start_time: datetime = field(default_factory=datetime.utcnow)
    _last_heartbeat: datetime | None = None
    _license_result: MeetingLicenseCheckResult | None = None
    _license_checked_at: datetime | None = None

    def __post_init__(self) -> None:
        """Initialize the adapter and perform initial license check."""
        if self.device_key:
            self._license_result = self.check_jupiter_devicekey(self.device_key)
            self._license_checked_at = datetime.utcnow()
            if self._license_result.status == MeetingLicenseStatus.VALID:
                # Send initial heartbeat to signal Jupiter is online
                self._send_heartbeat()
                logger.info("Device %s verified with Meeting: license VALID.", self.device_key)
            else:
                logger.warning(
                    "Device %s license check: %s - %s",
                    self.device_key,
                    self._license_result.status.value,
                    self._license_result.message,
                )
        else:
            logger.warning("No Meeting device_key configured for Jupiter; running in restricted/demo mode.")
            self._license_result = MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.CONFIG_ERROR,
                message="No device_key configured for Meeting license verification.",
                checked_at=datetime.utcnow().isoformat(),
            )

    def is_enabled(self) -> bool:
        """Return whether Meeting integration is configured."""
        return bool(self.device_key)

    def is_licensed(self) -> bool:
        """Return whether the current license is valid."""
        return (
            self._license_result is not None
            and self._license_result.status == MeetingLicenseStatus.VALID
        )

    def check_jupiter_devicekey(self, device_key: str) -> MeetingLicenseCheckResult:
        """Verify the validity of a Jupiter devicekey via the Meeting API.

        Business rule for a valid license:
        - HTTP 200 from GET {base_url}/devices/{device_key}
        - JSON["authorized"] == True
        - JSON["device_type"] == self.device_type_expected (default: "Jupiter")
        - JSON["token_count"] > 0

        Args:
            device_key: The device key to verify.

        Returns:
            MeetingLicenseCheckResult with status, message, and detailed fields.
        """
        url = f"{self.base_url.rstrip('/')}/devices/{device_key}"
        checked_at = datetime.utcnow().isoformat()
        
        headers = {"Accept": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
        except requests.exceptions.RequestException as e:
            logger.warning("Network error while checking Meeting license: %s", e)
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.NETWORK_ERROR,
                message=f"Network error contacting Meeting API: {e}",
                device_key=device_key,
                checked_at=checked_at,
                meeting_base_url=self.base_url,
                device_type_expected=self.device_type_expected,
            )

        http_status = response.status_code

        if http_status == 404:
            logger.warning("Device %s not found in Meeting (HTTP 404).", device_key)
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.INVALID,
                message="Device not found in Meeting (HTTP 404).",
                device_key=device_key,
                http_status=http_status,
                checked_at=checked_at,
                meeting_base_url=self.base_url,
                device_type_expected=self.device_type_expected,
            )

        if http_status != 200:
            logger.warning("Meeting API returned HTTP %d for device %s.", http_status, device_key)
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.INVALID,
                message=f"Meeting API error (HTTP {http_status}).",
                device_key=device_key,
                http_status=http_status,
                checked_at=checked_at,
                meeting_base_url=self.base_url,
                device_type_expected=self.device_type_expected,
            )

        # Parse JSON response
        try:
            data = response.json()
        except ValueError as e:
            logger.error("Invalid JSON response from Meeting API: %s", e)
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.INVALID,
                message=f"Invalid JSON response from Meeting API: {e}",
                device_key=device_key,
                http_status=http_status,
                checked_at=checked_at,
                meeting_base_url=self.base_url,
                device_type_expected=self.device_type_expected,
            )

        # Extract fields
        authorized = bool(data.get("authorized"))
        device_type = str(data.get("device_type") or "")
        token_count_raw = data.get("token_count")
        
        # Safe cast for token_count
        try:
            token_count = int(token_count_raw) if token_count_raw is not None else 0
        except (ValueError, TypeError):
            token_count = 0

        # Apply business rules
        reasons = []
        if not authorized:
            reasons.append("device not authorized")
        if device_type != self.device_type_expected:
            reasons.append(f"device_type is '{device_type}', expected '{self.device_type_expected}'")
        if token_count <= 0:
            reasons.append(f"token_count is {token_count} (must be > 0)")

        if reasons:
            message = "License invalid: " + "; ".join(reasons) + "."
            logger.warning("Device %s license invalid: %s", device_key, message)
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.INVALID,
                message=message,
                device_key=device_key,
                http_status=http_status,
                authorized=authorized,
                device_type=device_type,
                token_count=token_count,
                checked_at=checked_at,
                meeting_base_url=self.base_url,
                device_type_expected=self.device_type_expected,
            )

        # All conditions met
        logger.info("Device %s license valid: authorized, device_type=%s, tokens=%d.", device_key, device_type, token_count)
        return MeetingLicenseCheckResult(
            status=MeetingLicenseStatus.VALID,
            message="License valid: authorized, correct device_type, tokens > 0.",
            device_key=device_key,
            http_status=http_status,
            authorized=authorized,
            device_type=device_type,
            token_count=token_count,
            checked_at=checked_at,
            meeting_base_url=self.base_url,
            device_type_expected=self.device_type_expected,
        )

    def refresh_license(self) -> MeetingLicenseCheckResult:
        """Re-check the license and update internal state.
        
        Returns:
            The updated MeetingLicenseCheckResult.
        """
        if not self.device_key:
            self._license_result = MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.CONFIG_ERROR,
                message="No device_key configured for Meeting license verification.",
                checked_at=datetime.utcnow().isoformat(),
            )
        else:
            self._license_result = self.check_jupiter_devicekey(self.device_key)
        self._license_checked_at = datetime.utcnow()
        
        # Send heartbeat after successful license check
        if self._license_result.status == MeetingLicenseStatus.VALID:
            self._send_heartbeat()
        
        return self._license_result

    def _send_heartbeat(self) -> bool:
        """Send a heartbeat to the Meeting service to signal device presence.
        
        Sends a POST request to /api/devices/{device_key}/online.
        
        Returns:
            True if heartbeat was sent successfully, False otherwise.
        """
        if not self.device_key:
            return False
        
        url = f"{self.base_url.rstrip('/')}/devices/{self.device_key}/online"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            response = requests.post(url, headers=headers, timeout=self.timeout_seconds, json={})
            if response.status_code in (200, 201, 204):
                self._last_heartbeat = datetime.utcnow()
                logger.debug("Heartbeat sent successfully for device %s.", self.device_key)
                return True
            else:
                logger.warning("Heartbeat failed for device %s: HTTP %d", self.device_key, response.status_code)
                return False
        except requests.exceptions.RequestException as e:
            logger.warning("Network error sending heartbeat for device %s: %s", self.device_key, e)
            return False

    def heartbeat(self) -> bool:
        """Send a heartbeat to the Meeting service.
        
        Returns:
            True if heartbeat was sent successfully, False otherwise.
        """
        if not self.is_enabled():
            return False
        return self._send_heartbeat()

    def check_license(self) -> dict[str, object]:
        """Check license status and return details (legacy interface).
        
        This method maintains backward compatibility with existing code
        while using the new license verification under the hood.
        """
        now = datetime.utcnow()
        
        if self.is_licensed():
            return {
                "device_key": self.device_key,
                "is_licensed": True,
                "session_active": True,
                "session_remaining_seconds": None,
                "status": "active",
                "message": "Device registered and licensed.",
            }
        
        # Limited mode logic: grace period of 10 minutes
        elapsed = (now - self._start_time).total_seconds()
        limit_seconds = 600  # 10 minutes
        remaining = max(0, limit_seconds - elapsed)
        is_expired = remaining <= 0
        
        return {
            "device_key": self.device_key,
            "is_licensed": False,
            "session_active": not is_expired,
            "session_remaining_seconds": int(remaining),
            "status": "expired" if is_expired else "limited",
            "message": "Trial expired." if is_expired else "Trial mode (10 min limit).",
        }

    def get_license_status(self) -> MeetingLicenseCheckResult:
        """Get the current license verification result.
        
        Returns:
            The current MeetingLicenseCheckResult, or a CONFIG_ERROR if never checked.
        """
        if self._license_result is None:
            return MeetingLicenseCheckResult(
                status=MeetingLicenseStatus.CONFIG_ERROR,
                message="License has not been checked yet.",
                checked_at=datetime.utcnow().isoformat(),
            )
        return self._license_result

    def validate_feature_access(self, feature: str) -> None:
        """Raise MeetingError if the feature is restricted and license is invalid."""
        status = self.check_license()
        
        # If licensed, everything is allowed
        if status["is_licensed"]:
            return

        # If limited mode and session active, everything is allowed
        if status["session_active"]:
            return

        # If expired, block specific features
        restricted_features = {"run", "watch", "dynamic_scan"}
        if feature in restricted_features:
            raise MeetingError(
                message=f"Feature '{feature}' is not available. Trial expired.",
                details={"remaining": 0, "code": "LICENSE_EXPIRED"}
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Meeting Protocol API Methods
    # These methods are part of the Meeting integration protocol and may be
    # called when Meeting service is available. Static analysis may incorrectly
    # flag them as unused when Meeting integration is not active.
    # ─────────────────────────────────────────────────────────────────────────

    def last_seen_payload(self) -> dict[str, object]:
        """Return a minimal status payload for Meeting.
        
        This method provides a snapshot of the current Jupiter state that can be
        sent to the Meeting service for monitoring and device tracking purposes.
        """
        return {
            "deviceKey": self.device_key,
            "projectRoot": str(self.project_root),
            "timestamp": datetime.utcnow().isoformat(),
            "license": self.check_license(),
        }

    def notify_online(self) -> bool:
        """Notify Meeting service that Jupiter device is online.
        
        This method is called when Jupiter starts up or when a license check
        succeeds, to inform the Meeting service of device presence. It can also
        be called periodically as a heartbeat.
        
        Returns:
            True if notification was sent successfully, False otherwise.
        """
        if not self.is_enabled():
            logger.debug("Meeting integration disabled; skipping notify_online.")
            return False
        success = self._send_heartbeat()
        if success:
            logger.info("Notified Meeting service that device %s is online.", self.device_key)
        return success
