# V1 — Points de conception et travaux à venir

Les spécifications disent *ce que le produit doit faire* ; ce fichier décrit
*ce qu'on prévoit de construire prochainement*.

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

La palette géographique V1 utilise une amplitude chromatique continue à deux
échelles et un mapping directionnel continu en OKLCH depuis une référence
explicitement configurée :

```text
A(d) = regional_amplitude
       × (1 − exp(−(d / regional_distance_km)^regional_exponent))
       + amplitude_at_reference
       × (d / reference_distance_km)^distance_exponent

target_hue = wrap(bearing + directional_hue_offset)
t = 1 − exp(−A / direction_transition_amplitude)

hue = shortest_arc_lerp(base_hue, target_hue, t)
chroma = lerp(base_chroma, directional_target_chroma, t)

a = chroma × cos(hue)
b = chroma × sin(hue)
```

Paramètres V1 par défaut :

```text
regional_amplitude = 0,12
regional_distance_km = 125
regional_exponent = 2,0

reference_distance_km = 1 000
amplitude_at_reference = 0,16
distance_exponent = 1,35

directional_hue_offset = 195°
direction_transition_amplitude = 0,10
directional_target_chroma = 0,18
lightness = 0,72
```

`directional_hue_offset` est une orientation de palette chromatique, non une
propriété géographique intrinsèque. Elle doit rester explicite et configurable.

Critère perceptuel :

```text
Lyon ↔ Bron                  quasi identiques
Noirétable ↔ Arconsat        nuances proches
Lyon ↔ Arcens                clairement différents
Lyon ↔ Bellegarde            clairement différents
régions françaises distinctes → différences perceptibles
France ↔ Pologne             très nettement différentes
lieux polonais proches       même famille chromatique
directions lointaines différentes → familles chromatiques différentes
```

La configuration ne dépend pas du jeu de données affiché. Le gamut mapping
sRGB conserve une couleur représentable sans introduire de seuil géographique.
