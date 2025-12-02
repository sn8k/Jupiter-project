# Changelog: Settings Save Fix & PATCH Endpoint

## Version 1.3.3

### Problem
- Settings page Save buttons returned HTTP 422 (Unprocessable Content)
- Code Quality plugin Save button did nothing (no request sent)

### Root Causes

#### 1. POST /config requires full ConfigModel
The `POST /config` endpoint expected a complete `ConfigModel` with all required fields (`server_host`, `server_port`, etc.). The individual save functions only sent partial data.

**Solution**: Added `PATCH /config` endpoint that accepts `PartialConfigModel` (all fields optional) and only updates provided fields.

#### 2. Code Quality JS not executing
The `get_settings_html()` method included `<script>` tags inline. When HTML is inserted via `innerHTML`, browsers don't execute scripts for security reasons.

**Solution**: Separated JavaScript into `get_settings_js()` method. The `loadPluginSettings()` function in `app.js` injects JS via `document.createElement('script')` which does execute.

### Files Changed

#### jupiter/server/models.py
- Added `PartialConfigModel` class with all fields optional

#### jupiter/server/routers/system.py
- Added import for `PartialConfigModel`
- Added `PATCH /config` endpoint with partial update logic

#### jupiter/web/app.js
- Changed `saveNetworkSettings()` from POST to PATCH
- Changed `saveUISettings()` from POST to PATCH  
- Changed `saveSecuritySettings()` from POST to PATCH
- Changed `saveProjectPerformanceSettings()` from POST to PATCH

#### jupiter/plugins/code_quality.py
- Split `get_settings_html()`: removed `<script>` block, kept only HTML and `<style>`
- Added `get_settings_js()` method returning the JavaScript code

### API Changes
- New endpoint: `PATCH /config` - Partial configuration update
- Existing `POST /config` unchanged (full replacement)
