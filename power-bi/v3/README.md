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

## Logo

La pastille en haut du rail contient le symbole OP en blanc, entre deux pointillés de limites (USL / LSL). Le logo
complet, en blanc, ouvre la ligne au-dessus du titre. Le logo n'est pas stocké dans ce dépôt public :
`make_logo_assets.py <logo.png>` en crée les versions blanches dans `out/brand/` (ignoré par git), en recolorant
seulement les formes du logo d'origine. Sans ces fichiers, les fonds reprennent l'icône et le texte d'origine.

## Régénérer

0. Versions blanches du logo (une fois) :
   ```bash
   python make_logo_assets.py <logo.png>
   ```
1. Rendre les fonds de page (Chromium via Playwright) :
   ```bash
   python -c "import design; [open(f'out/bg_{p}.html','w').write(design.page_html(p)) for p in design.PAGES]"
   ```
   ```bash
   node tools/render_backgrounds.js out/bg_home.html out/bg_home.png out/bg_overview.html out/bg_overview.png out/bg_chars.html out/bg_chars.png out/bg_rl.html out/bg_rl.png out/bg_cpk.html out/bg_cpk.png out/bg_rl_details.html out/bg_rl_details.png
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
6. Remplacer seulement les fonds de page d'un `.pbix`, sans toucher au modèle, aux données ni aux visuels :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python update_backgrounds.py <V4.pbix>
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
- le rapport V3 n'a ni page Cpk ni filtre de période, donc les colonnes *Cpk sums* et `Period Key` ne sont pas
  calculées.

Les noms des autres colonnes ne changent pas : le rapport n'est pas modifié.

```bash
python build_pq_template.py <V3.pbix> --range 2025-01-01 2030-01-01
```

Le script reconstruit le modèle et le valide avec la bibliothèque Microsoft Tabular Object Model. Il vérifie aussi
que chaque champ utilisé par le rapport existe dans le modèle. `--range` préremplit `RangeStart` et `RangeEnd`.
