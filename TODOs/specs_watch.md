La fonction **"Watch"** dans la **top bar** de la WebUI de Jupiter est conçue pour fournir une **surveillance en temps réel** du projet pendant l'analyse ou l'exécution. Plus précisément, cette fonctionnalité permet de suivre en continu les changements ou les processus actifs dans un projet, ce qui est particulièrement utile pour :

### 1. **Suivi des exécutions en direct (live tracking)**

* Lorsque l'utilisateur lance une commande comme `run` ou `scan`, **"Watch"** permet de suivre les événements en temps réel, comme :

  * Les **fonctions appelées** pendant l'exécution (dynamique),
  * Les **changements de fichiers** (scan continu),
  * Les **alertes ou erreurs** générées pendant l'analyse.

### 2. **Affichage des événements en direct**

* En activant **"Watch"**, l'utilisateur peut voir, au fur et à mesure de l'analyse :

  * Quels fichiers sont **actuellement scannés**,
  * Quelle **fonction est en train d'être analysée**,
  * Les **logs en temps réel** générés pendant l'exécution de l’analyse ou du scan.
* Cela permet de visualiser, dans l'interface, les **progressions** et les **résultats en direct** plutôt que d'attendre que le processus soit terminé.

### 3. **Interactivité et feedback immédiat**

* L’interface WebUI doit mettre à jour les sections pertinentes en temps réel avec les informations de progression. Cela peut inclure :

  * Le nombre de **fonctions** analysées,
  * L’état actuel de l’**analyse dynamique**,
  * Les **statuts des fichiers** (en analyse, terminés, erreurs détectées).

### 4. **Utilité pour les projets en cours d'analyse ou de refactorisation**

* **Watch** peut aussi être utile pendant le processus de **simulation** d'impact (ex : `simulate remove`), car l’utilisateur peut voir en direct quels fichiers ou fonctions seraient affectés par la suppression simulée.

### En résumé :

La fonction **"Watch"** permet à l’utilisateur de suivre les analyses et exécutions en temps réel, avec un feedback immédiat sur les changements, appels de fonctions, et processus en cours. Elle est essentielle pour avoir une vision interactive et dynamique du travail de Jupiter sans attendre la fin des processus analytiques.
