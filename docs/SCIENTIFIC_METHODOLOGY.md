# Méthodologie scientifique proposée

## Statut et hypothèses

Ce document distingue désormais le prototype implémenté des extensions envisagées. Aucune référence numérique agricole ni rotation locale n’est présumée. Les données NASA POWER intégrées restent des estimations maillées ; leur validation parcellaire n’est pas établie.

### Contrôles implémentés, version 2

- Noms de cultures non vides et ordre chronologique des lignes contrôlés sans réorganisation silencieuse.
- ET₀ externe : source, méthode, unité mm/day, surface short_grass, localisation, période du fichier et UTC obligatoires. Contrôle structurel distinct d’une conformité FAO-56, qui reste non vérifiée.
- Kc : culture, stade, dates, coefficient, référence, justification régionale et surface de référence obligatoires pour calculer. Les confirmations restent déclaratives ; aucune référence n’est automatiquement certifiée indépendante.
- ETc quotidienne = Kc de la ligne × ET₀ quotidienne ; sommes et volumes finis contrôlés. Aucune interpolation automatique des coefficients ni génération de calendrier local.
- Couvertures calculées par rapport à tous les jours de l’horizon commun : jours culturaux et jours ETc calculés, périodes et jours manquants. Un sous-total peut être consulté mais ne devient pas un total complet comparable. Les intercultures ne sont pas assimilées à une évaporation nulle.
- Comparabilité quantitative limitée aux horizons complets et à une même série/méthode/localisation ET₀ ; aucun classement automatique. La comparaison des volumes exige une même surface connue.
- Quatre axes séparés : déclarations utilisateur, données complètes, calcul disponible et validation agronomique. Cette dernière reste non réalisée dans le prototype.
- Réponses NASA contrôlées en UTC et en cohérence de coordonnées ; provenance et réponse brute exportables avec empreinte du JSON canonique.

### ET₀ quotidienne implémentée : FAO-56

`src/agrinova/analysis/eto.py` implémente l’équation 6 et les équations météorologiques 7–9, 11–13, 17/19, 21–25, 37–40, 42 et 47 de [FAO-56, chapitre 3](https://www.fao.org/4/X0490E/x0490e07.htm) et [chapitre 4](https://www.fao.org/4/X0490E/x0490e08.htm).

La formule quotidienne est : ET₀ = [0,408 Δ (Rn − G) + γ × 900/(T + 273) × u₂ × (es − ea)] / [Δ + γ × (1 + 0,34 u₂)], en mm/jour. Le modèle utilise T=(Tmax+Tmin)/2, la pression PS en kPa et le vent déjà à 2 m. L’irradiation solaire observée/estimée Rs est convertie explicitement en MJ/m²/jour si son unité est kWh/m²/jour (facteur exact 3,6). Le rayonnement net est dérivé pour l’herbe de référence ; l’albédo 0,23 et G=0 sont les hypothèses FAO quotidiennes de cette surface, pas des paramètres de cultures.

L’EA NASA utilise la RH2M moyenne via l’équation 19. Il s’agit d’une approximation de l’humidité, moins souhaitable que l’équation 17 sur RHmin/RHmax ; RH2M est une moyenne temporelle NASA et non une mesure des deux extrema. Cette limite est affichée ; aucun extremum n’est fabriqué. Le vent de calcul est limité au minimum 0,5 m/s recommandé par FAO pour représenter la convection en air calme ; le vent source et le vent utilisé restent distincts. Rs/Rso est plafonné à 1 uniquement pour le terme de nébulosité, comme prescrit par FAO ; sa valeur source reste conservée.

Rso utilise le jour de l’année, la latitude et l’altitude moyenne MERRA-2 fournie dans la géométrie NASA. Ce relief de maille n’est pas une altitude de parcelle validée. PS reste la pression effectivement retournée ; aucune pression météo manquante n’est remplacée dans la voie NASA.

Les variables absentes, valeurs manquantes, unités non reconnues, ET₀ négatives ou résultats non finis conduisent à une valeur journalière indisponible avec motif. Le prototype applique également un contrôle conservateur : un facteur de nébulosité ou d’humidité négatif dans l’approximation de rayonnement net interdit le calcul, au lieu d’imposer une borne inférieure ou une correction non validée. Ce refus est une politique explicite de disponibilité du prototype, pas une observation météo manquante. Aucun remplissage ni méthode de remplacement climatique n’est utilisé. Une période incomplète ne peut pas alimenter automatiquement ETc. Aux hautes latitudes en hiver, les limites des équations de rayonnement imposent une prudence supplémentaire ; le pilote ne constitue pas une validation globale.

Le cas indépendant est l’**exemple 18 de FAO-56** : Uccle, latitude 50°48′N, altitude 100 m, 6 juillet (J=187), Tmin=12,3°C, Tmax=21,5°C, RHmin=63%, RHmax=84%, vent à 10 m=10 km/h. Le rayonnement Rs=22,07 MJ/m²/jour est l’intermédiaire publié, non une donnée inventée. Les tests vérifient le calcul complet (ET₀≈3,88 mm/jour), Ra, Rn, ea et la conversion du vent ; un autre cas FAO vérifie les branches d’humidité. Ces tests ne remplacent pas une validation locale des produits NASA.

Le bilan hydrique et l’irrigation décrits ci-dessous restent **non implémentés**.

Le premier système envisagé sera fondé sur des règles agronomiques sourcées et des indicateurs physiques traçables. Aucune nécessité d’apprentissage automatique n’est établie. Les bénéfices seront formulés comme possibilités conditionnelles, pas comme gains prouvés.

## Indicateurs environnementaux envisagés

| Indicateur | Calcul proposé | Conditions et limites |
|---|---|---|
| Précipitation cumulée | Somme des hauteurs valides sur une période définie, en mm | Vérifier si les entrées sont hauteurs ou taux ; convertir les taux selon la durée ; une absence n’est pas un zéro. |
| Température | Moyenne, minima et maxima sur les périodes culturales, en °C | Seuils de stress seulement après référence propre à la culture et au stade. |
| ET₀ | FAO-56 Penman–Monteith quotidien, en mm/jour | Implémenté avec traçabilité des entrées, contrôles d’unités et cas publié ; indisponibilité explicite si entrées/domaines incomplets ; exactitude locale non validée. |
| Bilan climatique indicatif | P − ET₀ sur la même période, en mm | Indicateur de contexte ; ni bilan du sol ni besoin d’irrigation d’une culture. |
| Anomalie climatique | Valeur de période moins moyenne des périodes homologues d’une référence explicitée | Période de référence, couverture et comparabilité à valider ; ne pas qualifier de normale climatique sans justification. |
| Humidité du sol | Statistiques des observations/estimations valides du produit choisi, unités natives explicites | Profondeur et résolution conservées ; pas de conversion en réserve racinaire sans modèle et paramètres validés. |
| NDVI, si pertinent | (réflectance proche infrarouge − rouge) / (proche infrarouge + rouge), sans unité | Bandes adaptées, corrections, masques qualité et dénominateur valide ; ni rendement ni identification certaine d’une culture. |
| Relief, si utile | Altitude du produit et pente dérivée avec méthode documentée | Référentiels, résolution et sensibilité de la pente à contrôler. |

La sélection finale dépendra des besoins et des sources validées. Les tendances régionales de stockage d’eau ou les produits de stress supplémentaires ne seront étudiés que si leur apport est démontré.

## Besoins en eau des cultures

Le workflow ETc contrôle la couverture sur la saison saisie, indépendamment des lacunes ET₀ hors saison. Il exige 100 % des jours ET₀ et des intervalles Kc documentés pour publier un total saisonnier. Les jours absents sont listés ; aucune interpolation ni assimilation à zéro. Chaque stade utilise le coefficient constant fourni et confirmé par l’utilisateur ; aucun coefficient, calendrier ou ajustement climatique n’est généré. Les transitions variables demandent des intervalles documentés plus fins ; ce prototype ne construit pas automatiquement la courbe Kc des équations 66–67. Les cultures successives sont séparées ; des cycles successifs de la même culture peuvent être distingués par `crop_cycle`. Les lacunes de stades à l’intérieur d’un cycle empêchent un total saisonnier.

Le [chapitre 6 de FAO-56](https://www.fao.org/4/X0490E/x0490e0b.htm), équation 58 et tableau 12, traite du blé, de la féverole et du pois chiche, avec des distinctions de culture et de récolte à respecter. Ce lien documente la méthode et le champ des références, sans importer de coefficients génériques ni affirmer une validation marocaine. Les tableaux de stades conservent source, applicabilité déclarée et statut de vérification indépendante. Les calculs exposent ETc quotidienne, cumul par saison, contributions par intervalle, unité mm et couverture. Si un cycle échoue, les autres restent consultables séparément ; la comparaison des rotations conserve ses contrôles stricts d’horizon commun complet et de même base ET₀.

1. Identifier culture, variété si pertinente, dates et stades, pratiques et situation hydrique, à partir des informations de l’agriculteur et de références applicables.
2. Vérifier la disponibilité des variables nécessaires à ET₀ et documenter la méthode retenue. Toute méthode de remplacement devra être justifiée et présentée comme telle.
3. Pour l’approche à coefficient simple et en conditions de référence, utiliser **ETc(t) = Kc(t) × ET₀(t)**, en mm par pas de temps. Les coefficients et durées de stade restent à rechercher et valider ; aucun Kc n’est fixé ici. Cette ETc ne décrit pas automatiquement l’évapotranspiration réelle sous stress.
4. Distinguer ETc, précipitation totale, précipitation efficace, réserve du sol, irrigation nette et eau prélevée. Le calcul d’irrigation nécessite un bilan cohérent incluant stockage racinaire, entrées, ruissellement, drainage et éventuelle remontée capillaire. Sans paramètres adéquats, indiquer « besoin d’irrigation non estimable ».
5. Si un besoin net est validé, convertir en besoin brut avec une efficience sourcée et cohérente avec le système d’irrigation : **besoin brut = besoin net / efficience**, avec efficience dans ]0, 1]. Si l’efficience est inconnue, ne pas calculer de prélèvement.
6. Conversion dimensionnelle uniquement : **volume (m³) = hauteur (mm) × surface (ha) × 10**. Ce facteur est une conversion d’unités, pas une référence agronomique.

Comparer les besoins sur l’ensemble de la rotation et par période critique de disponibilité en eau. Une somme annuelle peut masquer une incompatibilité saisonnière. Aucun rendement ni gain économique n’est déduit directement d’un indicateur hydrique.

## Aptitude culturale et contraintes

L’aptitude sera évaluée au moyen de critères vérifiables, sans indice arbitraire de « convenance » :

- calendrier et durée des cycles, compatibilité des successions et fenêtres de travail ;
- besoins hydriques face aux volumes, dates et restrictions réellement disponibles ;
- texture, profondeur, drainage, salinité et autres paramètres du sol pertinents ;
- contraintes de températures par culture et stade si les seuils sont sourcés ;
- antécédents, familles botaniques et risques phytosanitaires à valider localement ;
- matériel, main-d’œuvre, débouchés et contraintes déclarées par l’agriculteur.

Chaque règle conserve sa référence, sa zone d’application, sa version, ses entrées et son résultat : **satisfait**, **incompatible** ou **inconnu**. Les critères critiques doivent être identifiés avec un agronome avant implémentation. Une inconnue critique bloque l’admissibilité à une proposition ; elle n’est pas assimilée à une conformité. Les observations régionales ne remplacent pas les mesures de sol de la parcelle.

## Construction et comparaison des rotations

### Analyse qualitative implémentée

Le module `rotation/agronomy.py` conserve les références et leur portée avec chaque constat. Il reconnaît un ensemble explicite de noms des trois cultures pilotes, sans recherche approximative ni extension automatique à d’autres cultures. La famille est appuyée par Kew POWO : [Triticum](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:30034910-2), [Vicia faba](https://powo.science.kew.org/taxon/524737-1) et [Cicer arietinum](https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:486336-1/general-information). Le nom générique « blé » ne détermine pas une espèce ou une variété.

Les symbioses sont documentées séparément par le [guide USDA sur la féverole](https://plants.usda.gov/DocumentLibrary/plantguide/pdf/pg_vifa.pdf) et la [biologie du pois chiche, OGTR, §7.3.1](https://www.ogtr.gov.au/sites/default/files/files/2021-07/the_biology_of_chickpeas_-_version_1_march_2019_0.pdf). Aucune quantité d’azote fixé ni crédit résiduel n’est déduit de l’identification. Les [principes de succession FAO](https://www.fao.org/4/y5146e/y5146e0a.htm) et de [couverture du sol](https://www.fao.org/4/v9926e/v9926e06.htm) servent à formuler des possibilités et risques conditionnels, sans transposer de rendement, dose, pratique régionale ou seuil sanitaire.

L’ordre saisi est conservé. Les lignes de stades d’un même cycle ne comptent pas comme des répétitions ; les cycles successifs de la même culture doivent être distingués par `crop_cycle`. Les frontières semis/récolte sont des déclarations distinctes des dates de stades. Des dates contradictoires, inversées, hors horizon ou des chevauchements sont signalés et bloquent le calcul associé. Les périodes potentiellement sans couvert ne sont calculées qu’entre cycles dont toutes les frontières sont connues et cohérentes ; aucune extrapolation aux bords de l’horizon ni assimilation d’une absence de stade à un sol nu. La couverture réelle reste inconnue.

Les preuves climatiques utilisent les dates exactes des stades, excluent les valeurs non finies, affichent couverture et dates manquantes, et n’exposent une somme de pluie que si la période est complète. Les extrema thermiques restent descriptifs ; aucun seuil d’aptitude n’est ajouté. La provenance climatique est conservée dans chaque résultat lorsque fournie par l’application. Les totaux ETc demeurent séparés de ces considérations qualitatives et soumis aux contrôles de comparabilité existants.

1. Recueillir la rotation actuelle sans supposition et vérifier la qualité de son historique.
2. Définir avec l’agriculteur les cultures envisageables, les contraintes, les priorités et l’horizon commun ; expliciter les cultures intermédiaires et intercultures.
3. Construire des alternatives uniquement avec des règles et références agronomiques validées ; aucune liste de rotations « typiques » n’est prescrite ici.
4. Évaluer les contraintes de chaque rotation, y compris de la référence. Conserver les motifs d’exclusion et les inconnues.
5. Comparer la rotation actuelle et au moins deux alternatives admissibles si les informations le permettent. Sinon, restituer le blocage sans inventer d’alternative.
6. Afficher un tableau de métriques avec unité, méthode, période et incertitude : besoins hydriques estimables, compatibilité saisonnière de l’eau, diversité culturale descriptive, contraintes et disponibilité des preuves. Une diversité accrue ne prouve pas un bénéfice agronomique. Les indicateurs de sol, de rendement et de marge restent indisponibles sans méthode et données appropriées.
7. Pour toute métrique quantitative, calculer si utile **Δ = valeur alternative − valeur référence**, à périmètre identique ; expliquer le sens du signe. Un pourcentage n’est calculé que si le dénominateur est valide et non nul.
8. Présenter les compromis selon les priorités, sans score global par défaut. Une éventuelle dominance de Pareto ne sera discutée qu’entre métriques comparables et suffisamment renseignées, en considérant leurs incertitudes. Si un classement pondéré est demandé ultérieurement, documenter normalisation, directions, poids choisis, données manquantes et sensibilité avant utilisation.

La comparaison distingue résultats calculés, hypothèses et bénéfices seulement attendus. Elle ne promet ni augmentation de rendement, ni réduction d’intrants, ni amélioration du sol sans preuve adaptée.

## Gestion des incertitudes

- Qualifier séparément incertitudes de mesure/restitution, échelle spatiale, période, paramètres culturaux et déclarations agricoles.
- Afficher la couverture : nombre de pas valides / nombre de pas attendus sur la période. Le seuil d’acceptation sera justifié pour chaque indicateur avant calcul opérationnel.
- Propager les valeurs manquantes avec leur motif. Toute imputation future exige une méthode évaluée, une trace et une analyse de sensibilité ; pas de remplissage silencieux.
- Utiliser des plages ou scénarios seulement à partir d’incertitudes ou bornes sourcées ; ne pas inventer d’intervalle de confiance.
- Évaluer la sensibilité aux paramètres influents et la stabilité des conclusions. Si l’incertitude empêche de départager les stratégies, l’indiquer.
- Ne pas créer de note de confiance chiffrée sans calibration. Décrire les preuves disponibles et les contrôles manquants.
- Séparer climat historique, année observée et scénario futur ; aucune prévision n’est produite dans le périmètre actuel.

## Format d’une explication future

Pour chaque stratégie : calendrier et hypothèses ; état des contraintes ; motifs de comparaison ; preuves liées aux données et références ; métriques et comparaison à la rotation actuelle ; bénéfices potentiels ; risques ; informations manquantes ; conséquences de l’incertitude ; vérifications à discuter avec le conseiller agricole.

## Validation scientifique à préparer

Vérifier les unités, les agrégations, les calculs et les limites d’application sur des cas indépendants documentés. Confronter les estimations à des observations locales lorsqu’elles deviennent disponibles. Une concordance entre deux produits maillés n’est pas une validation de terrain. Faire relire les règles et les conclusions par une expertise agronomique pertinente pour la zone cible avant toute utilisation décisionnelle.
