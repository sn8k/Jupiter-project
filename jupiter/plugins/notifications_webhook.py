"""
Generic Webhook Notification Plugin for Jupiter.
Sends JSON payloads to a configured URL on specific events.
"""

from typing import Any, Dict, List
import logging
import httpx
import asyncio
from jupiter import __version__

logger = logging.getLogger(__name__)

class Plugin:
    name = "notifications_webhook"
    version = __version__
    description = "Sends notifications to a webhook URL."
    trust_level = "trusted"

    def __init__(self):
        self.config = {}
        self.url = None
        self.events = set()
        self.enabled = True

    def configure(self, config: Dict[str, Any]):
        self.config = config
        self.url = config.get("url")
        # Default to scan_complete if not specified, or empty?
        # Let's default to scan_complete for now if not specified but URL is present
        self.events = set(config.get("events", ["scan_complete"]))
        
        if not self.url:
            logger.warning(f"[{self.name}] No URL configured.")
            # We don't disable self.enabled here because it might be enabled in global config,
            # just that it won't work without URL.


    async def _send_webhook(self, event_type: str, payload: Dict[str, Any]):
        # Map internal event types to webhook events if needed
        # For now, we just pass them through if they match the config
        
        if not self.enabled:
            return
            
        # Simple mapping or check
        # If config events is ["scan_complete"], we map SCAN_FINISHED to it
        should_send = False
        webhook_event = event_type
        
        if event_type == "SCAN_FINISHED" and "scan_complete" in self.events:
            should_send = True
            webhook_event = "scan_complete"
        elif event_type in self.events:
            should_send = True
            
        if not should_send:
            return

        logger.info(f"[{self.name}] Sending webhook for event: {webhook_event}")
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.url,
                    json={
                        "event": webhook_event,
                        "payload": payload,
                        "timestamp": asyncio.get_event_loop().time()
                    },
                    timeout=5.0
                )
        except Exception as e:
            logger.error(f"[{self.name}] Failed to send webhook: {e}")

    def hook_on_scan(self, report: Dict[str, Any]):
        # Legacy hook, kept for compatibility but we prefer the event bus if we had one
        # Since we don't have a global event bus that plugins subscribe to yet (except via hooks),
        # we can keep this.
        # BUT, the requirement is "Adapter le plugin... pour se brancher sur ces événements typés".
        # Since the API now broadcasts events, maybe we should have a way for plugins to listen to them?
        # For now, let's just call _send_webhook from here as a fallback or primary way.
        asyncio.create_task(self._send_webhook("SCAN_FINISHED", {"file_count": len(report.get("files", []))}))

    def on_scan(self, report: Dict[str, Any]):
        """Called after a scan is completed."""
        if "scan_complete" in self.events:
            # We run the async send in the background if possible, 
            # but since this hook might be sync, we use asyncio.create_task if loop is running
            # or just fire and forget logic depending on the runner context.
            # For simplicity in this sync hook context, we might need a helper.
            # However, Jupiter's plugin manager calls hooks synchronously.
            # We'll use a fire-and-forget approach via a new loop if needed or just run_until_complete
            # CAUTION: Running async from sync is tricky. 
            # Ideally, Jupiter's plugin system should support async hooks.
            # Assuming we are in an async context (FastAPI) for some calls, but CLI is sync.
            
            summary = {
                "root": report.get("root"),
                "file_count": len(report.get("files", [])),
                "timestamp": report.get("last_scan_timestamp")
            }
            
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._send_webhook("scan_complete", summary))
            except RuntimeError:
                # No running loop (CLI mode), run sync
                asyncio.run(self._send_webhook("scan_complete", summary))

    def on_analyze(self, summary: Dict[str, Any]):
        """Called after analysis."""
        # Similar logic for analysis events if needed
        pass
