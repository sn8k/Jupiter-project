# Changelog – Settings Page UX Improvements

## [1.2.1] – 2025-12-02

### Changed

#### Meeting License Section
- Removed the "Dernière réponse Meeting" status box (duplicate of License Details grid)
- Replaced the "Refresh" button with a "💾 Save" button for saving Meeting settings
- Removed alert popups when checking license – status now shown in License Details grid only
- Added `saveMeetingSettings()` function to save Device Key, Auth Token, and Heartbeat Interval
- License check is automatically triggered after saving settings

#### Interface Section
- Moved "Allow Run Command" checkbox from Security section into Interface section
- Added explanatory hint text for the setting
- Removed empty Security section entirely

#### User Management Section
- Added Token column to user table (displays masked •••••••• for security)
- Added inline edit mode for existing users:
  - ✏️ Edit button to enter edit mode
  - 💾 Save button to confirm changes
  - ❌ Cancel button to discard changes
  - 🗑️ Delete button (existing)
- Users can now modify: name, token (optional), role
- Section now spans full width for better usability
- Added `PUT /users/{name}` API endpoint for user updates

### Technical Details

#### Files Modified
- `jupiter/web/index.html` – Restructured Settings sections
- `jupiter/web/app.js` – Added `saveMeetingSettings()`, improved `renderUsers()` with edit mode
- `jupiter/web/styles.css` – Added `.users-table`, `.settings-section-wide` styles
- `jupiter/web/lang/en.json` – Added 20+ new translation keys
- `jupiter/web/lang/fr.json` – Added French equivalents
- `jupiter/server/routers/auth.py` – Added `PUT /users/{name}` endpoint

#### New API Endpoints
- `PUT /users/{name}` – Update user name, token, and/or role (admin only)

#### New Translation Keys
- `meeting_save_btn`, `meeting_settings_saved`, `meeting_save_failed`, `meeting_save_error`
- `settings_allow_run`, `settings_allow_run_hint`
- `settings_users_token`
- `user_name_required`, `user_name_token_required`
- `user_update_failed`, `user_update_error`
- `user_add_failed`, `user_add_error`
- `user_delete_confirm`, `user_delete_failed`, `user_delete_error`

### Motivation
Improved Settings page UX by:
1. Removing redundant UI elements (duplicate license status display)
2. Consolidating related settings (Allow Run moved to Interface)
3. Enabling full CRUD operations on users without page reload
4. Better visual feedback via logs instead of disruptive alert popups
