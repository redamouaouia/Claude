"""Helpers shared by the V3 template builders: turning a .pbix into a .pbit, and checking report fields."""
import json
import sys

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
    if missing:
        sys.exit("fields used by the report but missing from the model:\n" +
                 "\n".join(f"  {e}[{p}] in {n}" for e, p, n in sorted(missing)))
    print(f"report fields: OK ({len(used)} distinct columns and measures found in the model)")
