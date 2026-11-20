"""Quality Dashboard V2: one Databricks table, pages Overview and Characteristics, packaged as a .pbit.

Usage:  python build_template.py <original .pbix> [settings.json]

- <original .pbix> is only used to copy the Power BI version files and the base theme.
- settings.json (default: databricks.local.json, git-ignored) holds the SQL warehouse host / HTTP path
  and the date range loaded in Power BI Desktop (RangeStart / RangeEnd).
Outputs go to ./out (git-ignored): model/ (TMDL), DataModelSchema.json, Quality_Dashboard_V2.pbit.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import uuid
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "build"))
import build_report as br  # noqa: E402  (shared visual helpers)
from build_report import (  # noqa: E402
    ASC, BLUE, CARD_BORDER, DESC, MUTED, NAV_ACTIVE, NAV_SUB, NAVY, ORANGE, ROW_SLICER_H, ROW_SLICER_Y, TEXT, WHITE,
    Page, b, bookmark, button, col, color, d, distribute, donut, hexid, in_filter, kpi_card, l, link_bookmark,
    link_clear, link_page, mea, meta, para, pass_fail_table, props, run, s, set_link, slicer, stacked_pass_fail,
    textbox, vc_card, vc_plain, visual,
)

T = "Quality Tracker"
SOURCE_TABLE = "domain_qual_prd.gold.dp_cpower_qda_quality_tracker"

# --------------------------------------------------------------------------- source query (Databricks SQL)
# One row per measured value. Pass / Fail labels, the inspection key and the reaction-limit flag are computed
# in Databricks so that Power BI only stores small, well-compressed columns.
SQL_LINES = [
    "SELECT",
    "  plant AS `Plant`,",
    "  posting_date AS `Date`,",
    "  CAST(date_trunc('MONTH', posting_date) AS DATE) AS `Month`,",
    "  CASE WHEN endswith(key_inspection_plan_plant, concat('_', plant))",
    "       THEN left(key_inspection_plan_plant, length(key_inspection_plan_plant) - length(plant) - 1)",
    "       ELSE key_inspection_plan_plant END AS `Part`,",
    "  process AS `Test`,",
    "  characteristic AS `Characteristic`,",
    "  CASE characteristic_status WHEN 'OK' THEN 'Pass' WHEN 'KO' THEN 'Fail' ELSE 'Not evaluated' END"
    " AS `Characteristic Result`,",
    "  CASE process_status WHEN 'OK' THEN 'Pass' WHEN 'KO' THEN 'Fail' ELSE 'Not assessed' END AS `Inspection Result`,",
    "  xxhash64(key_order_inspection_plan_index_plant, process_id, date_time) AS `Inspection ID`,",
    "  NULLIF(trim(reason_for_inspection), '') AS `Inspection Reason`,",
    "  NULLIF(trim(bmm_machine), '') AS `Press`,",
    "  kpc AS `KPC`,",
    "  key_kpc AS `Key KPC Code`,",
    "  CASE WHEN characteristic_result = 'control limit violated' THEN 1 ELSE 0 END AS `RL Violation`,",
    # Detail of a reaction-limit violation, for the details page. Empty on the other ~99 % of the rows,
    # so these columns cost almost nothing in the model.
    *[f"  CASE WHEN characteristic_result = 'control limit violated' THEN {src} END AS `{name}`{sep}"
      for (src, name), sep in zip([("date_time", "RL Time"), ("characteristic_value_num", "RL Value"),
                                   ("limit_min_alert", "RL Low Limit"), ("limit_max_alert", "RL High Limit"),
                                   ("lsl_inspection_plan", "RL LSL"), ("usl_inspection_plan", "RL USL")],
                                  [","] * 5 + [""])],
    f"FROM {SOURCE_TABLE}",
]
SQL_WHERE = "WHERE posting_date >= DATE'{start}' AND posting_date < DATE'{end}'"
SQL_ORDER = "ORDER BY `Plant`, `Date`, `Inspection ID`"

COLUMNS = [  # (name, TMDL dataType, M type, hidden, format)
    ("Plant", "string", "type text", False, None),
    ("Date", "dateTime", "type date", False, "dd/MM/yyyy"),
    ("Month", "dateTime", "type date", False, "MMM yy"),
    ("Part", "string", "type text", False, None),
    ("Test", "string", "type text", False, None),
    ("Characteristic", "string", "type text", False, None),
    ("Characteristic Result", "string", "type text", False, None),
    ("Inspection Result", "string", "type text", False, None),
    ("Inspection ID", "int64", "Int64.Type", True, "0"),
    ("Inspection Reason", "string", "type text", False, None),
    ("Press", "string", "type text", False, None),
    ("KPC", "string", "type text", False, None),
    ("Key KPC Code", "int64", "Int64.Type", True, "0"),
    ("RL Violation", "int64", "Int64.Type", True, "0"),
    ("RL Time", "dateTime", "type datetime", False, "dd/MM/yyyy HH:mm"),
    ("RL Value", "double", "type number", False, "0.####"),
    ("RL Low Limit", "double", "type number", False, "0.####"),
    ("RL High Limit", "double", "type number", False, "0.####"),
    ("RL LSL", "double", "type number", False, "0.####"),
    ("RL USL", "double", "type number", False, "0.####"),
]
RL_DETAIL = "Only filled for values outside the reaction limits (RL Violation = 1)."
COLUMN_INFO = {  # name: (display folder, description)
    "RL Time": ("Reaction limit details", "Date and time of the measurement. " + RL_DETAIL),
    "RL Value": ("Reaction limit details", "Measured value. " + RL_DETAIL),
    "RL Low Limit": ("Reaction limit details", "Lower reaction (alert) limit. " + RL_DETAIL),
    "RL High Limit": ("Reaction limit details", "Upper reaction (alert) limit. " + RL_DETAIL),
    "RL LSL": ("Reaction limit details", "Lower specification limit of the inspection plan. " + RL_DETAIL),
    "RL USL": ("Reaction limit details", "Upper specification limit of the inspection plan. " + RL_DETAIL),
}


def m_text(t):
    return '"' + t.replace('"', '""') + '"'


def m_source():
    lines = [f"        {m_text(x)}," for x in SQL_LINES]
    where = ('        "WHERE posting_date >= DATE\'" & StartDate & "\' AND posting_date < DATE\'" & EndDate & "\'",')
    lines += [where, f"        {m_text(SQL_ORDER)}"]
    types = ",\n        ".join("{" + m_text(c[0]) + ", " + c[2] + "}" for c in COLUMNS)
    return "\n".join([
        "let",
        "    // Power BI Desktop loads RangeStart..RangeEnd only; the service loads 12 months (incremental refresh).",
        '    StartDate = Date.ToText(Date.From(RangeStart), [Format = "yyyy-MM-dd"]),',
        '    EndDate = Date.ToText(Date.From(RangeEnd), [Format = "yyyy-MM-dd"]),',
        "    Sql = Text.Combine({",
        *lines,
        '    }, "#(lf)"),',
        "    Source = Databricks.Query(DatabricksHost, DatabricksHttpPath,"
        " [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]),",
        "    Result = Source(Sql),",
        "    Typed = Table.TransformColumnTypes(Result, {",
        "        " + types,
        "    })",
        "in",
        "    Typed",
    ])


REFRESH_M = "\n".join([
    "let",
    '    Source = #table(type table [#"Refreshed At" = datetime], {{DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow())}})',
    "in",
    "    Source",
])

# --------------------------------------------------------------------------- measures (DAX)
MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Inspections", "DISTINCTCOUNT('Quality Tracker'[Inspection ID])", "#,0", "Inspections",
     "Number of inspections (one result per test on a part).", None),
    ("Inspections Pass", "IF(\n\tNOT ISBLANK([Inspections]),\n\tCALCULATE([Inspections], KEEPFILTERS("
     "'Quality Tracker'[Inspection Result] = \"Pass\")) + 0\n)", "#,0", "Inspections", None, None),
    ("Inspections Fail", "IF(\n\tNOT ISBLANK([Inspections]),\n\tCALCULATE([Inspections], KEEPFILTERS("
     "'Quality Tracker'[Inspection Result] = \"Fail\")) + 0\n)", "#,0", "Inspections", None, None),
    ("Inspections Assessed", "[Inspections Pass] + [Inspections Fail]", "#,0", "Inspections",
     "Inspections with a Pass or Fail result (not assessed ones are left out of the percentages).", None),
    ("Inspection Pass %", "DIVIDE([Inspections Pass], [Inspections Assessed])", "0.0%", "Inspections", None, None),
    ("Inspection Fail %", "DIVIDE([Inspections Fail], [Inspections Assessed])", "0.0%", "Inspections", None, None),
    ("Inspection Pass % 12M", "CALCULATE(\n\t[Inspection Pass %],\n\tALLEXCEPT('Quality Tracker', "
     "'Quality Tracker'[Plant]),\n\t'Quality Tracker'[Date] > EDATE(TODAY(), -12),\n\t'Quality Tracker'[Date] <= "
     "TODAY()\n)", "0.0%", "Inspections", "Gauge: last 12 months rolling, follows the Plant filter only.", None),
    ("Pass % Target", "0.95", "0%", "Inspections", None, None),
    ("Measured Values", "COUNTROWS('Quality Tracker')", "#,0", "Characteristics", "Number of measured values.", None),
    ("Char Pass", "IF(\n\tNOT ISBLANK([Measured Values]),\n\tCALCULATE([Measured Values], KEEPFILTERS("
     "'Quality Tracker'[Characteristic Result] = \"Pass\")) + 0\n)", "#,0", "Characteristics", None, None),
    ("Char Fail", "IF(\n\tNOT ISBLANK([Measured Values]),\n\tCALCULATE([Measured Values], KEEPFILTERS("
     "'Quality Tracker'[Characteristic Result] = \"Fail\")) + 0\n)", "#,0", "Characteristics", None, None),
    ("Char Evaluated", "[Char Pass] + [Char Fail]", "#,0", "Characteristics",
     "Measured values with a Pass or Fail result (not evaluated ones are left out of the percentages).", None),
    ("Char Pass %", "DIVIDE([Char Pass], [Char Evaluated])", "0.0%", "Characteristics", None, None),
    ("Char Fail %", "DIVIDE([Char Fail], [Char Evaluated])", "0.0%", "Characteristics", None, None),
    ("Char Pass Bar", "[Char Pass]", None, "Bars", "Bar length = number of values, label = share of the bar.",
     '"""" & FORMAT([Char Pass %], "0.0%") & """"'),
    ("Char Fail Bar", "[Char Fail]", None, "Bars", None, '"""" & FORMAT([Char Fail %], "0.0%") & """"'),
    ("Last Refresh", "\"Last refresh · \" & FORMAT(MAX('Refresh Info'[Refreshed At]), \"dd/mm/yyyy hh:nn\") & \" UTC\"",
     None, "Report", None, None),
    # Reaction limits (page 3): a violation is a measured value that passes but is outside the reaction limits.
    ("RL Violations", "SUM('Quality Tracker'[RL Violation])", "#,0", "Reaction limits",
     "Measured values that pass but are outside the reaction (alert) limits.", None),
    ("RL Share", "DIVIDE([RL Violations], CALCULATE([RL Violations], ALLSELECTED()))", "0.0%", "Reaction limits",
     "Share of all the violations in the current selection.", None),
    ("RL Violation %", "DIVIDE([RL Violations], [Char Evaluated])", "0.00%", "Reaction limits",
     "Violations out of the evaluated values (Pass + Fail).", None),
    ("RL Summary", "IF(\n\tISBLANK([Measured Values]),\n\t\"No measured values in this selection\",\n\t"
     "FORMAT([RL Violations], \"#,0\") & \" values outside the reaction limits · \" & FORMAT([RL Violation %], "
     "\"0.00%\") & \" of evaluated values\"\n)", None, "Reaction limits",
     "Subtitle of the violations-per-day chart.", None),
    ("RL Details Title", "VAR part = SELECTEDVALUE('Quality Tracker'[Part])\nRETURN\n\tIF(ISBLANK(part), \"All parts\", "
     "\"Part \" & part) & \" · \" & FORMAT([RL Violations] + 0, \"#,0\") & \" values outside the reaction limits\"",
     None, "Reaction limits", "Context line of the details page (the part chosen with the Details button).", None),
]


def tmdl_name(n):
    return n if n.replace("_", "").isalnum() and not n[0].isdigit() else "'" + n.replace("'", "''") + "'"


def tmdl_expr(text, indent):
    """Single line stays inline; multi-line goes below the declaration, one level deeper than the properties."""
    if "\n" not in text:
        return " " + text, []
    pad = "\t" * indent
    return "", [pad + line for line in text.split("\n")]


def write_model(out, settings, source_m=None, columns=None):
    """TMDL model in out/model. source_m / columns replace the Quality Tracker query and column list (variants)."""
    source_m = source_m or m_source()
    columns = columns or COLUMNS
    model_dir = out / "model"
    if model_dir.exists():
        shutil.rmtree(model_dir)
    (model_dir / "tables").mkdir(parents=True)
    (model_dir / "database.tmdl").write_text("database 'Quality Dashboard'\n\tcompatibilityLevel: 1601\n\n")
    (model_dir / "model.tmdl").write_text(
        "model Model\n\tculture: en-US\n\n"
        "\tannotation __PBI_TimeIntelligenceEnabled = 0\n\n"
        '\tannotation PBI_QueryOrder = ["DatabricksHost","DatabricksHttpPath","RangeStart","RangeEnd",'
        '"Quality Tracker","Refresh Info"]\n\n'
        "ref table 'Quality Tracker'\nref table 'Refresh Info'\n\n")

    rs = settings["range_start"].split("-")
    re_ = settings["range_end"].split("-")
    params = [
        ("DatabricksHost", m_text(settings["host"]), "Text"),
        ("DatabricksHttpPath", m_text(settings["http_path"]), "Text"),
        ("RangeStart", f"#datetime({int(rs[0])}, {int(rs[1])}, {int(rs[2])}, 0, 0, 0)", "DateTime"),
        ("RangeEnd", f"#datetime({int(re_[0])}, {int(re_[1])}, {int(re_[2])}, 0, 0, 0)", "DateTime"),
    ]
    exp = []
    for name, value, typ in params:
        exp += [f'expression {name} = {value} meta [IsParameterQuery=true, Type="{typ}", IsParameterQueryRequired=true]',
                f"\tlineageTag: {uuid.uuid4()}", "", f"\tannotation PBI_ResultType = {typ}", ""]
    (model_dir / "expressions.tmdl").write_text("\n".join(exp) + "\n")

    lines = [f"table {tmdl_name(T)}", f"\tlineageTag: {uuid.uuid4()}", ""]
    for name, expr, fmt, folder, desc, dyn in MEASURES:
        if desc:
            lines.append(f"\t/// {desc}")
        inline, below = tmdl_expr(expr, 3)
        lines.append(f"\tmeasure {tmdl_name(name)} ={inline}")
        lines += below
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        if dyn:
            lines += ["", f"\t\tformatStringDefinition = {dyn}"]
        lines.append("")
    for name, dtype, m_type, hidden, fmt in columns:
        folder, desc = COLUMN_INFO.get(name, (None, None))
        if desc:
            lines.append(f"\t/// {desc}")
        lines.append(f"\tcolumn {tmdl_name(name)}")
        lines.append(f"\t\tdataType: {dtype}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        if hidden:
            lines.append("\t\tisHidden")
        if folder:
            lines.append(f"\t\tdisplayFolder: {folder}")
        lines += [f"\t\tlineageTag: {uuid.uuid4()}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {name}", "",
                  "\t\tannotation SummarizationSetBy = Automatic", ""]
        if m_type == "type date":
            lines[-1:-1] = ["\t\tannotation UnderlyingDateTimeDataType = Date", ""]
    lines += [f"\tpartition {tmdl_name(T)} = m", "\t\tmode: import", "\t\tsource ="]
    lines += ["\t\t\t\t" + x for x in source_m.split("\n")]
    lines += ["", "\tannotation PBI_ResultType = Table", ""]
    (model_dir / "tables" / f"{T}.tmdl").write_text("\n".join(lines) + "\n")

    refresh = [
        "table 'Refresh Info'", f"\tlineageTag: {uuid.uuid4()}", "",
        "\tcolumn 'Refreshed At'", "\t\tdataType: dateTime", "\t\tformatString: General Date", "\t\tisHidden",
        f"\t\tlineageTag: {uuid.uuid4()}", "\t\tsummarizeBy: none", "\t\tsourceColumn: Refreshed At", "",
        "\t\tannotation SummarizationSetBy = Automatic", "",
        "\tpartition 'Refresh Info' = m", "\t\tmode: import", "\t\tsource =",
        *["\t\t\t\t" + x for x in REFRESH_M.split("\n")], "",
        "\tannotation PBI_ResultType = Table", "",
    ]
    (model_dir / "tables" / "Refresh Info.tmdl").write_text("\n".join(refresh) + "\n")
    return model_dir


# --------------------------------------------------------------------------- report pages
F = {
    "plant": col(T, "Plant", "Plant"),
    "part": col(T, "Part", "Part (inspection plan)"),
    "test": col(T, "Test", "Test"),
    "char": col(T, "Characteristic", "Characteristic"),
    "reason": col(T, "Inspection Reason", "Inspection reason"),
    "date": col(T, "Date", "Date"),
    "month": col(T, "Month", "Month"),
    "press": col(T, "Press", "Press"),
    "kpc": col(T, "KPC", "KPC label"),
    "insp_result": col(T, "Inspection Result"),
    "insp": mea(T, "Inspections", "Inspections"),
    "insp_pass": mea(T, "Inspections Pass"),
    "insp_fail": mea(T, "Inspections Fail"),
    "insp_pass_pct": mea(T, "Inspection Pass %"),
    "insp_fail_pct": mea(T, "Inspection Fail %"),
    "pass12": mea(T, "Inspection Pass % 12M", "Pass %"),
    "target": mea(T, "Pass % Target", "Target"),
    "last_refresh": mea(T, "Last Refresh", "Last refresh"),
    "mv": mea(T, "Measured Values", "Measured values"),
    "c_eval": mea(T, "Char Evaluated", "Evaluated values"),
    "c_pass": mea(T, "Char Pass"),
    "c_fail": mea(T, "Char Fail"),
    "c_pass_pct": mea(T, "Char Pass %"),
    "c_fail_pct": mea(T, "Char Fail %"),
    "c_pass_bar": mea(T, "Char Pass Bar"),
    "c_fail_bar": mea(T, "Char Fail Bar"),
}
SLICERS = {  # key: (field, mode, sync group)
    "plant": ("plant", "Dropdown", "Plant"), "part": ("part", "Dropdown", "Part"),
    "test": ("test", "Dropdown", "Test"), "char": ("char", "Dropdown", "Characteristic"),
    "reason": ("reason", "Dropdown", "Inspection reason"), "date": ("date", "Between", "Date"),
    "press": ("press", "Dropdown", "Press"), "kpc": ("kpc", "Dropdown", "KPC"),
}
SEARCHABLE = {"part", "test", "char", "reason", "press"}
NAV = [("overview", "Overview"), ("chars", "Characteristics")]


def build_pages(bookmarks):
    pages = {k: Page(hexid(), t) for k, t in NAV}
    names = {k: p.name for k, p in pages.items()}

    def header(p, key, title, slicers, panel_slicers):
        p.add(textbox([para([run("", 10, WHITE)])], vc=vc_plain(bg=NAVY)), 0, 0, 196, 720)
        p.add(textbox([para([run("OP", 22, WHITE, True), run("mobility", 22, WHITE)])]), 14, 16, 178, 40)
        p.add(textbox([para([run("Quality Dashboard", 11, WHITE, True)]),
                       para([run("Plant Visual Management", 10, NAV_SUB)])]), 14, 60, 178, 44)
        for i, (k, label) in enumerate(NAV):
            active = k == key
            p.add(button(label, fill=NAV_ACTIVE if active else None, text_color=NAVY if active else WHITE, size=11,
                         bold=active, align="left", link=link_page(names[k]), hover_fill=None if active else WHITE),
                  14, 126 + i * 41, 168, 34)
        p.add(button("Clear all filters", outline=WHITE, text_color=WHITE, size=10, link=link_clear()),
              24, 645, 158, 29)
        p.add(textbox([para([run("ⓘ  Information", 10, WHITE)])]), 14, 684, 160, 24)
        p.add(textbox([para([run(title, 20, NAVY, True, "Segoe UI Semibold")])]), 204, 10, 420, 44)
        p.add(visual("card", {"Values": [F["last_refresh"]]},
                     objects={"labels": [props(color=color(NAVY), fontSize=d(9), fontFamily=s("Segoe UI"))],
                              "categoryLabels": [props(show=b(False))]},
                     vc=vc_card(None, radius=14, shadow=False, pad=(0, 0, 6, 6), header=False)),
              1055, 18, 210, 30)
        pos = distribute([w for _, w in slicers] + [0.62])
        for (sk, _), (x, w) in zip(slicers, pos):
            fk, mode, group = SLICERS[sk]
            p.add(slicer(F[fk], mode, sync=group, search=sk in SEARCHABLE), x, ROW_SLICER_Y, w, ROW_SLICER_H)
        mx, mw = pos[-1]
        more_btn = p.add(button(f"More filters ({len(panel_slicers)})", fill=WHITE, size=10, bold=True, radius=10),
                         mx, ROW_SLICER_Y, mw, ROW_SLICER_H)
        return lambda: more_filters_panel(p, title, panel_slicers, more_btn)

    def more_filters_panel(p, title, panel_slicers, more_btn):
        panel = {}
        overlay = p.add(button(None, fill=NAVY, fill_transp=72, radius=0, hidden=True), 0, 0, 980, 720)
        panel[overlay] = "actionButton"
        panel[p.add(textbox([para([run("More filters", 15, NAVY, True, "Segoe UI Semibold")]),
                             para([run("Opened with the “More filters” button. "
                                       "Selections apply to all pages.", 9, MUTED)])],
                            vc=dict(vc_plain(bg=WHITE),
                                    padding=[props(top=d(18), bottom=d(0), left=d(16), right=d(40))]),
                            hidden=True), 980, 0, 300, 720)] = "textbox"
        close_x = p.add(button("✕", size=13, text_color=NAVY, hidden=True), 1240, 14, 26, 26)
        panel[close_x] = "actionButton"
        y = 92
        for sk in panel_slicers:
            fk, mode, group = SLICERS[sk]
            panel[p.add(slicer(F[fk], mode, sync=group, hidden=True, panel=True, search=sk in SEARCHABLE),
                        996, y, 268, 54)] = "slicer"
            y += 62
        panel[p.add(button("Reset", outline=NAVY, size=10, bold=True, link=link_clear(), hidden=True),
                    996, y + 8, 128, 32)] = "actionButton"
        close_btn = p.add(button("Close", fill=NAVY, text_color=WHITE, size=10, bold=True, hidden=True),
                          1136, y + 8, 128, 32)
        panel[close_btn] = "actionButton"
        bm_open = bookmark(f"{title} – More filters open", p.name, {n: (t, False) for n, t in panel.items()})
        bm_close = bookmark(f"{title} – More filters closed", p.name, {n: (t, True) for n, t in panel.items()})
        bookmarks.extend([bm_open, bm_close])
        set_link(p, more_btn, link_bookmark(bm_open["name"]))
        for n in (overlay, close_x, close_btn):
            set_link(p, n, link_bookmark(bm_close["name"]))

    # ---------------- Page 1: Overview (inspections)
    p = pages["overview"]
    finish = header(p, "overview", "Overview",
                    [("plant", 1), ("part", 1.05), ("test", 1), ("reason", 1.05), ("date", 1.75)], ["press", "kpc"])
    p.add(visual("gauge", {"Y": [F["pass12"]], "TargetValue": [F["target"]]},
                 objects={"axis": [props(min=d(0), max=d(1))],
                          "dataPoint": [props(fill=color(BLUE), target=color(NAVY))],
                          "calloutValue": [props(show=b(True), color=color(BLUE), fontSize=d(24), labelPrecision=l(1))],
                          "labels": [props(show=b(True), color=color(MUTED), fontSize=d(9))],
                          "target": [props(show=b(True), color=color(MUTED), fontSize=d(9))]},
                 vc=vc_card("Pass % vs target – last 12 months")), 210, 126, 253, 244)
    pass_pct = F["insp_pass_pct"].as_("Pass %")
    p.add(visual("lineChart", {"Category": [F["month"]], "Y": [pass_pct, F["target"]]},
                 objects={
                     "categoryAxis": [props(axisType=s("Categorical"), showAxisTitle=b(False), gridlineShow=b(False),
                                            labelColor=color(MUTED), fontSize=d(9))],
                     "valueAxis": [props(showAxisTitle=b(False), gridlineShow=b(True), gridlineStyle=s("dotted"),
                                         gridlineColor=color(CARD_BORDER), labelColor=color(MUTED), end=d(1),
                                         fontSize=d(9))],
                     "legend": [props(show=b(True), position=s("TopLeft"), showTitle=b(False), fontSize=d(9))],
                     "dataPoint": [{"properties": {"fill": color(BLUE)}, "selector": meta(pass_pct.ref)},
                                   {"properties": {"fill": color(NAVY)}, "selector": meta(F["target"].ref)}],
                     "lineStyles": [{"properties": {"showMarker": b(True), "strokeWidth": l(2)},
                                     "selector": meta(pass_pct.ref)},
                                    {"properties": {"lineStyle": s("dashed"), "showMarker": b(False),
                                                    "strokeWidth": l(2)}, "selector": meta(F["target"].ref)}],
                     "labels": [props(show=b(True), color=color(TEXT), fontSize=d(9), labelPrecision=l(0)),
                                {"properties": {"showSeries": b(False)}, "selector": meta(F["target"].ref)}],
                 },
                 vc=vc_card("Pass % per month"), order=[(F["month"], ASC)]), 474, 126, 473, 244)
    p.add(donut(T, "Inspection Result", F["insp"], "Pass & Fail %"), 958, 126, 307, 244,
          filters=[in_filter(F["insp_result"], ["Pass", "Fail"])])
    p.add(visual("decompositionTreeVisual",
                 {"Analyze": [F["insp_fail"].as_("Fail count")],
                  "ExplainBy": [F["part"].as_("Part"), F["test"], F["reason"]]},
                 vc=vc_card("Where do inspections fail? (click + to drill down)")), 210, 383, 642, 324)
    n_test = p.add(pass_fail_table(F["test"], F["insp_pass_pct"], F["insp_pass"], F["insp_fail"], F["insp_fail_pct"],
                                   F["insp_fail"], "Results per test"), 863, 383, 402, 324)
    n_part = p.add(pass_fail_table(F["part"].as_("Part"), F["insp_pass_pct"], F["insp_pass"], F["insp_fail"],
                                   F["insp_fail_pct"], F["insp_fail"], "Results per part", hidden=True),
                   863, 383, 402, 324)
    sw = dict(size=9, radius=6)
    n_part_off = p.add(button("Part", fill="#F1F4F9", text_color=NAVY, **sw), 1164, 391, 46, 22)
    n_test_on = p.add(button("Test", fill=NAVY, text_color=WHITE, bold=True, **sw), 1212, 391, 46, 22)
    n_part_on = p.add(button("Part", fill=NAVY, text_color=WHITE, bold=True, hidden=True, **sw), 1164, 391, 46, 22)
    n_test_off = p.add(button("Test", fill="#F1F4F9", text_color=NAVY, hidden=True, **sw), 1212, 391, 46, 22)
    by_test = bookmark("Overview – Results per test", p.name, {
        n_test: ("tableEx", False), n_part: ("tableEx", True), n_part_off: ("actionButton", False),
        n_test_on: ("actionButton", False), n_part_on: ("actionButton", True), n_test_off: ("actionButton", True)})
    by_part = bookmark("Overview – Results per part", p.name, {
        n_test: ("tableEx", True), n_part: ("tableEx", False), n_part_off: ("actionButton", True),
        n_test_on: ("actionButton", True), n_part_on: ("actionButton", False), n_test_off: ("actionButton", False)})
    bookmarks.extend([by_test, by_part])
    set_link(p, n_part_off, link_bookmark(by_part["name"]))
    set_link(p, n_test_off, link_bookmark(by_test["name"]))
    finish()

    # ---------------- Page 2: Characteristics (measured values)
    p = pages["chars"]
    finish = header(p, "chars", "Characteristics",
                    [("plant", 0.85), ("part", 1.05), ("test", 0.95), ("char", 1.05), ("reason", 1.05),
                     ("date", 1.7)], ["kpc", "press"])
    p.add(kpi_card(F["c_pass_pct"].as_("Characteristic pass %"), "Characteristic pass %"), 210, 126, 253, 117)
    p.add(kpi_card(F["mv"], "Measured values"), 210, 253, 253, 117)
    p.add(visual("lineChart", {"Category": [F["date"]], "Y": [F["c_fail"].as_("Fail"), F["c_pass"].as_("Pass")]},
                 objects={
                     "categoryAxis": [props(showAxisTitle=b(False), gridlineShow=b(False), labelColor=color(MUTED),
                                            fontSize=d(9))],
                     "valueAxis": [props(showAxisTitle=b(False), gridlineShow=b(True), gridlineStyle=s("dotted"),
                                         gridlineColor=color(CARD_BORDER), labelColor=color(MUTED), fontSize=d(9))],
                     "legend": [props(show=b(True), position=s("TopLeft"), showTitle=b(False), fontSize=d(9))],
                     "dataPoint": [{"properties": {"fill": color(ORANGE)}, "selector": meta(F["c_fail"].ref)},
                                   {"properties": {"fill": color(BLUE)}, "selector": meta(F["c_pass"].ref)}],
                     "lineStyles": [props(showMarker=b(True), strokeWidth=l(2))],
                 },
                 vc=vc_card("Measured values per day – Pass & Fail"), order=[(F["date"], ASC)]),
          474, 126, 791, 244)
    p.add(stacked_pass_fail(F["part"].as_("Part"), F["c_fail_bar"], F["c_pass_bar"], F["c_eval"],
                            "Part – Pass & Fail %"), 210, 383, 337, 324)
    p.add(stacked_pass_fail(F["test"], F["c_fail_bar"], F["c_pass_bar"], F["c_eval"], "Test – Pass & Fail %"),
          556, 383, 337, 324)
    p.add(pass_fail_table(F["char"], F["c_pass_pct"], F["c_pass"], F["c_fail"], F["c_fail_pct"], F["c_fail_pct"],
                          "Results per characteristic"), 902, 383, 363, 324)
    finish()
    return [pages[k] for k, _ in NAV]


def build_layout(orig_layout, bookmarks):
    pages = build_pages(bookmarks)
    cfg = json.loads(orig_layout["config"])
    cfg.pop("linguisticSchemaSyncVersion", None)
    cfg["activeSectionIndex"] = 0
    cfg["bookmarks"] = bookmarks
    return {
        "id": 0,
        "resourcePackages": orig_layout["resourcePackages"],
        "sections": [pg.section(i) for i, pg in enumerate(pages)],
        "config": json.dumps(cfg, ensure_ascii=False),
        "layoutOptimization": 0,
        "publicCustomVisuals": [],
        "pods": [],
    }


# --------------------------------------------------------------------------- packaging
CONTENT_TYPES = ('﻿<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/'
                 'package/2006/content-types"><Default Extension="json" ContentType="" />'
                 '<Override PartName="/Version" ContentType="" /><Override PartName="/DataModelSchema" '
                 'ContentType="" /><Override PartName="/DiagramLayout" ContentType="" /><Override '
                 'PartName="/Report/Layout" ContentType="" /><Override PartName="/Settings" '
                 'ContentType="application/json" /><Override PartName="/Metadata" ContentType="application/json" '
                 '/></Types>')


def model_schema(model_dir, schema):
    """Validates the TMDL folder with Microsoft's Tabular Object Model and writes the DataModelSchema (TMSL)."""
    tool = HERE / "tools" / "tmdl2json"
    run_ = subprocess.run(["dotnet", "run", "-c", "Release", "--project", str(tool), "--", str(model_dir), str(schema)],
                          capture_output=True, text=True, env={**__import__("os").environ,
                                                               "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                                                               "DOTNET_NOLOGO": "1"})
    print(run_.stdout.strip())
    if run_.returncode != 0:
        print(run_.stderr[-3000:])
        sys.exit("model conversion failed")
    return json.loads(schema.read_bytes().decode("utf-16-le"))


def diagram_layout(model_json):
    tags = {t["name"]: t.get("lineageTag") for t in model_json["model"]["tables"]}
    return {"version": "1.1.0", "diagrams": [{
        "ordinal": 0, "scrollPosition": {"x": 0, "y": 0},
        "nodes": [{"location": {"x": 40 + 300 * i, "y": 40}, "nodeIndex": name, "nodeLineageTag": tag,
                   "size": {"height": 300, "width": 234}, "zIndex": 0} for i, (name, tag) in enumerate(tags.items())],
        "name": "All tables", "zoomValue": 100, "pinKeyFieldsToTop": False, "showExtraHeaderInfo": False,
        "hideKeyFieldsWhenCollapsed": False, "tablesLocked": False}],
        "selectedDiagram": "All tables", "defaultDiagram": "All tables"}


def main(src_pbix, settings_path):
    settings = json.loads(pathlib.Path(settings_path).read_text())
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    model_dir = write_model(out, settings)
    schema = out / "DataModelSchema.json"
    model_json = model_schema(model_dir, schema)

    zin = zipfile.ZipFile(src_pbix)
    orig_layout = json.loads(zin.read("Report/Layout").decode("utf-16-le"))
    bookmarks = []
    layout = build_layout(orig_layout, bookmarks)
    diagram = diagram_layout(model_json)

    theme = "Report/StaticResources/SharedResources/BaseThemes/CY26SU02.json"
    dst = out / "Quality_Dashboard_V2.pbit"
    entries = [
        ("Version", zin.read("Version")),
        ("[Content_Types].xml", CONTENT_TYPES.encode("utf-8")),
        ("DataModelSchema", schema.read_bytes()),
        ("DiagramLayout", json.dumps(diagram).encode("utf-16-le")),
        ("Report/Layout", json.dumps(layout, ensure_ascii=False).encode("utf-16-le")),
        ("Settings", zin.read("Settings")),
        ("Metadata", zin.read("Metadata")),
        (theme, zin.read(theme)),
    ]
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
    print(f"written {dst} ({dst.stat().st_size:,} bytes): {len(layout['sections'])} pages, {len(bookmarks)} bookmarks")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else HERE / "databricks.local.json")
