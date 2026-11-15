# Registre des sources candidates

## Statut et règle de sélection

**État actuel : NASA POWER quotidien est intégré et testé au point de Beni Mellal.** Les variables sont demandées dans une même requête point, communauté AG, en UTC, contrôlé dans la réponse. L’intégration technique ne vaut pas validation agronomique locale.

| Paramètres vérifiés | Unités quotidiennes retournées | Usage |
|---|---|---|
| T2M, T2M_MIN, T2M_MAX | C | Climat ; Tmin/Tmax définissent Tmean FAO, T2M reste disponible et contrôlée |
| PRECTOTCORR | mm/day | Contexte de pluie ; pas une pluie efficace ni une entrée de l’équation ET₀ |
| RH2M | % | Humidité quotidienne, EA via FAO-56 eq.19 avec limite d’approximation documentée |
| WS2M | m/s | Vent déjà à 2 m ; aucun substitut d’une valeur absente |
| ALLSKY_SFC_SW_DWN | MJ/m^2/day en AG | Irradiation solaire Rs ; conversion kWh→MJ seulement si l’unité est explicitement documentée |
| PS | kPa | Pression quotidienne pour la constante psychrométrique |
| Troisième coordonnée de la géométrie | m | Altitude MERRA-2 moyenne de maille pour Rso, jamais un relevé parcellaire |

Les unités et la disponibilité ont été vérifiées sur une réponse réelle JSON quotidienne ; l’en-tête ASCII NASA identifie explicitement l’altitude comme moyenne MERRA-2. Le [service quotidien](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) conserve la résolution native : météorologie MERRA-2 0,5° × 0,625°, [rayonnement CERES/SRB 1° × 1°](https://power.larc.nasa.gov/docs/methodology/data/sources_fluxes/). L’historique météorologique commence en 1981 ; les flux radiatifs ont une couverture et une latence propres, à vérifier sur chaque réponse, sans remplir les périodes absentes.

La géométrie retournée doit correspondre au point demandé, avec une tolérance numérique d’identité de 0,0001° ; cette tolérance n’exprime pas la précision du produit. Une empreinte SHA-256 du JSON canonique relie les exports de provenance à la réponse NASA. Aucun fichier brut n’est automatiquement archivé : les téléchargements restent explicites.

Toutes les autres sources du tableau restent candidates, sans intégration. Leurs variables et résolutions sont à vérifier avant utilisation. Les descriptions initiales de phase 1 ci-dessous ne prouvent pas leur validation.

Une source sera retenue seulement après confirmation de sa couverture du Maroc, de son utilité, de ses caractéristiques, de ses droits d’usage et de son accès. Ne pas intégrer automatiquement cette liste entière.

## Sources NASA candidates

| Source | Variables candidates à vérifier | Rôle scientifique envisagé | Résolution spatiale et temporelle à vérifier | Accès à investiguer | Limites à évaluer | Statut |
|---|---|---|---|---|---|---|
| [NASA POWER](https://power.larc.nasa.gov/) | Températures, pluie, RH2M, WS2M, ALLSKY_SFC_SW_DWN et PS | Contexte climatique et ET₀ FAO-56 quotidienne conditionnelle | Météorologie 0,5° × 0,625° ; solaire 1° × 1° ; quotidien UTC | API point AG JSON ; unités effectivement contrôlées | Représentativité locale, relief moyen, humidité moyenne et limites radiatives ; validation locale absente | Paramètres intégrés et cas mathématique de référence testé ; usage agronomique local non validé |
| [SMAP](https://smap.jpl.nasa.gov/) | Humidité du sol, qualité et variables associées selon produit | Contexte de sécheresse et d’humidité superficielle | Empreinte/grille, profondeur représentée, revisite et agrégations du produit choisi | Catalogue Earthdata, authentification, sous-ensembles | Humidité superficielle distincte de l’eau disponible dans la zone racinaire ; produits observés et assimilés à distinguer | Candidat, non validé |
| [GPM / IMERG](https://gpm.nasa.gov/data/imerg) | Précipitation et indicateurs qualité | Variabilité des pluies et comparaison avec une source climatique initiale si utile | Grille, fréquence, accumulation, période ; version et catégorie de traitement | Documentation GPM, catalogue et services de sous-ensemble | Biais locaux, délai de disponibilité, distinction pluie estimée/pluie efficace | Candidat, non validé |
| [Landsat](https://landsat.gsfc.nasa.gov/) | Réflectance, bandes de qualité ; indicateurs de végétation dérivés | Historique du couvert et phénologie si résolution et nuages le permettent | Résolution par bande, revisite, disponibilité et collections | Distribution officielle NASA/USGS, produits de surface et masques qualité | Nuages, parcelles mixtes, corrections et continuité entre capteurs ; indice de végétation distinct d’un rendement | Candidat, non validé |
| [MODIS](https://modis.gsfc.nasa.gov/) | Indices de végétation selon produit | Contexte saisonnier à une échelle compatible avec la grille | Résolution, fenêtre de composition et série historique | Produits et catalogues Earthdata | Mélange de parcelles, qualité des composites, redondance éventuelle avec Landsat | Candidat, non validé |
| [ECOSTRESS](https://ecostress.jpl.nasa.gov/) | Température de surface, évapotranspiration selon produit | Analyse complémentaire d’épisodes de stress thermique/hydrique | Résolution par produit, heures de passage et disponibilité effective locale | Catalogue, niveaux de traitement et contrôle qualité | Échantillonnage irrégulier, nuages, interprétation du stress ; ET estimée distincte d’un besoin cultural de référence | Candidat, non validé |
| [SRTM](https://www.earthdata.nasa.gov/data/instruments/srtm) | Élévation ; pente dérivée | Contexte topographique et limites de représentativité climatique | Version du modèle, grille, référentiel vertical et date d’acquisition | Catalogue et distribution officielle | Modèle de surface, erreurs et précision de pente selon échelle ; ne caractérise pas le sol | Candidat, non validé |
| [GRACE / GRACE-FO](https://grace.jpl.nasa.gov/) | Anomalies de stockage total d’eau selon solution | Contexte hydrologique régional uniquement, si pertinent | Support spatial effectif, fréquence, référence des anomalies et incertitudes | Solutions officielles, documentation des traitements | Ne fournit pas le stock d’eau ni le débit accessible d’une parcelle ; séparer stockage total et nappe | Candidat, non validé |

## Sources complémentaires et informations locales

| Source | Variables et finalité candidates | Échelles et accès à vérifier | Limites et statut |
|---|---|---|---|
| [Sentinel-2 / Copernicus](https://dataspace.copernicus.eu/) | Réflectance, qualité, indices de végétation pour le suivi du couvert | Bandes, produits, revisite effective, masques nuageux et API | Source complémentaire, pas NASA ; utilité par rapport à Landsat à démontrer ; non validée |
| [ERA5 / Copernicus Climate Data Store](https://cds.climate.copernicus.eu/) | Variables météorologiques pour compléter ou comparer une source climatique | Produit précis, grille, fréquence, unités, licence, API et compte | Réanalyse modélisée ; cohérence des variables et correction locale à évaluer ; non validée |
| [FAO GAEZ](https://gaez.fao.org/) | Contexte agroécologique et hypothèses de cultures | Version, scénarios, gestion, grille, période et téléchargement/API disponibles | Aptitude régionale conditionnelle, pas diagnostic de parcelle ; non validée |
| [FAO Irrigation and Drainage Paper 56](https://www.fao.org/4/X0490E/X0490E00.htm) | Méthode ET₀, coefficients culturaux et conditions de calcul à examiner | Document méthodologique ; passages, tables, unités et conditions applicables à identifier | Ne pas transférer un coefficient sans vérifier culture, stade, climat et gestion ; référence candidate à examiner |
| Agriculteur et analyses de laboratoire | Rotation actuelle, calendriers, sol, irrigation, contraintes et priorités | Parcelle, dates de déclaration/prélèvement, méthode et unités | Déclarations distinctes des mesures ; représentativité, consentement et complétude à vérifier |
| Références agronomiques marocaines à identifier | Calendriers, contraintes de succession, variétés et paramètres agricoles | Publication, organisme, zone, période, méthode et conditions d’application | Aucune valeur retenue ; recherche et revue locale nécessaires |

## Fiche de validation obligatoire pour chaque source retenue

1. Organisme, titre, URL de documentation, produit, version, licence et date de vérification.
2. Couverture effective de la zone cible et des périodes d’intérêt ; coordonnées, grille et système de référence.
3. Variables exactes, définition, unités natives et cibles, valeurs sentinelles et indicateurs qualité.
4. Résolution spatiale native et support réel de l’information ; fréquence native et agrégations prévues.
5. Méthode de production : observation, restitution satellitaire, assimilation ou modèle ; incertitudes connues.
6. Accès, authentification, quotas, format, disponibilité, latence et procédure en cas d’échec.
7. Usage proposé, alternatives, justification de sélection ou rejet et validation locale disponible.
8. Relecteur, preuves documentaires et décision datée : candidat → documentation vérifiée → accès vérifié → données contrôlées → utilisable pour un usage défini, ou rejeté.

La vérification documentaire ne suffit pas à valider les données. Les essais d’accès et contrôles d’observations appartiennent aux phases ultérieures autorisées.

## Provenance attendue

Conserver pour chaque acquisition : requête sans secret, date d’accès, produit/version, couverture demandée et reçue, unités, qualité, réponse brute et empreinte de fichier. Chaque résultat dérivé référence ses entrées, transformations, agrégations et version de méthode. Une interpolation ou une désagrégation ne crée pas une observation de parcelle.

## Exclusions

SSURGO, Web Soil Survey (WSS), PRISM et Cropland Data Layer ne seront pas utilisés pour caractériser directement une ferme marocaine. Aucune source étrangère ne sera transférée à la zone cible sans justification de son domaine d’application.
