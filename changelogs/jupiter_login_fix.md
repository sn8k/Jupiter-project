# Fix Login UI and Config Loading

## Changes

- **CLI**: `handle_server` now passes the loaded `JupiterConfig` to `JupiterAPIServer`, ensuring that the `users` list and other settings are correctly propagated to the API server instance. This fixes the "Invalid credentials" issue where the server might have been using a default or empty configuration.
- **Web UI**: Added specific CSS styles for `#login-modal` to improve its appearance (padding, border radius, backdrop blur, input styling).

## Impact

- Users can now log in successfully with credentials defined in `jupiter.yaml`.
- The login modal is visually consistent with the rest of the application.
