# Changelog – jupiter/core/logging_utils.py
- Added centralized logging utilities to normalize user-provided levels (Debug/Info/Warning/Error/Critic) and configure root/Uvicorn loggers consistently.
- Added optional log file support to `configure_logging`, creating a file handler when a path is provided and preventing duplicate handlers for the same target.
