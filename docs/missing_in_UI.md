# Écarts CLI vs WebUI – Jupiter

Ce document liste les fonctionnalités disponibles en **CLI** qui ne sont **pas encore exposées** (ou partiellement) dans la **WebUI**.

> **Priorité** : La WebUI est l'interface prioritaire. Ce document sert à identifier les fonctionnalités CLI à intégrer dans l'UI.

**IMPERATIF : 
    - Mettre a jour la documentation complete dans le dossier docs 
    - mettre a jour les numeros de versions des fichiers ainsi que dans le fichier VERSION
    - mettre a jour le changelog de chaque fichier, le creer si manquant.
    - mettre a jour readme.md si besoin
    - cocher chaque action effectivement terminée. Ceci constitue la seule modification autorisée de ce document !**
---

## Légende

| Statut | Signification |
|--------|---------------|
| ❌ Absent | Fonctionnalité CLI non disponible dans la WebUI |
| ⚠️ Partiel | Fonctionnalité présente mais incomplète |
| ✅ OK | Fonctionnalité alignée CLI ↔ WebUI |

---

## 1. Commandes principales

| Commande CLI | WebUI | Statut | Notes |
|--------------|-------|--------|-------|
| `jupiter scan` | `/scan` + bouton Scan | ✅ OK | Options avancées via modal (v1.2.0: no-cache, snapshot label) |
| `jupiter analyze` | `/analyze` + vue Dashboard | ✅ OK | |
| `jupiter server` | N/A (lance le serveur) | ✅ OK | La WebUI tourne sur le serveur |
| `jupiter gui` | N/A (lance l'UI) | ✅ OK | Point d'entrée principal |
| `jupiter run "<cmd>"` | Modal "Run Command" | ✅ OK | Avec option `--with-dynamic` |
| `jupiter watch` | Bouton Watch + panneau temps réel | ✅ OK | |
| `jupiter update <source>` | Plugin `settings_update` | ✅ OK | Via Settings |
| `jupiter ci` | Vue CI / Quality Gates | ✅ OK | **Implémenté v1.2.0** |
| `jupiter snapshots list` | Vue History | ✅ OK | |
| `jupiter snapshots show <id>` | Vue History + panneau détail | ✅ OK | **Implémenté v1.2.0** |
| `jupiter snapshots diff <a> <b>` | Vue History + Diff | ✅ OK | |
| `jupiter simulate remove <target>` | Modal Simulate | ✅ OK | |
| `jupiter meeting check-license` | Settings > License Details | ✅ OK | **Implémenté v1.2.0** |

---

## 2. Détails des écarts

### 2.1 `jupiter ci` – Mode CI/CD ✅ Implémenté (v1.2.0)

**CLI :**
```bash
jupiter ci --json
jupiter ci --fail-on-complexity 15
jupiter ci --fail-on-duplication 5
jupiter ci --fail-on-unused 10
```

**Fonctionnalités :**
- Analyse complète avec quality gates
- Seuils configurables (complexité max, clusters de duplication, fonctions inutilisées)
- Code de retour non-zéro si seuils dépassés
- Sortie JSON pour intégration CI/CD

**WebUI actuelle :**
- ~~Aucun équivalent~~
- ~~Les métriques de qualité sont affichées mais sans "gates" ni validation pass/fail~~

**Intégration suggérée :**
- [x] Ajouter une vue "CI / Quality Gates" dans le menu
- [x] Afficher les seuils configurés (`ci.fail_on` du config)
- [x] Bouton "Run CI Check" qui retourne pass/fail
- [x] Historique des runs CI avec statut
- [x] Badge visuel pass/fail sur le dashboard

---

### 2.2 Options de scan avancées ✅ Implémenté (v1.2.0)

**CLI :**
```bash
jupiter scan --no-cache
jupiter scan --perf
jupiter scan --output report.json
jupiter scan --no-snapshot
jupiter scan --snapshot-label "v1.0"
```

**WebUI actuelle :**
- Modal de scan avec `show_hidden`, `incremental`, `ignore_globs`
- ~~Pas d'option `--no-cache` exposée~~
- Pas d'option `--perf` (profiling) – *déprioritisé, mode dev*
- ~~Pas d'export direct du rapport vers fichier~~
- ~~Pas de contrôle sur la création de snapshot~~

**Intégration suggérée :**
- [x] Ajouter checkbox "Skip cache" dans le modal scan
- [ ] Ajouter checkbox "Enable profiling" (mode dev/debug) – *déprioritisé*
- [x] Bouton "Export JSON" après scan (via Export Report existant)
- [x] Option "Don't create snapshot" / "Custom snapshot label"

---

### 2.3 Options d'analyse avancées ⚠️ Partiel

**CLI :**
```bash
jupiter analyze --top 10
jupiter analyze --perf
jupiter analyze --no-cache
```

**WebUI actuelle :**
- L'analyse est lancée automatiquement ou via refresh
- Le paramètre `top` n'est pas configurable dans l'UI
- Pas d'option profiling

**Intégration suggérée :**
- [ ] Ajouter un sélecteur "Top N files" dans les settings ou le dashboard
- [ ] Option profiling pour debug

---

### 2.4 `jupiter meeting check-license` – Vue détaillée ✅ Implémenté (v1.2.0)

**CLI :**
```bash
jupiter meeting check-license --json
```

**Retourne :**
- `device_key`
- `is_licensed`
- `http_status`
- `authorized`
- `device_type`
- `token_count`
- `checked_at`
- `meeting_base_url`

**WebUI actuelle :**
- Indicateur licence dans le footer (vert/rouge)
- ~~Quelques infos dans Settings > Meeting~~
- ~~Pas de vue complète avec tous les détails de vérification~~

**Intégration suggérée :**
- [x] Ajouter une section "License Details" dans Settings
- [x] Afficher toutes les infos de `/license/status`
- [x] Bouton "Refresh License" (déjà présent via API)
- [ ] Historique des vérifications de licence – *déprioritisé*

---

### 2.5 `jupiter snapshots show <id>` – Rapport complet ✅ Implémenté (v1.2.0)

**CLI :**
```bash
jupiter snapshots show <id> --report --json
```

**WebUI actuelle :**
- Liste des snapshots avec métadonnées
- Diff entre snapshots
- ~~Pas de visualisation du rapport complet d'un snapshot~~

**Intégration suggérée :**
- [x] Clic sur un snapshot → afficher le rapport complet
- [x] Option "View Full Report" dans le panneau History
- [x] Export JSON d'un snapshot spécifique

---

## 3. Paramètres CLI globaux non exposés

| Paramètre CLI | WebUI | Statut |
|---------------|-------|--------|
| `--root <path>` | Changement de projet via Projects | ✅ OK |
| `--version` | Affiché dans footer/header | ✅ OK |
| `--force` (update) | Option dans plugin settings_update | ✅ OK |

---

## 4. Récapitulatif des actions

### Priorité Haute ✅ Terminé
1. **Vue CI/Quality Gates** – ~~Manque critique pour les workflows d'équipe~~ ✅ Implémenté v1.2.0
2. **Export JSON des rapports** – ~~Utile pour intégrations externes~~ ✅ Déjà disponible

### Priorité Moyenne ✅ Terminé
3. Options de scan avancées (no-cache, ~~perf~~, snapshot control) ✅ Implémenté v1.2.0
4. Vue détaillée licence Meeting ✅ Implémenté v1.2.0
5. Vue rapport complet pour snapshots ✅ Implémenté v1.2.0

### Priorité Basse
6. Paramètre "top N" configurable pour analyze – *à évaluer*
7. Mode profiling dans l'UI (plutôt pour dev) – *déprioritisé*

---

## 5. API disponibles mais non utilisées par l'UI

Ces endpoints existent côté serveur mais ne sont pas (ou peu) exploités par `app.js` :

| Endpoint | Utilisé ? | Notes |
|----------|-----------|-------|
| `GET /analyze` | ✅ Oui | Dashboard |
| `POST /scan` | ✅ Oui | Bouton Scan |
| `POST /ci` | ✅ Oui | Vue CI (v1.2.0) |
| `GET /snapshots` | ✅ Oui | History |
| `GET /snapshots/{id}` | ✅ Oui | Vue détail snapshot (v1.2.0) |
| `GET /license/status` | ✅ Oui | License Details (v1.2.0) |
| `POST /license/refresh` | ✅ Oui | Settings |
| `GET /meeting/status` | ✅ Oui | License Details (v1.2.0) |
| `GET /metrics` | ❌ Non | Métriques système non affichées |
| `POST /init` | ❌ Non | Init projet via UI non disponible |

---

## 6. Changelog

| Date | Modification |
|------|--------------|
| 2025-12-02 | Création du document |
| 2025-01-XX | v1.2.0 – Implémentation CI, scan avancé, snapshots, licence |
