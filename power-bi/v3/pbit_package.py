"""Helpers shared by the V3 template builders: turning a .pbix into a .pbit, and checking report fields."""
import json
import pathlib
import sys
import zipfile

# Parts of a .pbix that a template does not have (data, credentials) or that are rebuilt for the new model.
REPLACED = {"Version", "[Content_Types].xml", "DataModel", "SecurityBindings", "DiagramLayout"}
PREFIX = "Report/definition/"


def content_types(raw):
    ct = raw.decode("utf-8-sig")
    ct = ct.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")
    ct = ct.replace('<Override PartName="/DataModel" ContentType="" />',
                    '<Override PartName="/DataModelSchema" ContentType="" />')
    if "/DataModelSchema" not in ct or "SecurityBindings" in ct or '"/DataModel"' in ct:
        sys.exit("unexpected [Content_Types].xml:\n" + ct)
    return ct.encode("utf-8-sig")


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def definitions(zin):
    """The report definition of a .pbix, as {path under Report/definition/: parsed JSON}."""
    return {n[len(PREFIX):]: json.loads(zin.read(n).decode("utf-8-sig"))
            for n in zin.namelist() if n.startswith(PREFIX) and n.endswith(".json")}


def check_fields(defs, model_json):
    """Every column or measure the report uses must exist in the model."""
    used, missing = report_fields(defs, model_json)
    if missing:
        sys.exit("fields used by the report but missing from the model:\n" +
                 "\n".join(f"  {e}[{p}] in {n}" for e, p, n in sorted(missing)))
    print(f"report fields: OK ({len(used)} distinct columns and measures found in the model)")


def report_fields(defs, model_json):
    """(fields used by the report, those missing from the model) as sets of (table, field[, file])."""
    fields = {t["name"]: {c["name"] for c in t.get("columns", [])} | {m["name"] for m in t.get("measures", [])}
              for t in model_json["model"]["tables"]}
    used, missing = set(), set()
    for name, doc in defs.items():
        aliases = {f["Name"]: f["Entity"] for o in walk(doc) for f in o.get("From", [])
                   if isinstance(f, dict) and "Name" in f and "Entity" in f}
        for o in walk(doc):
            src = o.get("Expression", {}).get("SourceRef") if isinstance(o.get("Expression"), dict) else None
            if "Property" in o and isinstance(src, dict):
                entity = src.get("Entity") or aliases.get(src.get("Source"))
                if entity:
                    used.add((entity, o["Property"]))
                    if o["Property"] not in fields.get(entity, ()):
                        missing.add((entity, o["Property"], name))
    return used, missing


def write_template(zin, defs, images, old, dst, schema_path, diagram):
    """Template (.pbit) from a .pbix: its report with `defs` and the background `images` (registered resources,
    replacing `old`), and the model of `schema_path` (DataModelSchema). No data, no credentials."""
    skip = REPLACED | {f"Report/StaticResources/RegisteredResources/{n}" for n in old}
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Version", zin.read("Version"))
        z.writestr("[Content_Types].xml", content_types(zin.read("[Content_Types].xml")))
        z.writestr("DataModelSchema", pathlib.Path(schema_path).read_bytes())
        z.writestr("DiagramLayout", json.dumps(diagram).encode("utf-16-le"))
        for n in zin.namelist():
            if n not in skip and not n.startswith(PREFIX):
                z.writestr(n, zin.read(n))
        for k, v in sorted(defs.items()):
            z.writestr(PREFIX + k, json.dumps(v, ensure_ascii=False, separators=(",", ":")))
        for n, data in images.items():
            z.writestr("Report/StaticResources/RegisteredResources/" + n, data)
