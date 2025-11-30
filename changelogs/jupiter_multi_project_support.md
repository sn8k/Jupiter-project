# Multi-Project Support

## Added
- **Global Configuration**: Introduced `GlobalConfig` to manage application-wide settings and list of projects.
- **Project Management**: Updated `ProjectManager` to handle multiple projects, create new projects, and switch between them.
- **CLI Wizard**: Added an interactive "Add Project" wizard that runs when no projects are configured.
- **Project Definition**: Added `ProjectDefinition` to track project metadata (ID, name, path, config file).

## Changed
- **CLI Entrypoint**: `jupiter` command now checks for configured projects and launches the wizard if none exist.
- **Configuration**: `jupiter.yaml` is now treated as a project-specific configuration, while global settings are stored in `~/.jupiter/global.yaml`.

## Fixed
- Addressed the limitation where the root served logic was not designed for multiple projects.
