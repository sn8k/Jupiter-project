# Contributing to Jupiter

Thank you for your interest in contributing to Jupiter! This document outlines the standards and workflows for developing on this project.

## Development Setup

1.  **Prerequisites**: Python 3.10+
2.  **Clone the repository**:
    ```bash
    git clone https://github.com/sn8k/jupiter.git
    cd jupiter
    ```
3.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # or
    .venv\Scripts\Activate.ps1 # Windows PowerShell
    ```
4.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    ```

## Workflow

1.  **Create a branch** for your feature or fix.
2.  **Implement your changes**, following the coding standards below.
3.  **Run tests** to ensure no regressions:
    ```bash
    pytest tests/
    ```
4.  **Lint your code**:
    ```bash
    flake8 .
    ```
5.  **Submit a Pull Request**.

## Coding Standards

We follow the guidelines defined in `AGENTS.md`. Key points:

*   **Language**: Python 3.10+ (use type hints everywhere).
*   **Style**: PEP 8.
*   **Naming**:
    *   Functions/Variables: `snake_case`
    *   Classes: `CamelCase`
    *   Constants: `UPPER_SNAKE_CASE`
*   **Docstrings**: Required for all public functions/classes (Google or NumPy style).
*   **Error Handling**: Use custom exceptions (`JupiterError` hierarchy) rather than generic ones.
*   **Logging**: Use the standard `logging` module. No `print()` in core code.

## Project Structure

*   `jupiter/core/`: Business logic (Scanner, Analyzer, Runner).
*   `jupiter/server/`: API (FastAPI) and Meeting integration.
*   `jupiter/cli/`: Command-line interface.
*   `jupiter/web/`: Frontend assets.
*   `jupiter/plugins/`: Built-in plugins.
*   `tests/`: Unit and integration tests.

## Documentation

*   Update `docs/` if you change behavior or add features.
*   Maintain `CHANGELOG.md` and `changelogs/` for significant changes.
