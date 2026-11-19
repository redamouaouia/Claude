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
sys.path.insert(0, str(HERE.parent / "v2"))
import build_template as bt  # noqa: E402  (V2 model: measures, columns, TMDL writer, TOM validation)

# Same rules as the SQL of the V2 / V3 model (build_template.SQL_LINES), written as Power Query steps.
# Power Query sends the first steps (columns, period, sort) to Databricks itself (query folding): without that,
# each refresh would download the whole table. "Stop folding" keeps every calculation after it in Power BI.
PQ_M = """let
    // Power Query version: no hand-written SQL, every rule is one of the steps below.
    Source = Databricks.Catalogs(DatabricksHost, DatabricksHttpPath, [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]),
    Catalog = Source{[Name = "domain_qual_prd"]}[Data],
    Schema = Catalog{[Name = "gold"]}[Data],
    Tracker = Schema{[Name = "dp_cpower_qda_quality_tracker"]}[Data],
    #"Keep 15 columns" = Table.SelectColumns(Tracker, {
        "plant", "posting_date", "key_inspection_plan_plant", "process", "characteristic",
        "characteristic_status", "process_status", "key_order_inspection_plan_index_plant", "process_id",
        "date_time", "reason_for_inspection", "bmm_machine", "kpc", "key_kpc", "characteristic_result"
    }),
    // Power BI Desktop loads RangeStart..RangeEnd only; the service loads 12 months (incremental refresh).
    StartDate = Date.From(RangeStart),
    EndDate = Date.From(RangeEnd),
    #"Filter period" = Table.SelectRows(#"Keep 15 columns", each [posting_date] >= StartDate and [posting_date] < EndDate),
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
    #"Rename columns" = Table.RenameColumns(#"Add RL Violation", {
        {"plant", "Plant"}, {"posting_date", "Date"}, {"process", "Test"}, {"characteristic", "Characteristic"},
        {"kpc", "KPC"}, {"key_kpc", "Key KPC Code"}
    }),
    #"Keep model columns" = Table.SelectColumns(#"Rename columns", {
        "Plant", "Date", "Month", "Part", "Test", "Characteristic", "Characteristic Result", "Inspection Result",
        "Inspection ID", "Inspection Reason", "Press", "KPC", "Key KPC Code", "RL Violation"
    }),
    Typed = Table.TransformColumnTypes(#"Keep model columns", {
        {"Plant", type text}, {"Date", type date}, {"Test", type text}, {"Characteristic", type text},
        {"KPC", type text}, {"Key KPC Code", Int64.Type}
    })
in
    Typed"""

# Inspection ID is a text key here (the SQL version hashes it to an integer with Databricks' xxhash64).
COLUMNS = [("Inspection ID", "string", "type text", True, None) if c[0] == "Inspection ID" else c
           for c in bt.COLUMNS]

# Parts of the .pbix that a template does not have (data, credentials) or that are rebuilt for the new model.
REPLACED = {"Version", "[Content_Types].xml", "DataModel", "SecurityBindings", "DiagramLayout"}


def content_types(raw):
    ct = raw.decode("utf-8-sig")
    ct = ct.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")
    ct = ct.replace('<Override PartName="/DataModel" ContentType="" />',
                    '<Override PartName="/DataModelSchema" ContentType="" />')
    if "/DataModelSchema" not in ct or "SecurityBindings" in ct or '"/DataModel"' in ct:
        sys.exit("unexpected [Content_Types].xml:\n" + ct)
    return ct.encode("utf-8-sig")


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def check_fields(zin, model_json):
    """Every column or measure the report uses must exist in the new model."""
    fields = {t["name"]: {c["name"] for c in t.get("columns", [])} | {m["name"] for m in t.get("measures", [])}
              for t in model_json["model"]["tables"]}
    used, missing = set(), set()
    for name in zin.namelist():
        if not (name.startswith("Report/definition/") and name.endswith(".json")):
            continue
        doc = json.loads(zin.read(name).decode("utf-8-sig"))
        aliases = {f["Name"]: f["Entity"] for o in _walk(doc) for f in o.get("From", [])
                   if isinstance(f, dict) and "Name" in f and "Entity" in f}
        for o in _walk(doc):
            src = o.get("Expression", {}).get("SourceRef") if isinstance(o.get("Expression"), dict) else None
            if "Property" in o and isinstance(src, dict):
                entity = src.get("Entity") or aliases.get(src.get("Source"))
                if entity:
                    used.add((entity, o["Property"]))
                    if o["Property"] not in fields.get(entity, ()):
                        missing.add((entity, o["Property"], name))
    if missing:
        sys.exit("fields used by the report but missing from the model:\n" +
                 "\n".join(f"  {e}[{p}] in {n}" for e, p, n in sorted(missing)))
    print(f"report fields: OK ({len(used)} distinct columns and measures found in the model)")


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
    check_fields(zin, model_json)
    dst = HERE / "out" / "Quality_Dashboard_V3_PQ.pbit"
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Version", zin.read("Version"))
        z.writestr("[Content_Types].xml", content_types(zin.read("[Content_Types].xml")))
        z.writestr("DataModelSchema", schema.read_bytes())
        z.writestr("DiagramLayout", json.dumps(bt.diagram_layout(model_json)).encode("utf-16-le"))
        copied = [n for n in zin.namelist() if n not in REPLACED]
        for name in copied:
            z.writestr(name, zin.read(name))
    print(f"written {dst} ({dst.stat().st_size:,} bytes): model rebuilt, {len(copied)} report parts copied, "
          f"range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
