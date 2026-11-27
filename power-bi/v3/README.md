# Quality Dashboard V3 – refonte visuelle

Même rapport que la V2 : même table Databricks, mêmes mesures, mêmes filtres et signets. Seul le design change.

## Ce qui change

| Zone | V3 |
|---|---|
| **Fond de page** | Une image dessinée pour chaque page : bandeau d'en-tête en dégradé marine, barre de navigation fine à icônes, trame de points discrète, cartes blanches aux ombres douces. |
| **Motif** | Une bande de tolérance (USL / LSL) traversée par un signal de mesure, avec un point hors limite en orange, dans l'en-tête. |
| **En-tête** | Titre de page, question à laquelle la page répond, libellés des filtres en petites capitales. Les filtres sont des menus déroulants blancs arrondis posés sur le bandeau. |
| **Cartes** | Un titre et un sous-titre explicatif sur chaque visuel, sans bordure. |
| **Overview** | Grand chiffre « Pass rate » (12 mois) avec l'objectif et la jauge en dessous. Courbe lissée avec aire, objectif 95 % en ligne de référence pointillée et zone ombrée. Pass % au centre du donut. Arbre de décomposition en orange. Bouton Part \| Test en pilules. |
| **Characteristics** | Cartes KPI avec une mini-courbe de tendance par jour. Courbe Pass / Fail avec un 2ᵉ axe pour les Fail, enfin lisibles. Barres affinées. |
| **More filters** | Voile plus sombre, panneau avec ombre, boutons en pilules. |

## Page 3 « Reaction limits »

`add_reaction_limits.py` ajoute la page 3 au `.pbix` V3 enregistré par Power BI Desktop. Comme le modèle change, il
produit un modèle de rapport (`out/Quality_Dashboard_V3_RL.pbit`) : à l'ouverture, Power BI recharge les données.
Si le `.pbix` fourni contient déjà la page 3, le modèle a déjà les colonnes et mesures nécessaires. Le script
reconstruit alors la page 3 et sa page de détail en gardant le modèle et ses données, et produit directement
`out/Quality_Dashboard_V3_RL.pbix`, sans rechargement.

Une violation est une valeur mesurée conforme (Pass), mais en dehors des limites de réaction
(`characteristic_result` = « control limit violated »). La page suit la maquette de la spécification :

| Élément | Contenu |
|---|---|
| Filtres visibles | Plant, Part, Test, Characteristic et Date, synchronisés avec les pages 1 et 2 |
| More filters | Inspection reason, KPC |
| Violations per day | Courbe bleu foncé (couleur des limites de réaction). Le sous-titre donne le total et le taux sur les valeurs évaluées. |
| Top 15 characteristics | Barres, avec un filtre Top 15 |
| Violations by part | Treemap : sélectionner une pièce, puis cliquer sur **Details ›** |
| Violations by test | Nombre de violations et part dans le total |
| Page de détail (masquée) | Ouverte par **Details ›** : date et heure, pièce, test, caractéristique, valeur, limites de réaction, LSL / USL |

Le modèle gagne 6 colonnes « RL … » dans le dossier *Reaction limit details*. Elles ne sont remplies que pour les
violations (environ 1 % des lignes), donc elles pèsent très peu. Il gagne aussi 5 mesures dans le dossier
*Reaction limits* : `RL Violations`, `RL Share`, `RL Violation %`, `RL Summary` et `RL Details Title`.

Avant d'écrire le fichier, le script vérifie :
- les propriétés de mise en forme, avec le catalogue des visuels ;
- les champs utilisés, par rapport au modèle ;
- les signets ;
- la liaison de la page de détail ;
- les règles de filtres du validateur PBIR de Microsoft.

## Page d'accueil et page 4 « Cpk »

`add_home_and_cpk.py` ajoute deux pages au `.pbix` qui contient les pages 1 à 3, et produit
`out/Quality_Dashboard_V9.pbit`. Le modèle change, donc les données se rechargent à l'ouverture. Si le modèle du
`.pbix` contient déjà tous les champs utilisés, le script reconstruit seulement les deux pages et écrit un `.pbix`.

- **Accueil** (concept B des propositions) : à gauche, le logo, la mission du rapport et les chiffres clés (le nombre
  d'usines et de valeurs mesurées viennent des données) ; à droite, une ligne par page qui l'ouvre, et un guide de
  lecture. La pastille du logo devient le bouton **Home** de toutes les pages.
- **Cpk**, marquée « To be validated », d'après la maquette de la spécification : Cpk pass %, donut Pass & Fail,
  Pass & Fail % par pièce et par test (avec le nombre de caractéristiques), Cpk de chaque caractéristique.
  More filters : Inspection reason, seuil Cpk (1,33 si aucun n'est choisi), Cpk pass / fail.

Le Cpk suit la méthode de la requête QDA de la spécification :
- il est calculé pour chaque usine, pièce, test et caractéristique, sur les caractéristiques variables dont le résultat
  est Pass ou Fail ;
- X̄ est la moyenne des valeurs ; R̄ est la moyenne des étendues mobiles, les valeurs étant prises dans l'ordre du temps ;
- σ = R̄ / 1,128 ;
- Cpk = min(USL − X̄, X̄ − LSL) / 3σ, ou le seul côté qui a une limite.

### Une seule table de données

Les sommes du Cpk sont calculées par Databricks, dans la requête de `Quality Tracker` (7 colonnes masquées du dossier
*Cpk sums*). Pour chaque caractéristique, motif d'inspection et jour, la dernière valeur mesurée du jour porte les
sommes de ce jour :
- le nombre de valeurs et leur somme ;
- le nombre d'étendues mobiles et leur somme ;
- l'USL et la LSL de la dernière mesure.

Les autres lignes restent vides. Power BI additionne ces sommes sur les jours filtrés, puis recalcule le Cpk. Sur des
données de test, le résultat est identique à la formule appliquée directement aux valeurs, à 10⁻¹³ près.

Le modèle n'a donc qu'une table de données, `Quality Tracker` (actualisation incrémentielle : 12 mois conservés,
7 jours actualisés). S'y ajoutent deux petites listes pour les filtres de la page Cpk :
- `Cpk Threshold` : 1, 1,33, 1,67 et 2 ;
- `Cpk Status` : Pass et Fail.

L'heure de la dernière actualisation est la colonne `Refreshed At`, ajoutée par Power Query sur chaque ligne. La
mesure `Last Refresh` en prend le maximum, sans tenir compte des filtres.

Les filtres de la page Cpk sont ceux de la page 2, avec les mêmes champs et les mêmes groupes de synchronisation.
Une sélection suit donc d'une page à l'autre, date comprise.

Écarts avec la requête QDA, faibles dès qu'une caractéristique a quelques dizaines de valeurs :
- Les étendues mobiles sont calculées à l'actualisation, sur la période que charge chaque requête : un mois pour
  l'historique du service, un jour pour les 7 derniers jours, `RangeStart`–`RangeEnd` dans Desktop.
- Quand la période filtrée commence dans une période chargée, la première étendue mobile de chaque caractéristique
  part de la dernière valeur d'avant le filtre. QDA, lui, repart de la première valeur de la période.
- Avec un filtre *Inspection reason*, les étendues mobiles restent celles calculées sur toutes les valeurs, quel que
  soit le motif.
- L'USL et la LSL sont celles de la dernière mesure de chaque période chargée. Sur plusieurs périodes, le calcul garde
  la plus haute.

## V10 : retours client sur Overview, filtre de période

`add_period_filter.py` applique les retours client à la V9 et produit `out/Quality_Dashboard_V10.pbit`. Le modèle
change, donc les données se rechargent à l'ouverture.

- **Overview** : le donut *Pass & Fail %* est supprimé, et la courbe mensuelle prend sa place. Le chiffre *Pass rate*
  et sa jauge suivent désormais tous les filtres : avant, ils montraient les 12 derniers mois avec le seul filtre
  Plant. Leur sous-titre indique la période choisie.
- **Filtre de période**, sous l'heure d'actualisation, sur Overview, Characteristics, Reaction limits et Cpk :
  - *Day* : les 24 dernières heures ;
  - *WTD* : depuis lundi ;
  - *MTD* : depuis le 1er du mois ;
  - *YTD* : depuis le 1er janvier ;
  - *Year* : les 12 derniers mois, choisi par défaut.

  Le filtre est synchronisé : la même période s'applique à toutes les pages. Il s'ajoute aux autres filtres, date
  comprise. *Clear filters* le vide aussi : toutes les données chargées sont alors prises (environ 12 mois dans le
  service).

Comment c'est construit (`period_model.py`) :
- Les heures de mesure sont l'heure locale de chaque usine. Les 24 heures de *Day* sont donc comptées depuis la
  dernière mesure de chaque usine (sur les 2 derniers jours). Une heure à plus de 14 h dans le futur est ignorée.
- La requête ajoute à `Quality Tracker` la colonne masquée `Period Key` : la date au format aaaammjj × 10, + 1 si la
  valeur est dans les 24 dernières heures de son usine.
- La table `Period`, recalculée à chaque actualisation à partir du jour de l'actualisation (UTC), donne pour chaque
  période les `Period Key` qu'elle garde.
- Une relation plusieurs-à-plusieurs, dans un seul sens, de `Period` vers `Quality Tracker` : chaque visuel suit le
  filtre sans changer ses mesures.
- Les 7 derniers jours sont actualisés à chaque fois (actualisation incrémentielle). Le repère des 24 heures est donc
  toujours à jour.

## V11 : page 5 « Trend chart », page Cpk sans donut

`add_trend_page.py` part de la V10 et produit `out/Quality_Dashboard_V11.pbit`. Le modèle change, donc les données
se rechargent à l'ouverture.

**Trend chart**, d'après la page 5 de la spécification :
- **Une caractéristique à la fois.** Part, Test et Characteristic sont marqués * dans le bandeau. Tant que les filtres
  laissent plusieurs couples usine + pièce + test + caractéristique, la courbe reste vide et son sous-titre dit quoi
  choisir.
- **Reaction limit violations** : les valeurs hors limites de réaction pour les filtres en cours.
- **Cpk** comparé à l'objectif, c'est-à-dire le seuil choisi dans More filters (1,33 par défaut). Le sous-titre
  indique *Goal 1.33 · ✔ Pass* ou *✖ Fail*.
- **La courbe** : chaque valeur mesurée, dans l'ordre du temps (heure locale de l'usine), avec les lignes USL, UCL,
  X̄, LCL et LSL. Leur nom et leur valeur sont affichés à droite. L'axe vertical couvre toujours les valeurs et
  toutes les limites.
- **Filtres** : les mêmes que sur les autres pages (mêmes groupes de synchronisation, filtre de période compris).
  More filters : Inspection reason et Cpk threshold.

Pour cette page, `Quality Tracker` gagne 4 colonnes :
- `Measured Value` et `Measured At`, la valeur et son heure, sur les lignes qui entrent dans le Cpk ;
- `Cpk UCL` et `Cpk LCL`, les limites de réaction de la dernière mesure, sur les lignes qui portent les sommes du
  Cpk.

L'USL, la LSL et X̄ viennent des colonnes déjà utilisées pour le Cpk.

**Autres changements :**
- Une 5e tuile *Trend chart* apparaît sur toutes les pages, et une 5e ligne sur la page d'accueil.
- Page Cpk : le donut Pass & Fail est supprimé et *Cpk pass %* occupe sa carte. La mention *To be validated*
  disparaît. La ligne *n of N characteristics* sous le chiffre a été retirée ensuite, dans le rapport V12.
- Le filtre de période revient sur *Year* sur toutes les pages.

## V12 : page d'accueil sans bandeau de navigation

Sur la page d'accueil, les lignes ouvrent les pages : le bandeau de gauche des pages d'analyse (tuiles des pages,
*Clear filters*) n'y est plus. Le panneau bleu du logo va jusqu'au bord gauche.

Le rapport s'appelle désormais **Plant visual management dashboard** (`design.REPORT_TITLE`). Ce titre apparaît
dans la ligne du haut de chaque page et, sur trois lignes, sur la page d'accueil, sous « Quality ».

`update_home_page.py` reconstruit les visuels de la page d'accueil et remplace les fonds de page dans un `.pbix`. Le
modèle, les données et les autres pages sont gardés : la sortie est un `.pbix`, `out/Quality_Dashboard_V12.pbix`.

## Design A « Rail marine » (modèles OPmobility)

Le design choisi parmi les trois propositions tirées des modèles de l'entreprise (bleu marine #0E3472, gris clair
#F4F6F8, arcs concentriques, titres en Outfit) :
- **Rail marine** de 150 px à gauche : logo blanc et « ‹ Home », les cinq pages (la page active dans une pastille
  blanche), *Clear filters* et la dernière actualisation en bas.
- **En-tête blanc** : titre et question de la page, arcs des modèles en haut à droite, filtre de période à côté du
  titre (style clair : la période choisie en bleu clair, contour marine).
- **Filtres** : chaque segment dans une boîte grise, sous son nom ; *More filters* (ou *Back*) avec un contour marine.
- **Contenu** : les visuels gardent leur ordre et leurs proportions dans la nouvelle zone de contenu. Les cartes
  blanches (bord gris clair, coins arrondis) sont dessinées dans le fond de page : les visuels perdent leur propre
  fond blanc. Le panneau *More filters* ne bouge pas.
- **Accueil** : à gauche, le logo marine, le titre et une ligne par page ; à droite, le panneau marine des modèles
  avec le logo blanc, les chiffres clés (en direct pour les sites et les valeurs mesurées) et la dernière
  actualisation.

`design_a.py` contient la géométrie et les fonds de page du design A ; `apply_design_a.py` l'applique à un `.pbix`
enregistré par Power BI Desktop. Le modèle, les données, les mesures, les filtres, les signets et les autres réglages
des visuels sont gardés : la sortie est un `.pbix`, `out/Plant visual management dashboard A.pbix`.

## V13 : chiffres clés sur Overview, page « Failure breakdown »

Retours client sur Overview (design A) :
- **Trois chiffres clés**, comme la maquette du client : *Failed inspections* (période choisie), *Fail rate* (part des
  inspections) et *Gap to target* (taux de réussite moins la cible de 95 %, en points : orange sous la cible, bleu à
  partir de la cible). L'icône et le nom sont dessinés dans le fond de page ; le chiffre et la ligne en dessous sont
  des cartes (nouveau visuel carte), dont la ligne est le nom du champ dans le visuel.
- **« Where do inspections fail? »** (arbre de décomposition) n'est plus affiché sur Overview : une tuile l'ouvre sur
  sa propre page, **Failure breakdown**, masquée dans les onglets. Cette page a les filtres d'Overview (copies des
  segments, mêmes groupes de synchronisation, panneau *More filters* et ses signets) et « ‹ Overview » pour revenir.

Le modèle reçoit deux mesures (`overview_model.py`) : `Pass % Gap` (format `+0.0 pp`) et `Pass % Gap Color`. La
sortie est donc un modèle `.pbit` : `out/Plant visual management dashboard V13.pbit` (données rechargées à l'ouverture).
`add_overview_figures.py` part du `.pbix` du design A.

## Design Relief (concept premium 2)

Choisi parmi trois propositions « premium » (Verre, Relief, Nuit). C'est l'évolution du design A, avec de la
profondeur et les coins continus des interfaces Apple (`corner-shape: squircle`), dessinés dans les fonds de page :
- **Rail marine flottant** (détaché des bords, reflets et ombre) : la page active est un bouton blanc en relief ;
  la dernière actualisation est dans un encart en creux.
- **Cartes blanches en relief** : ombres en plusieurs couches, lumière venant du haut.
- **Filtres et période dans des champs en creux** : la période choisie est une tuile blanche ; *More filters* et
  *Back* sont des boutons en relief dessinés (leurs zones de texte sont masquées).
- **Overview** : icônes 3D (dégradé, reflet, ombre colorée) sur les trois chiffres clés, tuile « Where do inspections
  fail? » en carte marine en relief, sélecteur Part / Test en contrôle segmenté.
- **Accueil** : tuiles des pages en relief, panneau marine avec des colonnes 3D isométriques, chiffres clés en
  pastilles, dernière actualisation.
Les visuels gardent leur rendu Power BI (Segoe UI, graphiques à plat) par-dessus.

`design_r.py` contient la géométrie et les fonds ; `apply_design_r.py` déplace les visuels d'un `.pbix` en design A
(V14) vers la géométrie Relief et ajuste leur style. Le modèle et les données sont gardés : la sortie est un `.pbix`,
`out/Plant visual management dashboard Relief.pbix`.

## V15 : le cumul partout, tous les filtres sur toutes les pages

Demande client : chaque visuel montre le cumul de la sélection, aucun visuel ne se limite à une période, chaque filtre
s'applique partout.
- Aucun visuel n'avait de filtre de période propre (vérifié : filtres de visuel, de page et de rapport, interactions,
  mesures à fenêtre fixe). Les chiffres clés, jauges, tableaux, barres et le Cpk étaient déjà des totaux de la
  sélection.
- **Graphiques dans le temps en cumul** (`cumul_model.py`) : à chaque point, le total depuis le début de la période
  choisie (et des dates, et des autres filtres) jusqu'à ce point. Overview : *Cumulative pass %* par mois ;
  Characteristics : *Pass & Fail · cumulative* par jour, et les deux cartes à courbe (le chiffre reste le total de la
  période, la courbe devient cumulée) ; Reaction limits : violations cumulées par jour. Le Trend chart reste la suite
  des valeurs mesurées de la période (un cumul de valeurs mesurées n'aurait pas de sens) ; son Cpk est celui de toute
  la période.
- **Tous les filtres sur toutes les pages d'analyse**, pages de détail comprises (Plant, Part, Test, Characteristic,
  Inspection reason, Date, Period, KPC, Press, Cpk threshold, Cpk status) : là où une page ne montre pas un filtre,
  une copie masquée du segment (même groupe de synchronisation) applique la sélection faite ailleurs. Cpk threshold et
  Cpk status reçoivent un groupe de synchronisation. La page d'accueil n'est pas filtrée.

`add_cumulative.py` part du `.pbix` Relief ; le modèle reçoit six mesures cumulées, la sortie est donc un modèle
`.pbit` : `out/Plant visual management dashboard V15.pbit`.

## V16 : page d'accueil, tuiles avec aperçu et pièce contrôlée

- **Tuiles de navigation** dans le style demandé : aperçu miniature de la page, numéro, nom, question, contenu de la
  page en une ligne, bouton rond marine en relief.
- **Panneau marine** : un véhicule et ses points de mesure (jeu et affleurement, ajustement du bouclier et du hayon,
  épaisseur de peinture, un point hors tolérance), choisi parmi quatre images (carte de contrôle, capabilité, usine
  connectée, pièce contrôlée : `design_r.ARTS`, choix dans `design_r.HOME_ART`).

`update_home_r.py` replace les boutons des tuiles et remplace le fond de la page d'accueil d'un rapport Relief
(`.pbix` ou `.pbit`) ; le reste est gardé. Sortie : `out/Plant visual management dashboard V16.pbit` depuis la V15.

## V17 / V18 : Overview avec les chiffres clés en haut, filtres centrés

- **Overview** : *Pass rate*, *Failed inspections*, *Fail rate* et *Gap to target* forment la première rangée (même
  style : icône 3D, nom, chiffre, ligne sous le chiffre). En dessous : *Cumulative pass %* et la tuile « Where do
  inspections fail? » à gauche ; la jauge (titrée *Pass rate vs 95 % target*, avec la période choisie) et le tableau
  des résultats avec son sélecteur Part / Test à droite.
- **Rangée des filtres** (toutes les pages) : V17 avait des champs plus hauts (54 px) ; à la demande du client, V18
  revient aux champs de 44 px. Les segments y font 30 px (au lieu de 25) sous leur nom, avec l'option *responsive*
  désactivée : Power BI ne les replie plus en icône d'entonnoir quand ils sont bas. La valeur des listes est centrée,
  le filtre de dates montre ses deux dates (texte en 9 pt).

`update_layout_r.py` applique ces changements à un rapport Relief (`.pbix` ou `.pbit`, modèle et données gardés)
après le rendu des fonds Relief (étape 11) : `out/Plant visual management dashboard V18.pbix` depuis la V17.

## V19 : retours client du 26-27/11 (filtres, limites du Trend chart)

1. **More filters montre sa sélection** : un badge orange à droite du bouton *More filters* donne le nombre de ses
   filtres qui ont une sélection ; rien quand aucun (mesures `filters_model.py`, un jeu par panneau).
2. **Clear filters vide aussi More filters** : le bouton « Clear all slicers » de Power BI ignore les segments masqués,
   et ceux du panneau le sont tant qu'il est fermé. Chaque filtre qu'une page n'affiche pas y a une copie visible de
   4 px, dans le coin en haut à gauche, à la couleur de la page (même groupe de synchronisation) : Clear filters la
   vide et la synchronisation vide les segments masqués. Clear filters passe aussi au-dessus du panneau et de son voile,
   qui prenait le clic quand le panneau était ouvert. Les copies masquées de la V15 sont remplacées par ces copies.
3. **Noms des process** : nouveau filtre *Process name* (colonne `procedure_reference`, `Quality Tracker[Process Name]`)
   dans le panneau More filters de chaque page.
4. **Limites UCL / LCL** : la table stocke les limites d'alerte (`limit_min_alert`, `limit_max_alert`) en millièmes de
   l'unité des valeurs, avec 3 décimales (rapport médian UCL / USL de 0,001 sur les données de novembre). La requête
   les multiplie par 1 000 : Trend chart et *Reaction limit details* sont à la bonne échelle. Précision : l'unité près,
   à corriger dans la source (et retirer alors ce facteur).

`update_filters_v19.py` part du `.pbix` Relief du client ; le modèle reçoit la colonne et les mesures, la sortie est un
modèle `.pbit` : `out/Plant visual management dashboard V19.pbit`.

## Logo

La pastille en haut du rail contient le symbole OP en blanc, entre deux pointillés de limites (USL / LSL). Le logo
complet, en blanc, ouvre la ligne au-dessus du titre. Le logo n'est pas stocké dans ce dépôt public :
`make_logo_assets.py <logo.png>` en crée les versions blanches et marine (`logo_navy.png`, accueil du design A) dans
`out/brand/` (ignoré par git), en recolorant seulement les formes du logo d'origine. Sans ces fichiers, les fonds reprennent l'icône et le texte d'origine.

## Régénérer

0. Versions blanches et marine du logo (une fois) :
   ```bash
   python make_logo_assets.py <logo.png>
   ```
1. Rendre les fonds de page (Chromium via Playwright) :
   ```bash
   python -c "import design; [open(f'out/bg_{p}.html','w').write(design.page_html(p)) for p in design.PAGES]"
   ```
   ```bash
   node tools/render_backgrounds.js out/bg_home.html out/bg_home.png out/bg_overview.html out/bg_overview.png out/bg_chars.html out/bg_chars.png out/bg_rl.html out/bg_rl.png out/bg_cpk.html out/bg_cpk.png out/bg_rl_details.html out/bg_rl_details.png out/bg_trend.html out/bg_trend.png
   ```
2. Appliquer le design au `.pbix` V2 enregistré par Power BI Desktop (format PBIR) :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python restyle.py <V2.pbix>
   ```
3. Ajouter la page 3 au `.pbix` V3 enregistré par Power BI Desktop :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_reaction_limits.py <V3.pbix> --range 2025-01-01 2030-01-01
   ```
4. Ajouter la page d'accueil et la page Cpk au `.pbix` qui contient les pages 1 à 3 :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_home_and_cpk.py <V8.pbix> --range 2026-01-01 2026-02-01
   ```
5. Appliquer les retours client (V10 : Overview, filtre de période) au `.pbix` V9, après l'étape 1 :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_period_filter.py <V9.pbix> --range 2026-01-01 2026-02-01
   ```
6. Ajouter la page 5 « Trend chart » au `.pbix` V10, après l'étape 1 :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_trend_page.py <V10.pbix> --range 2026-01-01 2026-02-01
   ```
7. Page d'accueil sans bandeau de navigation, dans le `.pbix` V11, après l'étape 1 (modèle et données gardés) :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_home_page.py <V11.pbix>
   ```
8. Remplacer seulement les fonds de page d'un `.pbix`, sans toucher au modèle, aux données ni aux visuels :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_backgrounds.py <V4.pbix>
   ```

9. Design A (modèles OPmobility), après l'étape 0 : rendre ses fonds de page, puis l'appliquer au `.pbix` du
   rapport (modèle et données gardés). Le fond d'Overview a déjà la mise en page V13 : enchaîner avec l'étape 10.
   ```bash
   python -c "import design_a as A; [open(f'out/bg_a_{p}.html','w').write(A.render_html(p)) for p in A.D.PAGES]"
   ```
   ```bash
   node tools/render_backgrounds.js out/bg_a_home.html out/bg_a_home.png out/bg_a_overview.html out/bg_a_overview.png out/bg_a_chars.html out/bg_a_chars.png out/bg_a_rl.html out/bg_a_rl.png out/bg_a_cpk.html out/bg_a_cpk.png out/bg_a_rl_details.html out/bg_a_rl_details.png out/bg_a_trend.html out/bg_a_trend.png out/bg_a_fails.html out/bg_a_fails.png
   ```
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python apply_design_a.py "<Plant visual management dashboard.pbix>"
   ```

10. Chiffres clés d'Overview et page « Failure breakdown » (V13), après l'étape 9 (fonds `bg_a_*` rendus, dont
    `bg_a_fails`) :
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_overview_figures.py "<Plant visual management dashboard A.pbix>" --range 2026-11-01 2026-12-01
    ```

11. Design Relief, sur le `.pbix` V14 (design A, après l'étape 10) : rendre ses fonds de page, puis l'appliquer :
    ```bash
    python -c "import design_r as R; [open(f'out/bg_r_{p}.html','w').write(R.render_html(p)) for p in R.D.PAGES]"
    ```
    ```bash
    node tools/render_backgrounds.js out/bg_r_home.html out/bg_r_home.png out/bg_r_overview.html out/bg_r_overview.png out/bg_r_chars.html out/bg_r_chars.png out/bg_r_rl.html out/bg_r_rl.png out/bg_r_rl_details.html out/bg_r_rl_details.png out/bg_r_cpk.html out/bg_r_cpk.png out/bg_r_trend.html out/bg_r_trend.png out/bg_r_fails.html out/bg_r_fails.png
    ```
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python apply_design_r.py "<V14.pbix>"
    ```

12. Le cumul partout et tous les filtres sur toutes les pages (V15), sur le `.pbix` Relief :
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python add_cumulative.py "<Relief.pbix>" --range 2026-11-01 2026-12-01
    ```

13. Page d'accueil Relief (V16), sur un rapport Relief (`.pbix` ou `.pbit`) :
    ```bash
    python -c "import design_r as R; open('out/bg_r_home.html','w').write(R.render_html('home'))"
    ```
    ```bash
    node tools/render_backgrounds.js out/bg_r_home.html out/bg_r_home.png
    ```
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_home_r.py "<Plant visual management dashboard V15.pbit>"
    ```

14. Overview avec les chiffres clés en haut et filtres centrés (V17), sur un rapport Relief, après le rendu des fonds
    Relief (étape 11) :
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_layout_r.py "<V16.pbix>"
    ```

15. Retours du 26-27/11 (V19), sur le `.pbix` Relief, après le rendu des fonds Relief (étape 11) :
    ```bash
    PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_filters_v19.py "<Relief.pbix>" --range 2026-11-01 2026-12-01
    ```

`restyle.py` vérifie chaque propriété de mise en forme écrite contre le catalogue officiel des visuels Power BI
(`@microsoft/powerbi-core-visual-schema`). Il vérifie aussi que chaque visuel ciblé par un signet existe toujours.
La géométrie est définie une seule fois, dans `design.py`, et partagée par le fond de page et les visuels.

## Variante Power Query (pour comparer)

`build_pq_template.py` produit `out/Quality_Dashboard_V3_PQ.pbit`, avec le même rapport et les mêmes mesures.
La requête Quality Tracker ne contient plus de SQL écrit à la main : elle lit la table avec le navigateur
Databricks, et chaque règle de la version SQL devient une étape Power Query.

| Étapes | Rôle |
|---|---|
| `Keep 20 columns`, `Filter period`, `Sort rows` | Power Query les traduit lui-même en requête Databricks (*query folding*). Sans cela, chaque actualisation téléchargerait toute la table. |
| `Stop folding` | Tout ce qui suit est calculé par Power BI, et non par Databricks. |
| `Add Month` … `Add RL USL` | Les mêmes règles que la requête SQL, une étape par règle. |

Différences de modèle :
- `Inspection ID` est un texte (*clé ordre-plan-indice | test | date-heure*), alors que la version SQL le réduit à un
  entier avec `xxhash64` ;
- le rapport V3 n'a ni pages Cpk et Trend chart ni filtre de période, donc les colonnes faites pour elles
  (*Cpk sums*, `Measured Value`, `Measured At`, `Period Key`) ne sont pas calculées.

Les noms des autres colonnes ne changent pas : le rapport n'est pas modifié.

```bash
python build_pq_template.py <V3.pbix> --range 2025-01-01 2030-01-01
```

Le script reconstruit le modèle et le valide avec la bibliothèque Microsoft Tabular Object Model. Il vérifie aussi
que chaque champ utilisé par le rapport existe dans le modèle. `--range` préremplit `RangeStart` et `RangeEnd`.
