"""Quality Dashboard V3: add the home page (concept B) and page 4 "Cpk" (to be validated).

Usage:  python add_home_and_cpk.py <.pbix with pages 1 to 3> [settings.json] [--range START END]

- Home: hero with the company logo, purpose and key figures (plants and measured values are live), one row per
  page that opens it, and a reading guide. The company symbol at the top of the rail becomes the Home button of
  every page.
- Cpk, laid out as the mockup of the specification: Cpk pass %, Pass & Fail donut, Pass & Fail % by part and by
  test (with the number of characteristics), Cpk of each characteristic. More filters: inspection reason,
  Cpk threshold (1.33 by default) and Cpk pass / fail. Its filters work on the Cpk table and carry the same sync
  group names as the filters of the other pages.
The model gets the Cpk tables and measures of cpk_model.py, and keeps the incremental refresh of Quality Tracker,
so the output is a template: out/Quality_Dashboard_V6.pbit (data reloaded on opening).
"""
import argparse
import copy
import json
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_reaction_limits as A  # noqa: E402  (cloning helpers, checks, page-2 index)
import cpk_model as cm  # noqa: E402
import design as D  # noqa: E402
import pbit_package as pkg  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, N, P, S, SEL  # noqa: E402

bt = cm.bt
CPK = cm.CPK
HOME_TITLE = "Home"
TITLES = {"Overview": "overview", "Characteristics": "chars", "Reaction limits": "rl",
          "Reaction limit details": "rl_details"}
NEW_TITLES = {HOME_TITLE, D.PAGES["cpk"]["title"]}
BG_NAMES = dict(A.BG_NAMES, home="Home", cpk="Cpk")


# --------------------------------------------------------------------------- fields of any table
def field(entity, kind, name):
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": name}}


def projection(entity, kind, name, display=None, active=False):
    p = {"field": field(entity, kind, name), "queryRef": f"{entity}.{name}", "nativeQueryRef": display or name}
    if display:
        p["displayName"] = display
    if active:
        p["active"] = True
    return p


def query(v, roles, sort=None):
    q = v["visual"]["query"]
    q["queryState"] = {role: {"projections": p} for role, p in roles.items()}
    if sort:
        entity, kind, name, direction = sort
        q["sortDefinition"] = {"sort": [{"field": field(entity, kind, name), "direction": direction}]}
    else:
        q.pop("sortDefinition", None)


def top_n(entity, column, measure, n):
    """Visual filter: the n values of `column` with the highest `measure` (rows where it is blank drop out)."""
    col = {"Column": {"Expression": {"SourceRef": {"Source": "c"}}, "Property": column}}
    sub = {"Version": 2, "From": [{"Name": "c", "Entity": entity, "Type": 0}], "Select": [dict(col, Name="field")],
           "OrderBy": [{"Direction": 2, "Expression": {"Measure": {
               "Expression": {"SourceRef": {"Source": "c"}}, "Property": measure}}}], "Top": n}
    return {"name": "Filter" + A.new_name(), "field": field(entity, "Column", column), "type": "TopN",
            "filter": {"Version": 2,
                       "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": sub}}, "Type": 2},
                                {"Name": "c", "Entity": entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [col],
                                                       "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
            "howCreated": "User"}


def nav_button(like, key, target, label):
    v = A.clone(like, hidden=False)
    A.place(v, *(D.BADGE if key == "home" else D.NAV_TILES[key]))
    A.set_link(v, type="PageNavigation", navigationSection=target, tooltip=label)
    return v


def retarget_slicer(v, entity, name, display, sync=None):
    """Same slicer, on another field: no saved selection, and the sync group name kept (or removed)."""
    query(v, {"Values": [projection(entity, "Column", name, display, active=True)]})
    v["visual"]["objects"].pop("general", None)
    if sync:
        v["visual"]["syncGroup"] = {"groupName": sync, "fieldChanges": False, "filterChanges": True}
    else:
        v["visual"].pop("syncGroup", None)
    return v


# --------------------------------------------------------------------------- page 4: Cpk
def build_cpk_page(src, idx, p1, page_ids):
    cards = D.PAGES["cpk"]["cards"]
    out, panel_map = [], {}

    def add(v, src_name=None):
        out.append(v)
        if src_name:
            panel_map[src_name] = v["name"]
        return v

    for label, key in D.NAV:
        add(nav_button(src[idx["nav:overview"]], key, page_ids[key], label))
    add(nav_button(src[idx["nav:overview"]], "home", page_ids["home"], "Home"))
    add(A.clone(src[idx["clear"]]))
    add(A.clone(src[idx["refresh"]]))

    slots = D.slicer_slots("cpk")
    sources = {"Plant": "Plant", "Part": "Part", "Test": "Test", "Characteristic": "Characteristic", "Month": "Date"}
    for (fname, label, _), (x, w) in zip(D.PAGES["cpk"]["slicers"], slots):
        s = A.clone(src[idx["slicer:" + sources[fname]]], x=x, y=D.SLICER_Y, w=w, h=D.SLICER_H)
        display = {"Part": "Part (inspection plan)"}.get(fname, fname)
        add(retarget_slicer(s, CPK, fname, display, sync=None if fname == "Month" else fname))
    mx, mw = slots[-1]
    add(A.clone(src[idx["more_look"]], x=mx, w=mw))
    more_btn = add(A.clone(src[idx["more_btn"]], x=mx, w=mw))

    # Cpk pass %
    hero = next(v for v in p1.values() if v["visual"]["visualType"] == "cardVisual")
    kx, ky, kw, kh = cards["kpi"]
    kpi = add(A.clone(hero))
    A.place(kpi, kx, ky, kw, D.CPK_FIGURE_H)
    query(kpi, {"Data": [projection(CPK, "Measure", "Cpk Pass %", "Cpk pass %")]})
    kpi["visual"]["objects"]["value"][0]["properties"]["fontSize"] = N(24)
    kpi["visual"]["visualContainerObjects"] = R.vco_card("Cpk pass %", "Characteristics with Cpk ≥ threshold",
                                                         pad=(12, 2, 16, 16), header=False)
    # Cpk Pass & Fail donut, under the figure, in the same card
    donut = add(A.clone(next(v for v in p1.values() if v["visual"]["visualType"] == "donutChart")))
    A.place(donut, kx + 8, ky + D.CPK_FIGURE_H - 4, kw - 16, kh - D.CPK_FIGURE_H)
    query(donut, {"Category": [projection("Cpk Status", "Column", "Status", "Status", active=True)],
                  "Y": [projection(CPK, "Measure", "Cpk Status Count", "Characteristics")]})
    donut.pop("filterConfig", None)
    for e in donut["visual"]["objects"]["dataPoint"]:
        for d in e.get("selector", {}).get("data", []):
            d["scopeId"]["Comparison"]["Left"] = field("Cpk Status", "Column", "Status")
    donut["visual"]["visualContainerObjects"] = R.vco_plain({"general": [P(keepLayerOrder=B(True))]})
    # Pass & Fail % by part and by test
    for key, role in (("bars_part", "Part"), ("bars_test", "Test")):
        bars = add(A.clone(src[idx["barChart"]] if role == "Part" else next(
            v for v in src.values() if v["visual"]["visualType"] == "barChart"
            and R.fields_of(v)["Category"] == ["Test"])))
        A.place(bars, *cards[key])
        query(bars, {"Category": [projection(CPK, "Column", role, role, active=True)],
                     "Y": [projection(CPK, "Measure", "Cpk Fail Bar", "Fail"),
                           projection(CPK, "Measure", "Cpk Pass Bar", "Pass")],
                     "Tooltips": [projection(CPK, "Measure", "Cpk Characteristics", "Characteristics")]},
              sort=(CPK, "Measure", "Cpk Characteristics", "Descending"))
        for e in bars["visual"]["objects"]["dataPoint"]:
            m = e["selector"]["metadata"]
            e["selector"]["metadata"] = f"{CPK}.Cpk Fail Bar" if m.endswith("Fail Bar") else f"{CPK}.Cpk Pass Bar"
        bars["visual"]["objects"]["valueAxis"] = [P(show=B(False), showAxisTitle=B(False), gridlineShow=B(False))]
        bars["visual"]["visualContainerObjects"] = R.vco_card(
            f"{role} – Cpk Pass & Fail %", "Share of characteristics · total = characteristics with a Cpk")
    # Characteristics – Cpk detail
    table = add(A.clone(src[idx["tableEx"]]))
    A.place(table, *cards["table"])
    cols = [("Column", "Plant", "Plant", 60), ("Column", "Characteristic", "Characteristic", 300),
            ("Column", "Part", "Part", 200), ("Column", "Test", "Test", 170), ("Measure", "Cpk Value", "Cpk", 70),
            ("Measure", "Cpk Threshold", "Threshold", 80), ("Measure", "Cpk Measured Values", "Measured values", 140),
            ("Measure", "Cpk Status Label", "Status", 80)]
    query(table, {"Values": [projection(CPK, k, n, d) for k, n, d, _ in cols]},
          sort=(CPK, "Measure", "Cpk Value", "Ascending"))
    o = table["visual"]["objects"]
    o["values"] = [x for x in o["values"] if "selector" not in x] + [
        SEL({"fontColor": {"solid": {"color": {"expr": {"Measure": {
            "Expression": {"SourceRef": {"Entity": CPK}}, "Property": "Cpk Status Color"}}}}}},
            {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{CPK}.Cpk Status Label"})]
    o["columnFormatting"] = [
        SEL({"styleHeader": B(True), "styleValues": B(True), "fontColor": C(R.NAVY)}, {"metadata": f"{CPK}.Cpk Value"}),
        SEL({"styleHeader": B(True), "styleValues": B(True), "dataBars": {
            "positiveColor": C("#9DC3E6"), "negativeColor": C("#9DC3E6"), "axisColor": C(R.WHITE),
            "reverseDirection": B(False), "hideText": B(False)}}, {"metadata": f"{CPK}.Cpk Measured Values"})]
    o["columnWidth"] = [SEL({"value": N(w)}, {"metadata": f"{CPK}.{n}"}) for _, n, _, w in cols]
    # One row per characteristic would mean tens of thousands of Cpk to compute and sort before the first row
    # shows: the table lists the 100 lowest Cpk of the current filters (a part or a test narrows it down).
    table["visual"]["visualContainerObjects"] = R.vco_card(
        "Characteristics – Cpk detail",
        f"The {cm.DETAIL_ROWS} lowest Cpk of the current filters · select a part or a test to see its characteristics")
    table["filterConfig"] = {"filters": [top_n(CPK, "Group", "Cpk Detail Rank", cm.DETAIL_ROWS)]}

    # More filters: inspection reason, Cpk threshold, Cpk pass / fail
    for role in ("overlay_look", "overlay_btn", "panel_bg", "x_look", "x_btn"):
        add(A.clone(src[idx[role]]), idx[role])
    first, second = src[idx["panel_slicer:KPC"]], src[idx["panel_slicer:Press"]]
    step = second["position"]["y"] - first["position"]["y"]
    reason = A.clone(src[idx["slicer:Inspection Reason"]], hidden=True)
    A.place(reason, *(first["position"][k] for k in ("x", "y", "width", "height")))
    for key in ("header", "items", "dropdown"):
        reason["visual"]["objects"][key] = copy.deepcopy(first["visual"]["objects"][key])
    reason["visual"]["visualContainerObjects"] = copy.deepcopy(first["visual"]["visualContainerObjects"])
    add(retarget_slicer(reason, CPK, "Inspection Reason", "Inspection reason", sync="Inspection reason"),
        idx["panel_slicer:KPC"])
    # No single-select mode: Power BI could then pick the first value (1.00) on its own, while nothing chosen
    # must mean 1.33 (measure Cpk Threshold).
    threshold = retarget_slicer(A.clone(first, y=first["position"]["y"] + step), "Cpk Threshold", "Threshold",
                                "Cpk threshold (1.33 if none)")
    add(threshold, idx["panel_slicer:Press"])
    status = add(retarget_slicer(A.clone(first, y=first["position"]["y"] + 2 * step), "Cpk Status", "Status",
                                 "Cpk pass / fail"))
    for role in ("reset", "close_look", "close_btn"):
        add(A.clone(src[idx[role]], y=src[idx[role]]["position"]["y"] + step), idx[role])
    return out, panel_map, more_btn, status


# --------------------------------------------------------------------------- home page
def build_home_page(src, idx, page_ids):
    out = []
    for label, key in D.NAV:
        out.append(nav_button(src[idx["nav:overview"]], key, page_ids[key], label))
    out.append(A.clone(src[idx["clear"]]))
    for label, key in D.NAV:
        row = A.clone(src[idx["x_btn"]], hidden=False)
        A.place(row, *D.HOME_ROWS[key])
        A.set_link(row, type="PageNavigation", navigationSection=page_ids[key], tooltip=f"Open {label}")
        out.append(row)
    refresh = A.clone(src[idx["refresh"]])
    x, y, w, h = D.HOME_REFRESH
    A.place(refresh, x + 24, y, w - 28, h)
    out.append(refresh)
    vx, vw, vh = D.HOME_FACT_VALUE
    for key, measure in D.HOME_FACTS:
        if not measure:
            continue
        card = A.clone(src[idx["refresh"]])
        A.place(card, vx, D.HOME_FACT_Y[key], vw, vh)
        query(card, {"Values": [projection(bt.T, "Measure", measure, measure)]})
        card["visual"]["objects"] = {
            "labels": [P(color=C(R.WHITE), fontSize=N(11.5), fontFamily=S("Segoe UI Semibold"))],
            "categoryLabels": [P(show=B(False))]}
        out.append(card)
    return out


# --------------------------------------------------------------------------- main
def strip_new_pages(defs, meta):
    """Removes the home and Cpk pages (re-run on a report that has them), their bookmarks and buttons."""
    gone = [p for p in meta["pageOrder"] if defs[f"pages/{p}/page.json"]["displayName"] in NEW_TITLES]
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
        if A.R.link_of(defs[k]).get("navigationSection") in gone:
            del defs[k]
    return gone


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("pbix")
    ap.add_argument("settings", nargs="?", default=str(HERE.parent / "v2" / "databricks.local.json"))
    ap.add_argument("--range", nargs=2, metavar=("START", "END"), help="RangeStart RangeEnd, as YYYY-MM-DD")
    args = ap.parse_args()

    zin = zipfile.ZipFile(args.pbix)
    defs = pkg.definitions(zin)
    meta = defs["pages/pages.json"]
    had_pages = bool(strip_new_pages(defs, meta))
    page_keys = {}
    for pid in meta["pageOrder"]:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in TITLES:
            sys.exit(f"unexpected page '{title}'")
        page_keys[pid] = TITLES[title]
    page_ids = {k: p for p, k in page_keys.items()}
    page_ids["home"], page_ids["cpk"] = A.new_name(), A.new_name()
    page_keys.update({page_ids["home"]: "home", page_ids["cpk"]: "cpk"})

    def visuals_of(pid):
        return {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}

    src = visuals_of(page_ids["chars"])
    idx = A.index_page(src, page_keys)
    idx["barChart"] = next(n for n, v in src.items() if v["visual"]["visualType"] == "barChart"
                           and R.fields_of(v)["Category"] == ["Part"])
    missing = [r for r in A.REQUIRED if r not in idx]
    if missing:
        sys.exit(f"page Characteristics: could not find {missing}")

    # Cpk tile and Home button on the existing pages
    for key in ("overview", "chars", "rl", "rl_details"):
        pid = page_ids[key]
        own = visuals_of(pid)
        like = own[A.index_page(own, page_keys)["nav:chars"]]
        z = max(v["position"]["z"] for v in own.values())
        for i, (k, label) in enumerate((("cpk", "Cpk"), ("home", "Home"))):
            v = nav_button(like, k, page_ids[k], label)
            v["position"]["z"] = v["position"]["tabOrder"] = z + 1000 * (i + 1)
            defs[f"pages/{pid}/visuals/{v['name']}/visual.json"] = v

    p1 = visuals_of(page_ids["overview"])
    cpk_visuals, panel_map, more_btn, status_slicer = build_cpk_page(src, idx, p1, page_ids)
    home_visuals = build_home_page(src, idx, page_ids)

    # bookmarks of the Cpk "More filters" panel: those of page 2, plus the third filter
    by_link = {R.link_of(src[idx[r]]).get("bookmark"): r for r in ("more_btn", "close_btn")}
    names = {}
    for b in [v for k, v in list(defs.items()) if k.startswith("bookmarks/") and k.endswith(".bookmark.json")]:
        role = by_link.get(b["name"])
        if not role:
            continue
        nb = copy.deepcopy(b)
        nb["name"] = "Bookmark" + A.new_name()
        nb["displayName"] = "Cpk – More filters " + ("open" if role == "more_btn" else "closed")
        targets = nb["options"]["targetVisualNames"]
        if any(n not in panel_map for n in targets):
            sys.exit(f"bookmark {b['displayName']}: no Cpk copy for {[n for n in targets if n not in panel_map]}")
        es = nb["explorationState"]
        sec = es["sections"].pop(page_ids["chars"])
        containers = {panel_map[n]: c for n, c in sec["visualContainers"].items()}
        containers[status_slicer["name"]] = copy.deepcopy(sec["visualContainers"][idx["panel_slicer:Press"]])
        sec["visualContainers"] = containers
        nb["options"]["targetVisualNames"] = [panel_map[n] for n in targets] + [status_slicer["name"]]
        es["sections"] = {page_ids["cpk"]: sec}
        es["activeSection"] = page_ids["cpk"]
        defs[f"bookmarks/{nb['name']}.bookmark.json"] = nb
        defs["bookmarks/bookmarks.json"]["items"].append({"name": nb["name"]})
        names[role] = nb["name"]
    A.set_link(more_btn, type="Bookmark", bookmark=names["more_btn"])
    closers = {panel_map[idx[r]] for r in ("overlay_btn", "x_btn", "close_btn")}
    for v in cpk_visuals:
        if v["name"] in closers:
            A.set_link(v, type="Bookmark", bookmark=names["close_btn"])

    template = defs[f"pages/{page_ids['chars']}/page.json"]
    for key, vlist, title in (("home", home_visuals, HOME_TITLE), ("cpk", cpk_visuals, D.PAGES["cpk"]["title"])):
        pid = page_ids[key]
        page = copy.deepcopy(template)
        page["name"], page["displayName"] = pid, title
        page.pop("filterConfig", None)
        defs[f"pages/{pid}/page.json"] = page
        for i, v in enumerate(vlist):
            v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
            defs[f"pages/{pid}/visuals/{v['name']}/visual.json"] = v
    meta["pageOrder"] = [page_ids[k] for k in ("home", "overview", "chars", "rl", "cpk", "rl_details")]
    meta["activePageName"] = page_ids["home"]

    images = {}
    for key in ("home", "overview", "chars", "rl", "cpk", "rl_details"):
        item = f"QualityDashboard{BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_{key}.png").read_bytes()
        A.set_background(defs[f"pages/{page_ids[key]}/page.json"], D.PAGES[key]["title"], item)
    report = defs["report.json"]
    old = [i["name"] for p in report["resourcePackages"] if p["name"] == "RegisteredResources" for i in p["items"]]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]

    problems = A.checks(defs, meta["pageOrder"])
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    print(f"report checks: OK ({len(meta['pageOrder'])} pages, {sum(1 for k in defs if '/visuals/' in k)} visuals, "
          f"{len(defs['bookmarks/bookmarks.json']['items'])} bookmarks)")

    # A .pbix that already has these pages, and whose model has every field they use: rebuilt pages, same model and
    # data, so the output is a .pbix (no reload). Otherwise, a template with the model below.
    if had_pages:
        used, missing = pkg.report_fields(defs, A.model_fields(args.pbix))
        if not missing:
            dst = HERE / "out" / "Quality_Dashboard_V6.pbix"
            A.write_pbix(zin, defs, images, old, dst)
            print(f"report fields: OK ({len(used)} in the model of the .pbix)\n"
                  f"written {dst} ({dst.stat().st_size:,} bytes): home and Cpk pages rebuilt, model and data kept")
            return
        print(f"model of the .pbix lacks {len(missing)} fields: building a template instead")

    settings = json.loads(pathlib.Path(args.settings).read_text())
    if args.range:
        settings["range_start"], settings["range_end"] = args.range
    work = HERE / "out" / "v6"
    work.mkdir(parents=True, exist_ok=True)
    model_dir = bt.write_model(work, settings, extra_measures=cm.HOME_MEASURES, extra_tables=cm.extra_tables(),
                               policy=cm.QT_POLICY)
    model_json = bt.model_schema(model_dir, work / "DataModelSchema.json")
    pkg.check_fields(defs, model_json)

    dst = HERE / "out" / "Quality_Dashboard_V6.pbit"
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
