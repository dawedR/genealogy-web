# Genealogy Web

Application web personnelle de visualisation généalogique.

## Objectifs

GeneWeb reste la base généalogique maître.

Cette application est destinée à exploiter en lecture seule les données
exportées depuis GeneWeb afin de proposer des visualisations complémentaires.

Objectifs envisagés :

- import du GEDCOM généré automatiquement par GeneWeb ;
- visualisation d'un arbre généalogique interactif ;
- arbre ascendant en éventail ;
- navigation entre les personnes ;
- représentation cartographique des lieux ;
- exploitation géographique et temporelle des événements généalogiques ;
- interface web adaptée aux ordinateurs et appareils mobiles.

## Architecture générale

```text
GeneWeb / Famille.gwb
        |
        | gwb2ged
        v
Famille_YYYY-MM-DD_HH-MM-SS.ged
        |
        | lecture seule
        v
Genealogy Web
        |
        +-- arbre / éventail
        |
        +-- cartographie
        |
        +-- recherche / navigation
