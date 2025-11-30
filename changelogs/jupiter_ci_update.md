# Changelog - CI/CD Integration

## Added
- **CI Command**: New `ci` subcommand in CLI (`jupiter ci`) to run analysis with quality gates.
- **Quality Gates**: New `ci` section in `jupiter.yaml` to define failure thresholds for complexity, duplication, and unused functions.
- **GitHub Actions Workflow**: Added `.github/workflows/jupiter-ci.yml` as a template for CI integration.
- **CLI Overrides**: `ci` command supports flags like `--fail-on-complexity` to override config values.

## Changed
- **Configuration**: Updated `JupiterConfig` to include `CiConfig`.
- **Documentation**: Updated `Manual.md` and `docs/user_guide.md` with CI/CD instructions.
