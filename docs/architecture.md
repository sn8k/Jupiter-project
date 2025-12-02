# Jupiter Architecture

Jupiter is designed as a modular system with a clear separation of concerns.

## Core Modules (`jupiter.core`)

* **Scanner (`scanner.py`)**: Responsible for traversing the filesystem, respecting ignore rules (`.jupiterignore`), and collecting file metadata (Python and JS/TS).
* **Analyzer (`analyzer.py`)**: Consumes scan results to produce aggregated statistics (file counts, sizes, hotspots) and language-specific insights.
* **Runner (`runner.py`)**: Handles execution of shell commands and capturing their output.
* **Tracer (`tracer.py`)**: Provides dynamic analysis capabilities (call graphs, execution timing) using `sys.settrace`.
* **Language Support (`language/`)**: Pluggable modules for analyzing specific languages (Python AST, JS/TS heuristics).
* **History (`history.py`)**: Manages snapshot storage and diffing.
* **Graph (`graph.py`)**: Builds the dependency graph consumed by the Live Map.
* **Simulator (`simulator.py`)**: Computes impact when virtually removing files or functions.

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
* Supports i18n (internationalization) with dynamic language discovery and theming.
  - Language files are located in `jupiter/web/lang/*.json`.
  - Each file includes a `_meta` block with `lang_code`, `lang_name`, and `version` (current: v1.0.1).
  - At startup, the UI scans known language files and populates the selector dynamically.
  - Built-in translations: French (`fr`), English (`en`), plus fun packs (Klingon, Sindarin/Elvish, Pirate French).
* **Settings Page**: Each configuration section (Network, Interface, Security, Meeting) has its own Save button for granular control.
* **Projects Page**: Performance settings (parallel scan, workers, timeout, graph options) are now located here as they are project-specific.
* Located in `jupiter/web/` and served by the API server or a separate dev server.

## Configuration (`jupiter.config`)

* Centralized configuration management using `<project>.jupiter.yaml`.
* Handles overrides via CLI arguments.

## Plugins (`jupiter.plugins`)

* An extensible plugin system to add custom analysis or hooks.
* Plugins implement the `Plugin` protocol.

## Security

* **Run Restrictions**: The `run` command can be restricted via `<project>.jupiter.yaml` (`security.allow_run`, `security.allowed_commands`).
* **Plugin Policy**: Plugins have a `trust_level` (experimental vs trusted).
* **Remote Projects**: Remote connectors use secure timeouts and masked error logging.
