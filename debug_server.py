import uvicorn
from pathlib import Path
from jupiter.server.api import app
from jupiter.server.meeting_adapter import MeetingAdapter
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.history import HistoryManager
from jupiter.server.manager import ProjectManager
from jupiter.config import load_config
from jupiter.core.logging_utils import configure_logging

def start():
    root = Path("C:/Dev_VSCode/Jupiter-project")
    config = load_config(root)
    active_level = configure_logging(
        config.logging.level,
        log_file=config.logging.path,
        reset_on_start=config.logging.reset_on_start,
    )
    app.state.root_path = root
    app.state.install_path = root
    app.state.meeting_adapter = MeetingAdapter(device_key=None, project_root=root)
    app.state.history_manager = HistoryManager(root)
    app.state.project_manager = ProjectManager(config)
    app.state.plugin_manager = PluginManager()
    
    print("Starting uvicorn...")
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level=active_level.lower())
    server = uvicorn.Server(config)
    import asyncio
    asyncio.run(server.serve())

if __name__ == "__main__":
    start()
