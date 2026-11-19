"""Quality Dashboard V3: apply the refined design to a .pbix saved by Power BI Desktop in PBIR format.

Usage:  python restyle.py <V2 .pbix saved by Power BI Desktop> [<output .pbix>]

Keeps the data model, measures, filters and bookmarks of the input file. Rewrites the report pages:
page backgrounds (rendered artwork), positions and formatting of every visual, one new KPI card.
Every formatting object/property written is checked against Microsoft's visual capabilities catalog
(@microsoft/powerbi-core-visual-schema) before the file is packaged.
"""
import copy
import json
import os
import pathlib
import secrets
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import design as D  # noqa: E402

T = "Quality Tracker"
NAVY, NAVY_DEEP, WHITE = "#0B2A5B", "#061A3C", "#FFFFFF"
BLUE, ORANGE = "#2F6EBA", "#ED7D31"
TEXT, MUTED, MUTED2, LINE = "#1B2A41", "#5A6B85", "#7A889C", "#E8EDF4"
NUM_FONT = "Segoe UI Semibold"


# --------------------------------------------------------------------------- PBIR literal helpers
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def S(t):
    return lit("'" + str(t).replace("'", "''") + "'")


def N(n):
    return lit(f"{n}D")


def I(n):
    return lit(f"{int(n)}L")


def B(x):
    return lit("true" if x else "false")


def C(h):
    return {"solid": {"color": S(h)}}


def P(**kw):
    return {"properties": kw}


def SEL(props, selector):
    return {"properties": props, "selector": selector}


DEFAULT = {"id": "default"}


def measure_expr(name):
    return {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": T}}, "Property": name}}}


def field(kind, name):
    return {kind: {"Expression": {"SourceRef": {"Entity": T}}, "Property": name}}


def projection(kind, name, display=None, active=False):
    p = {"field": field(kind, name), "queryRef": f"{T}.{name}", "nativeQueryRef": display or name}
    if display:
        p["displayName"] = display
    if active:
        p["active"] = True
    return p


# --------------------------------------------------------------------------- container formatting
def vco_card(title=None, subtitle=None, bg=True, pad=(12, 10, 16, 16), header=True):
    v = {
        "background": [P(show=B(bg), color=C(WHITE), transparency=N(0))],
        "border": [P(show=B(bg), color=C(WHITE), radius=N(16), width=N(1))],
        "dropShadow": [P(show=B(False))],
        "padding": [P(top=N(pad[0]), bottom=N(pad[1]), left=N(pad[2]), right=N(pad[3]))],
        "visualHeader": [P(show=B(header), foreground=C(MUTED), background=C(WHITE), border=C(WHITE),
                           transparency=N(0))],
        "general": [P(keepLayerOrder=B(True))],
    }
    if title:
        v["title"] = [P(show=B(True), text=S(title), fontColor=C(NAVY), fontSize=N(12),
                        fontFamily=S("Segoe UI Semibold"), alignment=S("left"))]
        v["subTitle"] = [P(show=B(bool(subtitle)), text=S(subtitle or ""), fontColor=C(MUTED2), fontSize=N(9),
                           fontFamily=S("Segoe UI"), alignment=S("left"))]
        v["divider"] = [P(show=B(False))]
    else:
        v["title"] = [P(show=B(False))]
    return v


def vco_plain(extra=None):
    v = {
        "background": [P(show=B(False))],
        "border": [P(show=B(False))],
        "dropShadow": [P(show=B(False))],
        "title": [P(show=B(False))],
        "visualHeader": [P(show=B(False))],
        "padding": [P(top=N(0), bottom=N(0), left=N(0), right=N(0))],
    }
    if extra:
        v.update(extra)
    return v


def button_objects(text=None, fill=None, fill_transp=0, text_color=NAVY, size=10, bold=False, outline=None,
                   outline_transp=0, shape="rectangleRounded", radius=8, hover=None, align="center", hmargin=6):
    o = {
        "icon": [SEL({"shapeType": S("blank")}, DEFAULT)],
        "text": [SEL({"show": B(bool(text)), "text": S(text or ""), "fontColor": C(text_color), "fontSize": N(size),
                      "fontFamily": S("Segoe UI Semibold" if bold else "Segoe UI"), "horizontalAlignment": S(align),
                      "verticalAlignment": S("middle"), "topMargin": I(0), "bottomMargin": I(0),
                      "leftMargin": I(hmargin), "rightMargin": I(hmargin)}, DEFAULT)],
        "fill": [SEL({"show": B(fill is not None), "fillColor": C(fill or WHITE), "transparency": N(fill_transp)},
                     DEFAULT)],
        # Power BI Desktop does not draw a button (fill, text) whose border is switched off with a 0 width,
        # as seen on screen: "Reset" (border on) showed, "Close" (border off) did not. Visible buttons therefore
        # always keep a 1 px border, in the fill colour when no border is wanted.
        "outline": [SEL({"show": B(True), "lineColor": C(outline or fill or WHITE),
                         "transparency": N(outline_transp if outline else (fill_transp if fill else 100)),
                         "weight": N(1)}, DEFAULT)],
        "shape": [SEL({"tileShape": S(shape), "roundEdge": I(radius)}, DEFAULT)],
    }
    if hover:
        o["fill"].append(SEL({"show": B(True), "fillColor": C(hover[0]), "transparency": N(hover[1])},
                             {"id": "hover"}))
    return o


# --------------------------------------------------------------------------- buttons = look + click area
# In this Power BI Desktop version, action buttons written from file only drew their border: fill and label
# did not show (except one button). Text boxes with a rounded background render reliably, and invisible
# buttons stay clickable. So every visible button is now a styled text box ("look") under a transparent
# button that carries the action; bookmarks show and hide both together.
LOOKS = {}  # button name -> look of its twin text box (filled per page)


def hotspot(vis):
    link = vis["visualContainerObjects"].get("visualLink")
    vis["objects"] = button_objects()
    vis["visualContainerObjects"] = vco_plain({"visualLink": link} if link else None)


def look(name, text, bg, fg, size=10, bold=True, radius=16, pad_top=6, bg_transp=0, border=True):
    LOOKS[name] = dict(text=text, bg=bg, fg=fg, size=size, bold=bold, radius=radius, pad_top=pad_top,
                       bg_transp=bg_transp, border=border)


def twin_textbox(btn, lk):
    pos = dict(btn["position"])
    pos["z"] = pos["z"] - 1
    pos["tabOrder"] = pos["z"]
    style = {"fontFamily": "Segoe UI Semibold" if lk["bold"] else "Segoe UI", "fontSize": f"{lk['size']}pt",
             "color": lk["fg"]}
    if lk["bold"]:
        style["fontWeight"] = "bold"
    t = {
        "$schema": btn["$schema"],
        "name": secrets.token_hex(10),
        "position": pos,
        "visual": {
            "visualType": "textbox",
            "objects": {"general": [P(paragraphs=[{"textRuns": [{"value": lk["text"], "textStyle": style}],
                                                   "horizontalTextAlignment": "center"}])]},
            "visualContainerObjects": {
                "background": [P(show=B(True), color=C(lk["bg"]), transparency=N(lk["bg_transp"]))],
                "border": [P(show=B(lk["border"]), color=C(lk["bg"]), radius=N(lk["radius"]), width=N(1))],
                "dropShadow": [P(show=B(False))],
                "title": [P(show=B(False))],
                "visualHeader": [P(show=B(False))],
                "padding": [P(top=N(lk["pad_top"]), bottom=N(0), left=N(2), right=N(2))],
            },
            "drillFilterOtherVisuals": True,
        },
    }
    if btn.get("isHidden"):
        t["isHidden"] = True
    return t


# --------------------------------------------------------------------------- reading the input report
def text_of(v):
    try:
        return v["visual"]["objects"]["text"][0]["properties"]["text"]["expr"]["Literal"]["Value"].strip("'")
    except (KeyError, IndexError):
        return None


def link_of(v):
    try:
        p = v["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
        return {k: x["expr"]["Literal"]["Value"].strip("'") for k, x in p.items()}
    except (KeyError, IndexError):
        return {}


def fields_of(v):
    out = {}
    for role, d in v["visual"].get("query", {}).get("queryState", {}).items():
        out[role] = [next(iter(p["field"].values()))["Property"] for p in d.get("projections", [])]
    return out


def fill_of(v):
    try:
        return v["visual"]["objects"]["fill"][0]["properties"]["fillColor"]["solid"]["color"]["expr"]["Literal"][
            "Value"].strip("'")
    except (KeyError, IndexError):
        return None


def classify(v, page_names):
    vt = v["visual"]["visualType"]
    pos = v["position"]
    hidden = v.get("isHidden", False)
    f = fields_of(v)
    if vt == "textbox":
        if hidden:
            return "panel_bg"
        if pos["x"] == 0 and pos["y"] == 0:
            return "nav_bg"
        if pos["y"] > 600:
            return "info"
        if pos["x"] > 150:
            return "page_title"
        return "logo" if pos["y"] < 50 else "nav_titles"
    if vt == "actionButton":
        link, txt = link_of(v), text_of(v)
        if link.get("type") == "PageNavigation":
            return "nav:" + page_names[link["navigationSection"]]
        if link.get("type") == "ClearAllSlicers":
            return "panel_reset" if hidden else "clear"
        if txt and txt.startswith("More filters"):
            return "more"
        if txt == "✕":
            return "panel_x"
        if txt == "Close":
            return "panel_close"
        if txt in ("Part", "Test"):
            return f"toggle:{txt}:{'on' if fill_of(v) == NAVY else 'off'}"
        if pos["width"] >= 900:
            return "overlay"
        return "button?"
    if vt == "slicer":
        return ("panel_slicer:" if hidden else "slicer:") + f["Values"][0]
    if vt == "card":
        return "refresh"
    if vt == "tableEx":
        return "table:" + f["Values"][0]
    if vt == "cardVisual":
        return "kpi:" + f["Data"][0]
    if vt == "barChart":
        return "bars:" + f["Category"][0]
    return vt


# --------------------------------------------------------------------------- the redesign
def restyle_page(page_key, visuals, new_visuals, removed):
    spec = D.PAGES[page_key]
    cards = spec["cards"]
    slots = D.slicer_slots(page_key)
    slicer_x = {name: s for (name, _, _), s in zip(spec["slicers"], slots)}
    more_x, more_w = slots[-1]

    def place(v, x, y, w, h):
        v["position"].update({"x": x, "y": y, "width": w, "height": h})

    for name, v in list(visuals.items()):
        slot = v["_slot"]
        vis = v["visual"]
        if slot in ("nav_bg", "logo", "nav_titles", "info", "page_title"):
            removed.append(name)
            continue

        if slot.startswith("nav:"):
            key = slot.split(":")[1]
            place(v, *D.NAV_TILES[key])
            vis["objects"] = button_objects(hover=(WHITE, 90), radius=14)
            link = vis["visualContainerObjects"].get("visualLink")
            vis["visualContainerObjects"] = vco_plain({"visualLink": link})
            vis["visualContainerObjects"]["visualLink"][0]["properties"]["tooltip"] = S(
                dict((k, lbl) for lbl, k in D.NAV)[key])
        elif slot == "clear":
            place(v, *D.CLEAR_TILE)
            vis["objects"] = button_objects(hover=(WHITE, 90), radius=14)
            link = vis["visualContainerObjects"].get("visualLink")
            vis["visualContainerObjects"] = vco_plain({"visualLink": link})
            vis["visualContainerObjects"]["visualLink"][0]["properties"]["tooltip"] = S("Clear all filters")
        elif slot == "refresh":
            rx, ry, rw, rh = D.REFRESH_PILL
            place(v, rx + 24, ry, rw - 28, rh)
            vis["objects"] = {"labels": [P(color=C("#E6EDF7"), fontSize=N(8.5), fontFamily=S("Segoe UI"))],
                              "categoryLabels": [P(show=B(False))]}
            vis["visualContainerObjects"] = vco_plain()
        elif slot.startswith("slicer:"):
            fname = slot.split(":", 1)[1]
            x, w = slicer_x[fname]
            place(v, x, D.SLICER_Y, w, D.SLICER_H)
            o = vis["objects"]
            o["header"] = [P(show=B(False))]
            o["items"] = [P(fontColor=C(NAVY), textSize=N(10), fontFamily=S("Segoe UI"), background=C(WHITE))]
            o["dropdown"] = [P(borderColor=C(WHITE), borderRadius=I(8), iconColor=C(NAVY))]
            if fname == "Date":
                o["date"] = [P(fontColor=C(NAVY), textSize=N(10), fontFamily=S("Segoe UI"), background=C(WHITE))]
                o["calendarButton"] = [P(iconColor=C(BLUE))]
            vis["visualContainerObjects"] = {
                "background": [P(show=B(True), color=C(WHITE), transparency=N(0))],
                "border": [P(show=B(True), color=C(WHITE), radius=N(8), width=N(1))],
                "dropShadow": [P(show=B(False))],
                "title": [P(show=B(False))],
                "visualHeader": [P(show=B(False))],
                "padding": [P(top=N(0), bottom=N(0), left=N(4), right=N(4))],
                "general": [P(keepLayerOrder=B(True))],
            }
        elif slot == "more":
            place(v, more_x, D.SLICER_Y, more_w, D.SLICER_H)
            hotspot(vis)
            look(name, f"More filters · {spec['more_count']}", WHITE, NAVY, size=9, radius=18, pad_top=8)

        # ---- page 1
        elif slot == "gauge":
            x, y, w, h = cards["hero"]
            place(v, x + 14, y + 128, w - 28, h - 134)
            vis["objects"] = {
                "axis": [P(min=N(0), max=N(1))],
                "dataPoint": [P(fill=C(BLUE), target=C(NAVY))],
                "calloutValue": [P(show=B(False))],
                "labels": [P(show=B(True), color=C(MUTED2), fontSize=N(8), fontFamily=S("Segoe UI"))],
                "target": [P(show=B(True), color=C(NAVY), fontSize=N(8), fontFamily=S("Segoe UI Semibold"))],
            }
            vis["visualContainerObjects"] = vco_plain({"general": [P(keepLayerOrder=B(True))]})
            hero = new_cardvisual(v, "Inspection Pass % 12M", "Pass rate", (x, y, w, 130), title="Pass rate",
                                  subtitle="Last 12 months · Plant filter only", size=28,
                                  color=BLUE, label="Target 95 %")
            new_visuals[hero["name"]] = hero
        elif slot == "lineChart" and page_key == "overview":
            place(v, *cards["line"])
            q = vis["query"]["queryState"]
            q["Y"]["projections"] = [p for p in q["Y"]["projections"] if p["queryRef"].endswith("Inspection Pass %")]
            ref = f"{T}.Inspection Pass %"
            vis["objects"] = {
                "dataPoint": [SEL({"fill": C(BLUE)}, {"metadata": ref})],
                "lineStyles": [P(lineChartType=S("smooth"), strokeWidth=N(3), showMarker=B(True),
                                 markerShape=S("circle"), markerSize=N(5), areaShow=B(True),
                                 areaMatchStrokeColor=B(True))],
                "labels": [P(show=B(True), color=C(NAVY), fontSize=N(9), fontFamily=S("Segoe UI Semibold"),
                             enableBackground=B(False))],
                "categoryAxis": [P(axisType=S("Categorical"), showAxisTitle=B(False), fontSize=N(9),
                                   labelColor=C(MUTED))],
                "valueAxis": [P(show=B(True), end=N(1), showAxisTitle=B(False), gridlineShow=B(True),
                                gridlineStyle=S("dotted"), gridlineColor=C(LINE), labelColor=C(MUTED2),
                                fontSize=N(8))],
                "legend": [P(show=B(False))],
                "y1AxisReferenceLine": [SEL({
                    "show": B(True), "displayName": S("Target 95 %"), "value": N(0.95), "lineColor": C(NAVY),
                    "transparency": N(25), "style": S("dashed"), "width": N(1.5), "position": S("front"),
                    "dataLabelShow": B(True), "dataLabelText": S("Name"), "dataLabelColor": C(NAVY),
                    "dataLabelHorizontalPosition": S("right"), "dataLabelVerticalPosition": S("above"),
                    "shadeShow": B(True), "shadeRegion": S("after"), "shadeColor": C(BLUE),
                    "shadeTransparency": N(93)}, {"id": "1"})],
            }
            vis["visualContainerObjects"] = vco_card("Pass % per month",
                                                     "Inspection pass rate per month · dashed line = 95 % target")
        elif slot == "donutChart":
            place(v, *cards["donut"])
            o = vis["objects"]
            o["slices"] = [P(innerRadiusRatio=I(72), startAngle=I(0))]
            o["dataPoint"] = [d for d in o["dataPoint"] if "selector" in d] + [
                P(borderShow=B(True), borderColor=C(WHITE), borderSize=N(2))]
            o["labels"] = [P(show=B(True), labelStyle=S("Category, percent of total"), position=S("outside"),
                             fontSize=N(9), color=C(TEXT), percentageLabelPrecision=I(1), overflow=B(True))]
            o["legend"] = [P(show=B(False))]
            vis["visualContainerObjects"] = vco_card("Pass & Fail %", "Inspections in the selected period")
        elif slot == "decompositionTreeVisual":
            place(v, *cards["decomp"])
            vis["objects"] = {
                "dataBars": [P(positiveBarColor=C(ORANGE), dataBarColor=C(ORANGE),
                               dataBarBackgroundColor=C("#F3F5F9"))],
                "tree": [P(accentColor=C(NAVY), connectorDefaultColor=C("#C9D3E0"), connectorType=S("curve"),
                           density=S("default"), responsiveLayout=B(True))],
                "categoryLabels": [P(categoryLabelFontColor=C(TEXT), categoryLabelFontSize=N(9),
                                     categoryLabelFontFamily=S("Segoe UI"))],
                "dataLabels": [P(dataLabelFontColor=C(NAVY), dataLabelFontSize=N(9), dataLabelBold=B(True),
                                 dataLabelFontFamily=S("Segoe UI"))],
                "levelHeader": [P(levelTitleFontColor=C(NAVY), levelTitleFontSize=N(10),
                                  levelTitleFontFamily=S("Segoe UI Semibold"), levelSubtitleFontColor=C(MUTED2),
                                  levelSubtitleFontSize=N(8), levelHeaderBackgroundColor=C(WHITE))],
            }
            vis["visualContainerObjects"] = vco_card(
                "Where do inspections fail?", "Failed inspections by part › test › inspection reason · click + to drill down")
        elif slot.startswith("table:") and page_key == "overview":
            place(v, *cards["table"])
            style_table(vis)
            what = "test" if slot.endswith("Test") else "part"
            vis["visualContainerObjects"] = vco_card(f"Results per {what}", f"Pass and fail by {what}")
        elif slot.startswith("toggle:"):
            _, label, state = slot.split(":")
            x, y, w, h = cards["table"]
            bx = x + w - 112 if label == "Part" else x + w - 58
            place(v, bx, y + 13, 52, 24)
            hotspot(vis)
            on = state == "on"
            look(name, label, NAVY if on else "#EEF2F8", WHITE if on else NAVY, size=9, bold=on, radius=12,
                 pad_top=3)

        # ---- page 2
        elif slot.startswith("kpi:"):
            measure = slot.split(":", 1)[1]
            first = measure == "Char Pass %"
            place(v, *cards["kpi1" if first else "kpi2"])
            vis["objects"] = {
                "value": [SEL({"fontColor": C(BLUE if first else NAVY), "fontSize": N(24), "fontFamily": S(NUM_FONT),
                               "horizontalAlignment": S("left")}, DEFAULT)],
                "label": [SEL({"show": B(False)}, DEFAULT)],
                **CARD_CLEAN,
                "trendVisualLibrary": [SEL({"show": B(True), "chartType": S("line"), "includePrimaryMeasure": B(True),
                                            "legendShow": B(False), "showTooltip": B(True)}, DEFAULT)],
                "lineTrendVisual": [SEL({"lineColor": C(BLUE if first else NAVY), "lineWidth": N(2),
                                         "lineShape": S("smooth"), "fillArea": B(True), "fillAreaTransparency": N(85),
                                         "showMarkers": B(False)}, DEFAULT)],
                "cartesianTrendVisual": [SEL({"showXAxis": B(False), "showYAxis": B(False)}, DEFAULT)],
            }
            vis["query"]["queryState"]["TrendVisualCategory"] = {
                "projections": [projection("Column", "Date", "Date", active=True)]}
            title = "Characteristic pass % · per day" if first else "Measured values · per day"
            vis["visualContainerObjects"] = vco_card(title, None, pad=(10, 6, 16, 16))
        elif slot == "lineChart":
            place(v, *cards["line"])
            q = vis["query"]["queryState"]
            fail = [p for p in q["Y"]["projections"] if p["queryRef"].endswith("Char Fail")]
            q["Y"]["projections"] = [p for p in q["Y"]["projections"] if p["queryRef"].endswith("Char Pass")]
            q["Y2"] = {"projections": fail}
            pref, fref = f"{T}.Char Pass", f"{T}.Char Fail"
            vis["objects"] = {
                "dataPoint": [SEL({"fill": C(BLUE)}, {"metadata": pref}), SEL({"fill": C(ORANGE)}, {"metadata": fref})],
                "lineStyles": [SEL({"lineChartType": S("smooth"), "strokeWidth": N(2.5), "showMarker": B(False),
                                    "areaShow": B(True), "areaMatchStrokeColor": B(True)}, {"metadata": pref}),
                               SEL({"lineChartType": S("smooth"), "strokeWidth": N(2), "showMarker": B(False),
                                    "areaShow": B(False)}, {"metadata": fref})],
                "legend": [P(show=B(True), position=S("TopRight"), fontSize=N(9), labelColor=C(TEXT),
                             showTitle=B(False))],
                "categoryAxis": [P(showAxisTitle=B(False), gridlineShow=B(False), fontSize=N(9), labelColor=C(MUTED))],
                "valueAxis": [P(show=B(True), showAxisTitle=B(False), gridlineShow=B(True), gridlineStyle=S("dotted"),
                                gridlineColor=C(LINE), labelColor=C(BLUE), fontSize=N(8))],
                "y2Axis": [P(show=B(True), secShowAxisTitle=B(False), secLabelColor=C(ORANGE), secFontSize=N(8))],
            }
            vis["visualContainerObjects"] = vco_card("Measured values per day",
                                                     "Pass on the left axis (blue) · Fail on the right axis (orange)")
        elif slot.startswith("bars:"):
            what = "part" if slot.endswith("Part") else "test"
            place(v, *cards["bars_part" if what == "part" else "bars_test"])
            o = vis["objects"]
            o["labels"] = [P(show=B(True), color=C(WHITE), fontSize=N(8.5), labelDisplayUnits=N(1),
                             labelPosition=S("InsideCenter"))]
            o["legend"] = [P(show=B(True), position=S("TopRight"), showTitle=B(False), fontSize=N(9),
                             labelColor=C(TEXT))]
            o["categoryAxis"] = [P(show=B(True), showAxisTitle=B(False), fontSize=N(9), labelColor=C(TEXT),
                                   innerPadding=I(34), maxMarginFactor=I(40 if what == "part" else 36))]
            vis["visualContainerObjects"] = vco_card(f"{what.capitalize()} – Pass & Fail %",
                                                     "Share of evaluated values · bar length = volume")
        elif slot.startswith("table:"):
            place(v, *cards["table"])
            style_table(vis)
            vis["visualContainerObjects"] = vco_card("Results per characteristic",
                                                     "Sorted by fail % · data bars for Pass % and Fail %")

        # ---- "More filters" panel (positions unchanged, refreshed look)
        elif slot == "overlay":
            hotspot(vis)
            look(name, "", NAVY_DEEP, WHITE, radius=0, pad_top=0, bg_transp=42, border=False)
        elif slot == "panel_bg":
            vis["visualContainerObjects"] = vco_plain({
                "background": [P(show=B(True), color=C(WHITE), transparency=N(0))],
                "dropShadow": [P(show=B(True), color=C(NAVY_DEEP), position=S("Outer"), preset=S("Custom"),
                                 shadowSpread=N(0), shadowBlur=N(28), angle=N(180), shadowDistance=N(2),
                                 transparency=N(70))],
                "padding": [P(top=N(22), bottom=N(0), left=N(18), right=N(40))],
            })
        elif slot.startswith("panel_slicer:"):
            o = vis["objects"]
            o["header"] = [P(show=B(True), fontColor=C(MUTED2), textSize=N(8.5), fontFamily=S("Segoe UI Semibold"))]
            o["items"] = [P(fontColor=C(NAVY), textSize=N(10), fontFamily=S("Segoe UI"), background=C("#F6F8FB"))]
            o["dropdown"] = [P(borderColor=C("#DCE3EE"), borderRadius=I(8), iconColor=C(NAVY))]
            vis["visualContainerObjects"] = vco_plain()
        elif slot == "panel_reset":
            link = vis["visualContainerObjects"].get("visualLink")
            vis["objects"] = button_objects("Reset", fill="#EEF2F8", outline=NAVY, outline_transp=60, text_color=NAVY,
                                            size=10, bold=True, shape="pill", hover=("#DDE6F2", 0))
            vis["visualContainerObjects"] = vco_plain({"visualLink": link})
        elif slot == "panel_close":
            hotspot(vis)
            look(name, "Close", NAVY, WHITE, size=10, radius=16, pad_top=6)
        elif slot == "panel_x":
            v["position"].update({"x": 1234, "y": 12, "width": 30, "height": 30})
            hotspot(vis)
            look(name, "✕", NAVY, WHITE, size=10, radius=15, pad_top=5)
        else:
            raise SystemExit(f"unhandled visual {name}: {slot}")


def style_table(vis):
    o = vis["objects"]
    o["columnHeaders"] = [P(fontColor=C(MUTED2), fontSize=N(9), fontFamily=S("Segoe UI Semibold"),
                            backColor=C(WHITE), wordWrap=B(True))]
    o["values"] = [P(fontSize=N(10), fontFamily=S("Segoe UI"), fontColorPrimary=C(TEXT), fontColorSecondary=C(TEXT),
                     backColorPrimary=C(WHITE), backColorSecondary=C("#FAFBFD"), wordWrap=B(True))] + \
        [x for x in o.get("values", []) if "selector" in x]
    o["grid"] = [P(gridVertical=B(False), gridHorizontal=B(True), gridHorizontalColor=C("#EEF2F7"),
                   outlineColor=C(LINE), outlineWeight=N(1), rowPadding=N(6))]


CARD_CLEAN = {  # new card visual: remove the default tile border, outline, accent bar and callout background
    "fillCustom": [SEL({"show": B(False)}, DEFAULT)],
    "outline": [SEL({"show": B(False)}, DEFAULT)],
    "border": [SEL({"show": B(False)}, DEFAULT)],
    "accentBar": [SEL({"show": B(False)}, DEFAULT)],
    "shadowCustom": [SEL({"show": B(False)}, DEFAULT)],
    "glowCustom": [SEL({"show": B(False)}, DEFAULT)],
    "cardCalloutArea": [SEL({"show": B(False)}, DEFAULT)],
}


def new_cardvisual(like, measure, display, rect, title, subtitle, size, color, label):
    x, y, w, h = rect
    name = secrets.token_hex(10)
    return {
        "$schema": like["$schema"],
        "name": name,
        "position": {"x": x, "y": y, "z": like["position"]["z"] - 500, "height": h, "width": w,
                     "tabOrder": like["position"]["z"] - 500},
        "visual": {
            "visualType": "cardVisual",
            "query": {"queryState": {"Data": {"projections": [projection("Measure", measure, display)]}},
                      "sortDefinition": {"isDefaultSort": True}},
            "objects": {
                "value": [SEL({"fontColor": C(color), "fontSize": N(size), "fontFamily": S(NUM_FONT),
                               "horizontalAlignment": S("left")}, DEFAULT)],
                "label": [SEL({"show": B(False)}, DEFAULT)],
                **CARD_CLEAN,
            },
            "visualContainerObjects": vco_card(title, subtitle, pad=(12, 2, 16, 16), header=False),
            "drillFilterOtherVisuals": True,
        },
    }


# --------------------------------------------------------------------------- capability check
def enum_values(spec):
    t = spec.get("type", {}) if isinstance(spec, dict) else {}
    e = t.get("enumeration") if isinstance(t, dict) else None
    if isinstance(e, dict):
        e = e.get("allMembers", [])
    return {str(x.get("value")) for x in e} if isinstance(e, list) else None


def check_capabilities(pages):
    cat_dir = pathlib.Path(os.environ.get("PBI_VISUAL_SCHEMA_DIR", ""))
    cap = json.loads((cat_dir / "capabilities.json").read_text())
    vco = json.loads((cat_dir / "vco-capabilities.json").read_text())
    problems = []
    for page, visuals in pages.items():
        for name, v in visuals.items():
            vt = v["visual"]["visualType"]
            objs = cap.get(vt, {}).get("objects", {})
            for on, entries in v["visual"].get("objects", {}).items():
                if on not in objs:
                    problems.append(f"{page}/{vt}: unknown object '{on}'")
                    continue
                for e in entries:
                    for pn, val in e.get("properties", {}).items():
                        spec = objs[on].get("properties", {}).get(pn)
                        if spec is None:
                            problems.append(f"{page}/{vt}: unknown property '{on}.{pn}'")
                            continue
                        allowed = enum_values(spec)
                        lit_val = val.get("expr", {}).get("Literal", {}).get("Value") if isinstance(val, dict) else None
                        if allowed and isinstance(lit_val, str) and lit_val.startswith("'"):
                            if lit_val.strip("'") not in allowed:
                                problems.append(f"{page}/{vt}: '{on}.{pn}' = {lit_val} not in {allowed}")
            for on, entries in v["visual"].get("visualContainerObjects", {}).items():
                props = vco.get(on, {}).get("properties", vco.get(on, {}))
                if on not in vco:
                    problems.append(f"{page}/{vt}: unknown container object '{on}'")
                    continue
                for e in entries:
                    for pn in e.get("properties", {}):
                        if pn not in props:
                            problems.append(f"{page}/{vt}: unknown container property '{on}.{pn}'")
            roles = {r["name"] for r in cap.get(vt, {}).get("dataRoles", [])}
            for role in v["visual"].get("query", {}).get("queryState", {}):
                if roles and role not in roles:
                    problems.append(f"{page}/{vt}: unknown data role '{role}'")
    return problems


# --------------------------------------------------------------------------- main
def main(src, dst):
    zin = zipfile.ZipFile(src)
    files = {n: zin.read(n) for n in zin.namelist()}
    prefix = "Report/definition/"
    defs = {n[len(prefix):]: json.loads(b) for n, b in files.items() if n.startswith(prefix)}

    pages_meta = defs["pages/pages.json"]
    page_names, page_keys = {}, {}
    for pid in pages_meta["pageOrder"]:
        disp = defs[f"pages/{pid}/page.json"]["displayName"]
        key = {"Overview": "overview", "Characteristics": "chars"}[disp]
        page_names[pid] = key
        page_keys[key] = pid

    out_defs = {k: v for k, v in defs.items() if "/visuals/" not in k}
    all_pages = {}
    twins = {}
    images = {}
    for key, pid in page_keys.items():
        visuals = {}
        for k, v in defs.items():
            if k.startswith(f"pages/{pid}/visuals/"):
                v = copy.deepcopy(v)
                v["_slot"] = classify(v, page_names)
                visuals[v["name"]] = v
        new_visuals, removed = {}, []
        LOOKS.clear()
        restyle_page(key, visuals, new_visuals, removed)
        for bname, lk in LOOKS.items():
            t = twin_textbox(visuals[bname], lk)
            new_visuals[t["name"]] = t
            twins[bname] = t["name"]
        for n in removed:
            visuals.pop(n)
        visuals.update(new_visuals)
        for v in visuals.values():
            v.pop("_slot", None)
            out_defs[f"pages/{pid}/visuals/{v['name']}/visual.json"] = v
        all_pages[key] = visuals

        # page background artwork
        img = f"QualityDashboard{key.capitalize()}{secrets.token_hex(6)}.png"
        images[img] = (HERE / "out" / f"bg_{key}.png").read_bytes()
        page = out_defs[f"pages/{pid}/page.json"]
        page["objects"] = {
            "background": [P(image={"image": {
                "name": S(f"{D.PAGES[key]['title']} background.png"),
                "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                         "ItemName": img}}},
                "scaling": S("Fit")}}, transparency=N(0))],
            "outspace": [P(color=C("#E7EDF5"), transparency=N(0))],
        }
    pages_meta["activePageName"] = page_keys["overview"]

    report = out_defs["report.json"]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]

    for k, bm in out_defs.items():
        if k.startswith("bookmarks/") and k.endswith(".bookmark.json"):
            names = bm["options"].get("targetVisualNames", [])
            for sec in bm["explorationState"]["sections"].values():
                vcs = sec.get("visualContainers", {})
                for n in list(vcs):
                    if n in twins:
                        entry = copy.deepcopy(vcs[n])
                        entry["singleVisual"]["visualType"] = "textbox"
                        entry["singleVisual"]["objects"] = {}
                        vcs[twins[n]] = entry
            bm["options"]["targetVisualNames"] = names + [twins[n] for n in names if n in twins]

    problems = check_capabilities(all_pages)
    bookmark_targets = set()
    for k, v in out_defs.items():
        if k.startswith("bookmarks/") and k.endswith(".bookmark.json"):
            bookmark_targets |= set(v["options"].get("targetVisualNames", []))
    names = {n for vis in all_pages.values() for n in vis}
    problems += [f"bookmark target {n} missing" for n in bookmark_targets - names]
    if problems:
        print("\n".join(problems))
        raise SystemExit("capability / bookmark check failed")
    print(f"capability check: OK ({sum(len(v) for v in all_pages.values())} visuals, "
          f"{len(bookmark_targets)} bookmark targets present)")

    ct = files["[Content_Types].xml"].decode("utf-8-sig")
    ct = ct.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")
    if 'Extension="png"' not in ct:
        ct = ct.replace('<Default Extension="json" ContentType="" />',
                        '<Default Extension="json" ContentType="" /><Default Extension="png" ContentType="image/png" />')
    with zipfile.ZipFile(dst, "w") as z:
        for info in zin.infolist():
            n = info.filename
            if n == "SecurityBindings" or n.startswith(prefix):
                continue
            data = files[n]
            if n == "[Content_Types].xml":
                data = ("﻿" + ct).encode("utf-8")
            zi = zipfile.ZipInfo(n, date_time=info.date_time)
            zi.compress_type = info.compress_type
            z.writestr(zi, data)
        for k, v in sorted(out_defs.items()):
            z.writestr(zipfile.ZipInfo(prefix + k), json.dumps(v, ensure_ascii=False, separators=(",", ":")),
                       compress_type=zipfile.ZIP_DEFLATED)
        for n, data in images.items():
            z.writestr(zipfile.ZipInfo("Report/StaticResources/RegisteredResources/" + n), data,
                       compress_type=zipfile.ZIP_DEFLATED)
    print(f"written {dst} ({pathlib.Path(dst).stat().st_size:,} bytes)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / "Quality_Dashboard_V3.pbix"))
