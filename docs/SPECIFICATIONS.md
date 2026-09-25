# Genealogy Web — Spécifications fonctionnelles

**Version :** 0.1  
**Statut :** brouillon de conception  
**Objet :** application générique de visualisation et d'édition graphique de données généalogiques issues d'un fichier GEDCOM.

---

# 1. Objectif

Genealogy Web est une application web permettant d'importer un fichier
GEDCOM et de produire des visualisations généalogiques interactives et
des documents de haute qualité destinés notamment à l'impression grand format.

L'application doit notamment permettre :

- l'exploration d'une généalogie ;
- la génération d'un éventail d'ascendance ;
- la génération d'un arbre combinant ascendance et descendance ;
- la représentation géographique des événements généalogiques ;
- la production de documents SVG, PDF et PNG ;
- l'impression sur des formats allant notamment jusqu'au A0.

Genealogy Web est un outil de visualisation.

Il ne constitue pas un logiciel de saisie généalogique et ne doit pas modifier
la source généalogique.

---

# 2. Principes structurants

## GEN-001 — Indépendance vis-à-vis de GeneWeb

L'application doit fonctionner à partir d'un fichier GEDCOM standard.

GeneWeb peut être utilisé comme producteur du GEDCOM, mais ne doit pas être
une dépendance fonctionnelle de l'application.

### Critères d'acceptation

- un GEDCOM provenant de GeneWeb peut être utilisé ;
- un GEDCOM provenant d'un autre logiciel peut être utilisé sous réserve
  de compatibilité avec les formats GEDCOM supportés ;
- aucune connexion à une base GeneWeb n'est nécessaire pour afficher
  une généalogie.

---

## GEN-002 — Lecture seule

L'application ne doit jamais modifier le fichier GEDCOM source ni la base
généalogique ayant servi à le produire.

### Critères d'acceptation

- l'import GEDCOM est en lecture seule ;
- les transformations internes n'altèrent pas le fichier source ;
- aucun mécanisme de mise à jour de GeneWeb n'est requis.

---

## GEN-003 — Absence de règles spécifiques à une généalogie

Le moteur ne doit contenir aucune constante fonctionnelle spécifique à une
famille ou un fichier GEDCOM particulier.

Sont notamment interdits dans le moteur :

- nom de personne particulier ;
- nom de famille particulier ;
- ville de référence codée en dur ;
- coordonnées cartographiques propres à une généalogie ;
- nom de fichier GEDCOM imposé ;
- palette construite explicitement pour un jeu de données particulier.

Ces éléments doivent être soit calculés, soit configurables.

---

# 3. Architecture fonctionnelle

L'application doit respecter la séparation logique suivante :

```text
GEDCOM
   |
   v
Import / parsing
   |
   v
Modèle généalogique normalisé
   |
   +----------------+----------------+
   |                |                |
   v                v                v
Éventail          Arbre             Carte
   |                |                |
   +----------------+----------------+
                    |
                    v
             Moteur d'export
              SVG/PDF/PNG
```

Le parsing GEDCOM, le modèle généalogique, la représentation graphique et
l'export doivent rester découplés.

---

# 4. Import GEDCOM

## GED-001 — Chargement d'un GEDCOM

L'utilisateur doit pouvoir sélectionner et charger un fichier GEDCOM.

### Priorité

V0

### Critères d'acceptation

- sélection d'un fichier `.ged` depuis l'interface ;
- lecture du fichier sans modification ;
- affichage d'un résultat d'import ;
- le nom physique du fichier n'est pas imposé.

---

## GED-002 — Formats supportés

La première version doit cibler au minimum les GEDCOM 5.5 et 5.5.1.

Le support d'autres versions doit pouvoir être ajouté ultérieurement sans
modifier le modèle fonctionnel de l'application.

### Priorité

V0

---

## GED-003 — Individus

L'import doit construire un modèle des individus.

Les informations suivantes doivent être reconnues lorsqu'elles sont présentes :

- identifiant GEDCOM ;
- prénom(s) ;
- nom ;
- sexe ;
- naissance ;
- baptême ;
- décès ;
- inhumation ou crémation ;
- relations familiales ;
- médias ou portraits lorsque disponibles.

### Priorité

V0

---

## GED-004 — Familles

L'import doit reconnaître les familles et leurs relations :

- conjoint 1 ;
- conjoint 2 ;
- enfants ;
- mariage et événements familiaux associés.

### Priorité

V0

---

## GED-005 — Événements

Le modèle interne doit représenter les événements indépendamment de leur
utilisation graphique.

Un événement peut notamment comporter :

```text
type
date
lieu
source
personne(s) concernée(s)
```

### Priorité

V0

---

## GED-006 — Lieux

Les lieux rencontrés dans le GEDCOM doivent être recensés sans altération
du libellé d'origine.

Le modèle doit permettre ultérieurement d'associer au lieu :

- un libellé normalisé ;
- une latitude ;
- une longitude ;
- un statut de géocodage.

### Priorité

V0 pour le recensement  
V2 pour le géocodage

---

## GED-007 — Dates incomplètes

Le modèle doit conserver les informations partielles présentes dans le GEDCOM.

Exemples :

```text
1884
MAR 1884
ABT 1884
BEF 1884
```

Une date inconnue ne doit pas être artificiellement complétée.

### Priorité

V0

---

## GED-008 — Rapport d'import

Après import, l'application doit présenter un bilan synthétique.

Exemple :

```text
Individus             428
Familles              173
Lieux distincts        96
Événements           1214
Lieux géolocalisés     59
Lieux non résolus      37
```

Les avertissements de parsing doivent être accessibles.

### Priorité

V0

---

# 5. Personne de référence

## ROOT-001 — Sélection

L'utilisateur doit pouvoir sélectionner une personne de référence parmi
les individus importés.

### Priorité

V0

### Critères d'acceptation

La recherche doit pouvoir utiliser au minimum :

- prénom ;
- nom ;
- année de naissance lorsque connue.

Deux homonymes doivent pouvoir être distingués.

---

## ROOT-002 — Changement de personne

La personne de référence doit pouvoir être changée sans réimporter le GEDCOM.

### Priorité

V0

---

# 6. Éventail d'ascendance

## FAN-001 — Génération de l'ascendance

L'application doit pouvoir calculer l'ascendance de la personne de référence.

### Priorité

V1

---

## FAN-002 — Numérotation Sosa

La position d'un ancêtre dans l'éventail doit suivre la structure Sosa-Stradonitz.

Les ancêtres inconnus ne doivent pas provoquer de décalage des autres branches.

### Priorité

V1

---

## FAN-003 — Nombre de générations

Le nombre de générations affichées doit être configurable.

### Priorité

V1

### Critères d'acceptation

- minimum fonctionnel : 1 génération ;
- maximum cible initial : au moins 10 générations ;
- changement possible sans réimport GEDCOM ;
- export conforme au nombre de générations sélectionné.

---

## FAN-004 — Ancêtres inconnus

L'utilisateur doit pouvoir choisir entre :

- afficher les secteurs correspondant aux ancêtres inconnus ;
- masquer visuellement ces secteurs.

La structure Sosa reste inchangée.

### Priorité

V1

---

## FAN-005 — Ouverture / compression de l'éventail

L'ouverture angulaire de l'éventail doit être configurable.

Le système doit permettre des représentations allant d'un éventail compact
à une représentation circulaire ou quasi circulaire.

### Priorité

V1

---

## FAN-006 — Contenu d'un secteur

Le contenu textuel affiché pour un individu doit être configurable.

Les données disponibles doivent notamment pouvoir inclure :

- prénom ;
- nom ;
- année ou date de naissance ;
- lieu de naissance ;
- année ou date de décès ;
- lieu de décès ;
- numéro Sosa.

### Priorité

V1

---

## FAN-007 — Titre

Le titre de la visualisation doit être configurable et pouvoir utiliser
des variables.

Exemple :

```text
Ascendance de {nom}
{generations} générations
```

### Priorité

V1

---

## FAN-008 — Lisibilité

La taille, l'orientation et la disposition du texte doivent s'adapter autant
que possible à l'espace disponible dans chaque secteur.

La visualisation doit rester exploitable pour une impression grand format.

### Priorité

V1

---

# 7. Coloration géographique

## COLOR-001 — Couleur d'un lieu

Un même lieu doit recevoir une couleur cohérente dans toutes les
visualisations.

### Priorité

V1

---

## COLOR-002 — Référence géographique

Le calcul géographique des couleurs ne doit pas utiliser de ville codée
en dur.

Le lieu de référence doit pouvoir être déterminé par configuration.

Options envisagées :

- lieu associé à la personne souche ;
- lieu sélectionné manuellement ;
- centre géographique calculé à partir des lieux connus.

### Priorité

V1

---

## COLOR-003 — Cohérence inter-modules

La couleur d'un lieu doit être identique dans :

- l'éventail ;
- la légende ;
- les cartes ;
- toute autre visualisation utilisant la dimension géographique.

### Priorité

V1

---

## COLOR-004 — Mode sans géographie

Les visualisations doivent fonctionner même lorsqu'aucune coordonnée
géographique n'est disponible.

### Priorité

V1

---

# 8. Légende

## LEG-001 — Lieux représentés

Une légende doit pouvoir afficher les lieux les plus représentés dans
la visualisation courante.

### Priorité

V1

---

## LEG-002 — Nombre d'éléments

Le nombre maximal de lieux affichés dans la légende doit être configurable.

### Priorité

V1

---

## LEG-003 — Fréquence

La légende doit pouvoir afficher le nombre d'individus ou d'événements
associés au lieu.

### Priorité

V1

---

# 9. Géographie et géocodage

## GEO-001 — Modèle de lieu

Le modèle interne d'un lieu doit pouvoir contenir :

```text
libellé GEDCOM original
libellé normalisé
latitude
longitude
statut
source du géocodage
```

### Priorité

V2

---

## GEO-002 — Cache de géocodage

Un lieu déjà géocodé doit pouvoir être réutilisé sans nouvelle requête
au service de géocodage.

### Priorité

V2

---

## GEO-003 — Ambiguïtés

Un lieu ambigu doit pouvoir être signalé à l'utilisateur.

Exemple :

```text
Wysokie, Pologne
```

L'application ne doit pas sélectionner silencieusement une localité
lorsque plusieurs correspondances plausibles existent.

### Priorité

V2

---

## GEO-004 — Correction manuelle

L'utilisateur doit pouvoir associer manuellement des coordonnées à un lieu
non résolu ou ambigu.

Cette correction doit pouvoir être conservée dans le cache.

### Priorité

V2

---

## GEO-005 — Carte générale

Une carte doit permettre de représenter les lieux associés à la généalogie
ou à la sélection courante.

### Priorité

V2

---

## GEO-006 — Emprise automatique

La carte doit déterminer automatiquement une emprise pertinente à partir
des points affichés.

Aucun centre ou niveau de zoom spécifique à une généalogie ne doit être
codé en dur.

### Priorité

V2

---

## GEO-007 — Carte détaillée

Le système doit permettre d'afficher une carte détaillée ou un encart
complémentaire lorsqu'une zone contient une forte concentration de lieux.

### Priorité

V2

---

# 10. Arbre combiné

## TREE-001 — Ascendance et descendance

Une visualisation distincte de l'éventail doit permettre d'afficher autour
d'une personne de référence :

- son ascendance ;
- sa ou ses familles ;
- sa descendance.

### Priorité

V3

---

## TREE-002 — Profondeurs indépendantes

Les profondeurs ascendante et descendante doivent être configurables
indépendamment.

### Priorité

V3

### Cible initiale

```text
Ascendance : 1 à 10 générations
Descendance : 0 à 10 générations
```

---

## TREE-003 — Pan et zoom

L'arbre doit être navigable par déplacement et zoom.

### Priorité

V3

---

## TREE-004 — Portraits

Lorsqu'un portrait exploitable est associé à une personne, il doit pouvoir
être affiché.

En son absence, l'interface peut utiliser une représentation générique.

### Priorité

V3

---

## TREE-005 — Échelle générationnelle

L'utilisateur doit pouvoir afficher ou masquer une échelle indiquant
les générations.

### Priorité

V3

---

## TREE-006 — Unions multiples

Le modèle et la visualisation doivent pouvoir représenter plusieurs unions.

La représentation graphique exacte reste à spécifier.

### Priorité

V3

---

# 11. Interactivité

## UI-001 — Zoom

Les grandes visualisations doivent pouvoir être zoomées sans perte de qualité
du contenu vectoriel.

---

## UI-002 — Déplacement

Les visualisations dépassant la surface d'affichage doivent pouvoir être
déplacées par l'utilisateur.

---

## UI-003 — Survol

Le survol d'un élément graphique doit pouvoir afficher des informations
complémentaires sans surcharger le document imprimé.

---

## UI-004 — Sélection

Une personne ou un lieu doit pouvoir devenir une sélection active.

Les différents modules pourront ultérieurement réagir à cette sélection.

---

# 12. Export

## EXP-001 — SVG

Les visualisations vectorielles doivent pouvoir être exportées en SVG.

### Priorité

V1

---

## EXP-002 — PDF

Les visualisations doivent pouvoir être exportées en PDF.

### Priorité

V1

---

## EXP-003 — PNG

Une exportation PNG doit être disponible pour les usages ne nécessitant
pas de vectoriel.

### Priorité

V1

---

## EXP-004 — Formats papier

L'export PDF doit prendre en charge au minimum :

```text
A0
A1
A2
A3
A4
```

### Priorité

V1

---

## EXP-005 — Orientation

L'utilisateur doit pouvoir choisir :

```text
Portrait
Paysage
```

### Priorité

V1

---

## EXP-006 — Vectoriel

Les arbres, textes, formes et traits doivent rester vectoriels dans le PDF
lorsque cela est techniquement possible.

Les images intégrées peuvent rester matricielles.

### Priorité

V1

---

## EXP-007 — Fidélité

Le document exporté doit reproduire les paramètres de la visualisation :

- nombre de générations ;
- couleurs ;
- libellés ;
- légende ;
- orientation ;
- portraits lorsque applicables.

---

# 13. Paramétrage

Les paramètres doivent être séparés en trois catégories.

## Paramètres utilisateur

Exemples :

```text
personne souche
nombre de générations
affichage des ancêtres inconnus
contenu des libellés
mode de coloration
lieu de référence
légende
format papier
orientation
```

## Paramètres avancés

Exemples :

```text
espacement
taille de police
densité graphique
dimensions
nombre maximal de labels
```

## Paramètres internes

Seules les constantes purement techniques doivent rester codées dans
l'application.

---

# 14. Persistance des paramètres

## CFG-001 — Configuration de visualisation

L'application doit à terme permettre de conserver une configuration de
visualisation indépendamment du GEDCOM.

Exemple :

```text
Éventail 8 générations
A0 paysage
couleurs géographiques
20 lieux dans la légende
affichage ville + années
```

### Priorité

À préciser.

---

## CFG-002 — Reproductibilité

À GEDCOM identique et configuration identique, l'application doit pouvoir
reproduire le même document.

Cette exigence est particulièrement importante pour les exports destinés
à l'impression.

---

# 15. Performance

## PERF-001

L'import et les visualisations doivent rester utilisables avec une généalogie
de plusieurs milliers d'individus.

Les objectifs chiffrés seront définis après mesure sur plusieurs GEDCOM.

---

## PERF-002

Le nombre total d'individus du GEDCOM ne doit pas imposer de construire
toutes les visualisations en mémoire simultanément.

---

# 16. Vie privée

## PRIV-001

Un GEDCOM chargé manuellement ne doit pas être publié ou transmis à un service
tiers sans action explicite de l'utilisateur.

---

## PRIV-002

Le géocodage constitue un cas particulier : si un service externe est utilisé,
l'utilisateur doit pouvoir identifier quelles informations lui sont envoyées.

---

## PRIV-003

Les GEDCOM de développement et de production ne doivent pas être versionnés
dans Git.

---

# 17. Périmètre explicitement exclu des premières versions

Ne font pas partie du périmètre initial :

- édition d'une personne ;
- création ou suppression d'une famille ;
- écriture dans GeneWeb ;
- export d'un GEDCOM modifié ;
- application mobile native ;
- collaboration multi-utilisateurs ;
- gestion avancée des droits ;
- remplacement d'un logiciel de généalogie ;
- résolution automatique certaine de tous les lieux historiques.

---

# 18. Roadmap fonctionnelle

## V0 — Socle

Objectif : démontrer que n'importe quel GEDCOM compatible peut être transformé
en un modèle généalogique exploitable.

Contenu :

- import GEDCOM ;
- parsing ;
- modèle Person / Family / Event / Place ;
- rapport d'import ;
- recherche d'individus ;
- choix de la personne souche ;
- inspection de son ascendance sous forme textuelle/debug.

Aucune visualisation complexe n'est nécessaire pour valider V0.

---

## V1 — Éventail

Objectif : produire un premier résultat réellement utilisable et imprimable.

Contenu :

- éventail Sosa ;
- 1 à 10 générations ;
- ancêtres inconnus ;
- compression/ouverture ;
- libellés configurables ;
- couleurs ;
- légende ;
- SVG ;
- PDF A0 à A4 ;
- PNG.

---

## V2 — Géographie

Objectif : ajouter la dimension spatiale.

Contenu :

- extraction des lieux ;
- cache de géocodage ;
- résolution des ambiguïtés ;
- corrections manuelles ;
- carte générale ;
- carte détaillée ;
- couleurs communes carte/éventail ;
- export cartographique.

---

## V3 — Arbre combiné

Objectif : généraliser les visualisations généalogiques.

Contenu :

- ascendance ;
- unions ;
- fratries lorsque pertinentes ;
- descendance ;
- profondeurs indépendantes ;
- portraits ;
- échelle générationnelle ;
- pan/zoom ;
- export grand format.

---

# 19. Questions ouvertes

Les points suivants doivent être décidés avant ou pendant les versions concernées.

## Q-001 — Implexes

Comment représenter graphiquement un ancêtre apparaissant plusieurs fois dans
l'ascendance ?

Possibilités :

- répéter la personne dans chaque position Sosa ;
- identifier visuellement les répétitions ;
- proposer un mode condensé.

---

## Q-002 — Lieux historiques

Doit-on distinguer :

```text
lieu tel qu'écrit dans le GEDCOM
lieu historique
lieu administratif actuel
coordonnées modernes
```

Le modèle doit au minimum permettre cette évolution sans perdre le libellé
GEDCOM original.

---

## Q-003 — Géocodage

Quel service ou référentiel utiliser ?

Contraintes :

- qualité France ;
- qualité Europe centrale/Pologne ;
- gestion des lieux historiques ;
- limites d'utilisation ;
- confidentialité ;
- possibilité de cache local.

---

## Q-004 — Médias GEDCOM

Comment résoudre les chemins de médias lorsque le GEDCOM référence des fichiers
externes ?

---

## Q-005 — Plusieurs unions

Quelle représentation adopter dans l'arbre combiné lorsqu'une personne a
plusieurs conjoints et plusieurs descendances ?

---

## Q-006 — Individus vivants

Faut-il proposer un mode de confidentialité masquant automatiquement certaines
informations concernant les personnes vivantes ?

---

## Q-007 — Configuration

Sous quelle forme sauvegarder les configurations utilisateur ?

Possibilités envisagées :

- JSON ;
- stockage navigateur ;
- configuration côté serveur.

La décision est différée jusqu'à la conception technique.

---

## Q-008 — Automatisation GeneWeb

Le mode serveur pourra-t-il automatiquement utiliser le dernier GEDCOM généré
par GeneWeb tout en conservant le mode générique d'upload manuel ?

Cette fonction ne doit pas créer de dépendance du cœur de l'application envers
GeneWeb.

---

# 20. Références legacy

Les anciennes applications ayant servi à produire les arbres et cartes
familiales doivent être conservées comme références fonctionnelles et visuelles.

Elles ne constituent pas la base de code du nouveau produit.

Les éléments à préserver sont notamment :

- logique générale de l'éventail ;
- impression grand format ;
- coloration géographique ;
- légende des lieux ;
- cartographie ;
- arbre ascendant/descendant ;
- portraits ;
- interaction pan/zoom.

Les éléments à ne pas reproduire sont notamment :

- coordonnées codées en dur ;
- lieu de référence codé en dur ;
- noms de fichiers imposés ;
- paramètres spécifiques à une famille ;
- duplication des règles entre plusieurs pages ;
- mélange parsing / modèle / rendu / export ;
- valeurs de mise en page disséminées dans le code.

---

# 21. Critère de réussite global

À terme, un utilisateur ne connaissant rien de la généalogie ayant servi au
développement doit pouvoir :

1. fournir son propre GEDCOM ;
2. choisir une personne ;
3. sélectionner une visualisation ;
4. régler les principaux paramètres ;
5. obtenir un résultat interactif ;
6. exporter un document haute définition ;
7. obtenir un résultat exploitable pour une impression grand format ;

sans modifier une ligne de code.
