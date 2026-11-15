# Exigences du projet

**État d’implémentation :** le prototype fournit NASA POWER quotidien, trois saisies de rotations, une démonstration fictive, des exports et une ETc conditionnelle aux métadonnées. Les contrôles v2 séparent déclarations, complétude, calcul et validation agronomique ; ils empêchent les comparaisons quantitatives de totaux incomplets. Les critères de validation agronomique locale restent ouverts. Les mentions de phase 1 ci-dessous décrivent le périmètre initial.

## Périmètre et utilisateurs

Zone cible : Beni Mellal–Afourer, Maroc. Utilisateur principal : agriculteur ; utilisateurs secondaires : conseiller agricole et équipe de validation scientifique. L’interface initiale sera en français. Les besoins linguistiques supplémentaires, la connectivité et les équipements disponibles restent à recueillir.

La phase 1 produit une définition vérifiable du projet. Elle exclut l’acquisition de données, la fixation de références agronomiques non vérifiées et le développement de l’application complète.

## Exigences fonctionnelles

| ID | Exigence | Critère d’acceptation futur |
|---|---|---|
| F01 | Saisir l’exploitation et sa localisation | Coordonnées ou géométrie validées, surface et unités explicites ; absence de localisation bloquante pour les analyses spatiales. |
| F02 | Recueillir l’historique et la rotation actuelle | Cultures, successions, dates/saisons et pratiques saisis ou confirmés par l’agriculteur ; aucun préremplissage présenté comme son historique. |
| F03 | Décrire le sol | Profondeur, texture, drainage, salinité et résultats d’analyse si disponibles ; valeur inconnue distincte de zéro ; provenance et date conservées. |
| F04 | Recueillir l’eau et les contraintes | Mode d’irrigation, disponibilité et calendrier, restrictions, matériel, main-d’œuvre, débouchés et contraintes culturales documentés. |
| F05 | Recueillir les priorités | Priorités explicites et modifiables : eau, risque, sol, production ou économie ; aucun poids caché. |
| F06 | Comparer au moins trois stratégies | Rotation actuelle et au moins deux alternatives évaluées sur un horizon commun ; hypothèses et calendrier affichés. |
| F07 | Contrôler la faisabilité | Chaque contrainte a un état satisfait, incompatible ou inconnu, accompagné de sa justification et de sa source. |
| F08 | Expliquer chaque stratégie | Motifs, preuves, bénéfices potentiels, risques, incertitudes et données manquantes visibles au même endroit. |
| F09 | Visualiser les résultats | Graphiques avec unités, périodes, couverture, origine et limites spatiales ; données manquantes visibles. |
| F10 | Restituer un résultat reproductible | Entrées, versions des références, paramètres, dates d’accès et méthodes identifiables dans le résultat. |

Si deux alternatives admissibles ne peuvent pas être établies, afficher l’insuffisance et les informations nécessaires. Ne jamais fabriquer une troisième stratégie ni assouplir silencieusement une contrainte. La rotation actuelle reste un scénario de référence même si elle présente des incompatibilités ; sa présence n’est pas une approbation agronomique.

## Exigences scientifiques

| ID | Exigence | Vérification attendue |
|---|---|---|
| S01 | Aucune observation NASA inventée | Toute valeur attribuée à NASA renvoie à une source, une requête, une période et un contrôle qualité. |
| S02 | Distinguer les types d’information | Observation in situ, estimation satellitaire, donnée modélisée, déclaration agricole, référence bibliographique et résultat calculé sont étiquetés séparément. |
| S03 | Vérifier la pertinence géographique | Couverture du Maroc démontrée ; SSURGO, WSS, PRISM et Cropland Data Layer exclus de la caractérisation directe des parcelles marocaines. |
| S04 | Documenter les échelles et unités | Produit/version, variable, unités, résolution native, grille, fréquence native, agrégation et période disponibles. |
| S05 | Limiter les intégrations | Chaque source résout un besoin identifié et apporte une information utile ; redondances justifiées. |
| S06 | Éviter tout score arbitraire | Aucun score global par défaut ; toute métrique ou éventuelle normalisation possède formule, paramètres, référence et domaine de validité. |
| S07 | Vérifier les contraintes avant proposition | Contrôles du calendrier, de l’eau, du sol, des successions et des contraintes de l’exploitation ; inconnues critiques bloquantes. |
| S08 | Qualifier les incertitudes | Couverture insuffisante, données manquantes, extrapolations et limites de transfert aux parcelles visibles. |
| S09 | Référencer les valeurs agricoles | Coefficients culturaux, seuils et calendriers proviennent de références applicables et revues ; aucune valeur générique inventée. |
| S10 | Limiter les conclusions | Besoin en eau ne vaut pas rendement ; satellite ne vaut pas analyse de sol ; climat historique ne vaut pas prévision. |

## Exigences utilisateur et qualité

- Français compréhensible, unités explicites, formulaires progressifs et possibilité de répondre « inconnu ».
- Expliquer les effets d’une entrée manquante et proposer une information concrète à recueillir.
- Respecter les priorités choisies sans masquer les compromis ni les incompatibilités.
- Signaler les échecs d’accès aux sources et les caches périmés ; aucun remplacement silencieux par des données synthétiques.
- Éviter la publication des coordonnées et données d’exploitation ; définir consentement, conservation et accès avant toute persistance utilisateur.
- Rendre les calculs testables sans interface et sans réseau ; isoler les secrets d’accès du code.
- Définir les objectifs de performance et d’accessibilité avec les utilisateurs avant validation de l’interface.

## Checklist de conformité au défi

Cette grille reflète le cahier des charges fourni. Elle ne constitue pas une certification des règles officielles de l’édition du défi.

- [x] Objectif d’adaptation agricole et zone cible documentés.
- [x] Comparaison de trois stratégies incluant la rotation actuelle spécifiée.
- [x] Données NASA, informations locales, sol, cultures et priorités prévus.
- [x] Explicabilité, contraintes et incertitude exigées.
- [x] Sources inadaptées aux fermes marocaines explicitement exclues.
- [x] Interdiction de données inventées et de scores arbitraires documentée.
- [ ] Édition, page officielle, ressources imposées et livrables du défi vérifiés en phase 2.
- [ ] Sources et références validées ; accès autorisé et licences confirmées.
- [ ] Acquisition, calculs et comparaison implémentés et testés.
- [ ] Validation locale avec expertise agronomique et utilisateurs réalisée.

## Informations encore nécessaires

Édition et URL officielle du défi ; parcelles et surfaces ; historique et rotation actuelle ; cultures envisageables ; horizon de comparaison ; analyses de sol ; calendrier et volumes d’eau ; pratiques et matériel ; priorités ; contraintes économiques ; références agronomiques locales ; interlocuteur de validation. Aucun de ces éléments n’est déduit du seul nom de la région.
