# Changelog – debug_server.py
- Debug server now loads `logging.level` from the project config, configures global/Uvicorn loggers accordingly, and reuses the hydrated `ProjectManager` config instance.
- Logging bootstrap now also forwards `logging.path` so debug runs honor the configured log destination.
