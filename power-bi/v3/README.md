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

## Régénérer

1. Rendre les fonds de page (Chromium via Playwright) :
   ```bash
   python -c "import design; [open(f'out/bg_{p}.html','w').write(design.page_html(p)) for p in design.PAGES]"
   ```
   ```bash
   node tools/render_backgrounds.js out/bg_overview.html out/bg_overview.png out/bg_chars.html out/bg_chars.png
   ```
2. Appliquer le design au `.pbix` V2 enregistré par Power BI Desktop (format PBIR) :
   ```bash
   PBI_VISUAL_SCHEMA_DIR=<node_modules>/@microsoft/powerbi-core-visual-schema/data python restyle.py <V2.pbix>
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
| `Keep 15 columns`, `Filter period`, `Sort rows` | Power Query les traduit lui-même en requête Databricks (*query folding*). Sans cela, chaque actualisation téléchargerait toute la table. |
| `Stop folding` | Tout ce qui suit est calculé par Power BI, et non par Databricks. |
| `Add Month` … `Add RL Violation` | Les mêmes règles que la requête SQL, une étape par règle. |

Seule différence de modèle : `Inspection ID` est un texte (*clé ordre-plan-indice | test | date-heure*), alors que
la version SQL le réduit à un entier avec `xxhash64`. Les noms de colonnes ne changent pas : le rapport n'est pas modifié.

```bash
python build_pq_template.py <V3.pbix> --range 2025-01-01 2030-01-01
```

Le script reconstruit le modèle et le valide avec la bibliothèque Microsoft Tabular Object Model. Il vérifie aussi
que chaque champ utilisé par le rapport existe dans le modèle. `--range` préremplit `RangeStart` et `RangeEnd`.
