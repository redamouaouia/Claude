"""Plant visual management dashboard V15: every visual shows the cumulative of the selection, every filter applies
everywhere (client request).

Usage:  python add_cumulative.py <Relief .pbix saved by Power BI Desktop> [settings.json] [--range START END]

- Charts over time and cards with a trend line use the cumulative measures of cumul_model.py: at each point, the total
  from the start of the selected period (and dates, and every other filter) up to that point. Cards keep the total of
  the selection as their figure. Overview: cumulative pass % by month; Characteristics: cumulative Pass and Fail by
  day, characteristic pass % and measured values as cumulative cards; Reaction limits: cumulative violations by day.
- Every filter (Plant, Part, Test, Characteristic, Inspection reason, Date, Period, KPC, Press, Cpk threshold and
  Cpk status) is on every analysis page, the details pages included: where a page does not show it, a hidden copy of
  the slicer (same sync group) applies the selection made elsewhere. The home page is left as it is.
No visual has a filter of its own on a period (checked). The model gets the cumulative measures, so the output is a
template: out/Plant visual management dashboard V15.pbit (data reloaded on opening).
"""
import argparse
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_period_filter as PF  # noqa: E402  (page titles)
import add_reaction_limits as A  # noqa: E402  (cloning, checks)
import pbit_package as pkg  # noqa: E402
import period_model as pm  # noqa: E402
from restyle import S  # noqa: E402

bt = pm.bt
T = bt.T
OUT_NAME = "Plant visual management dashboard V15"
# (page, visual type, measure now) -> (cumulative measure, title, subtitle or None to keep it)
SWAPS = {
    ("overview", "lineChart", "Inspection Pass %"): (
        "Inspection Pass % Cumul", "Cumulative pass %",
        "Pass rate from the start of the selected period, month by month · dashed line = 95 % target"),
    ("chars", "lineChart", "Char Pass"): (
        "Char Pass Cumul", "Pass & Fail · cumulative",
        "Pass (left axis, blue) and Fail (right axis, orange), added up from the start of the selected period"),
    ("chars", "lineChart", "Char Fail"): ("Char Fail Cumul", None, None),
    ("chars", "cardVisual", "Char Pass %"): ("Char Pass % Cumul", "Characteristic pass % · cumulative", None),
    ("chars", "cardVisual", "Measured Values"): ("Measured Values Cumul", "Measured values · cumulative", None),
    ("rl", "lineChart", "RL Violations"): ("RL Violations Cumul", "Reaction limit violations · cumulative", None),
}
SYNC_PAGES = ("overview", "chars", "rl", "cpk", "trend", "rl_details", "fails")  # every page but home
NEW_GROUPS = {"Cpk Threshold": "Cpk threshold", "Cpk Status": "Cpk status"}  # slicers that had no sync group
HIDDEN_AT = (1000, 660, 120, 30)  # hidden copies: out of the way, in the More filters panel area


def measures_of(v):
    return [p["field"]["Measure"]["Property"] for r in v["visual"].get("query", {}).get("queryState", {}).values()
            for p in r["projections"] if "Measure" in p["field"]]


def swap(v, old, new):
    """Replace a measure of the visual (projection, query references, formatting selectors)."""
    v["visual"] = json.loads(json.dumps(v["visual"]).replace(f'"{T}.{old}"', f'"{T}.{new}"'))
    for r in v["visual"]["query"]["queryState"].values():
        for p in r["projections"]:
            if p["field"].get("Measure", {}).get("Property") == old:
                p["field"]["Measure"]["Property"] = new
                p["queryRef"] = f"{T}.{new}"


def retitle(v, title, subtitle):
    vco = v["visual"].setdefault("visualContainerObjects", {})
    if title:
        vco["title"][0]["properties"]["text"] = S(title)
    if subtitle:
        st = vco.setdefault("subTitle", [{"properties": {}}])[0]["properties"]
        st["text"] = S(subtitle)


def cumulative_visuals(defs, keys):
    done = []
    for (key, vt, old), (new, title, subtitle) in SWAPS.items():
        hits = [v for k, v in defs.items() if k.startswith(f"pages/{keys[key]}/visuals/")
                and v["visual"]["visualType"] == vt and old in measures_of(v)]
        if len(hits) != 1:
            sys.exit(f"page {key}: {len(hits)} {vt} with [{old}] (one expected)")
        swap(hits[0], old, new)
        retitle(hits[0], title, subtitle)
        done.append(f"{key}: {vt} [{old}] -> [{new}]")
    return done


def slicer_group(v):
    """Sync group of a slicer, given to the slicers that had none (Cpk threshold, Cpk status)."""
    entity = [p["field"]["Column"]["Expression"]["SourceRef"]["Entity"]
              for r in v["visual"]["query"]["queryState"].values() for p in r["projections"]][0]
    if "syncGroup" not in v["visual"] and entity in NEW_GROUPS:
        v["visual"]["syncGroup"] = {"groupName": NEW_GROUPS[entity], "fieldChanges": True, "filterChanges": True}
    return v["visual"].get("syncGroup", {}).get("groupName")


def sync_everywhere(defs, keys):
    """A hidden copy of each slicer on every analysis page that does not have it."""
    by_page, template = {}, {}
    for key in SYNC_PAGES:
        for k, v in defs.items():
            if k.startswith(f"pages/{keys[key]}/visuals/") and v["visual"]["visualType"] in ("slicer", "advancedSlicerVisual"):
                g = slicer_group(v)
                if not g:
                    sys.exit(f"page {key}: slicer without sync group ({v['name']})")
                by_page.setdefault(key, set()).add(g)
                if g not in template or (v.get("isHidden") and not template[g].get("isHidden")):
                    template[g] = v  # a hidden copy when there is one (its formatting fits the More filters panel)
    added = {}
    for key in SYNC_PAGES:
        own = [v for k, v in defs.items() if k.startswith(f"pages/{keys[key]}/visuals/")]
        z = max(v["position"]["z"] for v in own)
        for g in sorted(set(template) - by_page.get(key, set())):
            c = A.clone(template[g], *HIDDEN_AT, hidden=True)
            c.pop("filterConfig", None)
            z += 100
            c["position"]["z"] = c["position"]["tabOrder"] = z
            defs[f"pages/{keys[key]}/visuals/{c['name']}/visual.json"] = c
            added.setdefault(key, []).append(g)
    return added


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="Relief .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    keys = {}
    for pid in meta["pageOrder"]:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in PF.TITLES:
            sys.exit(f"unexpected page '{title}'")
        keys[PF.TITLES[title]] = pid
    missing = set(PF.TITLES.values()) - set(keys)
    if missing:
        sys.exit(f"pages missing: {sorted(missing)}")
    if any("Cumul" in m for k, v in defs.items() if "/visuals/" in k for m in measures_of(v)):
        sys.exit("this report already has the cumulative visuals")

    print("\n".join(cumulative_visuals(defs, keys)))
    for key, groups in sync_everywhere(defs, keys).items():
        print(f"{key:11s} hidden synced slicers added: {', '.join(groups)}")

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages, {sum(1 for k in defs if '/visuals/' in k)} visuals)")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v15"
    work.mkdir(parents=True, exist_ok=True)
    model_dir = pm.write_model(work, settings)
    model_json = bt.model_schema(model_dir, work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)
    dst = HERE / "out" / f"{OUT_NAME}.pbit"
    pkg.write_template(zin, defs, {}, [], dst, work / "DataModelSchema.json", bt.diagram_layout(model_json))
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
