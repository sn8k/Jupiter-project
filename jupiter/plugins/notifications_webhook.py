"""Generic Webhook Notification Plugin for Jupiter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from jupiter import __version__
from jupiter.core.events import JupiterEvent, PLUGIN_NOTIFICATION

try:  # pragma: no cover - optional dependency in CLI-only workflows
    from jupiter.server.ws import manager as ws_manager
except Exception:  # pragma: no cover - fallback when server stack not loaded
    ws_manager = None

logger = logging.getLogger(__name__)


class Plugin:
    name = "notifications_webhook"
    version = __version__
    description = "Sends notifications to a webhook URL or falls back to local events."
    trust_level = "trusted"

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.url: str | None = None
        self.events: set[str] = {"scan_complete"}
        self.enabled = True

    def configure(self, config: Dict[str, Any]):
        self.config = config or {}
        self.url = self.config.get("url") or None
        self.events = set(self.config.get("events", ["scan_complete"])) or {"scan_complete"}

        if not self.url:
            logger.info("[%s] No webhook URL configured; notifications will stay local.", self.name)

    def hook_on_scan(self, report: Dict[str, Any]):
        """Compatibility shim for legacy hook naming."""
        self.on_scan(report)

    def on_scan(self, report: Dict[str, Any]):
        """Called after a scan is completed."""
        if "scan_complete" not in self.events:
            return

        file_count = len(report.get("files", []))
        summary: Dict[str, Any] = {
            "root": report.get("root"),
            "file_count": file_count,
            "timestamp": report.get("last_scan_timestamp"),
            "message": f"Scan completed ({file_count} files).",
        }
        if not self.url:
            summary["message"] += " Webhook URL not configured; delivered locally."

        self._schedule_notification("scan_complete", summary)

    def on_analyze(self, summary: Dict[str, Any]):
        """Called after analysis (reserved for future events)."""
        return

    def _schedule_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        if not self.enabled or event_alias not in self.events:
            return

        async def runner() -> None:
            await self._dispatch_notification(event_alias, payload)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(runner())
            return

        loop.create_task(runner())

    async def _dispatch_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        if self.url:
            await self._send_webhook(event_alias, payload)
        else:
            await self._emit_local_notification(event_alias, payload)

    async def _send_webhook(self, event_alias: str, payload: Dict[str, Any]):
        logger.info("[%s] Sending webhook for event: %s", self.name, event_alias)
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.url,
                    json={
                        "event": event_alias,
                        "payload": payload,
                        "timestamp": asyncio.get_running_loop().time(),
                    },
                    timeout=5.0,
                )
        except Exception as exc:
            logger.error("[%s] Failed to send webhook: %s", self.name, exc)

    async def _emit_local_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        message = payload.get("message") or event_alias
        logger.info("[%s] %s", self.name, message)

        if not ws_manager:
            return

        event_payload = {
            "source": self.name,
            "event": event_alias,
            "message": message,
            "details": payload,
        }
        try:
            await ws_manager.broadcast(JupiterEvent(type=PLUGIN_NOTIFICATION, payload=event_payload))
        except Exception as exc:  # pragma: no cover - log-only branch
            logger.warning("[%s] Failed to broadcast local notification: %s", self.name, exc)
