# Genealogy Web — Identité et réimport GEDCOM

**Version :** 0.1  
**Statut :** brouillon de conception

## 1. Objectif

Genealogy Web doit pouvoir réimporter une nouvelle version d'un GEDCOM
sans perdre les données propres à l'application :

- enrichissements géographiques ;
- corrections manuelles ;
- configurations de visualisation ;
- personne souche d'une visualisation ;
- préférences associées au projet.

Le GEDCOM reste la source de vérité pour les données généalogiques.

Le réimport ne doit jamais modifier le GEDCOM.

---

# 2. Problème

Deux exports successifs d'une même généalogie peuvent être différents.

Exemple :

```text
Export T1
@I123@ Jean DUPONT
@I124@ Marie MARTIN

Export T2
@I123@ Jean DUPONT
@I124@ Marie MARTIN
@I125@ Paul DUPONT
```

Le cas simple consiste à conserver les identifiants.

Mais une opération effectuée dans le logiciel généalogique source pourrait
potentiellement produire :

```text
Export T1
@I123@ Jean DUPONT

Export T2
@I847@ Jean DUPONT
```

Genealogy Web doit alors pouvoir déterminer si `@I123@` et `@I847@`
désignent probablement la même personne.

---

# 3. Principe fondamental

L'identité GEDCOM et l'identité logique ne doivent pas être confondues.

```text
SourceId
   @I123@
      │
      ▼
Person
 Jean DUPONT
```

`SourceId` identifie un enregistrement dans un GEDCOM donné.

Il ne constitue pas nécessairement une identité stable pour toute la durée
de vie d'un projet.

---

# 4. Empreinte du fichier GEDCOM

Chaque fichier GEDCOM importé doit pouvoir recevoir une empreinte.

Exemple :

```text
SHA-256
```

Propriétés conceptuelles :

```text
filename
size
modifiedAt
sha256
importedAt
```

## Règle

Si l'empreinte du GEDCOM est identique à celle de la dernière version importée,
aucun nouveau parsing complet n'est nécessaire.

Cela permet notamment d'utiliser un répertoire alimenté régulièrement par
GeneWeb sans retraiter inutilement un export inchangé.

---

# 5. SourceId

Chaque entité importée conserve son identifiant provenant du GEDCOM.

Exemples :

```text
@I123@
@F42@
```

Le `SourceId` constitue le premier mécanisme de rapprochement entre deux
imports successifs.

## Avantages

- comparaison rapide ;
- correspondance exacte ;
- aucune heuristique nécessaire.

## Limite

La stabilité de ces identifiants entre deux exports ne doit pas être considérée
comme garantie universellement.

---

# 6. Niveaux de rapprochement d'une personne

Le rapprochement doit utiliser plusieurs niveaux.

```text
Niveau 1
SourceId identique
        │
        ▼
correspondance directe

Niveau 2
SourceId différent
        │
        ▼
signature généalogique
        │
        ├── correspondance unique forte
        │       ▼
        │    candidat probable
        │
        └── ambiguïté
                ▼
           non résolu
```

Aucune correspondance ambiguë ne doit être acceptée silencieusement.

---

# 7. Signature généalogique d'une personne

Une signature peut être construite à partir d'informations relativement
discriminantes.

Exemples :

```text
nom normalisé
prénoms normalisés
sexe
date de naissance
lieu de naissance
date de décès
parents
conjoint(s)
```

Toutes ces informations ne sont pas nécessairement disponibles.

La signature doit donc supporter les données partielles.

---

# 8. Normalisation destinée au rapprochement

La normalisation utilisée pour rechercher une correspondance ne doit jamais
remplacer la donnée originale.

Exemple :

```text
Original
Écully

Valeur de comparaison
ECULLY
```

Autres normalisations envisageables :

```text
suppression des différences de casse
normalisation Unicode
espaces multiples
ponctuation non significative
```

Ces transformations servent uniquement à comparer.

---

# 9. Score de correspondance

Lorsqu'un `SourceId` ne suffit pas, le moteur pourra calculer un score de
correspondance.

Exemple conceptuel :

```text
même nom                  + poids fort
mêmes prénoms             + poids fort
même date de naissance    + poids très fort
même lieu de naissance    + poids moyen
mêmes parents             + poids très fort
même conjoint             + poids moyen
```

Les poids exacts ne sont pas définis dans ce document.

Ils devront être validés par des tests sur des GEDCOM réels.

---

# 10. États de réconciliation

Une comparaison entre une ancienne et une nouvelle entité peut produire :

```text
EXACT
PROBABLE
AMBIGUOUS
NEW
MISSING
```

## EXACT

Correspondance considérée comme certaine.

Exemple :

```text
SourceId identique
et données compatibles
```

## PROBABLE

Correspondance forte mais obtenue par heuristique.

Elle peut nécessiter une validation selon le contexte.

## AMBIGUOUS

Plusieurs correspondances plausibles existent.

Aucune fusion automatique.

## NEW

Entité présente uniquement dans le nouvel import.

## MISSING

Entité précédemment présente mais absente du nouvel import.

Elle ne doit pas nécessairement être supprimée immédiatement des données
propres à Genealogy Web.

---

# 11. Principe de prudence

Une fausse absence de rapprochement est préférable à une fausse fusion.

Autrement dit :

```text
"Je ne sais pas"
```

est un résultat valide.

Genealogy Web ne doit jamais associer silencieusement deux personnes lorsque
la correspondance est incertaine.

---

# 12. Réconciliation des lieux

Les lieux doivent suivre une logique différente des personnes.

Un enrichissement géographique doit pouvoir être réutilisé par toutes les
occurrences d'un même lieu.

Exemple :

```text
25 événements
        │
        ▼
"Bron, 69029, Rhône, Auvergne-Rhône-Alpes, France"
        │
        ▼
un PlaceEnrichment
        │
        ▼
latitude / longitude
```

---

# 13. Identité d'un lieu

L'identité initiale d'un lieu peut reposer sur son libellé GEDCOM exact.

Exemple :

```text
Bron, 69029, Rhône, Auvergne-Rhône-Alpes, France
```

Une clé normalisée peut être calculée pour rechercher des équivalences.

Exemple :

```text
bron|69029|rhone|auvergne-rhone-alpes|france
```

La clé normalisée ne remplace jamais `originalLabel`.

---

# 14. Variantes de lieux

Les chaînes suivantes peuvent potentiellement désigner le même lieu :

```text
Ecully
Écully
Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France
```

L'application peut proposer leur rapprochement.

Elle ne doit pas nécessairement les fusionner automatiquement lorsque
l'information disponible est insuffisante.

---

# 15. PlaceIdentity

À terme, plusieurs libellés GEDCOM pourront être associés à une même identité
géographique.

Conceptuellement :

```text
PlaceIdentity
│
├── "Ecully"
├── "Écully"
└── "Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France"
        │
        ▼
Écully
45.xxxxx
4.xxxxx
```

`PlaceIdentity` représente le lieu géographique identifié.

`Place` représente ce qui était écrit dans le GEDCOM.

Cette distinction permet de préserver les données sources.

---

# 16. Lieux ambigus

Exemple :

```text
Wysokie, Pologne
```

peut correspondre à plusieurs localités.

L'état doit rester :

```text
AMBIGUOUS
```

tant qu'une décision suffisamment fiable n'a pas été prise.

Une validation manuelle doit pouvoir produire :

```text
VALIDATED
```

---

# 17. Réutilisation des validations manuelles

Une validation manuelle doit survivre au réimport.

Exemple :

```text
Import 1
"Wysokie, Pologne"
      ↓
validation utilisateur
      ↓
PlaceIdentity X

Import 2
"Wysokie, Pologne"
      ↓
réutilisation de la validation
```

L'utilisateur ne doit pas avoir à résoudre plusieurs fois la même ambiguïté.

---

# 18. Réimport d'un projet

Le processus conceptuel est :

```text
Nouveau GEDCOM
      │
      ▼
calcul SHA-256
      │
      ├── identique
      │      ▼
      │   aucun changement
      │
      └── différent
             │
             ▼
           parsing
             │
             ▼
       nouveau modèle
             │
             ▼
       réconciliation
       /      |       \
 personnes familles  lieux
             │
             ▼
 conservation des enrichissements
             │
             ▼
      nouveau projet actif
```

---

# 19. Atomicité du réimport

Le projet actif ne doit pas être remplacé par un nouvel import incomplet ou
invalide.

Le principe doit être :

```text
ancien projet actif
       │
       │ nouveau GEDCOM
       ▼
import temporaire
       │
       ├── échec ─────► ancien projet conservé
       │
       └── succès
              │
              ▼
         réconciliation
              │
              ▼
       remplacement atomique
```

---

# 20. Rapport de réimport

Chaque réimport doit pouvoir produire un bilan.

Exemple :

```text
GEDCOM modifié

Personnes
  identiques             418
  nouvelles                5
  absentes                 2
  correspondances probables 1
  ambiguës                 1

Familles
  identiques             170
  nouvelles                3

Lieux
  déjà connus             91
  nouveaux                 4
  ambigus                  1
```

Ce rapport doit être consultable avant toute intervention manuelle nécessaire.

---

# 21. Personne souche d'un preset

Un `VisualizationPreset` ne doit pas dépendre exclusivement du `SourceId`.

Il doit pouvoir conserver suffisamment d'informations pour retrouver sa
personne souche après un réimport.

Conceptuellement :

```text
rootReference
├── sourceId
└── fingerprint
```

Lors du réimport :

```text
sourceId toujours valide
        │
       oui
        ▼
     réutiliser

sinon
        │
        ▼
réconciliation
```

Si la personne ne peut pas être retrouvée avec suffisamment de certitude,
le preset doit être conservé mais marqué comme nécessitant une nouvelle
sélection de souche.

---

# 22. Suppression d'une personne

Une personne absente d'un nouvel import ne doit pas provoquer immédiatement
la destruction de toutes les données qui lui étaient associées.

Elle peut être marquée :

```text
MISSING
```

Cela permet de gérer :

- suppression volontaire ;
- export partiel ;
- erreur temporaire ;
- changement d'identifiant non résolu.

---

# 23. Historique des imports

Le projet doit pouvoir conserver au minimum des métadonnées sur ses derniers
imports.

Exemple :

```text
2026-09-25 10:00
SHA-256 abc...
428 personnes

2026-09-25 14:00
SHA-256 def...
431 personnes
```

Il n'est pas nécessaire de conserver toutes les anciennes copies du GEDCOM.

---

# 24. Import automatique depuis GeneWeb

Le mode GeneWeb pourra surveiller un emplacement contenant les exports GEDCOM.

Exemple :

```text
/home/ubuntu/exports/gedcom/
```

L'application peut sélectionner le fichier le plus récent.

Cette fonction constitue un adaptateur d'entrée.

Le cœur de Genealogy Web reste indépendant de GeneWeb.

---

# 25. Fréquence

La fréquence de génération des GEDCOM et la fréquence de réimport de
Genealogy Web sont deux notions différentes.

Exemple :

```text
GeneWeb
export toutes les 5 minutes

Genealogy Web
       │
       ▼
observe le dernier fichier
       │
       ▼
SHA-256 identique ?
       │
    oui ──► rien
       │
    non
       ▼
réimport
```

Aucun parsing ne doit être effectué uniquement parce qu'un timer s'est
déclenché si les données n'ont pas changé.

---

# 26. Concurrence

Un réimport ne doit pas rendre indisponible la visualisation actuellement
consultée.

Pour les premières versions, une stratégie simple est suffisante :

```text
modèle actif
    +
construction du nouveau modèle
    +
échange une fois le nouveau modèle valide
```

---

# 27. Persistance

Les données de réconciliation doivent pouvoir être persistées.

Exemples :

```text
validations manuelles de lieux
correspondances confirmées entre personnes
références de souche
historique minimal des imports
```

Le format n'est pas défini ici.

JSON ou SQLite restent envisageables.

---

# 28. Cas à ne pas automatiser

Les situations suivantes ne doivent pas être résolues automatiquement sans
niveau de confiance suffisant :

```text
homonymes
jumeaux
dates inconnues
noms très fréquents
plusieurs Wysokie
changements importants de patronyme
plusieurs personnes ayant mêmes nom et prénom
```

---

# 29. Tests de réconciliation

Le moteur devra disposer de jeux de tests couvrant au minimum :

```text
identifiant inchangé
identifiant modifié
nouvelle personne
personne supprimée
homonymes
jumeaux
date corrigée
lieu corrigé
parent ajouté
conjoint ajouté
lieu renommé
lieu ambigu
```

---

# 30. Invariants

## REIMP-INV-001

Un réimport échoué ne modifie pas le projet actif.

## REIMP-INV-002

Une ambiguïté ne provoque pas de fusion automatique.

## REIMP-INV-003

Les données GEDCOM originales restent distinguables des enrichissements.

## REIMP-INV-004

Une validation manuelle ne doit pas être perdue lors d'un réimport normal.

## REIMP-INV-005

Un changement d'identifiant GEDCOM ne doit pas nécessairement créer une
nouvelle personne logique.

## REIMP-INV-006

Le mécanisme de réimport ne dépend pas de GeneWeb.

---

# 31. Stratégie V0

La V0 n'a pas besoin d'implémenter toute la réconciliation heuristique.

La première version peut utiliser :

```text
1. SHA-256 du GEDCOM
2. SourceId
3. comparaison des informations essentielles
4. rapport des différences
```

Les rapprochements heuristiques complexes pourront être ajoutés lorsque des
cas réels les justifieront.

Cette approche permet de ne pas sur-concevoir prématurément le système.

---

# 32. Principe directeur

Le système doit préférer :

```text
ambiguïté explicite
```

à :

```text
certitude inventée
```

Le but du mécanisme de réconciliation est de préserver le travail de
l'utilisateur entre deux imports, pas de réécrire silencieusement sa
généalogie.
