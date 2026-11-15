# AgriNova AI

Projet de système web explicable d’aide à la décision agricole pour la zone de **Beni Mellal–Afourer, Maroc**, proposé pour le NASA Space Apps Challenge, défi « Field Shift: Adapting Farms with NASA Data » (intitulé fourni dans le cahier des charges).

## Objectif

Permettre aux agriculteurs de comparer au moins trois stratégies de rotation, dont leur rotation actuelle, à partir de données environnementales NASA, des caractéristiques de leur exploitation et de leurs priorités. La rotation actuelle sera saisie par l’agriculteur : aucune rotation locale n’est présumée.

Chaque comparaison devra présenter les motifs, les éléments de preuve, les bénéfices potentiels, les risques et les informations manquantes. Le système soutient la décision et le dialogue avec un conseiller agricole ; il ne remplace pas l’expertise de terrain.

## Fonctionnalités prévues

- Saisie de la parcelle, du sol, de l’historique cultural, de l’irrigation et des contraintes.
- Acquisition traçable d’un nombre limité de sources pertinentes pour le Maroc.
- Analyse climatique et hydrique adaptée à la résolution des données disponibles.
- Vérification agronomique des rotations avant toute proposition.
- Comparaison transparente selon les priorités du producteur, avec incertitudes visibles.
- Interface initiale en français, graphiques et explications compréhensibles.

## État du projet

**Prototype Streamlit fonctionnel.** L’application interroge NASA POWER pour la température et la précipitation quotidiennes, présente leurs couvertures, accepte trois rotations et propose des exemples explicitement fictifs. Aucune rotation réelle d’agriculteur n’est fournie par défaut. Les données NASA sont des estimations météorologiques maillées, pas des mesures de parcelle.

Les contrôles scientifiques v2 refusent les cultures manquantes, l’ordre chronologique inversé, les réponses NASA non UTC ou incohérentes géographiquement, ainsi que les calculs ETc non finis. Ils distinguent déclarations, complétude, disponibilité du calcul et validation agronomique. Aucun score d’aptitude ni classement automatique n’est produit. La conformité officielle à l’édition du défi reste à vérifier.

## Exécuter et tester

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q
$env:AGRINOVA_LIVE_TEST = '1'
.\.venv\Scripts\python.exe -m pytest -q
```

Le test réseau est optionnel ; les tests ordinaires restent utilisables hors ligne. Les valeurs artificielles des tests ne sont jamais chargées comme données NASA ou références agricoles dans l’application.

## Calcul d’eau et métadonnées

Deux voies ET₀ sont disponibles dans le panneau de calcul de l’eau : import externe, ou calcul quotidien FAO-56 Penman–Monteith avec les variables NASA POWER vérifiées. Le calcul NASA exige températures, RH2M, WS2M, rayonnement solaire, pression et altitude documentée de la maille. Les jours incomplets ou hors domaine restent indisponibles, sans interpolation ni remplacement par zéro. Le résultat journalier, ses motifs et sa provenance sont exportables. Son utilisation pour ETc exige un choix explicite et une période intégralement calculable.

L’import externe reste inchangé : CSV `date` (AAAA-MM-JJ), `eto_mm` (mm/jour), source, méthode, unité `mm/day`, surface `short_grass`, point représenté et standard `UTC`. Les contrôles structurels ne certifient pas la méthode externe.

Le module [eto.py](src/agrinova/analysis/eto.py) reproduit le [cas FAO-56 n°18, Uccle, 6 juillet](https://www.fao.org/4/X0490E/x0490e08.htm) : environ 3,88 mm/jour, publié arrondi à 3,9. La voie NASA utilise RH2M moyenne dans l’équation 19, approximation documentée moins souhaitable que RHmin/RHmax ; aucune valeur RH extrême n’est inventée. Les hypothèses de surface de référence, le minimum de vent de calcul recommandé par FAO et la limite Rs/Rso sont conservés dans les intermédiaires/provenances. L’altitude de maille n’est pas un relevé de la parcelle.

Chaque ligne Kc demande culture, stade de croissance, dates, coefficient, référence, justification d’applicabilité régionale et surface de référence. Aucune valeur n’est préremplie. Une confirmation utilisateur reste une **déclaration**, jamais une vérification indépendante ni une certification FAO-56.

Le contrôle ETc porte sur chaque saison saisie : une lacune ET₀ hors saison ne bloque pas le calcul. Avec une série NASA incomplète, cochez l’utilisation des jours disponibles avec contrôle saisonnier. Chaque culture exige 100 % de couverture ET₀ et Kc entre ses dates saisies ; les dates manquantes sont affichées sans zéro ni interpolation. Les résultats détaillent ETc quotidienne, cumul saisonnier, contributions des stades, sources et limites. Les stades successifs de la même culture forment une saison ; utilisez le champ « Cycle cultural » pour séparer deux cycles successifs de blé. Kc reste constant sur chaque intervalle fourni, sans construction automatique d’une courbe FAO. Les résultats complets d’une culture restent disponibles si une autre culture est bloquée, sans produire de total incomplet de rotation.

Les totaux ETc ne sont comparables que pour des horizons complets, des couvertures complètes et une même base ET₀. Les sous-totaux restent identifiés comme partiels dans les détails. Les volumes exigent également une même surface connue. Les calendriers locaux et la faisabilité agronomique ne sont pas automatiquement validés.

L’analyse agronomique qualitative identifie uniquement les noms documentés du blé (Poaceae), de la féverole et du pois chiche (Fabaceae). Les autres noms restent inconnus. Chaque rotation expose familles, potentiel conditionnel de fixation azotée, répétitions, références, risques et informations manquantes, sans score ni classement. Les stades d’un cycle sont regroupés ; utilisez des identifiants distincts pour deux cycles successifs de la même culture. Les dates facultatives de semis et récolte permettent de repérer les intercultures internes potentiellement sans couvert, sans présumer l’absence de résidus ou de couvert. Les références biologiques générales ne valident ni les pratiques ni un bénéfice mesuré au Maroc. Les preuves climatiques détaillent les jours valides et les lacunes par stade ; la pluie totale ne représente pas l’eau d’irrigation disponible.

La pluie efficace, la réserve du sol, les besoins nets/bruts d’irrigation et l’efficience ne sont pas calculés. ETc ne représente pas un volume d’irrigation disponible ou nécessaire.

## Traçabilité et exports

Les exports CSV/JSON existants restent disponibles. La provenance NASA contient une empreinte SHA-256 du JSON canonique, la requête, les dates, les coordonnées et la version de traitement. La comparaison exporte les métadonnées ET₀/Kc, les périodes, les couvertures et les quatre axes de statut, y compris pour les scénarios fictifs. La réponse brute est disponible au téléchargement ; aucun archivage automatique sur disque n’est effectué.

## Technologies prévues

Python, Streamlit (interface française), Pandas et NumPy (traitement), Requests (accès HTTP), Plotly (visualisation), Pytest (tests). Scikit-learn sera envisagé seulement si une question scientifique, des données adaptées et une validation indépendante le justifient. Les versions et dépendances seront fixées lors de la préparation de l’implémentation.

## Documentation

- [Exigences et critères d’acceptation](docs/PROJECT_REQUIREMENTS.md)
- [Registre des sources candidates](docs/DATA_SOURCES.md)
- [Méthodologie scientifique proposée](docs/SCIENTIFIC_METHODOLOGY.md)
- [Feuille de route et stratégie de validation](docs/DEVELOPMENT_ROADMAP.md)

## Architecture cible

```text
AgriNova-AI/
├── README.md
├── .gitignore
├── docs/
│   ├── PROJECT_REQUIREMENTS.md
│   ├── DATA_SOURCES.md
│   ├── SCIENTIFIC_METHODOLOGY.md
│   └── DEVELOPMENT_ROADMAP.md
├── config/                     # Paramètres et références versionnées à venir
├── data/
│   ├── raw/                    # Réponses sources conservées sans modification
│   └── processed/              # Données dérivées et métadonnées de calcul
├── src/agrinova/
│   ├── domain/                 # Exploitation, sol, cultures, contraintes, provenance
│   ├── data/                   # Clients de sources, validation, cache et traçabilité
│   ├── analysis/               # Indicateurs climatiques et hydriques
│   ├── rotation/               # Faisabilité et comparaison des stratégies
│   ├── explainability/         # Preuves, limites et explications en français
│   └── ui/                    # Présentation Streamlit, séparée des calculs
└── tests/
    ├── unit/
    ├── integration/
    └── scientific/
```

Les fichiers `.gitkeep` conservent les dossiers vides. Les modules scientifiques devront fonctionner indépendamment de Streamlit ; l’interface consommera leurs résultats structurés. Les données brutes et traitées ne seront pas versionnées dans le dépôt par défaut.

## Limites scientifiques restantes

Les références Kc et leur applicabilité restent déclarées par l’utilisateur. Aucune validation locale indépendante, aucun catalogue de coefficients marocains, aucun modèle de stress ou de bilan hydrique n’est intégré. Le test FAO vérifie les équations, pas l’exactitude parcellaire des entrées NASA. La pluie efficace et l’irrigation nécessitent toujours une tâche scientifique distincte.
