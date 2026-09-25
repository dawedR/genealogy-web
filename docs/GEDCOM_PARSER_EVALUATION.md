# Évaluation des parseurs GEDCOM Python

**Date :** 2026-09-25  
**Statut :** décision V0

## Contexte

Trois bibliothèques Python ont été évaluées pour l'import GEDCOM de
Genealogy Web :

- `ged4py 0.5.5`
- `python-gedcom 1.1.0`
- `gedcomtools 0.6.0`

Environnement :

- Python 3.12.3
- GEDCOM GeneWeb 5.5.1 UTF-8
- 121 individus
- 49 familles
- environ 66 Ko

Une fixture artificielle a également été utilisée pour tester :

- Unicode ;
- dates partielles ;
- `ABT` ;
- `BEF` ;
- `BET ... AND ...` ;
- `FROM ... TO ...` ;
- tags personnalisés.

## ged4py

Points validés :

- lecture du GEDCOM GeneWeb 5.5.1 ;
- UTF-8 ;
- 121 individus et 49 familles ;
- noms structurés ;
- lieux ;
- pointeurs GEDCOM ;
- résolution automatique des pointeurs ;
- unions multiples ;
- navigation par chemins ;
- conservation des tags inconnus ;
- interprétation sémantique des dates.

Exemples :

```text
ABT 1901
→ DateValueAbout

BEF 1980
→ DateValueBefore

BET 1970 AND 1975
→ DateValueRange

FROM 1902 TO 1904
→ DateValuePeriod
