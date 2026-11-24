"""Quality Dashboard V11: page 5 "Trend chart", and the Cpk page without its donut.

Usage:  python add_trend_page.py <V10 .pbix> [settings.json] [--range START END]

- Trend chart, as in the specification (page 5): one characteristic at a time (Part, Test and Characteristic are
  marked *), its reaction limit violations, its Cpk against the goal (Cpk threshold of More filters, 1.33 if none)
  with Pass / Fail, and its measured values in time order against USL, UCL, X bar, LCL and LSL. The filters are
  those of page 2 (same fields, same sync groups) and the period filter; More filters: inspection reason and Cpk
  threshold.
- Navigation: a fifth tile "Trend chart" on every page, a fifth row on the home page.
- Cpk: the Pass & Fail donut is removed and Cpk pass % fills its card, with "n of N characteristics" below; the
  "To be validated" label is gone (page backgrounds).
- Period filter: Year selected again on every page, as the client asked.
Page backgrounds come from out/bg_*.png (render them first, see the README). The model is the one of
period_model.py (with the trend columns and measures), so the output is a template: out/Quality_Dashboard_V11.pbit.
"""
import argparse
import copy
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_home_and_cpk as H  # noqa: E402  (navigation buttons, home page, fields, slicer retargeting)
import add_period_filter as PF  # noqa: E402  (period filter, backgrounds)
import add_reaction_limits as A  # noqa: E402  (cloning helpers, checks)
import design as D  # noqa: E402
import pbit_package as pkg  # noqa: E402
import period_model as pm  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, N, P, S, SEL  # noqa: E402

bt = pm.bt
T = bt.T
OUT_NAME = "Quality_Dashboard_V11"
TREND_TITLE = D.PAGES["trend"]["title"]
RED, ORANGE, GREY = "#C00000", R.ORANGE, "#7A889C"
# Constant lines of the trend chart: (name, measure, colour, style), from the top
LIMITS = [("USL", "Trend USL", RED, "solid"), ("UCL", "Trend UCL", ORANGE, "dashed"),
          ("X̄", "Trend Mean", GREY, "dashed"), ("LCL", "Trend LCL", ORANGE, "dashed"),
          ("LSL", "Trend LSL", RED, "solid")]


def measure(name):
    return R.measure_expr(name)


def strip_trend_page(defs, meta):
    """Removes the trend page of an earlier run, its bookmarks and the buttons that open it."""
    gone = [p for p in meta["pageOrder"] if defs[f"pages/{p}/page.json"]["displayName"] == TREND_TITLE]
    for k in [k for k in defs if any(k.startswith(f"pages/{p}/") for p in gone)]:
        del defs[k]
    meta["pageOrder"] = [p for p in meta["pageOrder"] if p not in gone]
    dead = set()
    for k in [k for k in defs if k.startswith("bookmarks/") and k.endswith(".bookmark.json")]:
        if defs[k]["explorationState"].get("activeSection") in gone:
            dead.add(defs[k]["name"])
            del defs[k]
    index = defs["bookmarks/bookmarks.json"]
    index["items"] = [i for i in index["items"] if i["name"] not in dead]
    for k in [k for k in defs if "/visuals/" in k]:
        if R.link_of(defs[k]).get("navigationSection") in gone:
            del defs[k]


# --------------------------------------------------------------------------- Cpk page
def update_cpk_page(defs, pid):
    """Donut removed; Cpk pass % fills its card (the "n of N characteristics" line below it was taken out in V12)."""
    vis = {k: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
    for k in [k for k, v in vis.items() if v["visual"]["visualType"] == "donutChart"]:
        del defs[k]
    kpi = next(v for v in vis.values() if v["visual"]["visualType"] == "cardVisual")
    A.place(kpi, *D.PAGES["cpk"]["cards"]["kpi"])
    kpi["visual"]["objects"]["value"][0]["properties"]["fontSize"] = N(40)


def text_line(card_like, rect, measure_name, display):
    """One line of text from a measure, in a plain card (as the refresh time): grey, no background."""
    v = A.clone(card_like)
    A.place(v, *rect)
    H.query(v, {"Values": [H.projection(T, "Measure", measure_name, display)]})
    v["visual"]["objects"] = {
        "labels": [P(color=C(R.MUTED), fontSize=N(10), fontFamily=S("Segoe UI"))],
        "categoryLabels": [P(show=B(False))],
        "wordWrap": [P(show=B(False))]}
    v["visual"]["visualContainerObjects"] = R.vco_plain()
    return v


# --------------------------------------------------------------------------- page 5: Trend chart
def kpi_card(hero, rect, title, subtitle, value_measure, display, units=None, blank=None):
    """Card with a title, a fixed subtitle and one figure (measures in titles of this card type: see V11 fix)."""
    v = A.clone(hero)
    A.place(v, *rect)
    H.query(v, {"Data": [H.projection(T, "Measure", value_measure, display)]})
    value = v["visual"]["objects"]["value"][0]["properties"]
    value["fontSize"] = N(24)
    if units is not None:
        value["labelDisplayUnits"] = N(units)
    if blank is not None:
        value["showBlankAs"] = S(blank)
    v["visual"]["visualContainerObjects"] = R.vco_card(title, subtitle, pad=(12, 2, 16, 16), header=False)
    return v


def trend_chart(line_like, rect):
    v = A.clone(line_like)
    A.place(v, *rect)
    H.query(v, {"Category": [H.projection(T, "Column", "Measured At", "Measured at", active=True)],
                "Y": [H.projection(T, "Measure", "Trend Value", "Measured value")]},
            sort=(T, "Column", "Measured At", "Ascending"))
    ref = f"{T}.Trend Value"
    v["visual"]["objects"] = {
        "dataPoint": [SEL({"fill": C(R.BLUE)}, {"metadata": ref})],
        "lineStyles": [P(lineChartType=S("linear"), strokeWidth=N(2), showMarker=B(True), markerShape=S("circle"),
                         markerSize=N(4), areaShow=B(False))],
        "labels": [P(show=B(False))],
        "categoryAxis": [P(axisType=S("Categorical"), show=B(True), showAxisTitle=B(True),
                           titleText=S("Measured at (local time of the plant)"), titleFontSize=N(8),
                           titleColor=C(GREY), fontSize=N(8), labelColor=C(R.MUTED))],
        "valueAxis": [P(show=B(True), start=measure("Trend Axis Min"), end=measure("Trend Axis Max"),
                        showAxisTitle=B(False), gridlineShow=B(True), gridlineStyle=S("dotted"),
                        gridlineColor=C(R.LINE), labelColor=C(R.MUTED2), fontSize=N(8))],
        "legend": [P(show=B(False))],
        "y1AxisReferenceLine": [SEL({
            "show": B(True), "displayName": S(name), "value": measure(m), "lineColor": C(color),
            "transparency": N(0 if style == "solid" else 15), "style": S(style), "width": N(1.5),
            "position": S("back"), "dataLabelShow": B(True), "dataLabelText": S("ValueAndName"),
            "dataLabelColor": C(color), "dataLabelHorizontalPosition": S("right"),
            "dataLabelVerticalPosition": S("above")}, {"id": str(i + 1)}) for i, (name, m, color, style) in enumerate(LIMITS)],
    }
    # Title and subtitle from measures: what to select while the filters leave several characteristics.
    vco = R.vco_card("Trend chart", " ")
    vco["title"][0]["properties"]["text"] = measure("Trend Title")
    A.dynamic_subtitle(vco, "Trend Subtitle")
    v["visual"]["visualContainerObjects"] = vco
    v.pop("filterConfig", None)
    return v


def build_trend_page(src, idx, p1, card_like, page_ids):
    """Visuals of the trend page, the names of its "More filters" panel copies, and its More filters button."""
    cards = D.PAGES["trend"]["cards"]
    out, panel_map = [], {}

    def add(v, src_name=None):
        out.append(v)
        if src_name:
            panel_map[src_name] = v["name"]
        return v

    for label, key in D.NAV:
        add(H.nav_button(src[idx["nav:overview"]], key, page_ids[key], label))
    add(H.nav_button(src[idx["nav:overview"]], "home", page_ids["home"], "Home"))
    add(A.clone(src[idx["clear"]]))
    add(A.clone(src[idx["refresh"]]))
    # The slicers of page 2: same fields, same sync groups
    slots = D.slicer_slots("trend")
    for (fname, _, _), (x, w) in zip(D.PAGES["trend"]["slicers"], slots):
        add(A.clone(src[idx["slicer:" + fname]], x=x, y=D.SLICER_Y, w=w, h=D.SLICER_H))
    mx, mw = slots[-1]
    add(A.clone(src[idx["more_look"]], x=mx, w=mw))
    more_btn = add(A.clone(src[idx["more_btn"]], x=mx, w=mw))

    hero = next(v for v in p1.values() if v["visual"]["visualType"] == "cardVisual")
    add(kpi_card(hero, cards["violations"], "Reaction limit violations",
                 "Values outside the reaction limits · current filters", "RL Violations", "Violations", units=1))
    # Cpk, and under it the goal with Pass / Fail as a line of text (a measure in the subtitle of this card type
    # was refused by Power BI Desktop).
    cx, cy, cw, _ = cards["cpk"]
    add(kpi_card(hero, cards["cpk"], "Cpk", "Goal = Cpk threshold of More filters (1.33 if none)", "Trend Cpk", "Cpk",
                 blank="–"))
    add(text_line(card_like, (cx + 16, cy + 86, cw - 32, 24), "Trend Cpk Goal", "Goal"))
    line_like = next(v for v in p1.values() if v["visual"]["visualType"] == "lineChart")
    add(trend_chart(line_like, cards["chart"]))

    # More filters: inspection reason and Cpk threshold, in the two places of page 2 (KPC and Press)
    for role in ("overlay_look", "overlay_btn", "panel_bg", "x_look", "x_btn"):
        add(A.clone(src[idx[role]]), idx[role])
    first, second = src[idx["panel_slicer:KPC"]], src[idx["panel_slicer:Press"]]
    reason = A.clone(src[idx["slicer:Inspection Reason"]], hidden=True)
    A.place(reason, *(first["position"][k] for k in ("x", "y", "width", "height")))
    for key in ("header", "items", "dropdown"):
        reason["visual"]["objects"][key] = copy.deepcopy(first["visual"]["objects"][key])
    reason["visual"]["visualContainerObjects"] = copy.deepcopy(first["visual"]["visualContainerObjects"])
    add(reason, idx["panel_slicer:KPC"])
    threshold = H.retarget_slicer(A.clone(second), "Cpk Threshold", "Threshold", "Cpk threshold (1.33 if none)")
    add(threshold, idx["panel_slicer:Press"])
    for role in ("reset", "close_look", "close_btn"):
        add(A.clone(src[idx[role]]), idx[role])
    return out, panel_map, more_btn


def copy_panel_bookmarks(defs, src, idx, panel_map, from_pid, to_pid, title):
    """The "More filters" open / closed bookmarks of page 2, for the copies of its panel on another page."""
    by_link = {R.link_of(src[idx[r]]).get("bookmark"): r for r in ("more_btn", "close_btn")}
    names = {}
    for b in [v for k, v in list(defs.items()) if k.startswith("bookmarks/") and k.endswith(".bookmark.json")]:
        role = by_link.get(b["name"])
        if not role:
            continue
        nb = copy.deepcopy(b)
        nb["name"] = "Bookmark" + A.new_name()
        nb["displayName"] = f"{title} – More filters " + ("open" if role == "more_btn" else "closed")
        targets = nb["options"]["targetVisualNames"]
        if any(n not in panel_map for n in targets):
            sys.exit(f"bookmark {b['displayName']}: no copy for {[n for n in targets if n not in panel_map]}")
        es = nb["explorationState"]
        sec = es["sections"].pop(from_pid)
        sec["visualContainers"] = {panel_map[n]: c for n, c in sec["visualContainers"].items()}
        nb["options"]["targetVisualNames"] = [panel_map[n] for n in targets]
        es["sections"] = {to_pid: sec}
        es["activeSection"] = to_pid
        defs[f"bookmarks/{nb['name']}.bookmark.json"] = nb
        defs["bookmarks/bookmarks.json"]["items"].append({"name": nb["name"]})
        names[role] = nb["name"]
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="V10 .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    strip_trend_page(defs, meta)
    keys = {}
    for pid in meta["pageOrder"]:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in PF.TITLES:
            sys.exit(f"unexpected page '{title}'")
        keys[PF.TITLES[title]] = pid
    required = set(PF.TITLES.values()) - {"trend"}
    if required - set(keys):
        sys.exit(f"pages missing: {sorted(required - set(keys))}")
    keys["trend"] = A.new_name()
    page_keys = {pid: k for k, pid in keys.items()}

    def visuals_of(pid):
        return {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}

    src = visuals_of(keys["chars"])
    idx = A.index_page(src, page_keys)
    missing = [r for r in A.REQUIRED if r not in idx]
    if missing:
        sys.exit(f"page Characteristics: could not find {missing}")
    p1 = visuals_of(keys["overview"])
    card_like = next(v for v in p1.values() if v["visual"]["visualType"] == "card")  # plain card (refresh time)

    # Cpk page
    update_cpk_page(defs, keys["cpk"])

    # Trend chart page
    visuals, panel_map, more_btn = build_trend_page(src, idx, p1, card_like, keys)
    page = copy.deepcopy(defs[f"pages/{keys['chars']}/page.json"])
    page["name"], page["displayName"] = keys["trend"], TREND_TITLE
    page.pop("filterConfig", None)
    defs[f"pages/{keys['trend']}/page.json"] = page
    for i, v in enumerate(visuals):
        v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
        defs[f"pages/{keys['trend']}/visuals/{v['name']}/visual.json"] = v
    names = copy_panel_bookmarks(defs, src, idx, panel_map, keys["chars"], keys["trend"], TREND_TITLE)
    A.set_link(more_btn, type="Bookmark", bookmark=names["more_btn"])
    closers = {panel_map[idx[r]] for r in ("overlay_btn", "x_btn", "close_btn")}
    for v in visuals:
        if v["name"] in closers:
            A.set_link(v, type="Bookmark", bookmark=names["close_btn"])

    # "Trend chart" tile on the other pages, and the home page rebuilt with its fifth row
    for key in ("overview", "chars", "rl", "cpk", "rl_details"):
        own = visuals_of(keys[key])
        like = own[A.index_page(own, page_keys)["nav:chars"]]
        v = H.nav_button(like, "trend", keys["trend"], "Trend chart")
        v["position"]["z"] = v["position"]["tabOrder"] = max(x["position"]["z"] for x in own.values()) + 1000
        defs[f"pages/{keys[key]}/visuals/{v['name']}/visual.json"] = v
    for k in [k for k in defs if k.startswith(f"pages/{keys['home']}/visuals/")]:
        del defs[k]
    for i, v in enumerate(H.build_home_page(src, idx, keys)):
        v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
        defs[f"pages/{keys['home']}/visuals/{v['name']}/visual.json"] = v

    order = ("home", "overview", "chars", "rl", "cpk", "trend", "rl_details")
    meta["pageOrder"] = [keys[k] for k in order]
    PF.add_period_slicers(defs, keys)  # every page with the period filter, Year selected
    images, old = PF.set_backgrounds(defs, keys)

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages, {sum(1 for k in defs if '/visuals/' in k)} visuals, "
          f"{len(defs['bookmarks/bookmarks.json']['items'])} bookmarks)")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v11"
    work.mkdir(parents=True, exist_ok=True)
    model_dir = pm.write_model(work, settings)
    model_json = bt.model_schema(model_dir, work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)
    dst = HERE / "out" / f"{OUT_NAME}.pbit"
    pkg.write_template(zin, defs, images, old, dst, work / "DataModelSchema.json", bt.diagram_layout(model_json))
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
