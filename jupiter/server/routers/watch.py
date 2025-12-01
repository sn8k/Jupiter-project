"""Watch router for real-time file monitoring and function call tracking."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field

from jupiter.server.routers.auth import verify_token, require_admin
from jupiter.server.ws import manager as ws_manager
from jupiter.core.events import JupiterEvent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watch"])


class WatchStartRequest(BaseModel):
    """Request to start watching."""
    track_calls: bool = Field(default=True, description="Track function calls during run commands.")
    track_files: bool = Field(default=True, description="Track file modifications.")


class WatchStatusResponse(BaseModel):
    """Response for watch status."""
    active: bool
    started_at: Optional[str] = None
    track_calls: bool = False
    track_files: bool = False
    call_counts: Dict[str, int] = Field(default_factory=dict)
    total_events: int = 0


class FunctionCallEvent(BaseModel):
    """A function call event."""
    function: str
    file: str
    count: int
    timestamp: str


@dataclass
class WatchState:
    """Global watch state."""
    active: bool = False
    started_at: Optional[datetime] = None
    track_calls: bool = True
    track_files: bool = True
    call_counts: Dict[str, int] = field(default_factory=dict)
    total_events: int = 0
    _file_watcher_task: Optional[asyncio.Task] = None


# Global watch state
_watch_state = WatchState()


def get_watch_state() -> WatchState:
    """Get the global watch state."""
    return _watch_state


def _build_status_response(active: Optional[bool] = None, 
                           call_counts: Optional[Dict[str, int]] = None,
                           total_events: Optional[int] = None) -> WatchStatusResponse:
    """Build a WatchStatusResponse from current state with optional overrides.
    
    Args:
        active: Override active state (uses _watch_state.active if None)
        call_counts: Override call_counts (uses _watch_state.call_counts if None)
        total_events: Override total_events (uses _watch_state.total_events if None)
    
    Returns:
        WatchStatusResponse with current or overridden values.
    """
    return WatchStatusResponse(
        active=active if active is not None else _watch_state.active,
        started_at=_watch_state.started_at.isoformat() if _watch_state.started_at else None,
        track_calls=_watch_state.track_calls,
        track_files=_watch_state.track_files,
        call_counts=call_counts if call_counts is not None else dict(_watch_state.call_counts),
        total_events=total_events if total_events is not None else _watch_state.total_events
    )


@router.post("/watch/start")
async def start_watch(
    request: Request,
    body: WatchStartRequest,
    role: str = Depends(verify_token)
) -> WatchStatusResponse:
    """Start watching for file changes and function calls.
    
    When watch is active:
    - File modifications in the project are tracked
    - Function calls from `run` commands with dynamic=true are counted
    - Events are broadcast via WebSocket
    """
    global _watch_state
    
    if _watch_state.active:
        return _build_status_response()
    
    _watch_state.active = True
    _watch_state.started_at = datetime.utcnow()
    _watch_state.track_calls = body.track_calls
    _watch_state.track_files = body.track_files
    _watch_state.call_counts = {}
    _watch_state.total_events = 0
    
    # Broadcast watch started event
    await ws_manager.broadcast(JupiterEvent(
        type="WATCH_STARTED",
        payload={
            "track_calls": body.track_calls,
            "track_files": body.track_files,
            "started_at": _watch_state.started_at.isoformat()
        }
    ))
    
    logger.info("Watch started: track_calls=%s, track_files=%s", body.track_calls, body.track_files)
    
    return _build_status_response()


@router.post("/watch/stop")
async def stop_watch(
    request: Request,
    role: str = Depends(verify_token)
) -> WatchStatusResponse:
    """Stop watching and return final statistics."""
    global _watch_state
    
    if not _watch_state.active:
        return WatchStatusResponse(active=False)
    
    # Capture final state
    final_counts = dict(_watch_state.call_counts)
    final_events = _watch_state.total_events
    
    # Reset state
    _watch_state.active = False
    _watch_state.started_at = None
    _watch_state.call_counts = {}
    _watch_state.total_events = 0
    
    # Broadcast watch stopped event
    await ws_manager.broadcast(JupiterEvent(
        type="WATCH_STOPPED",
        payload={
            "final_call_counts": final_counts,
            "total_events": final_events
        }
    ))
    
    logger.info("Watch stopped. Total events: %d", final_events)
    
    return _build_status_response(active=False, call_counts=final_counts, total_events=final_events)


@router.get("/watch/status")
async def get_watch_status(request: Request) -> WatchStatusResponse:
    """Get current watch status."""
    return _build_status_response()


@router.get("/watch/calls")
async def get_call_counts(request: Request) -> Dict[str, int]:
    """Get current function call counts."""
    return dict(_watch_state.call_counts)


@router.post("/watch/calls/reset")
async def reset_call_counts(
    request: Request,
    role: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Reset function call counts."""
    _watch_state.call_counts = {}
    _watch_state.total_events = 0
    
    await ws_manager.broadcast(JupiterEvent(
        type="WATCH_CALLS_RESET",
        payload={}
    ))
    
    return {"success": True, "message": "Call counts reset."}


async def record_function_calls(calls: Dict[str, int]) -> None:
    """Record function calls from a dynamic analysis run.
    
    This is called by the run endpoint when dynamic analysis is enabled.
    Updates the global watch state and broadcasts events via WebSocket.
    
    Args:
        calls: Dictionary mapping function keys (file::function) to call counts.
    """
    if not _watch_state.active or not _watch_state.track_calls:
        return
    
    for func_key, count in calls.items():
        # Update cumulative count
        _watch_state.call_counts[func_key] = _watch_state.call_counts.get(func_key, 0) + count
        _watch_state.total_events += count
    
    # Broadcast the new calls
    await ws_manager.broadcast(JupiterEvent(
        type="FUNCTION_CALLS",
        payload={
            "calls": calls,
            "cumulative": dict(_watch_state.call_counts),
            "timestamp": datetime.utcnow().isoformat()
        }
    ))
    
    logger.debug("Recorded %d function call entries, total events: %d", len(calls), _watch_state.total_events)


async def broadcast_file_change(file_path: str, change_type: str) -> None:
    """Broadcast a file change event.
    
    Args:
        file_path: Path to the changed file.
        change_type: Type of change (created, modified, deleted).
    """
    if not _watch_state.active or not _watch_state.track_files:
        return
    
    _watch_state.total_events += 1
    
    await ws_manager.broadcast(JupiterEvent(
        type="FILE_CHANGE",
        payload={
            "path": file_path,
            "change_type": change_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    ))


async def broadcast_scan_progress(event_type: str, payload: Dict[str, Any]) -> None:
    """Broadcast a scan progress event.
    
    This is called by the scan endpoint during the scanning process
    to provide real-time feedback.
    
    Args:
        event_type: Type of progress event (SCAN_PROGRESS, SCAN_FILE_COMPLETED, etc.)
        payload: Event-specific data.
    """
    if not _watch_state.active:
        return
    
    _watch_state.total_events += 1
    
    await ws_manager.broadcast(JupiterEvent(
        type=event_type,
        payload={
            **payload,
            "timestamp": datetime.utcnow().isoformat()
        }
    ))


async def broadcast_log_message(level: str, message: str, source: str = "jupiter") -> None:
    """Broadcast a log message in real-time.
    
    Args:
        level: Log level (info, warning, error, debug).
        message: The log message.
        source: Source module/component.
    """
    if not _watch_state.active:
        return
    
    await ws_manager.broadcast(JupiterEvent(
        type="LOG_MESSAGE",
        payload={
            "level": level,
            "message": message,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        }
    ))


# Global reference to the main event loop for cross-thread communication
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def set_main_loop(loop: Optional[asyncio.AbstractEventLoop]) -> None:
    """Set the main event loop reference for cross-thread callbacks."""
    global _main_loop
    _main_loop = loop


def create_scan_progress_callback():
    """Create a callback function for use with ProjectScanner.
    
    Returns:
        A synchronous callback that queues async broadcasts using thread-safe mechanism.
    """
    if not _watch_state.active:
        return None
    
    def callback(event_type: str, payload: Dict[str, Any]) -> None:
        """Synchronous callback that schedules async broadcast from any thread."""
        global _main_loop
        
        # Update watch state counters (thread-safe simple operations)
        _watch_state.total_events += 1
        
        if not _main_loop:
            return
            
        try:
            # Schedule the coroutine to run on the main event loop from this thread
            future = asyncio.run_coroutine_threadsafe(
                broadcast_scan_progress(event_type, payload),
                _main_loop
            )
            # Don't wait for result - fire and forget
        except Exception as e:
            logger.debug("Failed to schedule broadcast: %s", e)
    
    return callback
