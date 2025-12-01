from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
import time

@dataclass
class JupiterEvent:
    type: str
    payload: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# Event Types
SCAN_STARTED = "SCAN_STARTED"
SCAN_FINISHED = "SCAN_FINISHED"
RUN_STARTED = "RUN_STARTED"
RUN_FINISHED = "RUN_FINISHED"
SNAPSHOT_CREATED = "SNAPSHOT_CREATED"
CONFIG_UPDATED = "CONFIG_UPDATED"
PLUGIN_TOGGLED = "PLUGIN_TOGGLED"
PLUGIN_NOTIFICATION = "PLUGIN_NOTIFICATION"

# Watch / Real-time Event Types
WATCH_STARTED = "WATCH_STARTED"
WATCH_STOPPED = "WATCH_STOPPED"
WATCH_CALLS_RESET = "WATCH_CALLS_RESET"
FUNCTION_CALLS = "FUNCTION_CALLS"
FILE_CHANGE = "FILE_CHANGE"

# Scan Progress Event Types (for real-time tracking)
SCAN_PROGRESS = "SCAN_PROGRESS"           # Emitted during scan with file count / current file
SCAN_FILE_PROCESSING = "SCAN_FILE_PROCESSING"  # Emitted when scanning a specific file
SCAN_FILE_COMPLETED = "SCAN_FILE_COMPLETED"    # Emitted when a file scan completes
FUNCTION_ANALYZED = "FUNCTION_ANALYZED"   # Emitted when a function is analyzed
ANALYSIS_PROGRESS = "ANALYSIS_PROGRESS"   # Emitted during analysis phase

# Simulate Event Types
SIMULATE_STARTED = "SIMULATE_STARTED"
SIMULATE_PROGRESS = "SIMULATE_PROGRESS"
SIMULATE_COMPLETED = "SIMULATE_COMPLETED"

# Log Event Type
LOG_MESSAGE = "LOG_MESSAGE"               # Real-time log messages
