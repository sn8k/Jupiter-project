# Jupiter Architecture

Jupiter is designed as a modular system with a clear separation of concerns.

## Core Modules (`jupiter.core`)

* **Scanner (`scanner.py`)**: Responsible for traversing the filesystem, respecting ignore rules (`.jupiterignore`), and collecting file metadata.
* **Analyzer (`analyzer.py`)**: Consumes scan results to produce aggregated statistics (file counts, sizes, hotspots) and language-specific insights.
* **Runner (`runner.py`)**: Handles execution of shell commands and capturing their output.
* **Tracer (`tracer.py`)**: Provides dynamic analysis capabilities (call graphs, execution timing) using `sys.settrace`.
* **Language Support (`language/`)**: Pluggable modules for analyzing specific languages. Currently supports Python (AST analysis).

## Server (`jupiter.server`)

* **API (`api.py`)**: A FastAPI application exposing the core functionality via REST endpoints.
* **Project Manager (`manager.py`)**: Manages project backends (local or remote) and instantiates the appropriate connectors.
* **Meeting Adapter (`meeting_adapter.py`)**: Manages integration with the Meeting service (licensing, presence).
* **WebSockets (`ws.py`)**: Handles real-time communication with the frontend.

## Connectors (`jupiter.core.connectors`)

* **BaseConnector (`base.py`)**: Abstract interface for project backends.
* **LocalConnector (`local.py`)**: Implementation for local filesystem projects.
* **RemoteConnector (`remote.py`)**: Implementation for remote Jupiter API projects.

## CLI (`jupiter.cli`)

* **Main (`main.py`)**: The entry point for the command-line interface. It parses arguments and invokes the appropriate core or server functions.

## Web UI (`jupiter.web`)

* A lightweight HTML/JS frontend that communicates with the API.
* Supports i18n and theming.
* Located in `jupiter/web/` and served by the API server or a separate dev server.

## Configuration (`jupiter.config`)

* Centralized configuration management using `jupiter.yaml`.
* Handles overrides via CLI arguments.

## Plugins (`jupiter.plugins`)

* An extensible plugin system to add custom analysis or hooks.
* Plugins implement the `Plugin` protocol.
