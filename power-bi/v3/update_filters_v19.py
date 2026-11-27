"""Plant visual management dashboard V19: client feedback of 26-27/11/2026 on the filters and the trend chart.

Usage:  python update_filters_v19.py <Relief .pbix saved by Power BI Desktop> [settings.json] [--range START END]

1. More filters shows its selection: a badge at the right of the More filters button, with the number of filters of
   the panel that have a selection (Fail orange); nothing when none (measures of filters_model.py).
2. Clear filters clears the More filters selection: Power BI's "Clear all slicers" skips hidden slicers, and the panel
   slicers are hidden while the panel is closed. Every filter that a page does not show has a visible copy there
   (same sync group), 4 px square in the top left corner and in the colour of the page: Clear filters clears it and
   the sync clears the hidden slicers. Clear filters is also above the panel and its overlay, which took the click
   while the panel was open. (The hidden copies of V15 are replaced by these.)
3. Process names: a new filter, Process name (procedure_reference), in the More filters panel of every page.
4. Trend chart: the table stores the alert limits in thousandths of the unit of the values; the query brings them back
   to that unit (build_template.py), for UCL / LCL and the limits of Reaction limit details.
Page backgrounds come from out/bg_r_*.png (render them first: README). The model gets the column Process Name and the
measures of the badge, so the output is a template: out/Plant visual management dashboard V19.pbit.
"""
import argparse
import copy
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_period_filter as PF  # noqa: E402  (page titles)
import add_reaction_limits as A  # noqa: E402  (cloning, checks)
import apply_design_a as AD  # noqa: E402  (panel visuals)
import apply_design_r as AR  # noqa: E402  (backgrounds of Relief)
import design_r as DR  # noqa: E402
import filters_model as fm  # noqa: E402
import pbit_package as pkg  # noqa: E402
import period_model as pm  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, I, N, P, S, SEL  # noqa: E402

bt = pm.bt
T = bt.T
OUT_NAME = "Plant visual management dashboard V19"
ANALYSIS = ("overview", "chars", "rl", "cpk", "trend", "rl_details", "fails")
TINY = (2, 2, 4, 4)  # visible copies of the filters a page does not show
PAGE_COLOUR = "#F2F5F9"  # the page background in the top left corner
PROCESS = ("Process Name", "Process name")  # column, name shown


def visuals(defs, pid):
    return [v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")]


def slicer_field(v):
    p = next(p for r in v["visual"]["query"]["queryState"].values() for p in r["projections"])
    return p["field"]["Column"]["Expression"]["SourceRef"]["Entity"], p["field"]["Column"]["Property"]


def is_slicer(v):
    return v["visual"]["visualType"] in ("slicer", "advancedSlicerVisual")


def bookmarks_of(defs, pid):
    return [b for k, b in defs.items() if k.startswith("bookmarks/") and k.endswith(".bookmark.json")
            and b["explorationState"].get("activeSection") == pid]


def add_process_filter(defs, pid):
    """Process name under the slicers of the More filters panel; the buttons of the panel move down."""
    vis = visuals(defs, pid)
    panel = sorted([v for v in vis if AD.is_panel(v) and v["visual"]["visualType"] == "slicer"],
                   key=lambda v: v["position"]["y"])
    if not panel:
        return None
    first, last = panel[0], panel[-1]
    step = panel[1]["position"]["y"] - first["position"]["y"] if len(panel) > 1 else 62
    below = last["position"]["y"] + last["position"]["height"]
    for v in vis:  # Reset, Close (look and button) under the slicers
        p = v["position"]
        if AD.is_panel(v) and p["x"] >= 980 and p["y"] >= below and p["height"] <= 40:
            p["y"] = round(p["y"] + step, 1)
    new = A.clone(first)
    column, shown = PROCESS
    proj = new["visual"]["query"]["queryState"]["Values"]["projections"][0]
    proj["field"]["Column"]["Expression"]["SourceRef"]["Entity"] = T
    proj["field"]["Column"]["Property"] = column
    proj.update(queryRef=f"{T}.{column}", nativeQueryRef=shown, displayName=shown)
    for s in new["visual"]["query"].get("sortDefinition", {}).get("sort", []):
        s["field"]["Column"]["Property"] = column
    for g in new["visual"]["objects"].get("general", []):  # no selection of the slicer it was copied from
        for key in ("filter", "selfFilter"):
            g["properties"].pop(key, None)
    new["visual"]["syncGroup"] = {"groupName": shown, "fieldChanges": True, "filterChanges": True}
    new["position"]["y"] = round(last["position"]["y"] + step, 1)
    new["position"]["z"] = new["position"]["tabOrder"] = max(v["position"]["z"] for v in panel) + 10
    defs[f"pages/{pid}/visuals/{new['name']}/visual.json"] = new
    for b in bookmarks_of(defs, pid):  # More filters open / closed show and hide it with the panel
        targets = b.get("options", {}).get("targetVisualNames", [])
        if first["name"] in targets:
            targets.append(new["name"])
            sec = b["explorationState"]["sections"][pid]["visualContainers"]
            sec[new["name"]] = copy.deepcopy(sec[first["name"]])
    return new


def tiny_copy(template):
    c = A.clone(template, *TINY, hidden=False)
    c.pop("filterConfig", None)
    o = c["visual"].setdefault("objects", {})
    if c["visual"]["visualType"] == "slicer":
        o["header"] = [P(show=B(False))]
        o["items"] = [P(fontColor=C(PAGE_COLOUR), background=C(PAGE_COLOUR), textSize=N(8))]
        o["dropdown"] = [P(borderColor=C(PAGE_COLOUR), iconColor=C(PAGE_COLOUR))]
        general = o.setdefault("general", [{"properties": {}}])
        general[0].setdefault("properties", {})["responsive"] = B(False)
    c["visual"]["visualContainerObjects"] = R.vco_plain()
    return c


def visible_copies(defs, keys):
    """Every filter a page does not show: a visible copy (Clear filters clears it, the sync does the rest)."""
    template, added = {}, {}
    for key in ANALYSIS:
        for v in visuals(defs, keys[key]):
            if is_slicer(v):
                g = v["visual"].get("syncGroup", {}).get("groupName")
                if g and (g not in template or (template[g].get("isHidden") and not v.get("isHidden"))):
                    template[g] = v
    for key in ANALYSIS:
        pid = keys[key]
        for v in visuals(defs, pid):  # hidden copies of V15 (out of the panel)
            if is_slicer(v) and v.get("isHidden") and not AD.is_panel(v):
                del defs[f"pages/{pid}/visuals/{v['name']}/visual.json"]
        shown = {v["visual"].get("syncGroup", {}).get("groupName") for v in visuals(defs, pid)
                 if is_slicer(v) and not v.get("isHidden")}
        used = {v["position"]["z"] for v in visuals(defs, pid)}
        z = 1
        for g in sorted(set(template) - shown):
            while z in used:
                z += 1
            c = tiny_copy(template[g])
            c["position"]["z"] = c["position"]["tabOrder"] = z
            used.add(z)
            defs[f"pages/{pid}/visuals/{c['name']}/visual.json"] = c
            added.setdefault(key, []).append(g)
    return added


def clear_on_top(defs, pid):
    """Clear filters above the More filters panel and its overlay."""
    vis = visuals(defs, pid)
    top = max(v["position"]["z"] for v in vis)
    n = 0
    for v in vis:
        if R.link_of(v).get("type") == "ClearAllSlicers" and v["position"]["x"] < DR.RAIL_BOX[2] + 14:
            top += 1000
            v["position"]["z"] = v["position"]["tabOrder"] = top
            n += 1
    return n


def badge(defs, pid, key):
    """Badge of the More filters button: number of its filters with a selection (measures of filters_model.py)."""
    vis = visuals(defs, pid)
    opens = {b["name"] for b in bookmarks_of(defs, pid) if b["displayName"].endswith("More filters open")}
    more = [v for v in vis if R.link_of(v).get("bookmark") in opens and 70 <= v["position"]["y"] < 140]
    if len(more) != 1:
        sys.exit(f"page {key}: {len(more)} More filters buttons (one expected)")
    hot = more[0]
    b = A.clone(hot)
    p = hot["position"]
    A.place(b, *DR.more_badge_rect(p["x"], p["width"], p["y"], p["height"]))
    b["visual"]["visualContainerObjects"]["visualLink"] = [P(show=B(False))]
    k = fm.set_of(key)
    b["visual"]["objects"] = {
        "icon": [SEL({"shapeType": S("blank")}, R.DEFAULT)],
        "text": [SEL({"show": B(True), "text": R.measure_expr(f"More Filters Badge {k}"), "fontColor": C(R.WHITE),
                      "fontSize": N(8), "fontFamily": S("Segoe UI Semibold"), "horizontalAlignment": S("center"),
                      "verticalAlignment": S("middle"), "topMargin": I(0), "bottomMargin": I(0), "leftMargin": I(0),
                      "rightMargin": I(0)}, R.DEFAULT)],
        "fill": [SEL({"show": B(True), "fillColor": {"solid": {"color": R.measure_expr(f"More Filters Badge Color {k}")}},
                      "transparency": N(0)}, R.DEFAULT)],
        "outline": [SEL({"show": B(False)}, R.DEFAULT)],
        "shape": [SEL({"tileShape": S("rectangleRounded"), "roundEdge": I(9)}, R.DEFAULT)],
    }
    used = {v["position"]["z"] for v in vis}
    z = p["z"] - 1
    while z in used:
        z -= 1
    b["position"]["z"] = b["position"]["tabOrder"] = z  # under the (transparent) button, which keeps the click
    defs[f"pages/{pid}/visuals/{b['name']}/visual.json"] = b


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="Relief .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    keys = {PF.TITLES[defs[f"pages/{p}/page.json"]["displayName"]]: p for p in meta["pageOrder"]}
    if any(slicer_field(v)[1] == PROCESS[0] for k, v in defs.items() if "/visuals/" in k and is_slicer(v)):
        sys.exit("this report already has the Process name filter")

    for key in ANALYSIS:
        pid = keys[key]
        new = add_process_filter(defs, pid)
        if new is not None:
            badge(defs, pid, key)
        print(f"{key:11s} process filter: {'yes' if new else 'no panel'}; Clear filters on top: {clear_on_top(defs, pid)}")
    for key, groups in visible_copies(defs, keys).items():
        print(f"{key:11s} visible copies: {', '.join(groups)}")
    images, old = AR.set_backgrounds(defs, keys)

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({sum(1 for k in defs if '/visuals/' in k)} visuals)")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v19"
    work.mkdir(parents=True, exist_ok=True)
    model_json = bt.model_schema(pm.write_model(work, settings), work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)
    dst = HERE / "out" / f"{OUT_NAME}.pbit"
    pkg.write_template(zin, defs, images, old, dst, work / "DataModelSchema.json", bt.diagram_layout(model_json))
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
