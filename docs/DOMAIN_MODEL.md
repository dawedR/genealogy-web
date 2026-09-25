# Genealogy Web — Modèle métier

**Version :** 0.1  
**Statut :** brouillon de conception

## 1. Objectif

Ce document décrit les concepts manipulés par Genealogy Web et leurs relations.

Il décrit le **modèle métier**, indépendamment de son implémentation future.

Il ne présuppose donc pas :

- de base SQL ;
- de framework ;
- de langage ;
- de format de stockage particulier.

Le GEDCOM reste la source généalogique de référence.

---

# 2. Vue générale

```text
GenealogyProject
│
├── Genealogy
│   │
│   ├── Person
│   │     └── Event
│   │
│   ├── Family
│   │     └── Event
│   │
│   ├── Place
│   │
│   └── Media
│
├── PlaceEnrichment
│
└── VisualizationPreset
      │
      ├── FanChartPreset
      ├── MapPreset
      └── TreePreset
```

Une distinction fondamentale doit être maintenue entre :

```text
Données généalogiques
        │
        │ proviennent du GEDCOM
        ▼
Person / Family / Event / Place

Données propres à Genealogy Web
        │
        ▼
géocodage
corrections
paramètres graphiques
configurations d'impression
```

---

# 3. GenealogyProject

`GenealogyProject` représente l'unité de travail de l'application.

Un projet associe une source généalogique à des enrichissements et à des
configurations de visualisation.

Exemple conceptuel :

```text
Projet "Famille"

Source
└── Famille.ged

Enrichissements
└── lieux
    ├── Wysokie → non résolu
    ├── Krasna → coordonnées validées
    └── Auschwitz → coordonnées validées

Visualisations
├── "Éventail cousinade"
└── "Carte cousinade"
```

## Propriétés conceptuelles

```text
id
name
source
genealogy
placeEnrichments
visualizationPresets
```

Le nom `Famille` n'a aucune signification particulière pour le moteur.

---

# 4. GenealogySource

`GenealogySource` décrit l'origine des données généalogiques.

Pour les premières versions :

```text
type = GEDCOM
```

Propriétés envisagées :

```text
filename
gedcomVersion
importDate
fingerprint
```

`fingerprint` pourra permettre de déterminer si le fichier source a changé
depuis le dernier import.

Le fichier source ne doit jamais être modifié par Genealogy Web.

---

# 5. Genealogy

`Genealogy` représente le modèle généalogique obtenu après parsing.

```text
Genealogy
├── persons
├── families
├── events
├── places
└── media
```

Ce modèle peut être reconstruit à partir du GEDCOM.

Il ne constitue donc pas nécessairement une donnée persistante.

---

# 6. Person

`Person` représente une personne généalogique unique.

## Identité

```text
id
givenNames
surname
sex
```

`id` correspond initialement à l'identifiant GEDCOM.

Il ne doit pas être utilisé comme numéro Sosa.

## Relations

Une personne peut être :

```text
enfant de 0 ou 1 famille parentale
membre de 0 à N familles comme conjoint
parent de 0 à N enfants
```

Le modèle doit supporter plusieurs unions.

## Événements

Une personne peut posséder plusieurs événements.

Exemples :

```text
BIRTH
BAPTISM
DEATH
BURIAL
CREMATION
RESIDENCE
OCCUPATION
...
```

Les événements ne doivent pas être transformés directement en propriétés
graphiques.

---

# 7. Family

`Family` représente une relation familiale telle qu'elle est exprimée dans
le GEDCOM.

Propriétés conceptuelles :

```text
id
partners
children
events
```

Une famille peut contenir notamment un événement de mariage.

Le modèle ne doit pas supposer qu'une personne ne possède qu'une seule famille.

---

# 8. Event

`Event` représente un fait généalogique datable et éventuellement localisable.

## Propriétés

```text
id
type
date
place
participants
source
```

Exemples :

```text
Birth
Death
Marriage
Burial
Residence
```

Le même modèle d'événement doit être exploitable par :

- l'éventail ;
- l'arbre ;
- les cartes ;
- les statistiques ;
- les exports.

---

# 9. GenealogyDate

Une date généalogique ne doit pas être représentée uniquement par une date
calendaire classique.

Elle doit pouvoir conserver la précision et les qualificatifs du GEDCOM.

Exemples :

```text
25 JAN 1910
JAN 1910
1910
ABT 1910
BEF 1910
AFT 1910
BET 1908 AND 1910
```

Propriétés conceptuelles possibles :

```text
originalValue
qualifier
year
month
day
endYear
endMonth
endDay
precision
```

Le texte original doit pouvoir être conservé.

L'application ne doit jamais inventer une précision absente du GEDCOM.

---

# 10. Place

`Place` représente un lieu tel qu'il apparaît dans les données généalogiques.

La notion de lieu doit être indépendante de sa géolocalisation.

## Propriétés minimales

```text
id
originalLabel
```

Exemple :

```text
originalLabel =
"Krasna, powiat de Końskie, gouvernement de Radom, Pologne"
```

Le libellé original doit toujours pouvoir être retrouvé.

---

# 11. PlaceEnrichment

`PlaceEnrichment` représente les informations ajoutées par Genealogy Web
à un lieu provenant du GEDCOM.

Ces informations ne modifient pas le `Place` original.

## Propriétés envisagées

```text
placeId
normalizedLabel
latitude
longitude
status
source
confidence
comment
```

## Statuts possibles

```text
UNRESOLVED
AUTOMATIC
AMBIGUOUS
MANUAL
VALIDATED
```

Exemple :

```text
Place

originalLabel:
"Wysokie, Pologne"

PlaceEnrichment

status:
AMBIGUOUS

candidates:
- Wysokie A
- Wysokie B
- Wysokie C
```

Une sélection automatique incertaine ne doit pas être présentée comme une
certitude.

---

# 12. Lieu historique et lieu moderne

Le modèle doit permettre à terme de distinguer plusieurs notions :

```text
Lieu mentionné dans la source
        │
        ├── nom historique
        ├── organisation administrative historique
        │
        ▼
Localité géographique
        │
        ├── coordonnées
        └── organisation administrative actuelle
```

Exemple :

```text
Auschwitz, Pologne
```

peut être conservé comme libellé historique de l'événement même si la
localité moderne correspond à Oświęcim.

La V0 ne doit pas tenter de résoudre automatiquement toute cette complexité.

Elle doit surtout éviter de rendre cette évolution impossible.

---

# 13. Media

`Media` représente une ressource associée à une personne, une famille ou
un événement.

Propriétés envisagées :

```text
id
type
path
title
mimeType
```

Exemples :

```text
portrait
photographie
document
blason
```

Le traitement des chemins GEDCOM vers des fichiers externes sera défini
ultérieurement.

---

# 14. Personne et occurrence graphique

Une personne généalogique et sa position dans une visualisation sont deux
concepts différents.

Cette distinction est essentielle pour les implexes.

Exemple :

```text
Person P123
Jean DUPONT

          ┌── AncestorOccurrence S42
P123 ─────┤
          └── AncestorOccurrence S58
```

Il n'existe qu'une seule `Person`.

Cette personne apparaît deux fois dans l'ascendance de la personne souche.

---

# 15. AncestorOccurrence

`AncestorOccurrence` représente une position dans une ascendance.

Propriétés conceptuelles :

```text
personId
sosa
generation
fatherOccurrence
motherOccurrence
```

Pour un Sosa donné :

```text
père = sosa × 2
mère = sosa × 2 + 1
```

Une occurrence peut exister sans personne connue.

Exemple :

```text
Sosa 42
personId = null
```

Cela permet de conserver correctement la structure de l'éventail même
lorsqu'un ancêtre est inconnu.

---

# 16. Implexe

Un implexe existe lorsqu'une même `Person` correspond à plusieurs
`AncestorOccurrence`.

Exemple :

```text
Person P123
├── Sosa 42
└── Sosa 58
```

Le modèle ne doit pas dupliquer `P123`.

La manière d'afficher cet implexe appartient au moteur de visualisation.

Plusieurs modes pourront être proposés :

```text
NORMAL
HIGHLIGHT
COLLAPSED
```

Le mode exact n'est pas encore spécifié.

---

# 17. VisualizationPreset

`VisualizationPreset` représente une configuration de visualisation
réutilisable.

Il ne contient pas les données généalogiques elles-mêmes.

Propriétés communes envisagées :

```text
id
name
type
rootPersonId
```

Exemples :

```text
"Éventail cousinade"
"Carte des origines"
"Arbre complet"
```

---

# 18. FanChartPreset

Configuration d'un éventail.

Propriétés envisagées :

```text
rootPersonId
generations
openingAngle
showUnknownAncestors
labelTemplate
titleTemplate
colorMode
referencePlace
legendSize
paperSize
orientation
```

Exemple :

```text
name              = "Éventail cousinade"
generations       = 8
paperSize         = A0
orientation       = LANDSCAPE
colorMode         = GEOGRAPHIC
legendSize        = 20
```

---

# 19. MapPreset

Configuration d'une carte.

Propriétés envisagées :

```text
scope
eventTypes
colorMode
autoBounds
detailMap
legend
paperSize
orientation
```

L'emprise géographique doit être calculable automatiquement.

Une emprise enregistrée manuellement pourra éventuellement être conservée
dans le preset.

---

# 20. TreePreset

Configuration d'un arbre combiné.

Propriétés envisagées :

```text
rootPersonId
ancestorGenerations
descendantGenerations
showSiblings
showPortraits
showGenerationScale
paperSize
orientation
```

---

# 21. Couleur géographique

La couleur géographique appartient à un service commun et non à une
visualisation particulière.

Conceptuellement :

```text
Place
  +
PlaceEnrichment
  +
ColorConfiguration
        |
        v
     Color
```

Le même résultat doit pouvoir être utilisé par :

```text
FanChart
Map
Legend
Tree
```

Le calcul exact sera défini dans l'architecture technique.

---

# 22. Données dérivées

Certaines informations peuvent être calculées à partir du modèle sans être
stockées dans le GEDCOM.

Exemples :

```text
numéro Sosa
génération
âge au décès
distance entre deux lieux
orientation géographique
fréquence d'un lieu
emprise cartographique
```

Ces données sont considérées comme dérivées.

Elles doivent pouvoir être recalculées.

---

# 23. Données persistantes et données reconstructibles

Le modèle distingue trois catégories.

## Source

```text
GEDCOM
```

Source généalogique de référence.

## Reconstructible

```text
Person
Family
Event
Place
AncestorOccurrence
statistiques
```

Ces données peuvent être reconstruites depuis le GEDCOM.

## Propre à Genealogy Web

```text
PlaceEnrichment
VisualizationPreset
préférences
corrections manuelles
```

Ces données doivent pouvoir être conservées indépendamment du GEDCOM.

---

# 24. Persistance

Le modèle métier ne présuppose aucune technologie de stockage.

Les premières versions pourront utiliser par exemple :

```text
JSON
```

Une évolution vers :

```text
SQLite
```

doit être possible sans modifier les concepts métier.

Aucun serveur SQL n'est requis par le modèle.

---

# 25. Réimport du GEDCOM

Un projet doit pouvoir recevoir une nouvelle version de son GEDCOM.

Exemple :

```text
Famille_10h00.ged
        |
        v
Projet
        |
Famille_14h00.ged
```

Le réimport doit reconstruire les données généalogiques tout en essayant de
préserver :

```text
PlaceEnrichment
VisualizationPreset
préférences
```

Cette fonctionnalité nécessite une stratégie d'identification stable des
objets.

---

# 26. Identifiants et stabilité

Les identifiants GEDCOM peuvent être utilisés pendant une session d'import.

Cependant, le modèle ne doit pas supposer sans vérification qu'un identifiant
GEDCOM est stable entre deux exports provenant de logiciels différents ou
entre toutes les opérations possibles.

La stratégie de rapprochement lors d'un réimport devra être spécifiée
séparément.

---

# 27. Invariants métier

Les invariants suivants doivent être respectés.

### INV-001

Une `Person` représente une personne, indépendamment du nombre de fois où
elle apparaît dans une visualisation.

### INV-002

Un numéro Sosa appartient à une occurrence d'ascendance et non à une personne.

### INV-003

Le libellé original d'un lieu provenant du GEDCOM n'est jamais perdu.

### INV-004

Un enrichissement géographique ne modifie pas les données généalogiques
sources.

### INV-005

Une visualisation ne doit pas modifier le modèle généalogique.

### INV-006

Une donnée reconstructible ne doit pas devenir indispensable à la restauration
d'un projet.

### INV-007

Une ambiguïté géographique doit pouvoir rester non résolue.

### INV-008

L'absence d'une date, d'un parent ou d'un lieu est une information valide et
ne constitue pas nécessairement une erreur.

---

# 28. Exemple conceptuel

```text
GenealogyProject
│
│ name = "Famille"
│
├── GenealogySource
│     filename = Famille.ged
│
├── Genealogy
│   │
│   ├── Person P1
│   │     David EXEMPLE
│   │
│   ├── Person P2
│   │     ...
│   │
│   ├── Event E1
│   │     type = BIRTH
│   │     person = P2
│   │     place = PL1
│   │
│   └── Place PL1
│         originalLabel =
│         "Krasna, powiat de Końskie, gouvernement de Radom, Pologne"
│
├── PlaceEnrichment
│     place = PL1
│     latitude = ...
│     longitude = ...
│     status = VALIDATED
│
└── FanChartPreset
      name = "Cousinade"
      rootPerson = P1
      generations = 8
      paperSize = A0
      orientation = LANDSCAPE
```

---

# 29. Hors du modèle métier

Les éléments suivants ne doivent pas contaminer le modèle métier :

```text
coordonnées SVG
rayon d'un secteur
position d'une boîte
niveau de zoom navigateur
élément DOM
couleur CSS
URL HTTP
composant d'interface
bibliothèque PDF
```

Ils appartiennent aux couches de présentation ou d'infrastructure.

---

# 30. Questions ouvertes

## DM-Q01 — Identité entre deux imports

Comment reconnaître de manière fiable qu'une personne du nouveau GEDCOM
correspond à une personne du précédent import ?

---

## DM-Q02 — Lieux équivalents

Comment déterminer que :

```text
Ecully
Écully
Écully, 69081, Rhône, Auvergne-Rhône-Alpes, France
```

désignent le même lieu sans détruire les libellés originaux ?

---

## DM-Q03 — Événements personnalisés

Comment représenter les événements GEDCOM non standards ou spécifiques à
certains logiciels ?

---

## DM-Q04 — Sources

Quel niveau de détail du système de sources GEDCOM doit être intégré au
modèle initial ?

---

## DM-Q05 — Adoption et relations non biologiques

Le modèle devra-t-il distinguer dès V0 :

```text
biologique
adoption
reconnaissance
tutelle
autres relations
```

ou cette distinction peut-elle être introduite ultérieurement ?

---

## DM-Q06 — Confidentialité

La notion de personne vivante et les règles de masquage doivent-elles faire
partie du modèle métier ou uniquement d'une politique de présentation ?

---

# 31. Principe directeur

Le modèle doit permettre de répondre à la question :

> « Que savons-nous de la généalogie ? »

sans dépendre de la question :

> « Comment allons-nous la dessiner ? »

Cette séparation constitue l'un des principes fondamentaux de la nouvelle
application.
