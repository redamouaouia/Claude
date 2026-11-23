"""Quality Dashboard V3: add page 3 "Reaction limits" and its drill-through details page.

Usage:  python add_reaction_limits.py <V3 .pbix> [settings.json] [--range START END]

- <V3 .pbix>: the V3 report saved by Power BI Desktop (PBIR format). Pages 1 and 2 keep their visuals, filters and
  bookmarks; they get the third navigation tile and their redrawn backgrounds.
- settings.json (default: ../v2/databricks.local.json, git-ignored): SQL warehouse host and HTTP path.
- --range START END: RangeStart / RangeEnd prefilled in the template (default: the range of settings.json).

Page 3 follows the mockup of the specification: violations per day, top 15 characteristics, violations by part
(with a "Details" button) and by test. "Details" opens a hidden drill-through page that lists the violations of the
selected part: date and time, part, test, characteristic, value, reaction limits and tolerance. Header filters,
navigation and the "More filters" panel are copies of those of page 2, so they stay synced with the other pages.
Two cases:
- the report has no page 3 yet: the model, with the new reaction-limit columns and measures, comes from
  ../v2/build_template.py, and the output is a template, out/Quality_Dashboard_V3_RL.pbit (data reloaded on opening);
- the report already has page 3 (saved after loading that template): pages 3 and its details page are rebuilt, the
  model and its data are kept, and the output is out/Quality_Dashboard_V3_RL.pbix.
Outputs are git-ignored.
"""
import argparse
import copy
import json
import math
import os
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "v2"))
import build_template as bt  # noqa: E402
import design as D  # noqa: E402
import pbit_package as pkg  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, N, P, S, SEL, T  # noqa: E402

RL_BLUE = "#1F4E79"    # colour of the reaction limits in the specification
RL_LIGHT = "#BDD7EE"   # its light shade, for data bars
RL_MID = "#7C9CC6"     # lowest value of the treemap gradient
PAGE_TITLES = {"Overview": "overview", "Characteristics": "chars"}
RL_TITLES = {D.PAGES["rl"]["title"], D.PAGES["rl_details"]["title"]}
ALL_POINTS = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}
BG_NAMES = {"overview": "Overview", "chars": "Characteristics", "rl": "ReactionLimits", "rl_details": "ReactionLimitDetails"}


# --------------------------------------------------------------------------- small builders
def new_name():
    return secrets.token_hex(10)


def clone(v, x=None, y=None, w=None, h=None, hidden=None):
    c = copy.deepcopy(v)
    c["name"] = new_name()
    for key, val in (("x", x), ("y", y), ("width", w), ("height", h)):
        if val is not None:
            c["position"][key] = val
    if hidden is True:
        c["isHidden"] = True
    elif hidden is False:
        c.pop("isHidden", None)
    return c


def place(v, x, y, w, h):
    v["position"].update({"x": x, "y": y, "width": w, "height": h})


def set_link(v, **props):
    v["visual"].setdefault("visualContainerObjects", {})["visualLink"] = [
        P(show=B(True), **{k: S(val) for k, val in props.items()})]


def new_visual(schema, vt, rect, roles, sort=None):
    x, y, w, h = rect
    v = {"$schema": schema, "name": new_name(),
         "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0},
         "visual": {"visualType": vt,
                    "query": {"queryState": {role: {"projections": p} for role, p in roles.items()}},
                    "objects": {}, "visualContainerObjects": {}, "drillFilterOtherVisuals": True}}
    if sort:
        kind, name, direction = sort
        v["visual"]["query"]["sortDefinition"] = {"sort": [{"field": R.field(kind, name), "direction": direction}]}
    return v


def set_query(v, roles, sort=None):
    q = v["visual"]["query"]
    q["queryState"] = {role: {"projections": p} for role, p in roles.items()}
    if sort:
        kind, name, direction = sort
        q["sortDefinition"] = {"sort": [{"field": R.field(kind, name), "direction": direction}]}


def ref(name):
    return f"{T}.{name}"


def dynamic_subtitle(vco, measure):
    vco["subTitle"][0]["properties"]["text"] = R.measure_expr(measure)
    return vco


# --------------------------------------------------------------------------- filters (PBIR filterConfig entries)
def _q(kind, name, alias="q"):
    return {kind: {"Expression": {"SourceRef": {"Source": alias}}, "Property": name}}


def _filter(kind, name, ftype, body):
    return {"name": "Filter" + new_name(), "field": R.field(kind, name), "type": ftype, "filter": body,
            "howCreated": "User"}


def above_zero(measure):
    return _filter("Measure", measure, "Advanced", {
        "Version": 2, "From": [{"Name": "q", "Entity": T, "Type": 0}],
        "Where": [{"Condition": {"Comparison": {"ComparisonKind": 1, "Left": _q("Measure", measure),
                                                "Right": {"Literal": {"Value": "0L"}}}}}]})


def top_n(column, measure, n):
    sub = {"Version": 2, "From": [{"Name": "q", "Entity": T, "Type": 0}],
           "Select": [dict(_q("Column", column), Name="field")],
           "OrderBy": [{"Direction": 2, "Expression": _q("Measure", measure)}], "Top": n}
    return _filter("Column", column, "TopN", {
        "Version": 2,
        "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": sub}}, "Type": 2},
                 {"Name": "q", "Entity": T, "Type": 0}],
        "Where": [{"Condition": {"In": {"Expressions": [_q("Column", column)],
                                        "Table": {"SourceRef": {"Source": "subquery"}}}}}]})


def equals(column, literal):
    return _filter("Column", column, "Categorical", {
        "Version": 2, "From": [{"Name": "q", "Entity": T, "Type": 0}],
        "Where": [{"Condition": {"In": {"Expressions": [_q("Column", column)],
                                        "Values": [[{"Literal": {"Value": literal}}]]}}}]})


def gradient(measure, low, high):
    """Colour by value, from `low` (smallest) to `high` (largest): the "fx" gradient of the format pane."""
    return {"solid": {"color": {"expr": {"FillRule": {
        "Input": {"Measure": {"Expression": {"SourceRef": {"Entity": T}}, "Property": measure}},
        "FillRule": {"linearGradient2": {
            "min": {"color": {"Literal": {"Value": f"'{low}'"}}},
            "max": {"color": {"Literal": {"Value": f"'{high}'"}}},
            "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}


def column_format(name, color=None, bars=None, values=True):
    props = {"styleHeader": B(True), "styleValues": B(values)}
    if color:
        props["fontColor"] = C(color)
    if bars:
        props["dataBars"] = {"positiveColor": C(bars), "negativeColor": C(bars), "axisColor": C(R.WHITE),
                             "reverseDirection": B(False), "hideText": B(False)}
    return SEL(props, {"metadata": ref(name)})


# --------------------------------------------------------------------------- reading page 2
def index_page(visuals, page_keys):
    """Role of each visual of a V3 page: navigation, header filters, "More filters" panel, content."""
    idx = {}
    for name, v in visuals.items():
        vt, p, hidden = v["visual"]["visualType"], v["position"], v.get("isHidden", False)
        link = R.link_of(v)
        role = None
        if vt == "actionButton":
            kind = link.get("type")
            if kind == "PageNavigation":
                role = "nav:" + page_keys.get(link.get("navigationSection"), "?")
            elif kind == "ClearAllSlicers":
                role = "reset" if hidden else "clear"
            elif p["width"] >= 900:
                role = "overlay_btn"
            elif hidden:
                role = "x_btn" if p["width"] <= 40 else "close_btn"
            elif kind == "Bookmark" and abs(p["y"] - D.SLICER_Y) < 2:
                role = "more_btn"
        elif vt == "textbox":
            if p["width"] >= 900:
                role = "overlay_look"
            elif hidden and p["x"] >= 970 and p["width"] >= 250:
                role = "panel_bg"
            elif hidden:
                role = "x_look" if p["width"] <= 40 else "close_look"
            elif abs(p["y"] - D.SLICER_Y) < 2:
                role = "more_look"
        elif vt == "slicer":
            role = ("panel_slicer:" if hidden else "slicer:") + R.fields_of(v)["Values"][0]
        elif vt == "card":
            role = "refresh"
        else:
            role = vt
        if role:
            idx.setdefault(role, name)
    return idx


REQUIRED = ["nav:overview", "nav:chars", "clear", "refresh", "more_look", "more_btn", "overlay_look", "overlay_btn",
            "panel_bg", "x_look", "x_btn", "reset", "close_look", "close_btn", "panel_slicer:KPC",
            "panel_slicer:Press", "slicer:Plant", "slicer:Part", "slicer:Test", "slicer:Characteristic",
            "slicer:Inspection Reason", "slicer:Date", "lineChart", "tableEx"]


# --------------------------------------------------------------------------- page 3 and its details page
def build_rl_page(src, idx, page_ids):
    """Visuals of page 3, in stacking order, and the page-2 → page-3 name map of the "More filters" panel."""
    cards = D.PAGES["rl"]["cards"]
    schema = src[idx["lineChart"]]["$schema"]
    out, panel_map = [], {}

    def add(v, src_name=None):
        out.append(v)
        if src_name:
            panel_map[src_name] = v["name"]
        return v

    for label, key in D.NAV:
        nav = add(clone(src[idx["nav:overview"]]))
        place(nav, *D.NAV_TILES[key])
        set_link(nav, type="PageNavigation", navigationSection=page_ids[key], tooltip=label)
    add(clone(src[idx["clear"]]))
    add(clone(src[idx["refresh"]]))
    slots = D.slicer_slots("rl")
    for (fname, _, _), (x, w) in zip(D.PAGES["rl"]["slicers"], slots):
        add(clone(src[idx["slicer:" + fname]], x=x, y=D.SLICER_Y, w=w, h=D.SLICER_H))
    mx, mw = slots[-1]
    add(clone(src[idx["more_look"]], x=mx, w=mw))
    more_btn = add(clone(src[idx["more_btn"]], x=mx, w=mw))

    # Reaction limit violations per day
    line = add(clone(src[idx["lineChart"]]))
    place(line, *cards["line"])
    set_query(line, {"Category": [R.projection("Column", "Date", "Date", active=True)],
                     "Y": [R.projection("Measure", "RL Violations", "Violations")]},
              sort=("Column", "Date", "Ascending"))
    line["visual"]["objects"] = {
        "dataPoint": [SEL({"fill": C(RL_BLUE)}, {"metadata": ref("RL Violations")})],
        "lineStyles": [SEL({"lineChartType": S("linear"), "strokeWidth": N(1.5), "showMarker": B(False),
                            "areaShow": B(True), "areaMatchStrokeColor": B(True)}, {"metadata": ref("RL Violations")})],
        "legend": [P(show=B(False))],
        "categoryAxis": [P(showAxisTitle=B(False), gridlineShow=B(False), fontSize=N(9), labelColor=C(R.MUTED))],
        "valueAxis": [P(show=B(True), showAxisTitle=B(False), gridlineShow=B(True), gridlineStyle=S("dotted"),
                        gridlineColor=C(R.LINE), labelColor=C(R.MUTED2), fontSize=N(8))],
    }
    line["visual"]["visualContainerObjects"] = dynamic_subtitle(
        R.vco_card("Reaction limit violations per day", "-"), "RL Summary")

    # Top 15 characteristics
    top = add(new_visual(schema, "clusteredBarChart", cards["top15"], {
        "Category": [R.projection("Column", "Characteristic", "Characteristic", active=True)],
        "Y": [R.projection("Measure", "RL Violations", "Violations")]},
        sort=("Measure", "RL Violations", "Descending")))
    top["visual"]["objects"] = {
        # Seen in Desktop: the series colour alone (metadata selector) left this chart in the theme's blue, while
        # the "all data points" selector coloured the treemap. Both are set, with the same colour.
        "dataPoint": [SEL({"fill": C(RL_BLUE)}, {"metadata": ref("RL Violations")}),
                      SEL({"fill": C(RL_BLUE)}, ALL_POINTS)],
        "labels": [P(show=B(True), color=C(R.TEXT), fontSize=N(9), labelPosition=S("OutsideEnd"))],
        "categoryAxis": [P(show=B(True), showAxisTitle=B(False), fontSize=N(9), labelColor=C(R.TEXT),
                           maxMarginFactor=R.I(58), innerPadding=R.I(28))],
        "valueAxis": [P(show=B(False), showAxisTitle=B(False), gridlineShow=B(False))],
        "legend": [P(show=B(False))],
    }
    top["visual"]["visualContainerObjects"] = R.vco_card("Top 15 characteristics",
                                                         "Characteristics with the most values outside the limits")
    top["filterConfig"] = {"filters": [top_n("Characteristic", "RL Violations", 15), above_zero("RL Violations")]}

    # Violations by part, with the Details button (drill-through)
    tree = add(new_visual(schema, "treemap", cards["treemap"], {
        "Group": [R.projection("Column", "Part", "Part", active=True)],
        "Values": [R.projection("Measure", "RL Violations", "Violations")],
        "Tooltips": [R.projection("Measure", "RL Violation %", "Violation rate")]},
        sort=("Measure", "RL Violations", "Descending")))
    tree["visual"]["objects"] = {
        "dataPoint": [SEL({"fill": gradient("RL Violations", RL_MID, RL_BLUE)}, ALL_POINTS)],
        "labels": [P(show=B(True), color=C(R.WHITE), fontSize=N(9), labelDisplayUnits=N(1), labelPrecision=R.I(0))],
        "categoryLabels": [P(show=B(True), color=C(R.WHITE), fontSize=N(9))],
        "legend": [P(show=B(False))],
    }
    # No visual header on this card: its icons would cover the Details button.
    tree["visual"]["visualContainerObjects"] = R.vco_card(
        "Violations by part", "Select a part, then Details for its list of values", header=False)
    tree["filterConfig"] = {"filters": [above_zero("RL Violations")]}
    tx, ty, tw, _ = cards["treemap"]
    details = clone(src[idx["x_btn"]], x=tx + tw - 14 - 86, y=ty + 12, w=86, h=26, hidden=False)
    set_link(details, type="Drillthrough", drillthroughSection=page_ids["rl_details"],
             enabledTooltip="List of the violations of the selected part",
             disabledTooltip="Select a part in the chart first")
    # Until a part is selected the button is disabled, and Power BI then paints its own grey "disabled" fill over
    # the label underneath (seen on screen). The disabled state is made a light white veil instead: the label
    # shows, greyed out, and becomes sharp once a part is selected.
    o = details["visual"]["objects"]
    o["fill"].append(SEL({"show": B(True), "fillColor": C(R.WHITE), "transparency": N(45)}, {"id": "disabled"}))
    o["text"].append(SEL({"show": B(False)}, {"id": "disabled"}))
    o["outline"].append(SEL({"show": B(False)}, {"id": "disabled"}))
    o["icon"].append(SEL({"shapeType": S("blank")}, {"id": "disabled"}))
    add(R.twin_textbox(details, dict(text="Details  ›", bg="#EEF2F8", fg=R.NAVY, size=9, bold=True, radius=13,
                                     pad_top=4, bg_transp=0, border=True)))
    add(details)

    # Violations by test, with their share
    table = add(clone(src[idx["tableEx"]]))
    place(table, *cards["table"])
    set_query(table, {"Values": [R.projection("Column", "Test", "Test"),
                                 R.projection("Measure", "RL Violations", "Violations"),
                                 R.projection("Measure", "RL Share", "Share")]},
              sort=("Measure", "RL Violations", "Descending"))
    o = table["visual"]["objects"]
    o["columnFormatting"] = [column_format("RL Violations", bars=RL_LIGHT),
                             column_format("RL Share", color=RL_BLUE)]
    # 310 px of columns in a 338 px wide table: room left for the vertical scroll bar (no horizontal scrolling)
    o["columnWidth"] = [SEL({"value": N(150)}, {"metadata": ref("Test")}),
                        SEL({"value": N(98)}, {"metadata": ref("RL Violations")}),
                        SEL({"value": N(62)}, {"metadata": ref("RL Share")})]
    table["visual"]["visualContainerObjects"] = R.vco_card("Violations by test",
                                                           "Number of violations · share of all the violations")
    table["filterConfig"] = {"filters": [above_zero("RL Violations")]}

    # "More filters" panel: Inspection reason and KPC, on top of everything
    for role in ("overlay_look", "overlay_btn", "panel_bg", "x_look", "x_btn"):
        add(clone(src[idx[role]]), idx[role])
    first, second = src[idx["panel_slicer:KPC"]], src[idx["panel_slicer:Press"]]
    reason = clone(src[idx["slicer:Inspection Reason"]], hidden=True)  # same field, sync group and selection
    place(reason, *(first["position"][k] for k in ("x", "y", "width", "height")))
    for key in ("header", "items", "dropdown"):
        reason["visual"]["objects"][key] = copy.deepcopy(first["visual"]["objects"][key])
    reason["visual"]["visualContainerObjects"] = copy.deepcopy(first["visual"]["visualContainerObjects"])
    add(reason, idx["panel_slicer:KPC"])
    add(clone(first, y=second["position"]["y"]), idx["panel_slicer:Press"])
    for role in ("reset", "close_look", "close_btn"):
        add(clone(src[idx[role]]), idx[role])
    return out, panel_map, more_btn


def build_details_page(src, idx, page_ids):
    cards = D.PAGES["rl_details"]["cards"]
    out = []
    for label, key in D.NAV:
        nav = clone(src[idx["nav:overview"]])
        place(nav, *D.NAV_TILES[key])
        set_link(nav, type="PageNavigation", navigationSection=page_ids[key], tooltip=label)
        out.append(nav)
    out.append(clone(src[idx["clear"]]))
    out.append(clone(src[idx["refresh"]]))

    context = clone(src[idx["refresh"]])
    place(context, *D.CONTEXT)
    set_query(context, {"Values": [R.projection("Measure", "RL Details Title", "Selection")]})
    context["visual"]["objects"] = {
        "labels": [P(color=C(R.WHITE), fontSize=N(12), fontFamily=S("Segoe UI Semibold"))],
        "categoryLabels": [P(show=B(False))]}
    out.append(context)

    back = clone(src[idx["x_btn"]], hidden=False)
    place(back, *D.BACK)
    set_link(back, type="Back", tooltip="Back to Reaction limits")
    out.append(R.twin_textbox(back, dict(text="‹  Back", bg=R.WHITE, fg=R.NAVY, size=9, bold=True, radius=18,
                                         pad_top=8, bg_transp=0, border=True)))
    out.append(back)

    table = clone(src[idx["tableEx"]])
    place(table, *cards["table"])
    columns = [("Column", "RL Time", "Date & time", 132), ("Column", "Part", "Part", 196),
               ("Column", "Test", "Test", 170), ("Column", "Characteristic", "Characteristic", 236),
               ("Column", "RL Value", "Value", 78), ("Column", "RL Low Limit", "Reaction low", 92),
               ("Column", "RL High Limit", "Reaction high", 92), ("Column", "RL LSL", "LSL", 52),
               ("Column", "RL USL", "USL", 52)]
    set_query(table, {"Values": [R.projection(k, n, d) for k, n, d, _ in columns]},
              sort=("Column", "RL Time", "Descending"))
    o = table["visual"]["objects"]
    o["columnFormatting"] = [column_format("RL Value", color=RL_BLUE)]
    o["columnWidth"] = [SEL({"value": N(w)}, {"metadata": ref(n)}) for _, n, _, w in columns]
    table["visual"]["visualContainerObjects"] = R.vco_card(
        "Values outside the reaction limits",
        "Most recent first · reaction low / high = alert limits · LSL / USL = tolerance of the inspection plan")
    table["filterConfig"] = {"filters": [equals("RL Violation", "1L")]}
    out.append(table)
    return out


# --------------------------------------------------------------------------- checks
def checks(defs, pages_order):
    """Structural rules of Microsoft's PBIR validator, applied to the whole report definition."""
    problems = []
    pages = {pid: defs[f"pages/{pid}/page.json"] for pid in pages_order}
    visuals = {pid: {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
               for pid in pages_order}
    cat_dir = pathlib.Path(os.environ.get("PBI_VISUAL_SCHEMA_DIR", ""))
    cap = json.loads((cat_dir / "capabilities.json").read_text())
    bookmarks = {k: v for k, v in defs.items() if k.startswith("bookmarks/") and k.endswith(".bookmark.json")}
    bookmark_names = {b["name"] for b in bookmarks.values()}

    filter_names = []
    for pid, page in pages.items():
        if len(pid) > 50:
            problems.append(f"page name too long: {pid}")
        for f in page.get("filterConfig", {}).get("filters", []):
            filter_names.append(f["name"])
        for name, v in visuals[pid].items():
            vis, pos = v["visual"], v["position"]
            where = f"{page['displayName']}/{vis['visualType']}/{name}"
            if len(name) > 50:
                problems.append(f"{where}: visual name too long")
            if pos["x"] < 0 or pos["y"] < 0 or pos["x"] + pos["width"] > page["width"] + 0.5 or \
                    pos["y"] + pos["height"] > page["height"] + 0.5:
                problems.append(f"{where}: outside the page")
            if vis["visualType"] == "textbox":
                sizes = [float(r["textStyle"]["fontSize"].rstrip("pt")) for para in
                         vis["objects"]["general"][0]["properties"]["paragraphs"] for r in para["textRuns"]
                         if r.get("textStyle", {}).get("fontSize")]
                if sizes:
                    pad = vis.get("visualContainerObjects", {}).get("padding", [{}])[0].get("properties", {})
                    top = float(pad.get("top", {}).get("expr", {}).get("Literal", {}).get("Value", "8D").rstrip("D"))
                    bottom = float(pad.get("bottom", {}).get("expr", {}).get("Literal", {}).get("Value", "8D").rstrip("D"))
                    floor = max(18, math.ceil(max(sizes) * 25 / 16)) + top + bottom
                    if pos["height"] < floor:
                        problems.append(f"{where}: text box {pos['height']}px < {floor}px")
            kinds = {r["name"]: r.get("kind") for r in cap.get(vis["visualType"], {}).get("dataRoles", [])}
            for role, state in vis.get("query", {}).get("queryState", {}).items():
                for proj in state.get("projections", []):
                    if not proj.get("nativeQueryRef"):
                        problems.append(f"{where}: projection without nativeQueryRef in {role}")
                    if kinds.get(role) == 0 and "Measure" in proj["field"]:
                        problems.append(f"{where}: measure in grouping role {role}")
                    if kinds.get(role) == 1 and "Column" in proj["field"]:
                        problems.append(f"{where}: column in measure role {role}")
            for f in v.get("filterConfig", {}).get("filters", []):
                filter_names.append(f["name"])
                aliases = {x["Name"] for x in f.get("filter", {}).get("From", [])}
                for clause in f.get("filter", {}).get("Where", []):
                    for o in pkg.walk(clause):
                        src = o.get("SourceRef")
                        if isinstance(src, dict) and ("Entity" in src or src.get("Source") not in aliases):
                            problems.append(f"{where}: filter {f['name']} refers to {src} in Where")
            link = R.link_of(v)
            if link.get("type") == "PageNavigation" and link.get("navigationSection") not in pages:
                problems.append(f"{where}: navigation to a missing page")
            if link.get("type") == "Drillthrough":
                target = pages.get(link.get("drillthroughSection"), {})
                if target.get("pageBinding", {}).get("type") != "Drillthrough":
                    problems.append(f"{where}: drill-through to a page that is not a drill-through page")
            if link.get("type") == "Bookmark" and link.get("bookmark") not in bookmark_names:
                problems.append(f"{where}: bookmark {link.get('bookmark')} missing")

        binding = page.get("pageBinding")
        if binding:
            dt = {f["name"]: f for f in page.get("filterConfig", {}).get("filters", [])
                  if f.get("howCreated") == "Drillthrough"}
            for prm in binding.get("parameters", []):
                f = dt.get(prm.get("boundFilter"))
                if not f or f.get("field") != prm.get("fieldExpr"):
                    problems.append(f"{page['displayName']}: drill-through parameter not bound to its filter")
            if not dt or not binding.get("parameters"):
                problems.append(f"{page['displayName']}: drill-through filter or parameter missing")
            if not any(v["visual"]["visualType"] == "actionButton" and not v.get("isHidden")
                       and R.link_of(v).get("type") == "Back" for v in visuals[pid].values()):
                problems.append(f"{page['displayName']}: no visible Back button")

    dupes = {n for n in filter_names if filter_names.count(n) > 1}
    problems += [f"duplicate filter name {n}" for n in dupes]
    indexed = {i["name"] for i in defs["bookmarks/bookmarks.json"]["items"]}
    for k, b in bookmarks.items():
        if b["name"] not in indexed:
            problems.append(f"bookmark {b['name']} not listed in bookmarks.json")
        if k != f"bookmarks/{b['name']}.bookmark.json":
            problems.append(f"bookmark file name {k} differs from its name")
        sec = b["explorationState"]["activeSection"]
        if sec not in pages:
            problems.append(f"bookmark {b['displayName']}: page {sec} missing")
            continue
        for n in b["options"].get("targetVisualNames", []):
            if n not in visuals[sec]:
                problems.append(f"bookmark {b['displayName']}: target {n} missing")
        for s, state in b["explorationState"]["sections"].items():
            for n in state.get("visualContainers", {}):
                if n not in visuals.get(s, {}):
                    problems.append(f"bookmark {b['displayName']}: visual {n} missing on {s}")
    problems += R.check_capabilities({pages[p]["displayName"]: visuals[p] for p in pages_order})
    return problems


# --------------------------------------------------------------------------- report that already has page 3
def strip_reaction_limits(defs, meta):
    """Removes page 3, its details page, their bookmarks and the buttons leading to them. True if they existed."""
    gone = [pid for pid in meta["pageOrder"] if defs[f"pages/{pid}/page.json"]["displayName"] in RL_TITLES]
    if not gone:
        return False
    for k in [k for k in defs if any(k.startswith(f"pages/{pid}/") for pid in gone)]:
        del defs[k]
    meta["pageOrder"] = [p for p in meta["pageOrder"] if p not in gone]
    if meta.get("activePageName") in gone:
        meta["activePageName"] = meta["pageOrder"][0]
    dead = set()
    for k in [k for k in defs if k.startswith("bookmarks/") and k.endswith(".bookmark.json")]:
        if defs[k]["explorationState"].get("activeSection") in gone:
            dead.add(defs[k]["name"])
            del defs[k]
    index = defs["bookmarks/bookmarks.json"]
    index["items"] = [i for i in index["items"] if i["name"] not in dead]
    for k in [k for k in defs if "/visuals/" in k]:
        link = R.link_of(defs[k])
        if link.get("navigationSection") in gone or link.get("drillthroughSection") in gone:
            del defs[k]
    return True


def model_fields(pbix):
    """Columns and measures of the model inside a .pbix, in the shape check_fields expects."""
    try:
        from pbixray import PBIXRay
    except ImportError:
        print("pbixray is not installed: fields are checked against the expected V3 model instead")
        tables = {T: [c[0] for c in bt.COLUMNS] + [m[0] for m in bt.MEASURES]}
    else:
        m = PBIXRay(pbix)
        tables = {}
        for _, r in m.schema.iterrows():
            tables.setdefault(r["TableName"], []).append(r["ColumnName"])
        for _, r in m.dax_measures.iterrows():
            tables.setdefault(r["TableName"], []).append(r["Name"])
    return {"model": {"tables": [{"name": t, "columns": [{"name": n} for n in names]} for t, names in tables.items()]}}


def write_pbix(zin, defs, images, old, dst):
    """Same .pbix with the new report: data model kept, credentials part dropped (Desktop rewrites it)."""
    skip = {"SecurityBindings"} | {f"Report/StaticResources/RegisteredResources/{n}" for n in old}
    ct = zin.read("[Content_Types].xml").decode("utf-8-sig").replace(
        '<Override PartName="/SecurityBindings" ContentType="" />', "")
    with zipfile.ZipFile(dst, "w") as z:
        for info in zin.infolist():
            n = info.filename
            if n in skip or n.startswith(pkg.PREFIX):
                continue
            zi = zipfile.ZipInfo(n, date_time=info.date_time)
            zi.compress_type = info.compress_type
            z.writestr(zi, ct.encode("utf-8-sig") if n == "[Content_Types].xml" else zin.read(n))
        for k, v in sorted(defs.items()):
            z.writestr(zipfile.ZipInfo(pkg.PREFIX + k), json.dumps(v, ensure_ascii=False, separators=(",", ":")),
                       compress_type=zipfile.ZIP_DEFLATED)
        for n, data in images.items():
            z.writestr(zipfile.ZipInfo("Report/StaticResources/RegisteredResources/" + n), data,
                       compress_type=zipfile.ZIP_DEFLATED)


# --------------------------------------------------------------------------- main
def set_background(page, title, item):
    page["objects"] = page.get("objects", {})
    page["objects"]["background"] = [P(image={"image": {
        "name": S(f"{title} background.png"),
        "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                 "ItemName": item}}},
        "scaling": S("Fit")}}, transparency=N(0))]
    page["objects"].setdefault("outspace", [P(color=C("#E7EDF5"), transparency=N(0))])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix", help="V3 .pbix saved by Power BI Desktop (PBIR format)")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    # A report that already has page 3 (its model has the reaction-limit columns and measures): pages 3 and its
    # details page are rebuilt and the model and its data are kept, so the output is a .pbix, not a template.
    rebuild = strip_reaction_limits(defs, meta)
    page_keys = {}
    for pid in meta["pageOrder"]:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in PAGE_TITLES:
            sys.exit(f"unexpected page '{title}': this script expects the V3 report with Overview and Characteristics")
        page_keys[pid] = PAGE_TITLES[title]
    page_ids = {key: pid for pid, key in page_keys.items()}
    page_ids["rl"], page_ids["rl_details"] = new_name(), new_name()
    page_keys.update({page_ids["rl"]: "rl", page_ids["rl_details"]: "rl_details"})

    def visuals_of(pid):
        return {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}

    src = visuals_of(page_ids["chars"])
    idx = index_page(src, page_keys)
    missing = [r for r in REQUIRED if r not in idx]
    if missing:
        sys.exit(f"page Characteristics: could not find {missing}")

    # third navigation tile on pages 1 and 2
    for key in ("overview", "chars"):
        pid = page_ids[key]
        own = visuals_of(pid)
        nav = clone(own[index_page(own, page_keys)["nav:chars"]])
        place(nav, *D.NAV_TILES["rl"])
        set_link(nav, type="PageNavigation", navigationSection=page_ids["rl"], tooltip="Reaction limits")
        nav["position"]["z"] = nav["position"]["tabOrder"] = max(v["position"]["z"] for v in own.values()) + 1000
        defs[f"pages/{pid}/visuals/{nav['name']}/visual.json"] = nav

    # page 3, its details page, and the bookmarks of the page 3 panel
    rl_visuals, panel_map, more_btn = build_rl_page(src, idx, page_ids)
    details_visuals = build_details_page(src, idx, page_ids)
    by_link = {R.link_of(src[idx[r]]).get("bookmark"): r for r in ("more_btn", "close_btn")}
    names = {}
    for bm_key, b in [(k, v) for k, v in list(defs.items()) if k.startswith("bookmarks/") and k.endswith(".bookmark.json")]:
        role = by_link.get(b["name"])
        if not role:
            continue
        nb = copy.deepcopy(b)
        nb["name"] = "Bookmark" + new_name()
        nb["displayName"] = "Reaction limits – More filters " + ("open" if role == "more_btn" else "closed")
        targets = nb["options"]["targetVisualNames"]
        unmapped = [n for n in targets if n not in panel_map]
        if unmapped:
            sys.exit(f"bookmark {b['displayName']}: no page-3 copy for {unmapped}")
        nb["options"]["targetVisualNames"] = [panel_map[n] for n in targets]
        es = nb["explorationState"]
        sec = es["sections"].pop(page_ids["chars"])
        sec["visualContainers"] = {panel_map[n]: c for n, c in sec["visualContainers"].items()}
        es["sections"] = {page_ids["rl"]: sec}
        es["activeSection"] = page_ids["rl"]
        defs[f"bookmarks/{nb['name']}.bookmark.json"] = nb
        defs["bookmarks/bookmarks.json"]["items"].append({"name": nb["name"]})
        names[role] = nb["name"]
    set_link(more_btn, type="Bookmark", bookmark=names["more_btn"])
    closers = {panel_map[idx[r]] for r in ("overlay_btn", "x_btn", "close_btn")}
    for v in rl_visuals:
        if v["name"] in closers:
            set_link(v, type="Bookmark", bookmark=names["close_btn"])

    template_page = defs[f"pages/{page_ids['chars']}/page.json"]
    for key, vlist in (("rl", rl_visuals), ("rl_details", details_visuals)):
        pid = page_ids[key]
        page = copy.deepcopy(template_page)
        page["name"], page["displayName"] = pid, D.PAGES[key]["title"]
        page.pop("filterConfig", None)
        defs[f"pages/{pid}/page.json"] = page
        for i, v in enumerate(vlist):
            v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
            defs[f"pages/{pid}/visuals/{v['name']}/visual.json"] = v
    details_page = defs[f"pages/{page_ids['rl_details']}/page.json"]
    part = R.field("Column", "Part")
    dt_filter = {"name": "Filter" + new_name(), "field": part, "type": "Categorical", "howCreated": "Drillthrough"}
    details_page["filterConfig"] = {"filters": [dt_filter]}
    details_page["pageBinding"] = {"name": new_name(), "type": "Drillthrough",
                                   "parameters": [{"name": new_name(), "boundFilter": dt_filter["name"],
                                                   "fieldExpr": copy.deepcopy(part)}]}
    details_page["type"] = "Drillthrough"
    details_page["visibility"] = "HiddenInViewMode"
    meta["pageOrder"] += [page_ids["rl"], page_ids["rl_details"]]
    meta["activePageName"] = page_ids["rl"]

    # page backgrounds: every page is redrawn with the three navigation tiles
    images = {}
    for key in ("overview", "chars", "rl", "rl_details"):
        item = f"QualityDashboard{BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_{key}.png").read_bytes()
        set_background(defs[f"pages/{page_ids[key]}/page.json"], D.PAGES[key]["title"], item)
    report = defs["report.json"]
    old = [i["name"] for p in report["resourcePackages"] if p["name"] == "RegisteredResources" for i in p["items"]]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]

    problems = checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages, "
          f"{sum(1 for k in defs if '/visuals/' in k)} visuals, {len(defs['bookmarks/bookmarks.json']['items'])} bookmarks)")

    if rebuild:
        pkg.check_fields(defs, model_fields(args.pbix))
        dst = HERE / "out" / "Quality_Dashboard_V3_RL.pbix"
        write_pbix(zin, defs, images, old, dst)
        print(f"written {dst} ({dst.stat().st_size:,} bytes): page 3 and its details page rebuilt, model and data kept")
        return

    # model: V2 model with the reaction-limit columns and measures
    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "rl"
    work.mkdir(parents=True, exist_ok=True)
    model_json = bt.model_schema(bt.write_model(work, settings), work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)

    dst = HERE / "out" / "Quality_Dashboard_V3_RL.pbit"
    skip = pkg.REPLACED | {f"Report/StaticResources/RegisteredResources/{n}" for n in old}
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Version", zin.read("Version"))
        z.writestr("[Content_Types].xml", pkg.content_types(zin.read("[Content_Types].xml")))
        z.writestr("DataModelSchema", (work / "DataModelSchema.json").read_bytes())
        z.writestr("DiagramLayout", json.dumps(bt.diagram_layout(model_json)).encode("utf-16-le"))
        for n in zin.namelist():
            if n not in skip and not n.startswith(pkg.PREFIX):
                z.writestr(n, zin.read(n))
        for k, v in sorted(defs.items()):
            z.writestr(pkg.PREFIX + k, json.dumps(v, ensure_ascii=False, separators=(",", ":")))
        for n, data in images.items():
            z.writestr("Report/StaticResources/RegisteredResources/" + n, data)
    print(f"written {dst} ({dst.stat().st_size:,} bytes), range {settings['range_start']} .. {settings['range_end']}")


if __name__ == "__main__":
    main()
