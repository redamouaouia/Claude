# Quality Dashboard V2 – une seule table Databricks

Source unique : `domain_qual_prd.gold.dp_cpower_qda_quality_tracker`, sur le SQL warehouse Databricks.
Cette version contient les pages **Overview** et **Characteristics**. Reaction limits, Cpk et le libellé
Key field label viendront ensuite.

## Ouvrir le modèle (template)

1. Double-cliquez sur `Quality_Dashboard_V2.pbit`. Power BI Desktop ouvre une fenêtre de paramètres, déjà remplie :

   | Paramètre | Rôle |
   |---|---|
   | `DatabricksHost` | Adresse du workspace Databricks |
   | `DatabricksHttpPath` | SQL warehouse utilisé pour lire la table |
   | `RangeStart` / `RangeEnd` | Période chargée **dans Power BI Desktop** (environ 1 mois, soit à peu près 4 M lignes) |

2. Cliquez sur **Charger**. Si Power BI demande une connexion, choisissez **Microsoft Entra ID**, puis
   **Se connecter** et **Connecter**. S'il demande l'autorisation d'exécuter une requête native, cliquez sur **Exécuter**.
3. Attendez la fin du chargement, qui prend quelques minutes, puis vérifiez les deux pages.
4. Faites **Fichier › Enregistrer sous** et enregistrez le rapport en `.pbix`.

Dans Desktop, seule la période `RangeStart`–`RangeEnd` est chargée, ce qui garde le fichier léger.
La jauge « 12 derniers mois » ne montre donc que cette période tant que le rapport n'est pas publié.

## Avant de publier (espace Pro)

1. Dans le volet **Données**, faites un clic droit sur **Quality Tracker** › **Actualisation incrémentielle**.
   Réglez **Archiver les données** à *12 mois* et **Actualiser de façon incrémentielle** à *7 jours*, puis cliquez sur **Appliquer**.
2. Publiez le rapport. Ensuite, dans le service Power BI, ouvrez les paramètres du modèle sémantique :
   - Dans **Informations d'identification de la source de données**, choisissez **OAuth2** et connectez-vous.
   - Dans **Actualisation planifiée**, vous pouvez programmer jusqu'à **8 actualisations par jour** en Pro.
3. La première actualisation dans le service charge les 12 mois (environ 47 M lignes, une seule fois).
   Les suivantes ne rechargent que les 7 derniers jours.

## Contenu du modèle

- **Quality Tracker** : une ligne par valeur mesurée. La requête SQL ne lit que 20 des 65 colonnes de la table.
  Elle calcule dans Databricks :
  - `Inspection Result`, à partir de `process_status` : OK → Pass, KO → Fail, NA → Not assessed ;
  - `Characteristic Result`, à partir de `characteristic_status` : OK → Pass, KO → Fail, NA → Not evaluated ;
  - `Inspection ID`, une empreinte de *ordre + plan + indice + test + date/heure* (749 535 inspections sur 12 mois) ;
  - `Part`, le plan d'inspection sans le suffixe `_PLANT` ;
  - `RL Violation`, qui vaut 1 si `characteristic_result` = « control limit violated » (pour la page Reaction limits) ;
  - `RL Time`, `RL Value`, `RL Low Limit`, `RL High Limit`, `RL LSL` et `RL USL` : la date et l'heure, la valeur,
    les limites de réaction et la tolérance, remplies seulement pour ces violations (page de détail).
- **Refresh Info** : l'heure de la dernière actualisation, en UTC.
- Les pourcentages Pass / Fail ne comptent que les résultats **Pass** et **Fail** : les inspections
  *Not assessed* et les valeurs *Not evaluated* sont exclues.

## Régénérer le template

```bash
python build_template.py <un .pbix existant> databricks.local.json
```

`databricks.local.json` (non versionné) contient l'adresse du warehouse et la période Desktop.
Le script valide le modèle avec la bibliothèque Microsoft Tabular Object Model (`tools/tmdl2json`, .NET 8).
