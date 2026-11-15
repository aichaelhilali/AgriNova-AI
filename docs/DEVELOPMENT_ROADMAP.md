# Feuille de route de développement

**Mise à jour :** le prototype comprend NASA POWER, les formulaires, la démonstration, ETc conditionnelle et ET₀ quotidienne FAO-56 avec un cas publié indépendant. Les phases ci-dessous décrivent la trajectoire initiale, pas une validation scientifique locale acquise. La pluie efficace, l’irrigation et la validation locale indépendante restent hors du périmètre actuel.

## Phases et dépendances

| Phase | Travail et livrable | Dépendances | Condition de sortie |
|---|---|---|---|
| 1. Définition | Documentation, périmètre, exigences, méthode proposée et structure du dépôt | Cahier des charges fourni | Livrables présents ; inconnues et étapes suivantes explicites |
| 2. Investigation des sources | Vérifier la page du défi et la documentation des sources ; registre sourcé de sélection/rejet | Approbation explicite après phase 1 ; édition et ressources du défi à confirmer | Sources limitées, justifiées, caractéristiques vérifiées et limites recensées ; aucun jeu de données téléchargé dans cette étape documentaire |
| 3. Saisie exploitation | Schéma des entrées, unités, provenance, champs inconnus, contraintes et priorités | Exigences phase 1 et enseignements phase 2 ; échanges utilisateurs | Schéma relu ; rotation actuelle fournie par l’agriculteur ; données critiques identifiées |
| 4. Acquisition NASA | Clients, contrôles des réponses, cache et conservation des métadonnées | Sources retenues, localisation/périodes, autorisation d’acquisition, accès et licences | Données réelles traçables ; erreurs explicites ; aucun substitut artificiel |
| 5. Analyse environnementale | Indicateurs retenus et couverture des séries | Données contrôlées de phase 4 et périodes de phase 3 | Calculs vérifiés, unités cohérentes, limites d’échelle visibles |
| 6. Cultures et sols | Références locales, paramètres et règles d’aptitude | Schéma phase 3, méthode phase 1, références examinées en phase 2 | Règles et paramètres sourcés, pertinence locale revue ; inconnues critiques définies |
| 7. Comparaison des rotations | Scénario actuel, alternatives admissibles, contraintes et compromis | Phases 5 et 6, historique et priorités de phase 3 | Comparaison explicable de trois stratégies si possible ; blocage justifié sinon |
| 8. Explications | Restitution structurée des preuves, bénéfices potentiels, risques et limites | Résultats structurés des phases 5–7 | Aucune conclusion non étayée ; liens entre motifs, règles et données |
| 9. Interface Streamlit | Formulaires français, graphiques et présentation des compromis | Schémas stabilisés, calculs et explications utilisables sans UI | Parcours compréhensible ; erreurs et inconnues visibles ; séparation UI/calculs |
| 10. Validation intégrée | Revue scientifique, tests de bout en bout et retour utilisateurs | Ensemble des modules précédents | Limites connues documentées ; validation agronomique et critères d’acceptation vérifiés |

Les tests et la revue scientifique accompagnent chaque phase : la phase 10 consolide la validation. Aucun calendrier de livraison n’est fixé sans connaître l’accès aux données et la disponibilité des utilisateurs et experts.

## Responsabilités architecturales

- `domain/` définit les données d’exploitation, les unités, les états de contraintes et la provenance, indépendamment des API.
- `data/` transforme des réponses externes en données contrôlées ; il conserve l’origine et ne fabrique pas de valeurs.
- `analysis/` expose les calculs physiques et leur domaine de validité.
- `rotation/` utilise les références validées et les résultats analytiques pour tester les contraintes et comparer.
- `explainability/` transforme les résultats structurés en explications reliées aux preuves.
- `ui/` collecte les entrées et affiche les sorties ; aucune règle scientifique cachée dans les widgets.
- `config/` accueillera les paramètres validés et versionnés ; aucun secret dans le dépôt.
- `data/raw/` et `data/processed/` restent locaux par défaut ; la conservation, les droits et la protection des données devront être définis avant acquisition et persistance utilisateur.

## Stratégie de test

| Niveau | Vérifications prévues | Dépendance externe |
|---|---|---|
| Unitaire | Conversions d’unités, validations de coordonnées/dates, sentinelles, valeurs inconnues, agrégation et formules | Aucune |
| Intégration | Contrats des clients, erreurs HTTP, quotas, schémas et provenance ; réponses enregistrées seulement après acquisition autorisée | Tests ordinaires hors ligne ; tests réseau séparés et explicites |
| Scientifique | Cas de référence indépendants et sourcés ; calcul hydrique, cohérence temporelle, paramètres et sensibilité | Références validées et revue agronomique |
| Contraintes et comparaison | Rotation actuelle absente, sol inconnu, manque d’eau, calendrier incompatible, moins de deux alternatives, priorités différentes | Cas de test contrôlés |
| Interface et parcours | Saisie française, unités, navigation, visibilité des preuves, risques et erreurs ; aucune recommandation si inconnue critique | Application future et tests utilisateurs |

Des valeurs numériques construites pour tester une formule seront admises uniquement comme **cas unitaires explicitement artificiels**, isolés des données d’application et jamais présentés comme observations NASA ou résultats de terrain. Aucun jeu de données synthétique n’est créé à cette phase. Les attentes des tests scientifiques devront provenir d’un calcul indépendant ou d’une référence, pas seulement reproduire le code testé.

## Inconnues et risques à traiter

| Risque ou information manquante | Conséquence | Réponse prévue |
|---|---|---|
| Édition et règles officielles du défi non vérifiées | Ressources ou livrables attendus incertains | Confirmer la page officielle au début de phase 2 |
| Parcelles, rotation actuelle et horizon inconnus | Pas de sélection concrète de stratégies | Recueillir les entrées avec l’agriculteur en phase 3 |
| Sol, irrigation et références locales incomplets | Faisabilité et besoin d’eau non déterminables | Identifier les informations critiques et consulter une expertise locale |
| Résolution spatiale insuffisante | Précision parcellaire illusoire | Expliquer l’échelle et limiter les conclusions |
| Nuages, lacunes, biais ou séries incompatibles | Indicateurs non comparables ou indisponibles | Contrôles qualité, périodes cohérentes, refus de calcul si nécessaire |
| Accès, licence, quota ou authentification | Acquisition impossible ou difficile à reproduire | Vérification documentaire puis essais autorisés ; erreurs explicites et cache traçable |
| Paramètres culturaux transférés sans validation | Besoins en eau ou contraintes erronés | Références applicables, revue et sensibilité avant utilisation |
| Dépendances logicielles non fixées | Environnement futur non reproductible | Fixer et tester les versions au démarrage de l’implémentation |
| Données d’exploitation sensibles | Divulgation de localisation ou pratiques | Politique d’accès, consentement et conservation avant stockage |

## Point d’arrêt et prochaine tâche exacte

Le point d’arrêt de phase 1 est historique et a été dépassé par les demandes d’implémentation autorisées. Les futures extensions scientifiques nécessitent chacune une autorisation et un protocole de validation distincts ; aucune nouvelle source n’est intégrée par cette mise à jour.

Prochain travail scientifique à définir séparément : vérifier les règles de l’édition du défi et établir un protocole de revue locale des références culturales et de la représentativité climatique. NASA POWER et les équations quotidiennes Penman–Monteith sont implémentés et testés, avec limites d’entrées et de domaine explicites. Une pluie efficace ou un bilan d’irrigation nécessitent encore des entrées justifiées, des cas indépendants et une validation spécifique avant implémentation.
