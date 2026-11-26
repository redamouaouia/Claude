"""Plant visual management dashboard V13: key figures on Overview, the decomposition tree on a page of its own.

Usage:  python add_overview_figures.py <design A .pbix> [settings.json] [--range START END]

Client requests on Overview:
- three key figures, as in the client mockup: failed inspections (selected period), fail rate (share of the
  inspections) and gap to target (pass rate against the 95 % target, in percentage points: orange below the target,
  blue at or above it). Their icon and name are drawn in the page background (design_a.py); the figure and the line
  under it are card visuals.
- "Where do inspections fail?" (decomposition tree) is no longer shown on Overview: a tile opens it on its own page,
  "Failure breakdown", which has the filters of Overview (copies of its slicers, same sync groups, the More filters
  panel and its bookmarks) and "‹ Overview" to go back. The page is not in the page tabs.
Page backgrounds come from out/bg_a_*.png (design A, render them first: README). The model gets the gap measures
(overview_model.py), so the output is a template: out/Plant visual management dashboard V13.pbit (data reloaded on
opening).
"""
import argparse
import copy
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_home_and_cpk as H  # noqa: E402  (queries)
import add_period_filter as PF  # noqa: E402  (page titles)
import add_reaction_limits as A  # noqa: E402  (cloning helpers, checks)
import apply_design_a as AD  # noqa: E402  (panel visuals, backgrounds of design A)
import design as D  # noqa: E402
import design_a as DA  # noqa: E402
import pbit_package as pkg  # noqa: E402
import period_model as pm  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, I, N, S, SEL  # noqa: E402

bt = pm.bt
T = bt.T
OUT_NAME = "Plant visual management dashboard V13"
FAILS_TITLE = D.PAGES["fails"]["title"]
# Key figures: (key in design_a.KPI, measure, line under the figure, colour of the figure)
FIGURES = [
    ("failed", "Inspections Fail", "Selected period", C(R.NAVY)),
    ("rate", "Inspection Fail %", "Share of inspections", C(R.ORANGE)),
    ("gap", "Pass % Gap", "Pass rate vs 95% target", {"solid": {"color": R.measure_expr("Pass % Gap Color")}}),
]
HOVER = {"id": "hover"}


def part_of(v):
    """rail, header, panel (More filters, hidden) or content, from the geometry of design A."""
    p = v["position"]
    if AD.is_panel(v):
        return "panel"
    if p["x"] < DA.RAIL:
        return "rail"
    return "header" if p["y"] < DA.CONTENT_Y0 - 2 else "content"


def hotspot(like, rect, radius, page_id, tooltip):
    """Transparent page button over a tile drawn in the background, with a light navy tint on hover."""
    v = A.clone(like)
    A.place(v, *rect)
    A.set_link(v, type="PageNavigation", navigationSection=page_id, tooltip=tooltip)
    o = v["visual"]["objects"]
    o["fill"] = [SEL({"show": B(False), "fillColor": C(R.WHITE), "transparency": N(0)}, R.DEFAULT),
                 SEL({"show": B(True), "fillColor": C(DA.NAVY), "transparency": N(94)}, HOVER)]
    o["shape"] = [SEL({"tileShape": S("rectangleRounded"), "roundEdge": I(radius)}, R.DEFAULT)]
    return v


def figure(hero, key, measure, line, color):
    """One key figure: the value (as the Pass rate figure), and the line under it as the label of the card."""
    v = A.clone(hero)
    A.place(v, *DA.kpi_value_rect(key))
    H.query(v, {"Data": [H.projection(T, "Measure", measure, line)]})
    o = v["visual"]["objects"]
    value = o["value"][0]["properties"]
    value.update(fontColor=color, fontSize=N(28), labelDisplayUnits=N(1), showBlankAs=S("–"))
    o["label"] = [SEL({"show": B(True), "position": S("belowValue"), "fontColor": C(R.MUTED2), "fontSize": N(9.5),
                       "fontFamily": S("Segoe UI"), "horizontalAlignment": S("left")}, R.DEFAULT)]
    v["visual"]["visualContainerObjects"] = R.vco_plain()
    return v


def copy_bookmarks(defs, names, from_pid, to_pid, from_title, to_title):
    """Bookmarks of a page whose targets were all copied (More filters open / closed), for the copy."""
    made = {}
    for k, b in sorted(defs.items()):
        if not (k.startswith("bookmarks/") and k.endswith(".bookmark.json")):
            continue
        es = b["explorationState"]
        targets = b.get("options", {}).get("targetVisualNames", [])
        if es.get("activeSection") != from_pid or not targets or any(n not in names for n in targets):
            continue
        nb = copy.deepcopy(b)
        nb["name"] = "Bookmark" + A.new_name()
        nb["displayName"] = b["displayName"].replace(from_title, to_title, 1)
        sec = nb["explorationState"]["sections"].pop(from_pid)
        sec["visualContainers"] = {names[n]: c for n, c in sec.get("visualContainers", {}).items() if n in names}
        nb["explorationState"]["sections"] = {to_pid: sec}
        nb["explorationState"]["activeSection"] = to_pid
        nb["options"]["targetVisualNames"] = [names[n] for n in targets]
        made[b["name"]] = nb
    for old, nb in made.items():
        defs[f"bookmarks/{nb['name']}.bookmark.json"] = nb
        defs["bookmarks/bookmarks.json"]["items"].append({"name": nb["name"]})
    return {old: nb["name"] for old, nb in made.items()}


def build_fails_page(defs, keys):
    """New page: Overview's rail, header and More filters panel (copies), the decomposition tree, ‹ Overview."""
    ov, fid = keys["overview"], keys["fails"]
    own = {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{ov}/visuals/")}
    trees = [v for v in own.values() if v["visual"]["visualType"] == "decompositionTreeVisual"]
    if len(trees) != 1:
        sys.exit(f"Overview: {len(trees)} decomposition trees (one expected)")
    tree = trees[0]
    out, names = [], {}
    for v in sorted(own.values(), key=lambda x: x["position"]["z"]):
        if part_of(v) == "content":
            continue
        c = A.clone(v)
        names[v["name"]] = c["name"]
        out.append(c)
    made = copy_bookmarks(defs, names, ov, fid, D.PAGES["overview"]["title"], FAILS_TITLE)
    for v in out:  # the buttons of the copied panel open / close the copied bookmarks
        link = R.link_of(v)
        if link.get("type") == "Bookmark":
            if link["bookmark"] not in made:
                sys.exit(f"Failure breakdown: button {v['name']} opens a bookmark of Overview ({link['bookmark']})")
            A.set_link(v, **{k: (made[x] if k == "bookmark" else x) for k, x in link.items() if k != "show"})

    del defs[f"pages/{ov}/visuals/{tree['name']}/visual.json"]  # the tree moves to the new page
    A.place(tree, *DA.map_rect(*D.PAGES["fails"]["cards"]["decomp"]))
    out.append(tree)
    like = next(v for v in out if R.link_of(v).get("type") == "PageNavigation" and part_of(v) == "rail")
    back = hotspot(like, DA.BACK_LINK, 14, ov, "Back to Overview")
    back["position"]["z"] = back["position"]["tabOrder"] = tree["position"]["z"] - 500
    out.append(back)
    page = copy.deepcopy(defs[f"pages/{ov}/page.json"])
    page["name"], page["displayName"], page["visibility"] = fid, FAILS_TITLE, "HiddenInViewMode"
    defs[f"pages/{fid}/page.json"] = page
    for v in out:
        defs[f"pages/{fid}/visuals/{v['name']}/visual.json"] = v
    return tree, len(out), len(made)


def update_overview(defs, keys, tree_z):
    """Key figures and the tile of the failure breakdown, in the place of the tree."""
    ov = keys["overview"]
    own = {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{ov}/visuals/")}
    hero = next(v for v in own.values() if v["visual"]["visualType"] == "cardVisual"
                and "Inspection Pass %" in json.dumps(v["visual"].get("query", {})))
    like = next(v for v in own.values() if R.link_of(v).get("type") == "PageNavigation" and part_of(v) == "rail")
    new = [figure(hero, *f) for f in FIGURES]
    new.append(hotspot(like, DA.FAILS_TILE, 12, keys["fails"], "Open the failure breakdown (decomposition tree)"))
    used = {v["position"]["z"] for v in own.values()}
    for i, v in enumerate(new):  # in the place of the tree, under the More filters panel
        z = tree_z + 10 * i
        if z in used:
            sys.exit(f"Overview: z {z} already used")
        v["position"]["z"] = v["position"]["tabOrder"] = z
        defs[f"pages/{ov}/visuals/{v['name']}/visual.json"] = v
    return len(new)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="design A .pbix saved by Power BI Desktop (PBIR format)")
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
    if "fails" in keys:
        sys.exit(f"the report already has the page '{FAILS_TITLE}'")
    missing = set(PF.TITLES.values()) - PF.OPTIONAL - set(keys)
    if missing or "trend" not in keys:
        sys.exit(f"pages missing: {sorted(missing | ({'trend'} - set(keys)))}")
    keys["fails"] = A.new_name()

    tree, copied, marks = build_fails_page(defs, keys)
    added = update_overview(defs, keys, tree["position"]["z"])
    meta["pageOrder"].append(keys["fails"])
    images, old = AD.set_backgrounds(defs, keys)

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages; {FAILS_TITLE}: {copied} visuals, {marks} bookmarks; "
          f"Overview: {added} visuals added, the tree moved)")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v13"
    work.mkdir(parents=True, exist_ok=True)
    model_dir = pm.write_model(work, settings)
    model_json = bt.model_schema(model_dir, work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)
    dst = HERE / "out" / f"{OUT_NAME}.pbit"
    pkg.write_template(zin, defs, images, old, dst, work / "DataModelSchema.json", bt.diagram_layout(model_json))
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
