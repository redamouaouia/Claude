"""Quality Dashboard V10: client feedback on Overview, and a period filter on every analysis page.

Usage:  python add_period_filter.py <V9 .pbix> [settings.json] [--range START END]

- Overview: the Pass & Fail % donut is removed and the monthly line takes its place. The Pass rate figure and its
  gauge follow every filter (they showed the last 12 months, with the plant filter only); their subtitle names the
  period chosen.
- Period filter on Overview, Characteristics, Reaction limits and Cpk, under the refresh time: Day (last 24 hours),
  WTD, MTD, YTD and Year (last 12 months, chosen by default). One sync group: the same period on every page.
- Page backgrounds from out/bg_*.png (render them first, see the README): new Overview layout, track of the filter.
The model gets the table Period and the column Period Key of Quality Tracker (period_model.py), so the output is a
template: out/Quality_Dashboard_V10.pbit (data reloaded on opening).
"""
import argparse
import json
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_reaction_limits as A  # noqa: E402  (cloning helpers, checks, backgrounds)
import design as D  # noqa: E402
import pbit_package as pkg  # noqa: E402
import period_model as pm  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, I, N, P, S, SEL  # noqa: E402

bt = pm.bt
T = bt.T
OUT_NAME = "Quality_Dashboard_V10"
TITLES = {"Home": "home", "Overview": "overview", "Characteristics": "chars", "Reaction limits": "rl", "Cpk": "cpk",
          "Reaction limit details": "rl_details", "Trend chart": "trend"}
OPTIONAL = {"trend"}  # pages added after V10
BG_NAMES = dict(A.BG_NAMES, home="Home", cpk="Cpk", trend="TrendChart")
# States of the button slicer (ids of its formatting selectors, as in the Power BI base theme)
HOVER, PRESS, SELECTED = {"id": "interaction:hover"}, {"id": "interaction:press"}, {"id": "selection:selected"}
ACCENT = "#6FA8E8"  # light blue of the active page marker
FORMER_12M = "Inspection Pass % 12M"


def period_slicer(schema, z):
    """Button slicer on Period[Period]: one row of tiles on the track drawn in the page background, Year selected."""
    x, y, w, h = D.PERIOD_TRACK
    col = {"Column": {"Expression": {"SourceRef": {"Entity": pm.PERIOD}}, "Property": "Period"}}
    year = {"Version": 2, "From": [{"Name": "p", "Entity": pm.PERIOD, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "p"}}, "Property": "Period"}}],
                "Values": [[{"Literal": {"Value": f"'{pm.DEFAULT_PERIOD}'"}}]]}}}]}
    tiles = len(pm.PERIODS)
    return {
        "$schema": schema, "name": A.new_name(),
        "position": {"x": x + 2, "y": y + 2, "z": z, "height": h - 4, "width": w - 4, "tabOrder": z},
        "visual": {
            "visualType": "advancedSlicerVisual",
            "query": {"queryState": {"Values": {"projections": [
                {"field": col, "queryRef": f"{pm.PERIOD}.Period", "nativeQueryRef": "Period", "active": True}]}}},
            "objects": {
                "general": [P(filter={"filter": year})],
                "selection": [P(singleSelect=B(True), strictSingleSelect=B(False), selectAllCheckboxEnabled=B(False))],
                "layout": [P(rowCount=I(1), columnCount=I(tiles), maxTiles=I(tiles), cellPadding=I(2),
                             backgroundShow=B(False))],
                "shapeCustomRectangle": [SEL({"tileShape": S("rectangleRoundedByPixel"), "rectangleRoundedCurve": I(9)},
                                             R.DEFAULT)],
                "fillCustom": [SEL({"show": B(True), "fillColor": C(R.WHITE), "transparency": N(100)}, R.DEFAULT),
                               SEL({"fillColor": C(R.WHITE), "transparency": N(86)}, HOVER),
                               SEL({"fillColor": C(R.WHITE), "transparency": N(78)}, PRESS),
                               SEL({"fillColor": C(ACCENT), "transparency": N(0)}, SELECTED)],
                "outline": [SEL({"show": B(False)}, R.DEFAULT)],
                # White text on the dark header; navy on the selected tile (light blue, readable with both).
                "value": [SEL({"show": B(True), "fontFamily": S("Segoe UI Semibold"), "fontSize": N(8.5),
                               "fontColor": C(R.WHITE), "transparency": N(22), "horizontalAlignment": S("center"),
                               "verticalAlignment": S("middle")}, R.DEFAULT),
                          SEL({"fontColor": C(R.NAVY), "transparency": N(0)}, SELECTED)],
                "label": [SEL({"show": B(False)}, R.DEFAULT)],
                "padding": [SEL({"paddingSelection": S("Custom"), "leftMargin": I(0), "rightMargin": I(0),
                                 "topMargin": I(0), "bottomMargin": I(0)}, R.DEFAULT)],
                "selectionIcon": [SEL({"show": B(False)}, R.DEFAULT)],
                "accentBar": [SEL({"show": B(False)}, R.DEFAULT)],
            },
            "visualContainerObjects": R.vco_plain({"subTitle": [P(show=B(False))]}),
            "syncGroup": {"groupName": "Period", "fieldChanges": True, "filterChanges": True},
            "drillFilterOtherVisuals": True}}


def is_period_slicer(v):
    return v["visual"]["visualType"] == "advancedSlicerVisual" and pm.PERIOD in [
        p["field"]["Column"]["Expression"]["SourceRef"].get("Entity")
        for r in v["visual"]["query"]["queryState"].values() for p in r["projections"] if "Column" in p["field"]]


def update_overview(defs, pid):
    """Donut removed, line widened, Pass rate figure and gauge on all the filters."""
    vis = {k: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
    gone = [k for k, v in vis.items() if v["visual"]["visualType"] == "donutChart"]
    for k in gone:
        del defs[k]
    line = next(v for v in vis.values() if v["visual"]["visualType"] == "lineChart")
    A.place(line, *D.PAGES["overview"]["cards"]["line"])
    for k, v in vis.items():
        if v["visual"]["visualType"] in ("cardVisual", "gauge") and FORMER_12M in json.dumps(v):
            v = defs[k] = json.loads(json.dumps(v).replace(FORMER_12M, "Inspection Pass %"))
            if v["visual"]["visualType"] == "cardVisual":
                A.dynamic_subtitle(v["visual"]["visualContainerObjects"], "Period Label")
    return len(gone)


def add_period_slicers(defs, keys):
    for k in [k for k, v in defs.items() if "/visuals/" in k and is_period_slicer(v)]:  # from an earlier run
        del defs[k]
    panels = {}  # page id: names of the visuals of the "More filters" panel (shown by bookmarks)
    for k, b in defs.items():
        if k.startswith("bookmarks/") and k.endswith(".bookmark.json"):
            panels.setdefault(b["explorationState"].get("activeSection"), set()).update(
                b.get("options", {}).get("targetVisualNames", []))
    for key in [k for k in D.PERIOD_PAGES if k in keys]:
        pid = keys[key]
        vis = {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
        refresh = next(v for v in vis.values() if v["visual"]["visualType"] == "card"
                       and round(v["position"]["y"]) == D.REFRESH_PILL[1])
        z = refresh["position"]["z"] + 1
        panel_z = [vis[n]["position"]["z"] for n in panels.get(pid, ()) if n in vis]
        if panel_z and z >= min(panel_z):  # the open panel must cover the filter
            z = min(panel_z) - 1
        s = period_slicer(refresh["$schema"], z)
        defs[f"pages/{pid}/visuals/{s['name']}/visual.json"] = s


def set_backgrounds(defs, keys):
    images = {}
    for key, pid in keys.items():
        item = f"QualityDashboard{BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_{key}.png").read_bytes()
        A.set_background(defs[f"pages/{pid}/page.json"], D.PAGES[key]["title"], item)
    report = defs["report.json"]
    old = [i["name"] for p in report["resourcePackages"] if p["name"] == "RegisteredResources" for i in p["items"]]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]
    return images, old


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="V9 .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    keys = {}
    for pid in meta["pageOrder"]:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in TITLES:
            sys.exit(f"unexpected page '{title}'")
        keys[TITLES[title]] = pid
    if set(TITLES.values()) - OPTIONAL - set(keys):
        sys.exit(f"pages missing: {sorted(set(TITLES.values()) - OPTIONAL - set(keys))}")

    removed = update_overview(defs, keys["overview"])
    add_period_slicers(defs, keys)
    images, old = set_backgrounds(defs, keys)

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages, {sum(1 for k in defs if '/visuals/' in k)} visuals; "
          f"{removed} donut removed, period filter on {len(D.PERIOD_PAGES)} pages)")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v10"
    work.mkdir(parents=True, exist_ok=True)
    model_dir = pm.write_model(work, settings)
    model_json = bt.model_schema(model_dir, work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)
    dst = HERE / "out" / f"{OUT_NAME}.pbit"
    pkg.write_template(zin, defs, images, old, dst, work / "DataModelSchema.json", bt.diagram_layout(model_json))
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
