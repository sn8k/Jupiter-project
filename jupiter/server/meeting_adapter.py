"""Meeting integration stubs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MeetingAdapter:
    """Handle communication with the Meeting service.

    This adapter intentionally remains lightweight; it only tracks connection
    intent and exposes minimal state so future implementations can plug real
    network operations without changing callers.
    """

    device_key: str | None
    project_root: Path

    def is_enabled(self) -> bool:
        """Return whether Meeting integration is configured."""

        return bool(self.device_key)

    def last_seen_payload(self) -> dict[str, object]:
        """Return a minimal status payload for Meeting."""

        return {
            "deviceKey": self.device_key,
            "projectRoot": str(self.project_root),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def notify_online(self) -> None:
        """Log an online notification placeholder."""

        if not self.is_enabled():
            logger.debug("Meeting integration disabled; skipping notify_online.")
            return
        logger.info("Would notify Meeting service that device %s is online", self.device_key)
