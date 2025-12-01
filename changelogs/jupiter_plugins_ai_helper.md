# Changelog - jupiter/plugins/ai_helper.py

## [0.3.1] - 2025-12-01
- Ajout d'une journalisation détaillée (INFO/DEBUG) lors de la configuration, de la capture des fichiers scannés et de la génération d'idées afin que le loglevel défini dans les Settings permette de diagnostiquer les heuristiques déclenchées.

## [0.3.0] - 2025-12-01
- Définit un numéro de version propre au plugin (`0.3.0`) pour ne plus dépendre du numéro global de Jupiter dans l'UI Plugins.

## [0.1.0] - 2025-10-17
- Création initiale du plugin AI Helper.
- Implémentation de la classe `AIHelperPlugin`.
- Ajout de la dataclass `AISuggestion`.
- Implémentation du hook `on_analyze` pour injecter des suggestions dans le rapport.
- Ajout d'une logique mock pour générer des suggestions basées sur des heuristiques simples (densité de fonctions, fonctions inutilisées).

- Ajout d'heuristiques avancées :
  - Détection des "God Objects" (fichiers avec trop de fonctions).
  - Détection des fichiers trop volumineux (> 50KB).
  - Analyse de couverture de tests (fichiers sources sans fichier de test correspondant).
  - Utilisation des données de scan (on_scan) pour l'analyse globale.
