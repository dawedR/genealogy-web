# Legacy prototypes

Ce répertoire contient les prototypes et sorties de référence de
l'application généalogique antérieure à Genealogy Web.

Ils sont conservés uniquement comme références fonctionnelles,
algorithmiques et visuelles.

## Règles

Le contenu de `legacy/` n'est pas du code de production.

Il ne doit pas être importé ou exécuté directement par l'application
Genealogy Web.

Les prototypes peuvent être étudiés pour retrouver :

- algorithmes ;
- règles de visualisation ;
- choix de géométrie ;
- logique de coloration géographique ;
- comportements fonctionnels ;
- exemples de sorties attendues.

Toute logique reprise doit être réimplémentée dans l'architecture actuelle
et couverte par des tests.

Les dépendances, structures de données et choix techniques legacy ne sont
pas des contraintes pour la nouvelle application.

## Contenu

### fan-chart/diagrames et cartes

Prototypes HTML/JavaScript historiques :

- `index.html`
- `indexSVG.html`
- `colorie.html`
- `arbre.html`
- `map.html`


### reference-output/

Exemples de sorties historiques :

- `Fanchart_a0_landscape.pdf`
- `Arbre_A0_PAYSAGE.pdf`
- `multi_map_a2.pdf`