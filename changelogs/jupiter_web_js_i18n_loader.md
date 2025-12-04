# Changelog - jupiter/web/js/i18n_loader.js

## v0.1.0
- Initial creation of I18nLoader module
- Dynamic language file loading from lang/*.json
- Automatic language detection (localStorage, URL param, browser)
- Fallback language support
- DOM automatic translation via data-i18n attribute
- String interpolation with {{variable}} syntax
- Plural forms handling (zero, one, two, few, many, other)
- MutationObserver for dynamic content translation
- Date/time/number formatting with Intl API
- Relative time formatting ("2 hours ago")
- RTL language direction detection
- Plugin translation namespace support
- Global shorthand `t()` function
- Translation caching for performance
