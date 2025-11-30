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
