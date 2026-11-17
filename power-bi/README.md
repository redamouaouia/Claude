# Quality Dashboard V1 – rebuilt report

| File | What it is |
|---|---|
| `Quality_Dashboard_V1.pbix` | *(not in git: contains production data)* Your report with the 4 mockup pages (Overview, Characteristics, Reaction limits, Cpk) and a hidden drill-through page "Reaction limits – details". Your previous 5 pages are kept, hidden, named `OLD – …`. The data model is unchanged. |
| `model_changes.tmdl` | Script that adds the 5 columns and 28 measures used by the new pages and sets one relationship to filter both ways. Nothing is deleted. |
| `Quality Dashboard theme.json` | Optional theme (colours, rounded white cards, shadow). The new visuals are already formatted without it. |
| `build/build_report.py` | Script that generated the pages. It can regenerate the layout from the original file. |
| `checks.local.md` | *(not in git)* Reference values from your current data and the counts behind the data findings. |

## Steps in Power BI Desktop (about 10 minutes)

1. **Open** `Quality_Dashboard_V1.pbix`. Until step 2 is done, the new visuals show *"Something's wrong with one or more fields"*. That is expected.
2. **Add the measures.** Open **TMDL view** (icon in the left bar), then **+ New tab**. Paste all of `model_changes.tmdl` and click **Apply**.
   - Optional: before applying, change `"ADR"` in the `Plant` column to the plant name users should see.
3. **Load 12 months for the gauge.** Go to **Transform data → Inspection Page → Source** (gear icon). In the SQL statement, change
   `p.DATUM >= DATEADD(MONTH, -4, GETDATE())` to `p.DATUM >= DATEADD(MONTH, -12, GETDATE())`, then click **Close & Apply**.
   Only the inspection table changes. `Query1` (2 M measured values) stays at 4 months.
4. **Refresh**, then optionally go to **View → Themes → Browse for themes** and pick `Quality Dashboard theme.json`.
5. **Check the numbers.** Compare what you see with the reference values in `checks.local.md`.
   That file is kept out of git because this repository is public.

6. **Try the interactions:**
   - **More filters** opens the side panel. **Close**, **✕** or a click on the dark area closes it.
   - The **Part | Test** switch on Overview changes the results table.
   - **Details ›** on Reaction limits: select a part in the treemap first, then click it.
   - **Clear all filters** in the side menu resets all filters.
7. **Save.** Once you're happy with the new pages, delete the `OLD – …` pages.

## Things I could not test (built outside Power BI Desktop)

- **Bookmarks** (More filters panel, Part/Test switch). If a button doesn't show or hide the right visuals:
  1. Open **View → Bookmarks** and **View → Selection**.
  2. Select the bookmark and show or hide the panel visuals.
  3. Click **… → Update**.
- **Drill-through.** If **Details ›** stays grey after you select a part, open the hidden page *Reaction limits – details* and drag `Query1 › Inspection Plan` into the **Drill through** well.
- **Decomposition tree** opens collapsed. Click **+** to expand Part › Test › Inspection reason. Its bars use the default blue; you can set them to orange under *Format → Bars*.

## Deliberate differences from the mockup

- **Part / Test – Pass & Fail % bars:** bar length = number of values, the labels show the %, and the count is in the tooltip. There's no number at the end of each bar.
- **Logo:** the side menu uses the text "OPmobility". Replace it with the official logo image (*Insert → Image*).
- **Plant:** QDA holds one plant, so Plant is a constant column (`ADR`).
- **Page 4 filter:** it uses *Part name*, as in the spec. It is not synced with *Part (inspection plan)* on pages 1–3.
- **Information button:** it has no action yet.

## Data findings (for whoever owns the SQL queries)

The counts behind each point are in `checks.local.md`.

1. **Cpk query marks characteristics "Fail" without a Cpk.** Some characteristics have no USL and no LSL, and the `Cpk Pass/Fail` CASE falls through to `ELSE 'Fail'`. The new measures leave them out. To fix it at the source, add `WHEN [USL] IS NULL AND [LSL] IS NULL THEN NULL` to that CASE.
2. **Missing Cpk threshold.** Method *"Cp / Cpk = 1.67 min."* has no `CPMIN` in `STDMETHODE`, so its characteristics get no threshold and no Pass/Fail.
3. **Cpk is now counted per characteristic** (part + test + characteristic). The old page counted measured values.
4. **Cpk doesn't follow the date filter.** It is computed in SQL over the whole loaded window (4 months). The date filter chooses which characteristics are shown, but it does not recalculate their Cpk.
5. **Some inspections in `Query1` have no row in `Inspection Page`.** They drop out as soon as a date, part or plant filter is used. The likely cause is that `Inspection Page` joins operations on `ip.VORGANG = p.SUCH2` only.
6. **Inspection reason spellings are mixed.** For example *Start Up / First Good Part*, *START_UP*, *START UP*. A mapping table would clean up the filter.
7. **Model clean-up.** The `Characteristics Page` table duplicates `Query1` and is related to nothing, so its slicers on the old Inspections page had no effect. You can delete it after removing the `OLD – …` pages.

## Model change worth knowing

The `Query1 → Inspection Page` relationship now filters **both directions**. That lets the characteristic filters (Key field label, KPC) also filter the inspection visuals on Overview. A Key field label filter on Overview means "inspections that contain at least one characteristic of that class".
