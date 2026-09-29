`**. Les spécifications disent *ce que le produit doit faire* ; ce fichier dira *ce qu'on prévoit de construire prochainement*. 

```markdown
# V1 — Points de conception et travaux à venir

## Libellés de l'éventail

### Politique de contenu par génération

À concevoir.

Objectif : permettre un niveau de détail différent selon la distance à la
personne souche.

Exemple initial à évaluer :

| Générations | Contenu |
|---|---|
| G0–G1 | Sosa, nom/prénoms, date + lieu de naissance, date + lieu de décès |
| G2–G3 | Sosa, nom/prénoms, dates naissance/décès |
| G4–G5 | Sosa, nom/prénoms, années naissance/décès |
| G6–G10 | nom/prénoms, années naissance/décès |

Cette table est une hypothèse de conception, pas encore une spécification
figée.

La politique par génération doit précéder la dégradation automatique
selon l'espace disponible.

### Dégradation automatique

Implémentée initialement :

1. dates GEDCOM complètes ;
2. années seules ;
3. suppression progressive des informations secondaires ;
4. abréviation des prénoms en préservant autant que possible le nom ;
5. ellipse en dernier recours.

À tester sur :
- 4 générations ;
- 6 générations ;
- 8 générations ;
- 10 générations ;
- ouvertures 180°, 240°, 270°, 360° ;
- formats d'impression futurs A4 à A0.

## Coloration géographique

La première palette OKLab utilisera une projection locale centrée sur une
référence explicitement configurée. L’échelle V1 est fixée à
`12 000 km par unité OKLab` : sur les lieux validés de Maurice, elle conserve
une famille polonaise cohérente, distingue Łódź de Kielce/Radom et garde des
variations locales discrètes. Elle ne dépend pas du jeu de données affiché.
