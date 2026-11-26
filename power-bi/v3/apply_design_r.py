"""Plant visual management dashboard: design "Relief" (premium concept 2) on the .pbix of design A (V14).

Usage:  python apply_design_r.py <.pbix in design A, saved by Power BI Desktop> [<output .pbix>]

Render the Relief backgrounds first (README). Then, on every page:
- rail: page buttons, Home, Clear filters and the last refresh move onto the floating rail of design_r.py;
- header: the period filter into its inset track (chosen period: raised white tile), the filters into their inset wells,
  More filters and Back as raised buttons drawn in the background (their textbox looks are hidden), "‹ Overview" of
  Failure breakdown before the title;
- content: every visual moves from the content area of design A to the one of Relief (same order and proportions);
  the Part / Test switch of Overview becomes a segmented control (raised white choice);
- the More filters panel is not moved.
The home page visuals move onto the Relief home (page tiles, key-figure chips, last refresh). Model, data, measures,
filters, bookmarks and every other setting are kept: the output is a .pbix.
"""
import json
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_period_filter as PF  # noqa: E402  (page titles, button slicer states)
import add_reaction_limits as A  # noqa: E402  (placing, checks, .pbix writer, model fields)
import apply_design_a as AD  # noqa: E402  (panel visuals, literals)
import design as D  # noqa: E402
import design_a as DA  # noqa: E402  (geometry of design A: where the visuals are now)
import design_r as DR  # noqa: E402  (geometry of Relief)
import pbit_package as pkg  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, I, N, P, S, SEL  # noqa: E402

OUT_NAME = "Plant visual management dashboard Relief"
SELECTED_TOGGLE = "#0B2A5B"  # fill of the chosen side of the Part / Test switch in design A


# --------------------------------------------------------------------------- styles of Relief
def style_slicer(v):
    vco = v["visual"].setdefault("visualContainerObjects", {})
    vco["background"] = [P(show=B(False))]
    vco["border"] = [P(show=B(False))]
    o = v["visual"].setdefault("objects", {})
    for e in o.get("items", []):
        e["properties"]["background"] = C(DR.WELL)
        e["properties"]["fontColor"] = C(DR.TEXT)
    for e in o.get("dropdown", []):
        e["properties"]["borderColor"] = C(DR.WELL)


def style_period(v):
    """Segmented control in its inset track: the chosen period as a raised white tile, navy text."""
    o = v["visual"]["objects"]
    o["fillCustom"] = [SEL({"show": B(True), "fillColor": C(R.WHITE), "transparency": N(100)}, R.DEFAULT),
                       SEL({"fillColor": C(DR.NAVY), "transparency": N(92)}, PF.HOVER),
                       SEL({"fillColor": C(DR.NAVY), "transparency": N(86)}, PF.PRESS),
                       SEL({"fillColor": C(R.WHITE), "transparency": N(0)}, PF.SELECTED)]
    o["outline"] = [SEL({"show": B(False)}, R.DEFAULT),
                    SEL({"show": B(True), "lineColor": C("#D3DCE8"), "weight": N(1), "transparency": N(0)}, PF.SELECTED)]
    o["value"] = [SEL({"show": B(True), "fontFamily": S("Segoe UI Semibold"), "fontSize": N(8.5), "fontColor": C(DR.MUTED),
                       "transparency": N(0), "horizontalAlignment": S("center"), "verticalAlignment": S("middle")},
                      R.DEFAULT),
                  SEL({"fontColor": C(DR.NAVY)}, PF.SELECTED)]
    o["shapeCustomRectangle"] = [SEL({"tileShape": S("rectangleRoundedByPixel"), "rectangleRoundedCurve": I(11)},
                                     R.DEFAULT)]


def toggle_side(v):
    """'on' / 'off' for the textboxes of the Part / Test switch of Overview, else None."""
    if v["visual"]["visualType"] != "textbox":
        return None
    runs = [r for p in v["visual"]["objects"].get("general", [{}])[0].get("properties", {}).get("paragraphs", [])
            for r in p.get("textRuns", [])]
    if [r.get("value") for r in runs] not in (["Part"], ["Test"]):
        return None
    bg = AD.lit(v["visual"].get("visualContainerObjects", {}).get("background", [{}])[0].get("properties", {})
                .get("color", {}).get("solid", {}).get("color"))
    return "on" if (bg or "").strip("'").upper() == SELECTED_TOGGLE else "off"


def style_toggle(v, side):
    vco = v["visual"]["visualContainerObjects"]
    runs = [r for p in v["visual"]["objects"]["general"][0]["properties"]["paragraphs"] for r in p["textRuns"]]
    if side == "on":  # raised white choice
        vco["background"] = [P(show=B(True), color=C(R.WHITE), transparency=N(0))]
        vco["border"] = [P(show=B(True), color=C(R.WHITE), radius=N(9), width=N(1))]
        vco["dropShadow"] = [P(show=B(True), color=C("#102850"), transparency=N(80), position=S("Outer"),
                               preset=S("Custom"), angle=N(90), shadowDistance=N(1), shadowBlur=N(5), shadowSpread=N(0))]
        for r in runs:
            r["textStyle"].update(color=DR.NAVY, fontFamily="Segoe UI Semibold")
            r["textStyle"].pop("fontWeight", None)
    else:  # the track shows through
        vco["background"] = [P(show=B(False))]
        vco["border"] = [P(show=B(False))]
        vco["dropShadow"] = [P(show=B(False))]
        for r in runs:
            r["textStyle"].update(color=DR.MUTED, fontFamily="Segoe UI")
            r["textStyle"].pop("fontWeight", None)


def hover(v, color, transparency):
    o = v["visual"]["objects"]
    o["fill"] = [e for e in o.get("fill", []) if e.get("selector") != {"id": "hover"}] + [
        SEL({"show": B(True), "fillColor": C(color), "transparency": N(transparency)}, {"id": "hover"})]


# --------------------------------------------------------------------------- pages
def redesign_page(defs, pid, key, page_keys):
    moved = {"rail": 0, "header": 0, "content": 0, "panel": 0, "hidden looks": 0, "switch": 0}
    vis = {k: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
    old_slots = DA.slicer_slots(key) if D.PAGES[key]["slicers"] else []
    new_slots = DR.slicer_slots(key) if D.PAGES[key]["slicers"] else []
    for v in vis.values():
        p, vt, link = v["position"], v["visual"]["visualType"], R.link_of(v)
        if AD.is_panel(v):
            moved["panel"] += 1
            continue
        if p["x"] < DA.RAIL:  # rail: page buttons, Home, Clear filters, last refresh
            target = page_keys.get(link.get("navigationSection"))
            if link.get("type") == "PageNavigation" and target in DR.NAV:
                A.place(v, *DR.NAV[target])
            elif link.get("type") == "PageNavigation" and target == "home":
                A.place(v, *DR.HOME_LINK)
            elif link.get("type") == "ClearAllSlicers":
                A.place(v, *DR.CLEAR)
            elif vt == "card":
                A.place(v, *DR.REFRESH)
            else:
                sys.exit(f"page {key}: rail visual not understood ({vt}, {link})")
            moved["rail"] += 1
        elif p["y"] < DA.CONTENT_Y0 - 2:  # header
            if vt == "advancedSlicerVisual":  # period filter
                x, y, w, h = DR.PERIOD
                A.place(v, x + 3, y + 3, w - 6, h - 6)
                style_period(v)
            elif vt == "slicer":
                i = AD.nearest(p["x"], [x for x, _ in old_slots[:-1]])
                A.place(v, *DR.slicer_rect(*new_slots[i]))
                style_slicer(v)
            elif link.get("type") == "PageNavigation":  # ‹ Overview, before the title of Failure breakdown
                A.place(v, *DR.BACK_LINK)
                hover(v, DR.NAVY, 94)
            elif p["x"] >= DA.X1 - DA.MORE_W - 2:  # More filters / Back: drawn raised in the background
                if vt == "textbox":
                    v["isHidden"] = True
                    moved["hidden looks"] += 1
                else:
                    A.place(v, *((new_slots[-1][0], DR.FILTER_Y, new_slots[-1][1], DR.FILTER_H) if new_slots
                                 else DR.BACK))
                    hover(v, DR.NAVY, 94)
            elif vt == "card" and key == "rl_details":  # the part chosen with "Details", in its well
                x, y, w, h = DR.CONTEXT
                A.place(v, *DR.slicer_rect(x, w))
            else:
                sys.exit(f"page {key}: header visual not understood ({vt} at {p['x']}, {p['y']})")
            moved["header"] += 1
        else:  # content
            A.place(v, *DR.map_rect(p["x"], p["y"], p["width"], p["height"]))
            side = toggle_side(v) if key == "overview" else None
            if side:
                style_toggle(v, side)
                moved["switch"] += 1
            if key == "overview" and link.get("type") == "PageNavigation":  # tile of the failure breakdown (navy)
                hover(v, R.WHITE, 90)
            moved["content"] += 1
    return moved


def _measure(v):
    q = v["visual"].get("query", {}).get("queryState", {}).get("Data", {}).get("projections", [])
    return q[0]["field"].get("Measure", {}).get("Property") if q else None


def arrange_overview(defs, pid, page_keys):
    """V17: the four key figures in the first row; the cumulative pass % and the failure tile below on the left, the
    gauge (titled, with the period) and the results table (with its Part / Test switch) on the right."""
    vis = [v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/") and not AD.is_panel(v)]
    cards = {_measure(v): v for v in vis if v["visual"]["visualType"] == "cardVisual"}
    for key, measure in (("pass", "Inspection Pass %"), ("failed", "Inspections Fail"), ("rate", "Inspection Fail %"),
                         ("gap", "Pass % Gap")):
        if measure not in cards:
            sys.exit(f"Overview: no card of [{measure}]")
        A.place(cards[measure], *DR.kpi_value_rect(key))
    hero = cards["Inspection Pass %"]  # Pass rate, as the three other figures: value, and its line under it
    hero["visual"]["objects"]["label"] = [SEL({"show": B(True), "position": S("belowValue"), "fontColor": C(R.MUTED2),
                                               "fontSize": N(9.5), "fontFamily": S("Segoe UI"),
                                               "horizontalAlignment": S("left")}, R.DEFAULT)]
    proj = hero["visual"]["query"]["queryState"]["Data"]["projections"][0]
    proj["displayName"] = proj["nativeQueryRef"] = "Share of inspections passed"
    hero["visual"]["visualContainerObjects"] = R.vco_plain()
    one = {t: [v for v in vis if v["visual"]["visualType"] == t] for t in ("gauge", "lineChart")}
    for t, rect in (("gauge", DR.OV_GAUGE), ("lineChart", DR.OV_LINE)):
        if len(one[t]) != 1:
            sys.exit(f"Overview: {len(one[t])} {t} (one expected)")
        A.place(one[t][0], *rect)
    gauge = one["gauge"][0]
    vco = R.vco_card("Pass rate vs 95 % target", " ", bg=False, pad=(12, 4, 16, 16), header=False)
    A.dynamic_subtitle(vco, "Period Label")
    gauge["visual"]["visualContainerObjects"] = vco
    for v in vis:
        link = R.link_of(v)
        if v["visual"]["visualType"] == "tableEx":
            A.place(v, *DR.OV_TABLE)
        elif link.get("type") == "PageNavigation" and page_keys.get(link.get("navigationSection")) == "fails":
            A.place(v, *DR.OV_TILE)
    # Part / Test switch: its textboxes and their bookmark buttons, left (Part) and right (Test)
    boxes = [v["position"] for v in vis if toggle_side(v)]
    switch = [v for v in vis if v["visual"]["visualType"] in ("textbox", "actionButton") and any(
        abs(v["position"]["x"] - q["x"]) < 1 and abs(v["position"]["y"] - q["y"]) < 1 for q in boxes)]
    if len(switch) != 8:
        sys.exit(f"Overview: {len(switch)} visuals for the Part / Test switch (8 expected)")
    middle = sum(v["position"]["x"] for v in switch) / len(switch)
    left, right = DR.toggle_rects()
    for v in switch:
        A.place(v, *(left if v["position"]["x"] < middle else right))


def place_filter_row(defs, pid, key):
    """V17: slicers, More filters / Back and the details card into the taller wells of the filter row."""
    slots = DR.slicer_slots(key) if D.PAGES[key]["slicers"] else []
    n = 0
    for v in [v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")]:
        p, vt = v["position"], v["visual"]["visualType"]
        if v.get("isHidden") or p["x"] < DR.X0 - 4 or not 70 <= p["y"] < 140:
            continue
        if vt == "slicer":
            i = AD.nearest(p["x"], [x for x, _ in slots[:-1]])
            A.place(v, *DR.slicer_rect(*slots[i]))
        elif vt == "actionButton" and p["x"] >= DR.X1 - DR.MORE_W - 2:
            A.place(v, *((slots[-1][0], DR.FILTER_Y, slots[-1][1], DR.FILTER_H) if slots else DR.BACK))
        elif vt == "card" and key == "rl_details":
            x, y, w, h = DR.CONTEXT
            A.place(v, *DR.slicer_rect(x, w))
        else:
            continue
        n += 1
    return n


def redesign_home(defs, pid, page_keys):
    """Home visuals onto the Relief home: page tiles, key-figure chips, last refresh."""
    n = 0
    for v in [v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")]:
        vt, link = v["visual"]["visualType"], R.link_of(v)
        fields = json.dumps(v["visual"].get("query", {}))
        if vt == "actionButton" and link.get("type") == "PageNavigation":
            A.place(v, *DR.HOME_TILES[page_keys[link["navigationSection"]]])
        elif vt == "card" and '"Last Refresh"' in fields:
            x, y, w, h = DR.HOME_REFRESH
            A.place(v, x + 28, y, w - 36, h)
        elif vt == "card" and ('"Plants"' in fields or '"Home Measured Values"' in fields):
            x, y, w, h = DR.CHIPS["plants" if '"Plants"' in fields else "values"]
            A.place(v, x + 10, y + 5, w - 20, 36)
        else:
            sys.exit(f"home page: visual not understood ({vt})")
        n += 1
    return n


def set_backgrounds(defs, keys):
    images = {}
    for key, pid in keys.items():
        item = f"PlantVMRelief{PF.BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_r_{key}.png").read_bytes()
        A.set_background(defs[f"pages/{pid}/page.json"], D.PAGES[key]["title"], item)
        defs[f"pages/{pid}/page.json"]["objects"]["outspace"] = [P(color=C(DR.CANVAS), transparency=N(0))]
    report = defs["report.json"]
    old = [i["name"] for p in report["resourcePackages"] if p["name"] == "RegisteredResources" for i in p["items"]]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]
    return images, old


def main(src_path, dst):
    zin = zipfile.ZipFile(src_path)
    defs = pkg.definitions(zin)
    order = defs["pages/pages.json"]["pageOrder"]
    keys = {}
    for pid in order:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in PF.TITLES:
            sys.exit(f"unexpected page '{title}'")
        keys[PF.TITLES[title]] = pid
    page_keys = {pid: k for k, pid in keys.items()}
    background = json.dumps(defs[f"pages/{keys['overview']}/page.json"].get("objects", {}))
    if "PlantVMRelief" in background:
        sys.exit("this report already has the Relief design")
    if "PlantVM" not in background:
        sys.exit("this report is not in design A (run apply_design_a.py first)")

    for key, pid in keys.items():
        if key != "home":
            print(f"{key:11s}", redesign_page(defs, pid, key, page_keys))
    arrange_overview(defs, keys["overview"], page_keys)
    print(f"{'home':11s} {redesign_home(defs, keys['home'], page_keys)} visuals moved")
    images, old = set_backgrounds(defs, keys)

    problems = A.checks(defs, order)
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    used, missing = pkg.report_fields(defs, A.model_fields(src_path))
    if missing:
        sys.exit("fields missing from the model: " + ", ".join(sorted({f"{e}[{p}]" for e, p, _ in missing})))
    A.write_pbix(zin, defs, images, old, dst)
    print(f"report checks and fields OK ({len(used)}); written {dst} ({pathlib.Path(dst).stat().st_size:,} bytes)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / f"{OUT_NAME}.pbix"))
