# TODO – Intégration Meeting : vérification de la devicekey Jupiter  
_(version standalone, sans dépendance à d'autres docs)_

## IMPERATIF
Pendant tout le developpement : 
- garder ce fichier a jour en cochant les cases des taches effectivement terminées, pas avant. Ceci est la seule modification autorisée de ce document.
- maintenir constamment a jour les docs dans le dossier docs/, /readme.md, les changelogs, et les numeros de versions.


## 1. Objectif fonctionnel

Mettre en place dans Jupiter une vérification **lecture seule** de la licence via l'API Meeting, basée sur une **devicekey dédiée Jupiter**.

Règle métier retenue pour considérer la licence Jupiter comme **valide** :

- La requête HTTP `GET /api/devices/{device_key}` vers le backend Meeting retourne **HTTP 200**.
- Dans le JSON de réponse :
  - `authorized == true`
  - `device_type == "Jupiter"` (type de device réservé pour Jupiter)
  - `token_count > 0` (au moins 1 token restant)

Sinon, la licence Jupiter est considérée comme **non valide / expirée**.

Backend Meeting par défaut (prod) :  
`https://meeting.ygsoft.fr`  
Base API : `https://meeting.ygsoft.fr/api`

Exemple de fiche device Meeting (côté admin) correspondant à Jupiter :

- device key : `C86015A0C19686A1C7ECE6CC7C8F4874`
- device type : `Jupiter`
- Serial number : `V1-S01-00005`
- Authorized : `Yes`
- Token left : `10` (=> `token_count = 10`)

---

## 2. Adapter Meeting : implémenter la vérification de licence

### 2.1. Créer / compléter `jupiter/server/meeting_adapter.py`

- [x] Vérifier si le fichier existe, sinon le créer.
- [x] Ajouter les imports nécessaires :
  - [x] `from dataclasses import dataclass`
  - [x] `from enum import Enum`
  - [x] `from typing import Optional`
  - [x] `import logging`
  - [x] `import requests` (ou lib HTTP déjà utilisée dans le projet)
- [x] Définir une **enum de statut** de licence :

  Exemple :

  ```python
  class MeetingLicenseStatus(str, Enum):
      VALID = "valid"
      INVALID = "invalid"
      NETWORK_ERROR = "network_error"
      CONFIG_ERROR = "config_error"
  ```

- [x] Définir un **dataclass** de résultat détaillé :

  ```python
  @dataclass
  class MeetingLicenseCheckResult:
      status: MeetingLicenseStatus
      message: str
      device_key: Optional[str] = None
      http_status: Optional[int] = None
      authorized: Optional[bool] = None
      device_type: Optional[str] = None
      token_count: Optional[int] = None
  ```

- [x] Ajouter une classe `MeetingAdapter` (ou compléter celle existante) avec au moins :

  - [x] Attributs de config (passés au constructeur) :
    - `base_url: str`  (ex: `"https://meeting.ygsoft.fr/api"`)
    - `device_type_expected: str = "Jupiter"`
    - `timeout_seconds: float = 5.0`
    - (optionnel) `auth_token: Optional[str] = None` pour un token HTTP si besoin plus tard.
  - [x] Logger : `self.logger = logging.getLogger(__name__)`

- [x] Implémenter une méthode publique principale :

  ```python
  def check_jupiter_devicekey(
      self,
      device_key: str,
  ) -> MeetingLicenseCheckResult:
      """
      Vérifie la validité de la devicekey Jupiter via l'API Meeting.

      Règle:
      - GET {base_url}/devices/{device_key}
      - Licence valide si:
        - HTTP 200
        - JSON["authorized"] == True
        - JSON["device_type"] == self.device_type_expected ("Jupiter" par défaut)
        - JSON["token_count"] > 0

      Retourne un MeetingLicenseCheckResult détaillé.
      """
  ```

### 2.2. Détails de l'appel HTTP vers Meeting

- [x] Construire l'URL :

  - `url = f"{self.base_url.rstrip('/')}/devices/{device_key}"`

  Avec `base_url` par défaut : `"https://meeting.ygsoft.fr/api"`.

- [x] Préparer les headers :

  - [x] `headers = {"Accept": "application/json"}`
  - [x] Ajouter éventuellement un header d'auth si un token est configuré :
    - Ex : `headers["Authorization"] = f"Bearer {self.auth_token}"` (optionnel, à ne pas forcer tant que non nécessaire).

- [x] Exécuter la requête :

  - [x] Utiliser `requests.get(url, headers=headers, timeout=self.timeout_seconds)`
  - [x] Gérer les exceptions réseau (`requests.exceptions.RequestException`) :
    - Retourner `MeetingLicenseCheckResult(status=NETWORK_ERROR, message="...", device_key=...)`.
    - Log niveau `WARNING` ou `ERROR`.

- [x] Interprétation du code HTTP :

  - [x] `200` :
    - Par défaut **poursuivre** l'analyse du JSON.
  - [x] `404` :
    - Considérer la licence **INVALID**.
    - Message : `"Device not found in Meeting (HTTP 404)."`
  - [x] Autres codes (400, 401, 403, 500, …) :
    - Considérer la licence **INVALID** (erreur côté Meeting ou droits insuffisants).
    - Inclure le code dans `http_status` et dans le message pour debug.

### 2.3. Interpréter le JSON de `/api/devices/{device_key}`

Réponse typique Meeting (extrait doc) :

```json
{
  "device_key": "...",
  "device_name": "...",
  "product_serial": "...",
  "authorized": true,
  "device_type": "...",
  "distribution": "...",
  "token_code": "...",
  "token_count": 0,
  "note": "...",
  "ip_address": "...",
  "parent_device_key": "...",
  "bundles": [ ... ],
  "ghost_candidate_url": "...",
  "ap_ssid": "...",
  "ap_password": "...",
  "http_pw_low": "...",
  "http_pw_medium": "...",
  "http_pw_high": "...",
  "services": ["ssh", "vnc", "http", "scp"]
}
```

- [x] Extraire dans la méthode :

  - `authorized = bool(data.get("authorized"))`
  - `device_type = str(data.get("device_type") or "")`
  - `token_count = data.get("token_count")`

- [x] Vérifier et caster `token_count` :

  - Si `token_count` est `None` ou non numérique → considérer comme **0**.
  - `token_count_int = int(token_count) if token_count is not None else 0`

- [x] Appliquer la règle métier :

  - [x] Si `authorized is True`
  - [x] ET `device_type == self.device_type_expected` (par défaut `"Jupiter"`)
  - [x] ET `token_count_int > 0`
  - ⇒ **status = VALID**, message clair (ex. `"License valid: authorized, correct device_type, tokens > 0."`).

  - [x] Sinon :
    - **status = INVALID**
    - message détaillé (indiquer quelle condition échoue : non autorisé, mauvais type, pas de token, etc.).

- [x] Remplir `MeetingLicenseCheckResult` avec :

  - `device_key`
  - `authorized`
  - `device_type`
  - `token_count`
  - `http_status` (code HTTP reçu)

---

## 3. Configuration globale Jupiter pour Meeting

### 3.1. Global config YAML (~/.jupiter/global_config.yaml)

But : ne pas hardcoder l'URL et les paramètres Meeting dans le code.

- [x] Ajouter une section dans la config globale (fichier utilisateur) :

  Exemple minimal :

  ```yaml
  meeting:
    base_url: "https://meeting.ygsoft.fr/api"
    device_type: "Jupiter"
    timeout_seconds: 5.0
    # auth_token: ""  # Optionnel : si un jour l'API Meeting impose un token
  ```

- [x] Assurer le chargement de cette section dans le code qui instancie `MeetingAdapter`.

### 3.2. Code de chargement / instanciation de `MeetingAdapter`

- [x] Trouver l'endroit central où la config globale est chargée (probablement dans `jupiter/config` ou `jupiter/server/manager.py`).
- [x] Ajouter l'extraction des valeurs Meeting :

  - `meeting_base_url = config.get("meeting", {}).get("base_url", "https://meeting.ygsoft.fr/api")`
  - `meeting_device_type = config.get("meeting", {}).get("device_type", "Jupiter")`
  - `meeting_timeout = config.get("meeting", {}).get("timeout_seconds", 5.0)`
  - `meeting_auth_token = config.get("meeting", {}).get("auth_token")` (optionnel)

- [x] Instancier `MeetingAdapter` avec ces paramètres et le rendre accessible au serveur/API.

---

## 4. Intégration dans le démarrage du serveur Jupiter

### 4.1. Au lancement du serveur (`jupiter.cli.main server` / `gui`)

- [x] Identifier le point d'entrée serveur (ex. `jupiter/cli/main.py` et/ou `jupiter/server/api.py`).
- [x] Au démarrage :

  - [x] Charger la config globale.
  - [x] Créer une instance de `MeetingAdapter`.
  - [x] Lire la **devicekey Jupiter** à partir de la config (exemple souhaité) :

    ```yaml
    jupiter:
      device_key: "C86015A0C19686A1C7ECE6CC7C8F4874"
    ```

  - [x] Si aucune `device_key` n'est configurée :
    - Retourner un statut `CONFIG_ERROR` dans la logique de licence.
    - Logger un **WARNING** clair : "No Meeting device_key configured for Jupiter; running in restricted/demo mode."
    - Considérer la licence comme **non vérifiée** ou **invalid** mais laisser Jupiter démarrer (mode restreint).

  - [x] Si une `device_key` est présente :
    - [x] Appeler `meeting_adapter.check_jupiter_devicekey(device_key)`.
    - [x] En fonction du résultat :
      - `VALID` : démarrer en mode normal.
      - `INVALID` : démarrer en mode **restreint / démo** (voir 4.2).
      - `NETWORK_ERROR` : démarrer en mode **dégradé** (ne pas bloquer, mais logguer).

### 4.2. Mode restreint / timer (comportement licence invalide)

- [x] Définir une structure (classe / objet global / variable) pour stocker l'état de licence dans le serveur :

  - `license_status: MeetingLicenseStatus`
  - `license_message: str`
  - `license_checked_at: datetime`
  - (optionnel) `license_expires_at: datetime` si timer implémenté

- [x] Si la licence n'est pas **VALID** :

  - [x] Implémenter un **timer** interne de grâce (ex: 10 minutes) pendant lequel Jupiter reste utilisable avant blocage ou limitations.
  - [x] Après expiration du timer :
    - Soit bloquer certaines routes (scan/analyze/etc.) avec une réponse d'erreur explicite.
    - Soit afficher uniquement un message de licence expirée, selon choix futur.

- [ ] Recommandation : prévoir un **re-check périodique** de la licence (ex. toutes les X minutes) pour récupérer automatiquement si Meeting redevient accessible ou si la licence est corrigée.

---

## 5. Exposer l'état de licence dans l'API Jupiter

### 5.1. Endpoint HTTP de statut licence

- [x] Dans `jupiter/server/api.py` (ou module équivalent FastAPI) :

  - [x] Ajouter un endpoint, par exemple :

    - `GET /license/status`

  - [x] Réponse JSON attendue :

    ```json
    {
      "status": "valid" | "invalid" | "network_error" | "config_error",
      "message": "texte humain expliquant l'état",
      "device_key": "C86015A0C19686A1C7ECE6CC7C8F4874",
      "checked_at": "2025-06-01T12:34:56Z",
      "meeting_base_url": "https://meeting.ygsoft.fr/api",
      "device_type_expected": "Jupiter",
      "authorized": true,
      "device_type": "Jupiter",
      "token_count": 10
    }
    ```

- [x] Ce endpoint doit lire les infos depuis l'état global de licence mis à jour au démarrage et/ou lors d'un re-check.

### 5.2. Cohérence avec l'UI / frontend (facultatif pour l'instant)

- [x] Si le frontend Jupiter consomme déjà un statut licence, veiller à ce que les clés JSON soient simples (`status`, `message`).
- [x] Prévoir que l'UI affiche clairement :
  - Licence valide,
  - Erreur de config (pas de devicekey),
  - Erreur Meeting (réseau),
  - Licence invalide (non autorisée, type incorrect, plus de tokens).

---

## 6. Support CLI pour la licence Meeting

- [x] Dans `jupiter/cli/main.py` :

  - [x] Ajouter une commande, par exemple :
    - `jupiter meeting check-license`
  - [x] Comportement :
    - Charger la config globale.
    - Instancier `MeetingAdapter`.
    - Lire la `device_key` Jupiter dans la config.
    - Appeler `check_jupiter_devicekey`.
    - Afficher en **texte clair** dans la console :
      - Statut (`VALID`, `INVALID`, `NETWORK_ERROR`, `CONFIG_ERROR`).
      - Message détaillé.
      - device_key utilisée.
      - Détail des champs : `authorized`, `device_type`, `token_count`, `http_status`.

- [x] Codes de sortie CLI (optionnel mais utile) :
  - `0` si licence **VALID**.
  - `1` si **INVALID**.
  - `2` en cas de **CONFIG_ERROR**.
  - `3` en cas de **NETWORK_ERROR**.

---

## 7. Tests & robustesse

### 7.1. Tests unitaires du `meeting_adapter`

- [x] Créer un fichier de tests, par ex. `tests/test_meeting_adapter.py`.
- [x] Mocker `requests.get` pour couvrir :

  - [x] Cas **VALID** :
    - HTTP 200
    - `authorized = true`
    - `device_type = "Jupiter"`
    - `token_count = 10`

  - [x] Cas **device non trouvé** :
    - HTTP 404
    - ⇒ status = INVALID, message explicite.

  - [x] Cas **device non autorisé** :
    - HTTP 200
    - `authorized = false`
    - ⇒ status = INVALID, raison = "not authorized".

  - [x] Cas **mauvais device_type** :
    - HTTP 200
    - `device_type = "AutreChose"`
    - ⇒ INVALID.

  - [x] Cas **token_count == 0** :
    - HTTP 200
    - ⇒ INVALID.

  - [x] Cas **réseau indisponible** :
    - `requests.get` lève `RequestException`.
    - ⇒ status = NETWORK_ERROR.

  - [x] Cas **JSON incomplet ou mal formé** :
    - HTTP 200, mais champs manquants.
    - Assurer que le code ne crashe pas.
    - Considérer INVALID avec message explicite.

### 7.2. Résilience générale

- [x] Vérifier qu'une erreur Meeting (réseau, JSON, etc.) :

  - Ne fait pas crasher le serveur Jupiter.
  - Est correctement loggée.
  - Fait basculer proprement en mode dégradé / restreint.

---

## 8. Documentation & changelogs (rappels locaux au repo)

Même si ce fichier TODO doit être standalone, les actions concrètes dans le repo doivent rester cohérentes avec l'organisation existante.

- [x] Mettre à jour la documentation globale de Jupiter :

  - [x] `Manual.md` (racine du projet) :
    - Ajouter une section "Licence Meeting / devicekey Jupiter" expliquant :
      - La notion de devicekey côté Meeting.
      - La règle métier (authorized + device_type=Jupiter + tokens>0).
      - Comment configurer `~/.jupiter/global_config.yaml` (`meeting.base_url`, `meeting.device_type`, `meeting.timeout_seconds`, `jupiter.device_key`).
      - Comment utiliser la commande CLI `jupiter meeting check-license`.
      - Comment interpréter l'endpoint `/license/status`.

  - [x] `README.md` :
    - Ajouter un court paragraphe résumant la dépendance optionnelle à Meeting pour la licence Jupiter.

- [x] Mettre à jour / créer les changelogs dédiés :

  - [x] `changelogs/jupiter_server_meeting_adapter.md` :
    - Décrire l'ajout de `MeetingAdapter` et de la logique de vérification de licence.
  - [x] Éventuels autres changelogs si des fichiers supplémentaires sont modifiés (`cli`, `api`, etc.).

- [x] Vérifier que ce fichier `TODOs/todo_meeting_auth.md` reste à jour :
  - [x] Cocher au fur et à mesure les tâches réellement complétées (ne jamais cocher une tâche non implémentée).
