"""Meeting integration stubs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


from jupiter.core.exceptions import MeetingError

@dataclass
class MeetingAdapter:
    """Handle communication with the Meeting service.

    This adapter intentionally remains lightweight; it only tracks connection
    intent and exposes minimal state so future implementations can plug real
    network operations without changing callers.
    """

    device_key: str | None
    project_root: Path
    _start_time: datetime = field(default_factory=datetime.utcnow)
    _last_heartbeat: datetime | None = None
    _registered: bool = False

    def __post_init__(self) -> None:
        """Initialize the adapter."""
        if self.device_key:
            self.register_device()

    def is_enabled(self) -> bool:
        """Return whether Meeting integration is configured."""
        return bool(self.device_key)

    def register_device(self) -> bool:
        """Simulate device registration."""
        # Mock validation: only this specific key is considered valid
        VALID_KEY = "7F334701F08E904D796A83C6C26ADAF3"

        if self.device_key == VALID_KEY:
            self._registered = True
            self._last_heartbeat = datetime.utcnow()
            logger.info("Device %s registered with Meeting.", self.device_key)
            return True
        
        if self.device_key:
            logger.warning("Invalid device key provided: %s", self.device_key)
        else:
            logger.warning("No device key provided. Running in limited mode.")
            
        self._registered = False
        return False

    def heartbeat(self) -> bool:
        """Send a heartbeat to the Meeting service."""
        if self._registered:
            self._last_heartbeat = datetime.utcnow()
            # In a real implementation, we would send a request here.
            return True
        return False

    def check_license(self) -> dict[str, object]:
        """Check license status and return details."""
        now = datetime.utcnow()
        
        if self._registered:
            return {
                "device_key": self.device_key,
                "is_licensed": True,
                "session_active": True,
                "session_remaining_seconds": None,
                "status": "active",
                "message": "Device registered and licensed.",
            }
        
        # Limited mode logic
        elapsed = (now - self._start_time).total_seconds()
        limit_seconds = 600  # 10 minutes
        remaining = max(0, limit_seconds - elapsed)
        is_expired = remaining <= 0
        
        return {
            "device_key": None,
            "is_licensed": False,
            "session_active": not is_expired,
            "session_remaining_seconds": int(remaining),
            "status": "expired" if is_expired else "limited",
            "message": "Trial expired." if is_expired else "Trial mode (10 min limit).",
        }

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
                code="LICENSE_EXPIRED",
                message=f"Feature '{feature}' is not available. Trial expired.",
                details={"remaining": 0}
            )

    def last_seen_payload(self) -> dict[str, object]:
        """Return a minimal status payload for Meeting."""
        return {
            "deviceKey": self.device_key,
            "projectRoot": str(self.project_root),
            "timestamp": datetime.utcnow().isoformat(),
            "license": self.check_license(),
        }

    def notify_online(self) -> None:
        """Log an online notification placeholder."""
        if not self.is_enabled():
            logger.debug("Meeting integration disabled; skipping notify_online.")
            return
        self.heartbeat()
        logger.info("Would notify Meeting service that device %s is online", self.device_key)
