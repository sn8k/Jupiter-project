# Changelog - jupiter/web/js/i18n_loader.js

## v0.2.0
### Added
- Plugin translation loading and merging
  - `loadPluginTranslations(pluginId, lang)` - Load translations for a single plugin
  - `loadAllPluginTranslations()` - Load translations for all plugins with UI contributions
  - `pt(pluginId, key, params)` - Shorthand for plugin translations
  - `hasPluginTranslations(pluginId)` - Check if plugin has loaded translations
  - `_mergePluginTranslations(pluginId, lang, translations)` - Internal merge helper
- Plugin namespace support (`plugin.<pluginId>.<key>`)
- Cache invalidation for plugin keys when translations are updated

### Changed
- Improved cache management to handle plugin translation updates

## v0.1.0
### Added
- Initial release
- Dynamic language file loading
- Automatic language detection (localStorage, URL parameter, browser language)
- Fallback language support
- DOM automatic translation via data-i18n attribute
- String interpolation with {{variable}} syntax
- Plural forms handling (zero, one, two, few, many, other)
- MutationObserver for dynamic content translation
- Language change event emission
- Translation caching
- Nested key support with dot notation
- Get/set language methods
- List available languages
- Check if translation exists
