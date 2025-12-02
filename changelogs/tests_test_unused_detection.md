# Changelog – tests/test_unused_detection.py

Tests unitaires pour la détection améliorée des fonctions inutilisées.

---

## [1.0.0] – 2025-12-02

### Création Initiale

Suite de tests complète pour valider les améliorations de `jupiter/core/language/python.py` v1.1.0.

#### Classes de Tests

**1. `TestFrameworkDecoratorDetection`** (9 tests)
- FastAPI `@router.get`, `@router.post`
- Flask `@app.route`
- Click `@click.command`
- pytest `@pytest.fixture`
- `@abstractmethod`, `@property`, `@staticmethod`, `@classmethod`

**2. `TestKnownPatterns`** (8 tests)
- Dunders : `__init__`, `__str__`, `__enter__`, `__exit__`, `__post_init__`
- Sérialisation : `to_dict`, `from_dict`
- Hooks plugins : `on_scan`, `on_analyze`
- Tests : `setUp`, `tearDown`

**3. `TestDynamicRegistration`** (4 tests)
- `parser.set_defaults(func=handler)`
- `app.add_command(cmd)`
- `button.subscribe(callback)`
- `register(handler=func)`

**4. `TestTrueUnused`** (3 tests)
- Détection des vraies fonctions orphelines
- Distinction appelé vs non-appelé

**5. `TestIsLikelyUsed`** (4 tests)
- Validation de la fonction helper `is_likely_used()`
- Tous les dunders, méthodes de sérialisation, hooks

**6. `TestConstants`** (4 tests)
- `FRAMEWORK_DECORATORS` : 63+ patterns
- `KNOWN_USED_PATTERNS` : 127+ patterns
- `DYNAMIC_REGISTRATION_METHODS` : 8+ méthodes

**7. `TestComplexScenarios`** (3 tests)
- Mix de décorateurs, appels et orphelins
- Fonctions async avec décorateurs
- Décorateurs avec arguments (`@router.get("/items/{id}", response_model=Item)`)

#### Couverture

- **30+ tests** couvrant tous les scénarios d'amélioration
- Tests de non-régression pour les vrais orphelins
- Validation des constantes et helpers

#### Exécution

```bash
pytest tests/test_unused_detection.py -v
```
