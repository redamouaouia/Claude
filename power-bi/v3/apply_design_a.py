"""Plant visual management dashboard: design A of the OPmobility templates ("Rail marine") on a .pbix.

Usage:  python apply_design_a.py <.pbix saved by Power BI Desktop> [<output .pbix>]

Render the backgrounds of design A first (README). Then, on every page:
- rail (150 px): the page buttons, Home (logo) and Clear filters move to the rail of design A; the last refresh goes
  to its bottom;
- header: the period filter (light style) next to the title; the filters in the grey boxes, under their name; More
  filters (or Back) with a navy outline;
- content: every visual is moved and resized to the content area of design A (same order, same proportions); the
  card backgrounds are drawn in the page background, so the card visuals lose their own white background;
- the "More filters" panel is not moved.
The home page is built again: the pages on the left, the key figures and the last refresh on the navy panel.
Model, data, measures, filters, bookmarks and every other setting of the visuals are kept: the output is a .pbix.
"""
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_home_and_cpk as H  # noqa: E402  (fields, queries)
import add_period_filter as PF  # noqa: E402  (page titles, button slicer states)
import add_reaction_limits as A  # noqa: E402  (cloning, checks, .pbix writer, model fields)
import design as D  # noqa: E402  (geometry of the current design)
import design_a as DA  # noqa: E402  (geometry of design A)
import pbit_package as pkg  # noqa: E402
import restyle as R  # noqa: E402
from restyle import B, C, N, P, S, SEL  # noqa: E402

OLD_RAIL, OLD_HEADER = D.RAIL_W, D.ROW2_Y - 6  # left of x = 96: rail; above y = 150: header
LIGHT_BLUE = "#E1EAF7"


def lit(x):
    return x.get("expr", {}).get("Literal", {}).get("Value") if isinstance(x, dict) else None


def is_panel(v):
    """Visuals of the "More filters" panel (hidden, at the right, or the full-page overlay): not moved."""
    p = v["position"]
    return bool(v.get("isHidden")) and ((p["x"] >= 980 and p["y"] < 300) or (p["width"] >= 900 and p["height"] >= 700))


def is_card_container(v):
    """Visuals that drew their own white card (white border, radius 16): design A draws the cards in the page."""
    b = v["visual"].get("visualContainerObjects", {}).get("border", [{}])[0].get("properties", {})
    return lit(b.get("radius")) == "16D" and lit(b.get("color", {}).get("solid", {}).get("color")) == "'#FFFFFF'"


def nearest(value, options):
    return min(range(len(options)), key=lambda i: abs(options[i] - value))


# --------------------------------------------------------------------------- styles of design A
def style_slicer(v):
    vco = v["visual"].setdefault("visualContainerObjects", {})
    vco["background"] = [P(show=B(False))]
    vco["border"] = [P(show=B(False))]
    o = v["visual"].setdefault("objects", {})
    for e in o.get("items", []):
        e["properties"]["background"] = C(DA.GREY)
        e["properties"]["fontColor"] = C(DA.TEXT)
    for e in o.get("dropdown", []):
        e["properties"]["borderColor"] = C(DA.GREY)


def style_outlined(v):
    """More filters / Back: white, navy outline."""
    vco = v["visual"].setdefault("visualContainerObjects", {})
    vco["background"] = [P(show=B(True), color=C(R.WHITE), transparency=N(0))]
    vco["border"] = [P(show=B(True), color=C(DA.NAVY), radius=N(8), width=N(1.5))]


def style_period(v):
    """Light segmented control: grey text; the chosen period in light blue with a navy outline."""
    o = v["visual"]["objects"]
    o["fillCustom"] = [SEL({"show": B(True), "fillColor": C(R.WHITE), "transparency": N(100)}, R.DEFAULT),
                       SEL({"fillColor": C(DA.NAVY), "transparency": N(92)}, PF.HOVER),
                       SEL({"fillColor": C(DA.NAVY), "transparency": N(85)}, PF.PRESS),
                       SEL({"fillColor": C(LIGHT_BLUE), "transparency": N(0)}, PF.SELECTED)]
    o["outline"] = [SEL({"show": B(False)}, R.DEFAULT),
                    SEL({"show": B(True), "lineColor": C(DA.NAVY), "weight": N(1.2), "transparency": N(0)}, PF.SELECTED)]
    o["value"] = [SEL({"show": B(True), "fontFamily": S("Segoe UI Semibold"), "fontSize": N(8.5), "fontColor": C(DA.MUTED),
                       "transparency": N(0), "horizontalAlignment": S("center"), "verticalAlignment": S("middle")},
                      R.DEFAULT),
                  SEL({"fontColor": C(DA.NAVY)}, PF.SELECTED)]


# --------------------------------------------------------------------------- pages
def redesign_page(defs, pid, key, page_keys):
    moved = {"rail": 0, "header": 0, "content": 0, "panel": 0}
    vis = {k: v for k, v in defs.items() if k.startswith(f"pages/{pid}/visuals/")}
    old_slots = D.slicer_slots(key) if D.PAGES[key]["slicers"] else []
    new_slots = DA.slicer_slots(key) if D.PAGES[key]["slicers"] else []
    for v in vis.values():
        p, vt = v["position"], v["visual"]["visualType"]
        if is_panel(v):
            moved["panel"] += 1
            continue
        if p["x"] < OLD_RAIL:  # rail: page buttons, Home, Clear filters
            link = R.link_of(v)
            target = page_keys.get(link.get("navigationSection"))
            if link.get("type") == "PageNavigation" and target in DA.NAV:
                A.place(v, *DA.NAV[target])
            elif link.get("type") == "PageNavigation" and target == "home":
                A.place(v, *DA.HOME_LINK)
            elif link.get("type") == "ClearAllSlicers":
                A.place(v, *DA.CLEAR)
            else:
                sys.exit(f"page {key}: rail visual not understood ({vt}, {link})")
            moved["rail"] += 1
        elif p["y"] < OLD_HEADER:  # header
            if vt == "card" and p["y"] < 40:  # last refresh
                A.place(v, *DA.REFRESH)
                v["visual"]["objects"]["wordWrap"] = [P(show=B(True))]
            elif vt == "advancedSlicerVisual":  # period filter
                x, y, w, h = DA.PERIOD
                A.place(v, x + 2, y + 2, w - 4, h - 4)
                style_period(v)
            elif vt == "slicer":
                i = nearest(p["x"], [x for x, _ in old_slots[:-1]])
                A.place(v, *DA.slicer_rect(*new_slots[i]))
                style_slicer(v)
            elif p["x"] >= D.BACK[0] - 2:  # More filters / Back (look and button)
                A.place(v, *((new_slots[-1][0], DA.FILTER_Y, new_slots[-1][1], DA.FILTER_H) if new_slots else DA.BACK))
                if vt == "textbox":
                    style_outlined(v)
            elif vt == "card" and key == "rl_details":  # the part chosen with "Details"
                x, y, w, h = DA.CONTEXT
                A.place(v, *DA.slicer_rect(x, w))
                for e in v["visual"]["objects"].get("labels", []):
                    e["properties"]["color"] = C(DA.NAVY)
            else:
                sys.exit(f"page {key}: header visual not understood ({vt} at {p['x']}, {p['y']})")
            moved["header"] += 1
        else:  # content
            A.place(v, *DA.map_rect(p["x"], p["y"], p["width"], p["height"]))
            if is_card_container(v):
                vco = v["visual"]["visualContainerObjects"]
                vco["background"] = [P(show=B(False))]
                vco["border"] = [P(show=B(False))]
            moved["content"] += 1
    return moved


def build_home(src, idx, keys):
    """Home page of design A: one button per page row, the last refresh and the live figures on the navy panel."""
    out = []
    for label, key in D.NAV:
        row = A.clone(src[idx["x_btn"]], hidden=False)
        A.place(row, *DA.HOME_TILES[key])
        A.set_link(row, type="PageNavigation", navigationSection=keys[key], tooltip=f"Open {label}")
        out.append(row)
    refresh = A.clone(src[idx["refresh"]])
    x, y, w, h = DA.HOME_REFRESH
    A.place(refresh, x + 26, y, w - 30, h)
    out.append(refresh)
    for key, measure in D.HOME_FACTS:
        if not measure:
            continue
        card = A.clone(src[idx["refresh"]])
        # 40 px high, centred on the 32 px row of the background: room for the 16 pt figure of the plain card.
        A.place(card, DA.HOME_FACT_X, DA.HOME_FACT_Y[key] - 4, DA.HOME_FACT_W, 40)
        H.query(card, {"Values": [H.projection(H.bt.T, "Measure", measure, measure)]})
        card["visual"]["objects"] = {
            "labels": [P(color=C(R.WHITE), fontSize=N(16), fontFamily=S("Segoe UI Semibold"))],
            "categoryLabels": [P(show=B(False))]}
        out.append(card)
    return out


def set_backgrounds(defs, keys):
    images = {}
    for key, pid in keys.items():
        item = f"PlantVM{PF.BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_a_{key}.png").read_bytes()
        A.set_background(defs[f"pages/{pid}/page.json"], D.PAGES[key]["title"], item)
        defs[f"pages/{pid}/page.json"]["objects"]["outspace"] = [P(color=C(R.WHITE), transparency=N(0))]
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
    src = {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{keys['chars']}/visuals/")}
    idx = A.index_page(src, page_keys)  # before the move: roles are found from the current geometry
    for role in ("x_btn", "refresh"):
        if role not in idx:
            sys.exit(f"page Characteristics: no {role}")
    templates = {r: A.clone(src[idx[r]]) for r in ("x_btn", "refresh")}
    for r, v in templates.items():
        v["name"] = src[idx[r]]["name"]
    tidx = {r: r for r in templates}

    for key, pid in keys.items():
        if key == "home":
            continue
        print(f"{key:11s}", redesign_page(defs, pid, key, page_keys))
    home = keys["home"]
    for k in [k for k in defs if k.startswith(f"pages/{home}/visuals/")]:
        del defs[k]
    for i, v in enumerate(build_home(templates, tidx, keys)):
        v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
        defs[f"pages/{home}/visuals/{v['name']}/visual.json"] = v
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
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / "Plant visual management dashboard A.pbix"))
