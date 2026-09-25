# Genealogy Web — Architecture technique

**Version :** 0.1  
**Statut :** proposition d'architecture initiale

# 1. Objectifs

L'architecture doit répondre aux contraintes suivantes :

- fonctionner sur une petite VM Ubuntu ;
- consommer très peu de ressources au repos ;
- rester simple à administrer ;
- être indépendante de GeneWeb ;
- accepter n'importe quel GEDCOM compatible ;
- produire des visualisations interactives ;
- produire des documents vectoriels grand format ;
- permettre une évolution progressive ;
- faciliter les tests ;
- éviter les dépendances techniques inutiles.

Le projet privilégie la simplicité avant la capacité à monter en charge.

---

# 2. Architecture générale proposée

```text
                         Navigateur
              ┌──────────────────────────┐
              │                          │
              │  Interface Web           │
              │                          │
              │  SVG                     │
              │  éventail                │
              │  arbre                   │
              │  cartes                  │
              │                          │
              └────────────┬─────────────┘
                           │
                        HTTP/JSON
                           │
                           ▼
              ┌──────────────────────────┐
              │    Backend léger         │
              │                          │
              │  API                     │
              │  GEDCOM parser           │
              │  modèle métier           │
              │  projets                 │
              │  réconciliation          │
              │  export                  │
              └──────┬───────────┬───────┘
                     │           │
                     │           │
              ┌──────▼───┐   ┌──▼───────────┐
              │ GEDCOM   │   │ Persistance  │
              │          │   │ locale       │
              └──────────┘   └──────────────┘
```

GeneWeb n'appartient pas au cœur de cette architecture.

Il constitue éventuellement une source externe de GEDCOM.

---

# 3. Principe client / serveur

La répartition proposée est :

## Serveur

Responsable de :

- lecture GEDCOM ;
- parsing ;
- validation ;
- modèle métier ;
- gestion des projets ;
- persistance ;
- réimport ;
- réconciliation ;
- géocodage ;
- préparation des données destinées aux visualisations.

## Navigateur

Responsable de :

- interface utilisateur ;
- affichage ;
- interactions ;
- pan ;
- zoom ;
- rendu SVG ;
- légendes ;
- prévisualisation des exports.

Cette répartition évite de demander au serveur de générer continuellement
des images graphiques complexes.

---

# 4. Backend

## Choix initial proposé

Python.

Motivations :

- disponible facilement sous Ubuntu ;
- écosystème adapté au parsing de fichiers ;
- bonnes bibliothèques GEDCOM et géographiques disponibles ;
- faible coût d'exécution pour les volumes visés ;
- facilité de test ;
- lisibilité ;
- bonne intégration avec SQLite si nécessaire.

Ce choix devra être validé par un prototype.

---

# 5. Framework HTTP

## Choix proposé

FastAPI ou framework Python léger équivalent.

L'objectif n'est pas d'exploiter toutes les fonctionnalités du framework.

Il doit principalement fournir :

```text
HTTP
JSON
upload
routes
validation
gestion des erreurs
```

Le framework ne doit pas imposer une architecture complexe.

---

# 6. Frontend

## Principe

Le frontend doit rester aussi simple que possible.

La V0 ne nécessite pas nécessairement un framework frontend complexe.

Architecture envisageable :

```text
HTML
CSS
JavaScript / TypeScript
SVG
```

Une bibliothèque spécialisée peut être utilisée lorsque sa valeur est claire.

Exemples :

```text
Leaflet       cartographie
D3            géométrie / visualisations si nécessaire
svg2pdf       export vectoriel si pertinent
```

L'utilisation d'une bibliothèque doit répondre à un besoin identifié.

---

# 7. React / Vue / Angular

Aucun framework frontend lourd n'est requis par principe.

Il ne sera introduit que si la complexité de l'interface le justifie.

Pour V0 et probablement V1, une application JavaScript/TypeScript légère
peut suffire.

Objectif :

```text
moins de dépendances
moins de build
moins de RAM
moins de complexité
```

---

# 8. Modèle métier

Le modèle défini dans `DOMAIN_MODEL.md` doit rester indépendant :

- du framework HTTP ;
- du stockage ;
- du DOM ;
- du SVG ;
- de la bibliothèque cartographique.

Conceptuellement :

```text
              ┌─────────────────┐
              │  Domain Model   │
              └────────┬────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
    GEDCOM          Storage           API
    adapter         adapter           adapter
```

---

# 9. Parser GEDCOM

Le parser doit être isolé derrière une interface.

```text
GEDCOM
   │
   ▼
GedcomImporter
   │
   ▼
Genealogy
```

Ainsi, le reste de l'application ne manipule pas directement les tags GEDCOM.

Exemple :

```text
0 @I123@ INDI
1 NAME Jean /DUPONT/
1 BIRT
2 DATE 12 MAR 1901
```

devient conceptuellement :

```text
Person
  givenNames = Jean
  surname = DUPONT

Event
  type = BIRTH
  date = ...
```

---

# 10. Choix de la bibliothèque GEDCOM

La bibliothèque ne doit pas être choisie uniquement parce qu'elle sait lire
un exemple simple.

Elle devra être évaluée sur :

- GEDCOM 5.5 ;
- GEDCOM 5.5.1 ;
- dates partielles ;
- encodage UTF-8 ;
- caractères accentués ;
- relations familiales ;
- événements personnalisés ;
- médias ;
- tolérance aux variantes produites par différents logiciels.

La possibilité d'écrire notre propre couche de parsing complémentaire reste
ouverte.

---

# 11. Persistance V0

## Décision

Pas de serveur SQL.

Pour V0, le modèle généalogique peut être construit en mémoire lors de
l'import.

Les données propres à Genealogy Web peuvent initialement être conservées
dans des fichiers JSON.

Exemple :

```text
projects/
└── famille/
    ├── project.json
    ├── places.json
    └── presets.json
```

Le GEDCOM peut rester stocké séparément.

---

# 12. Évolution SQLite

SQLite pourra être introduit lorsque les besoins de persistance le
justifieront.

Cas pouvant justifier SQLite :

- nombreux enrichissements ;
- recherches fréquentes ;
- plusieurs projets ;
- historique d'import ;
- rapprochements ;
- cache de géocodage important.

SQLite ne nécessite aucun serveur permanent.

```text
Genealogy Web
      │
      ▼
genealogy-web.sqlite
```

Le passage JSON → SQLite ne doit pas modifier le modèle métier.

---

# 13. Pas de serveur de base de données

Les premières versions ne nécessitent pas :

```text
PostgreSQL
MySQL
MariaDB
MongoDB
Redis
```

Une telle dépendance ne sera introduite que si un besoin réel apparaît.

---

# 14. Organisation des données

Organisation envisagée :

```text
data/
├── projects/
│   ├── famille/
│   │   ├── source.ged
│   │   ├── project.json
│   │   ├── places.json
│   │   └── presets.json
│   │
│   └── autre-genealogie/
│       └── ...
│
└── cache/
    └── geocoding/
```

Le contenu de `data/` ne doit pas être versionné dans Git.

---

# 15. Organisation du code

Structure initiale envisagée :

```text
genealogy-web/
│
├── README.md
├── docs/
│   ├── SPECIFICATIONS.md
│   ├── DOMAIN_MODEL.md
│   ├── IDENTITY_AND_REIMPORT.md
│   └── ARCHITECTURE.md
│
├── src/
│   ├── domain/
│   ├── gedcom/
│   ├── services/
│   ├── storage/
│   ├── api/
│   └── web/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── data/
```

Cette structure reste indicative.

---

# 16. Séparation des responsabilités

## `domain`

Contient les concepts métier :

```text
Person
Family
Event
Place
Genealogy
AncestorOccurrence
...
```

Aucune dépendance HTTP ou SVG.

## `gedcom`

Responsable de la transformation :

```text
GEDCOM → Domain Model
```

## `services`

Logique applicative :

```text
ascendance
Sosa
réconciliation
géocodage
couleurs
statistiques
```

## `storage`

Persistance JSON ou SQLite.

## `api`

Interface HTTP.

## `web`

Frontend.

---

# 17. Calcul Sosa

Le calcul Sosa doit être un service métier.

```text
rootPerson
      │
      ▼
AncestorService
      │
      ▼
AncestorOccurrence[]
```

Le frontend reçoit les occurrences calculées.

Il ne doit pas reconstruire lui-même les relations GEDCOM.

---

# 18. Rendu de l'éventail

Le rendu doit être effectué en SVG dans le navigateur.

Motivations :

- vectoriel ;
- zoom sans perte ;
- interaction simple ;
- export ;
- DOM inspectable ;
- impression grand format.

Conceptuellement :

```text
AncestorOccurrence[]
        +
FanChartConfiguration
        │
        ▼
FanChartRenderer
        │
        ▼
SVG
```

---

# 19. Rendu cartographique

La cartographie interactive peut utiliser Leaflet ou une bibliothèque
équivalente.

Le moteur métier ne doit jamais dépendre de Leaflet.

```text
Place[]
   +
coordinates
   │
   ▼
MapViewModel
   │
   ▼
Leaflet
```

---

# 20. Couleurs

Un service unique doit calculer les couleurs.

```text
ColorService
```

Entrées possibles :

```text
lieu
coordonnées
lieu de référence
mode de coloration
```

Sortie :

```text
couleur
```

Ce service doit être commun aux cartes, éventails et légendes.

---

# 21. Export SVG

Le SVG affiché doit pouvoir être sauvegardé directement lorsque cela est
possible.

Cela garantit une sortie réellement vectorielle.

---

# 22. Export PDF

Deux stratégies devront être évaluées.

## Option A — navigateur

```text
SVG
 ↓
bibliothèque JavaScript
 ↓
PDF
```

## Option B — serveur

```text
SVG
 ↓
backend
 ↓
PDF
```

Le choix devra être effectué après un prototype A0 réel.

Critères :

- conservation du vectoriel ;
- polices ;
- images ;
- taille du fichier ;
- qualité d'impression ;
- mémoire consommée.

---

# 23. Export PNG

L'export PNG pourra être réalisé côté navigateur à partir du SVG.

Une limite de résolution devra être prévue pour éviter une consommation
mémoire excessive sur les très grands formats.

---

# 24. Géocodage

Le géocodage doit être encapsulé derrière une interface :

```text
Geocoder
   │
   ├── Provider A
   ├── Provider B
   └── Manual
```

Le modèle métier ne dépend d'aucun fournisseur.

---

# 25. Cache géographique

Les résultats de géocodage doivent être conservés localement.

Objectifs :

- limiter les requêtes externes ;
- améliorer les performances ;
- préserver les validations manuelles ;
- réduire la dépendance au fournisseur.

---

# 26. Adaptateur GeneWeb

GeneWeb doit être traité comme un adaptateur optionnel.

```text
GeneWeb
   │
   │ export GEDCOM
   ▼
GeneWebSourceAdapter
   │
   ▼
GedcomImporter
```

Fonctions possibles :

- détecter le dernier GEDCOM ;
- calculer son empreinte ;
- déclencher un réimport.

Le reste de l'application ne doit pas savoir que GeneWeb existe.

---

# 27. Upload manuel

Le mode générique reste :

```text
Navigateur
   │
   │ upload .ged
   ▼
API
   │
   ▼
GedcomImporter
```

Les deux modes aboutissent au même pipeline.

---

# 28. Déploiement

Architecture cible initiale :

```text
Internet
   │
   ▼
Nginx
   │
   ├── /geneweb/      → GeneWeb
   │
   └── /genealogy/    → Genealogy Web
                           │
                           ▼
                       backend Python
```

Les chemins définitifs restent à déterminer.

---

# 29. Processus serveur

L'objectif est de n'ajouter qu'un processus applicatif léger.

Exemple :

```text
systemd
   │
   ▼
genealogy-web.service
   │
   ▼
backend Python
```

Nginx reste le reverse proxy.

---

# 30. Consommation de ressources

Principe :

```text
CPU au repos ≈ nul
RAM au repos faible
```

Aucun traitement périodique lourd ne doit être nécessaire.

Les opérations coûteuses sont déclenchées :

- à l'import ;
- au réimport ;
- au géocodage ;
- à l'export.

---

# 31. Réimport automatique

Aucun polling fréquent n'est requis dans V0.

Une évolution pourra :

- observer le répertoire d'exports ;
- vérifier périodiquement le dernier fichier ;
- ou recevoir un signal après export GeneWeb.

Dans tous les cas, l'empreinte évite un parsing inutile.

---

# 32. Sécurité

Les fichiers GEDCOM contiennent des données privées.

Principes initiaux :

- stockage hors du dépôt Git ;
- pas d'accès direct par Nginx aux fichiers sources ;
- upload contrôlé ;
- noms de fichiers non utilisés directement comme chemins ;
- taille maximale d'upload ;
- validation du type de fichier ;
- aucune exécution de contenu importé.

---

# 33. Authentification

L'authentification applicative n'est pas nécessaire pour le prototype local.

Pour une exposition Internet, une protection devra être présente.

Dans un premier temps, la protection Nginx existante peut éventuellement
être réutilisée.

Une authentification propre à Genealogy Web pourra être étudiée ultérieurement.

---

# 34. Tests

Les tests doivent être présents dès V0.

## Tests unitaires

```text
dates GEDCOM
noms
relations
Sosa
normalisation
réconciliation
```

## Tests d'intégration

```text
GEDCOM → modèle
GEDCOM → ascendance
réimport → conservation enrichissements
```

## Tests visuels

À partir de V1 :

```text
modèle connu
    ↓
SVG
    ↓
comparaison / validation
```

---

# 35. Fixtures GEDCOM

Le dépôt doit contenir de petits GEDCOM artificiels destinés aux tests.

Exemples :

```text
simple-family.ged
missing-parent.ged
multiple-unions.ged
implex.ged
partial-dates.ged
ambiguous-places.ged
```

Ils ne doivent contenir aucune donnée familiale privée réelle.

---

# 36. Observabilité

Le backend doit produire des logs simples :

```text
import démarré
import terminé
nombre de personnes
nombre de familles
erreurs de parsing
réimport
géocodage
export
```

Pas de stack de monitoring supplémentaire requise pour V0.

---

# 37. Développement

Le dépôt Git constitue la source du code.

```text
VS Code
Remote SSH
     │
     ▼
/home/ubuntu/genealogy-web
     │
     ├── git diff
     ├── git commit
     └── git push
             │
             ▼
          GitHub
```

Contrairement à `geneweb-config`, aucun script de synchronisation depuis
la production n'est nécessaire pour les sources de Genealogy Web.

---

# 38. Déploiement futur

Le code exécuté en production devra à terme provenir d'une version Git connue.

Conceptuellement :

```text
Git
 │
 ▼
build / installation
 │
 ▼
production
```

Le code de production ne doit pas devenir une deuxième source indépendante
du dépôt Git.

---

# 39. Dépendances

Chaque dépendance externe doit répondre à au moins un besoin identifié.

Avant d'ajouter une dépendance importante, vérifier :

- utilité ;
- maintenance ;
- poids ;
- licence ;
- sécurité ;
- activité du projet ;
- possibilité de remplacement.

---

# 40. Décisions initiales

Les décisions suivantes sont proposées pour la première implémentation :

```text
Backend               Python
API                   FastAPI ou équivalent léger
Frontend              HTML/CSS/JS ou TypeScript léger
Visualisations        SVG
Carte                  Leaflet
Persistance V0        JSON
Persistance possible  SQLite
Reverse proxy         Nginx existant
Service               systemd
Base SQL serveur      aucune
```

Ces décisions restent révisables sur la base des prototypes.

---

# 41. Ce que V0 doit démontrer

V0 doit permettre le chemin complet :

```text
GEDCOM quelconque
       │
       ▼
     upload
       │
       ▼
     parser
       │
       ▼
 modèle métier
       │
       ▼
rapport d'import
       │
       ▼
recherche personne
       │
       ▼
choix de la souche
       │
       ▼
ascendance textuelle
```

Si ce pipeline est propre et testé, V1 pourra construire l'éventail dessus.

---

# 42. Ce que V0 ne doit pas faire

V0 n'a pas besoin de :

- PDF A0 ;
- carte ;
- géocodage ;
- portraits ;
- arbre descendant ;
- authentification applicative complexe ;
- base SQL ;
- synchronisation temps réel avec GeneWeb.

Ces fonctionnalités ne doivent pas ralentir la validation du socle.

---

# 43. Critère architectural principal

Une fonctionnalité graphique doit pouvoir être remplacée sans réécrire
le parser GEDCOM.

Un mécanisme de stockage doit pouvoir être remplacé sans réécrire
le modèle métier.

Un fournisseur de géocodage doit pouvoir être remplacé sans réécrire
les cartes.

GeneWeb doit pouvoir disparaître sans rendre Genealogy Web inutilisable.

Cette indépendance constitue le principal critère de qualité de
l'architecture.
