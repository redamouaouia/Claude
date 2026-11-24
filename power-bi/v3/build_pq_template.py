"""Quality Dashboard V3, Power Query variant, to compare with the SQL version.

Usage:  python build_pq_template.py <V3 .pbix> [settings.json] [--range START END]

- <V3 .pbix>: the V3 report saved by Power BI Desktop (PBIR format). Pages, visuals, bookmarks and page
  backgrounds are copied unchanged.
- settings.json (default: ../v2/databricks.local.json, git-ignored): SQL warehouse host and HTTP path.
- --range START END: RangeStart / RangeEnd prefilled in the template (default: the range of settings.json).

The model is the V2 model with one difference: the Quality Tracker query reads the table through the
Databricks navigator, and every rule of the SQL version is a Power Query step. Column names and measures
are the same, so the report works unchanged. Output: out/Quality_Dashboard_V3_PQ.pbit (git-ignored).
"""
import argparse
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "v2"))
import build_template as bt  # noqa: E402  (V2 model: measures, columns, TMDL writer, TOM validation)
import pbit_package as pkg  # noqa: E402

# Same rules as the SQL of the V2 / V3 model (build_template.SQL_LINES), written as Power Query steps.
# Power Query sends the first steps (columns, period, sort) to Databricks itself (query folding): without that,
# each refresh would download the whole table. "Stop folding" keeps every calculation after it in Power BI.
PQ_M = """let
    // Power Query version: no hand-written SQL, every rule is one of the steps below.
    Source = Databricks.Catalogs(DatabricksHost, DatabricksHttpPath, [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]),
    Catalog = Source{[Name = "domain_qual_prd"]}[Data],
    Schema = Catalog{[Name = "gold"]}[Data],
    Tracker = Schema{[Name = "dp_cpower_qda_quality_tracker"]}[Data],
    #"Keep 20 columns" = Table.SelectColumns(Tracker, {
        "plant", "posting_date", "key_inspection_plan_plant", "process", "characteristic",
        "characteristic_status", "process_status", "key_order_inspection_plan_index_plant", "process_id",
        "date_time", "reason_for_inspection", "bmm_machine", "kpc", "key_kpc", "characteristic_result",
        "characteristic_value_num", "limit_min_alert", "limit_max_alert", "lsl_inspection_plan", "usl_inspection_plan"
    }),
    // Power BI Desktop loads RangeStart..RangeEnd only; the service loads 12 months (incremental refresh).
    StartDate = Date.From(RangeStart),
    EndDate = Date.From(RangeEnd),
    #"Filter period" = Table.SelectRows(#"Keep 20 columns", each [posting_date] >= StartDate and [posting_date] < EndDate),
    // Rows of one inspection side by side: better compression, as with the ORDER BY of the SQL version.
    #"Sort rows" = Table.Sort(#"Filter period", {
        {"plant", Order.Ascending}, {"posting_date", Order.Ascending},
        {"key_order_inspection_plan_index_plant", Order.Ascending}, {"process_id", Order.Ascending},
        {"date_time", Order.Ascending}
    }),
    // Everything below runs in Power BI, not in Databricks.
    #"Stop folding" = Table.StopFolding(#"Sort rows"),
    // Month: first day of the month
    #"Add Month" = Table.AddColumn(#"Stop folding", "Month", each Date.StartOfMonth([posting_date]), type date),
    // Part: inspection plan without the "_<plant>" suffix
    #"Add Part" = Table.AddColumn(#"Add Month", "Part", each
        let
            plan = [key_inspection_plan_plant],
            suffix = "_" & [plant]
        in
            if plan <> null and [plant] <> null and Text.EndsWith(plan, suffix)
            then Text.Start(plan, Text.Length(plan) - Text.Length(suffix))
            else plan,
        type text),
    // Results: OK -> Pass, KO -> Fail, anything else (NA) -> Not evaluated / Not assessed
    #"Add Characteristic Result" = Table.AddColumn(#"Add Part", "Characteristic Result", each
        if [characteristic_status] = "OK" then "Pass"
        else if [characteristic_status] = "KO" then "Fail"
        else "Not evaluated", type text),
    #"Add Inspection Result" = Table.AddColumn(#"Add Characteristic Result", "Inspection Result", each
        if [process_status] = "OK" then "Pass"
        else if [process_status] = "KO" then "Fail"
        else "Not assessed", type text),
    // Inspection ID: one text key per inspection = order/plan/index key | test | date-time to the microsecond
    TimeKey = (t) =>
        if t is datetimezone then DateTimeZone.ToText(t, [Format = "yyyyMMddHHmmssffffffzzz", Culture = "en-US"])
        else if t is datetime then DateTime.ToText(t, [Format = "yyyyMMddHHmmssffffff", Culture = "en-US"])
        else Text.From(t),
    #"Add Inspection ID" = Table.AddColumn(#"Add Inspection Result", "Inspection ID", each
        Text.Combine({[key_order_inspection_plan_index_plant], Text.From([process_id], "en-US"), TimeKey([date_time])}, "|"),
        type text),
    // Text cleaning: leading and trailing spaces removed, empty text -> null
    #"Add Inspection Reason" = Table.AddColumn(#"Add Inspection ID", "Inspection Reason", each
        let t = Text.Trim([reason_for_inspection], " ") in if t = "" then null else t, type text),
    #"Add Press" = Table.AddColumn(#"Add Inspection Reason", "Press", each
        let t = Text.Trim([bmm_machine], " ") in if t = "" then null else t, type text),
    // Reaction limit flag (for the Reaction limits page)
    #"Add RL Violation" = Table.AddColumn(#"Add Press", "RL Violation", each
        if [characteristic_result] = "control limit violated" then 1 else 0, Int64.Type),
    // Detail of a violation, for the details page: empty on the other rows
    #"Add RL Time" = Table.AddColumn(#"Add RL Violation", "RL Time", each
        if [RL Violation] = 1 then (if [date_time] is datetimezone then DateTimeZone.RemoveZone([date_time]) else [date_time])
        else null, type datetime),
    #"Add RL Value" = Table.AddColumn(#"Add RL Time", "RL Value", each
        if [RL Violation] = 1 then [characteristic_value_num] else null, type number),
    #"Add RL Low Limit" = Table.AddColumn(#"Add RL Value", "RL Low Limit", each
        if [RL Violation] = 1 then [limit_min_alert] else null, type number),
    #"Add RL High Limit" = Table.AddColumn(#"Add RL Low Limit", "RL High Limit", each
        if [RL Violation] = 1 then [limit_max_alert] else null, type number),
    #"Add RL LSL" = Table.AddColumn(#"Add RL High Limit", "RL LSL", each
        if [RL Violation] = 1 then [lsl_inspection_plan] else null, type number),
    #"Add RL USL" = Table.AddColumn(#"Add RL LSL", "RL USL", each
        if [RL Violation] = 1 then [usl_inspection_plan] else null, type number),
    // Time of this refresh (UTC), on every row: the report shows the latest one
    RefreshedAt = DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow()),
    #"Add Refreshed At" = Table.AddColumn(#"Add RL USL", "Refreshed At", each RefreshedAt, type datetime),
    #"Rename columns" = Table.RenameColumns(#"Add Refreshed At", {
        {"plant", "Plant"}, {"posting_date", "Date"}, {"process", "Test"}, {"characteristic", "Characteristic"},
        {"kpc", "KPC"}, {"key_kpc", "Key KPC Code"}
    }),
    #"Keep model columns" = Table.SelectColumns(#"Rename columns", {
        "Plant", "Date", "Month", "Part", "Test", "Characteristic", "Characteristic Result", "Inspection Result",
        "Inspection ID", "Inspection Reason", "Press", "KPC", "Key KPC Code", "RL Violation",
        "RL Time", "RL Value", "RL Low Limit", "RL High Limit", "RL LSL", "RL USL", "Refreshed At"
    }),
    Typed = Table.TransformColumnTypes(#"Keep model columns", {
        {"Plant", type text}, {"Date", type date}, {"Test", type text}, {"Characteristic", type text},
        {"KPC", type text}, {"Key KPC Code", Int64.Type}
    })
in
    Typed"""

# Inspection ID is a text key here (the SQL version hashes it to an integer with Databricks' xxhash64).
# The V3 report has neither the Cpk and Trend chart pages nor the period filter: the columns of the SQL version made
# for them are left out.
LATER = ("Period Key", "Measured Value", "Measured At")
COLUMNS = [("Inspection ID", "string", "type text", True, None) if c[0] == "Inspection ID" else c
           for c in bt.COLUMNS if not c[0].startswith("Cpk ") and c[0] not in LATER]
# The step "Keep model columns" must list exactly the model columns, in the same order.
_kept = PQ_M.split('#"Keep model columns"')[1].split("{", 1)[1].split("}", 1)[0]
assert [x.strip().strip('"') for x in _kept.split(",")] == [c[0] for c in COLUMNS], "PQ_M and COLUMNS differ"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="V3 .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "pq"
    work.mkdir(parents=True, exist_ok=True)
    (work / "quality_tracker.m").write_text(PQ_M + "\n")
    model_dir = bt.write_model(work, settings, source_m=PQ_M, columns=COLUMNS)
    schema = work / "DataModelSchema.json"
    model_json = bt.model_schema(model_dir, schema)

    zin = zipfile.ZipFile(args.pbix)
    pkg.check_fields(pkg.definitions(zin), model_json)
    dst = HERE / "out" / "Quality_Dashboard_V3_PQ.pbit"
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Version", zin.read("Version"))
        z.writestr("[Content_Types].xml", pkg.content_types(zin.read("[Content_Types].xml")))
        z.writestr("DataModelSchema", schema.read_bytes())
        z.writestr("DiagramLayout", json.dumps(bt.diagram_layout(model_json)).encode("utf-16-le"))
        copied = [n for n in zin.namelist() if n not in pkg.REPLACED]
        for name in copied:
            z.writestr(name, zin.read(name))
    print(f"written {dst} ({dst.stat().st_size:,} bytes): model rebuilt, {len(copied)} report parts copied, "
          f"range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
