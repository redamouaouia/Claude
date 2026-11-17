"""Rebuild the Quality Dashboard report pages inside an existing .pbix.

Usage:  python build_report.py <input.pbix> <output.pbix>

Only the report layout is rewritten (Report/Layout). The data model is copied
unchanged: the measures and columns used by the new pages are added afterwards
with model_changes.tmdl (TMDL view in Power BI Desktop).
"""
import json
import secrets
import sys
import zipfile

# --------------------------------------------------------------------------- palette
NAVY = "#0B2A5B"        # side menu, titles
PAGE_BG = "#EEF1F6"
WHITE = "#FFFFFF"
CARD_BORDER = "#E1E6EE"
TEXT = "#1B2A41"
MUTED = "#5A6B85"
BLUE = "#2F6EBA"        # Pass
ORANGE = "#ED7D31"      # Fail
DARK_BLUE = "#1F4E79"   # reaction limits
LIGHT_BLUE = "#9DC3E6"
LIGHT_ORANGE = "#F4B183"
RL_LIGHT = "#B4C7DC"
NAV_ACTIVE = "#E8EEF8"
NAV_SUB = "#9DB8E0"

IP, Q = "Inspection Page", "Query1"


def hexid():
    return secrets.token_hex(10)


# --------------------------------------------------------------------------- literals
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(t):
    return lit("'" + t.replace("'", "''") + "'")


def d(n):
    return lit(f"{n}D")


def l(n):
    return lit(f"{n}L")


def b(x):
    return lit("true" if x else "false")


def color(h):
    return {"solid": {"color": s(h)}}


def props(**kw):
    return {"properties": kw}


def meta(ref):
    return {"metadata": ref}


DEFAULT = {"id": "default"}


# --------------------------------------------------------------------------- fields & queries
class Fld:
    def __init__(self, entity, prop, measure=False, display=None):
        self.entity, self.prop, self.measure, self.display = entity, prop, measure, display
        self.ref = f"{entity}.{prop}"

    def as_(self, display):
        return Fld(self.entity, self.prop, self.measure, display)


def col(e, p, display=None):
    return Fld(e, p, False, display)


def mea(e, p, display=None):
    return Fld(e, p, True, display)


def field_expr(f, source=None, entity=False):
    key = "Measure" if f.measure else "Column"
    ref = {"Entity": f.entity} if entity else {"Source": source}
    return {key: {"Expression": {"SourceRef": ref}, "Property": f.prop}}


def build_query(fields, order=None):
    aliases, frm = {}, []

    def alias(e):
        if e not in aliases:
            base = "i" if e == IP else ("q" if e == Q else e[0].lower())
            a, n = base, 1
            while a in aliases.values():
                a, n = f"{base}{n}", n + 1
            aliases[e] = a
            frm.append({"Name": a, "Entity": e, "Type": 0})
        return aliases[e]

    sel = []
    for f in fields:
        e = field_expr(f, alias(f.entity))
        e["Name"] = f.ref
        e["NativeReferenceName"] = f.display or f.prop
        sel.append(e)
    q = {"Version": 2, "From": frm, "Select": sel}
    if order:
        q["OrderBy"] = [{"Direction": dirn, "Expression": field_expr(f, alias(f.entity))} for f, dirn in order]
    return q


ASC, DESC = 1, 2
ACTIVE_ROLES = {"Category", "Group", "Values_slicer"}


def visual(vtype, roles=None, objects=None, vc=None, order=None, hidden=False, extra=None):
    roles = roles or {}
    fields, seen = [], set()
    for fl in roles.values():
        for f in fl:
            if f.ref not in seen:
                seen.add(f.ref)
                fields.append(f)
    sv = {"visualType": vtype}
    if fields:
        proj = {}
        for r, fl in roles.items():
            items = []
            for f in fl:
                it = {"queryRef": f.ref}
                if r in ("Category", "Group") or (vtype == "slicer" and r == "Values"):
                    it["active"] = True
                items.append(it)
            proj[r] = items
        sv["projections"] = proj
        sv["prototypeQuery"] = build_query(fields, order)
        cp = {f.ref: {"displayName": f.display} for f in fields if f.display}
        if cp:
            sv["columnProperties"] = cp
        if not order:
            sv["hasDefaultSort"] = True
    sv["drillFilterOtherVisuals"] = True
    if objects:
        sv["objects"] = objects
    if vc:
        sv["vcObjects"] = vc
    if hidden:
        sv["display"] = {"mode": "hidden"}
    if extra:
        sv.update(extra)
    return sv


# --------------------------------------------------------------------------- container formatting
def vc_card(title=None, title_size=12, radius=12, shadow=True, bg=WHITE, border=True,
            border_color=CARD_BORDER, header=True, pad=(8, 8, 12, 12)):
    v = {
        "background": [props(show=b(True), color=color(bg), transparency=d(0))],
        "border": [props(show=b(border), color=color(border_color), radius=d(radius))],
        "dropShadow": [props(show=b(shadow), color=color(NAVY), position=s("Outer"), preset=s("Custom"),
                             shadowSpread=d(0), shadowBlur=d(10), angle=d(90), shadowDistance=d(2),
                             transparency=d(88))],
        "padding": [props(top=d(pad[0]), bottom=d(pad[1]), left=d(pad[2]), right=d(pad[3]))],
    }
    if title:
        v["title"] = [props(show=b(True), text=s(title), fontColor=color(NAVY), fontSize=d(title_size),
                            fontFamily=s("Segoe UI Semibold"), alignment=s("left"))]
    else:
        v["title"] = [props(show=b(False))]
    if not header:
        v["visualHeader"] = [props(show=b(False))]
    return v


def vc_plain(bg=None, transparency=0, radius=0, border_color=None):
    v = {
        "background": [props(show=b(bg is not None), color=color(bg or WHITE), transparency=d(transparency))],
        "border": [props(show=b(border_color is not None), color=color(border_color or WHITE), radius=d(radius))],
        "dropShadow": [props(show=b(False))],
        "title": [props(show=b(False))],
        "visualHeader": [props(show=b(False))],
        "padding": [props(top=d(0), bottom=d(0), left=d(0), right=d(0))],
    }
    return v


# --------------------------------------------------------------------------- building blocks
def run(text, size=10, col_=NAVY, bold=False, font="Segoe UI"):
    st = {"fontFamily": font, "fontSize": f"{size}pt", "color": col_}
    if bold:
        st["fontWeight"] = "bold"
    return {"value": text, "textStyle": st}


def para(runs, align="left"):
    return {"textRuns": runs, "horizontalTextAlignment": align}


def textbox(paragraphs, vc=None, hidden=False):
    return visual("textbox", objects={"general": [props(paragraphs=paragraphs)]}, vc=vc or vc_plain(), hidden=hidden)


def link_page(section):
    return [props(show=b(True), type=s("PageNavigation"), navigationSection=s(section))]


def link_bookmark(bm):
    return [props(show=b(True), type=s("Bookmark"), bookmark=s(bm))]


def link_back():
    return [props(show=b(True), type=s("Back"))]


def link_clear():
    return [props(show=b(True), type=s("ClearAllSlicers"))]


def link_drill(section):
    return [props(show=b(True), type=s("Drillthrough"), drillthroughSection=s(section))]


def button(text=None, icon="blank", fill=None, fill_transp=0, text_color=NAVY, size=10, bold=False,
           align="center", outline=None, radius=6, link=None, hidden=False, hover_fill=None):
    font = "Segoe UI Semibold" if bold else "Segoe UI"
    objs = {
        "icon": [{"properties": {"shapeType": s(icon)}, "selector": DEFAULT}],
        "text": [{"properties": {"show": b(bool(text)), "text": s(text or ""), "fontColor": color(text_color),
                                 "fontSize": d(size), "fontFamily": s(font), "horizontalAlignment": s(align),
                                 "verticalAlignment": s("middle")}, "selector": DEFAULT}],
        "fill": [{"properties": {"show": b(fill is not None), "fillColor": color(fill or WHITE),
                                 "transparency": d(fill_transp)}, "selector": DEFAULT}],
        "outline": [{"properties": {"show": b(outline is not None), "lineColor": color(outline or NAVY),
                                    "weight": d(1), "transparency": d(0), "roundEdge": d(radius)},
                     "selector": DEFAULT}],
        "shape": [{"properties": {"tileShape": s("rectangleRounded"), "roundEdge": d(radius)}, "selector": DEFAULT}],
    }
    if hover_fill:
        objs["fill"].append({"properties": {"show": b(True), "fillColor": color(hover_fill), "transparency": d(80)},
                             "selector": {"id": "hover"}})
    vc = vc_plain()
    if link:
        vc["visualLink"] = link
    return visual("actionButton", objects=objs, vc=vc, hidden=hidden)


def slicer(f, mode="Dropdown", sync=None, hidden=False, search=False, panel=False):
    objs = {
        "data": [props(mode=s(mode))],
        "header": [props(show=b(True), fontColor=color(NAVY), textSize=d(9), fontFamily=s("Segoe UI"))],
        "items": [props(fontColor=color(TEXT), textSize=d(10), background=color(WHITE))],
    }
    if mode == "Between":
        objs["slider"] = [props(show=b(False))]
        objs["dateRange"] = [props(includeToday=b(True))]
    if search:
        objs["general"] = [props(selfFilterEnabled=b(True))]
    if panel:
        vc = vc_plain(bg=WHITE)
    else:
        vc = vc_card(None, radius=10, pad=(4, 4, 10, 10), header=False)
    extra = {"syncGroup": {"groupName": sync, "fieldChanges": True, "filterChanges": True}} if sync else None
    return visual("slicer", {"Values": [f]}, objects=objs, vc=vc, hidden=hidden, extra=extra,
                  order=[(f, ASC)])


def scope_color(entity, prop, value, hexcolor):
    return {"properties": {"fill": color(hexcolor)},
            "selector": {"data": [{"scopeId": {"Comparison": {
                "ComparisonKind": 0,
                "Left": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                "Right": {"Literal": {"Value": "'" + value + "'"}}}}}]}}


def table_objects(colfmt, extra_values=None):
    objs = {
        "columnHeaders": [props(fontColor=color(NAVY), fontSize=d(10), fontFamily=s("Segoe UI Semibold"),
                                outline=s("BottomOnly"), backColor=color(WHITE), wordWrap=b(True))],
        "values": [props(fontSize=d(10), fontColorPrimary=color(TEXT), fontColorSecondary=color(TEXT),
                         backColorPrimary=color(WHITE), backColorSecondary=color(WHITE))],
        "grid": [props(gridVertical=b(False), gridHorizontal=b(True), gridHorizontalColor=color(CARD_BORDER),
                       outlineColor=color(NAVY), outlineWeight=l(2), rowPadding=l(4))],
        "total": [props(totals=b(False))],
        "columnFormatting": colfmt,
    }
    if extra_values:
        objs["values"].extend(extra_values)
    return objs


def colfmt(f, font_color=None, header=True, values=True, bar=None):
    p = {}
    if font_color:
        p.update(fontColor=color(font_color), styleHeader=b(header), styleValues=b(values))
    if bar:
        p["dataBars"] = {"positiveColor": color(bar), "negativeColor": color(LIGHT_ORANGE),
                         "axisColor": color(WHITE), "reverseDirection": b(False), "hideText": b(False)}
    return {"properties": p, "selector": meta(f.ref)}


def pass_fail_table(row_field, pass_pct, pass_n, fail_n, fail_pct, sort_field, title, hidden=False):
    roles = {"Values": [row_field, pass_pct.as_("Pass %"), pass_n.as_("Pass"), fail_n.as_("Fail"),
                        fail_pct.as_("Fail %")]}
    cf = [colfmt(pass_pct, BLUE, bar=LIGHT_BLUE), colfmt(pass_n, BLUE, values=False),
          colfmt(fail_n, ORANGE, values=False), colfmt(fail_pct, ORANGE, bar=LIGHT_ORANGE)]
    cf[3]["properties"]["dataBars"]["positiveColor"] = color(LIGHT_ORANGE)
    return visual("tableEx", roles, objects=table_objects(cf), vc=vc_card(title), order=[(sort_field, DESC)],
                  hidden=hidden)


def stacked_pass_fail(category, fail_bar, pass_bar, count, title):
    roles = {"Category": [category], "Y": [fail_bar.as_("Fail"), pass_bar.as_("Pass")], "Tooltips": [count]}
    objs = {
        "dataPoint": [{"properties": {"fill": color(ORANGE)}, "selector": meta(fail_bar.ref)},
                      {"properties": {"fill": color(BLUE)}, "selector": meta(pass_bar.ref)}],
        "labels": [props(show=b(True), color=color(WHITE), fontSize=d(9), labelDisplayUnits=d(1),
                         labelPosition=s("InsideCenter"))],
        "legend": [props(show=b(True), position=s("TopLeft"), showTitle=b(False), fontSize=d(9))],
        "valueAxis": [props(show=b(False), gridlineShow=b(False))],
        "categoryAxis": [props(show=b(True), showAxisTitle=b(False), fontSize=d(9), labelColor=color(MUTED))],
        "totals": [props(show=b(False))],
    }
    return visual("barChart", roles, objects=objs, vc=vc_card(title), order=[(count, DESC)])


def donut(category_entity, category_prop, value, title, label_style="Category, percent of total"):
    cat = col(category_entity, category_prop)
    objs = {
        "legend": [props(show=b(False))],
        "labels": [props(show=b(True), labelStyle=s(label_style), percentageLabelPrecision=l(1),
                         fontSize=d(10), color=color(TEXT), position=s("outside"), overflow=b(True))],
        "slices": [props(innerRadiusRatio=l(62), startAngle=l(0))],
        "dataPoint": [scope_color(category_entity, category_prop, "Pass", BLUE),
                      scope_color(category_entity, category_prop, "Fail", ORANGE),
                      props(borderShow=b(False))],
    }
    return visual("donutChart", {"Category": [cat], "Y": [value]}, objects=objs, vc=vc_card(title))


def kpi_card(f, title):
    objs = {
        "value": [{"properties": {"fontColor": color(BLUE), "fontSize": d(30), "fontFamily": s("Segoe UI Semibold"),
                                  "horizontalAlignment": s("left")}, "selector": DEFAULT}],
        "label": [{"properties": {"show": b(False)}, "selector": DEFAULT}],
        "fillCustom": [{"properties": {"show": b(False), "fillColor": color(WHITE)}, "selector": DEFAULT}],
        "layout": [props(alignment=s("middle"))],
    }
    return visual("cardVisual", {"Data": [f]}, objects=objs, vc=vc_card(title, title_size=13))


# --------------------------------------------------------------------------- page assembly
class Page:
    def __init__(self, name, display, hidden=False):
        self.name, self.display, self.hidden = name, display, hidden
        self.containers, self.filters, self.z = [], [], 0

    def add(self, sv, x, y, w, h, filters=None, name=None):
        name = name or hexid()
        self.z += 1000
        cfg = {"name": name, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": self.z, "width": w,
                                                                 "height": h, "tabOrder": self.z}}],
               "singleVisual": sv}
        self.containers.append({"x": x, "y": y, "z": self.z, "width": w, "height": h,
                                "config": json.dumps(cfg, ensure_ascii=False),
                                "filters": json.dumps(filters or [], ensure_ascii=False)})
        return name

    def section(self, ordinal):
        cfg = {"objects": {"background": [props(color=color(PAGE_BG), transparency=d(0))],
                           "outspace": [props(color=color(PAGE_BG), transparency=d(0))]}}
        if self.hidden:
            cfg["visibility"] = 1
        return {"name": self.name, "displayName": self.display,
                "filters": json.dumps(self.filters, ensure_ascii=False), "ordinal": ordinal,
                "visualContainers": self.containers, "config": json.dumps(cfg, ensure_ascii=False),
                "displayOption": 1, "width": 1280, "height": 720}


def bookmark(display, section, states):
    """states: {visual name: (visual type, hidden?)}; only these visuals are touched, data is not captured."""
    vcs = {}
    for n, (vt, hid) in states.items():
        sv = {"visualType": vt, "objects": {}}
        if hid:
            sv["display"] = {"mode": "hidden"}
        vcs[n] = {"singleVisual": sv}
    return {"displayName": display, "name": "Bookmark" + hexid(),
            "explorationState": {"version": "1.3", "activeSection": section,
                                 "sections": {section: {"visualContainers": vcs}}},
            "options": {"targetVisualNames": list(states), "suppressData": True, "applyOnlyToTargetVisuals": True}}


# --------------------------------------------------------------------------- fields used by the pages
F = {
    # Inspection Page (page 1 + shared filters)
    "plant": col(IP, "Plant", "Plant"),
    "part": col(IP, "Inspection Plan", "Part (inspection plan)"),
    "test": col(IP, "Process Name", "Test"),
    "reason": col(IP, "Inspection Reason", "Inspection reason"),
    "day": col(IP, "Inspection Day", "Date"),
    "press": col(IP, "Press", "Press"),
    "month": col(IP, "Inspection Month", "Month"),
    "passfail": col(IP, "Test PassFail"),
    "insp": mea(IP, "Inspections", "Inspections"),
    "insp_pass": mea(IP, "Inspections Pass"),
    "insp_fail": mea(IP, "Inspections Fail"),
    "insp_pass_pct": mea(IP, "Inspection Pass %"),
    "insp_fail_pct": mea(IP, "Inspection Fail %"),
    "pass12": mea(IP, "Inspection Pass % 12M", "Pass %"),
    "target": mea(IP, "Pass % Target", "Target"),
    "last_refresh": mea(IP, "Last Refresh", "Last refresh"),
    # Query1 (pages 2-4)
    "q_part": col(Q, "Inspection Plan", "Part"),
    "q_partname": col(Q, "Part Name", "Part name"),
    "q_test": col(Q, "Process Name", "Test"),
    "char": col(Q, "Characteristic", "Characteristic"),
    "kfl": col(Q, "Key Field Label", "Key field label"),
    "kpc": col(Q, "KPC", "KPC label"),
    "mday": col(Q, "Measurement Day", "Date"),
    "cpk_thr": col(Q, "Cpk Threshold", "Cpk threshold"),
    "cpk_pf": col(Q, "Cpk Pass/Fail", "Cpk pass / fail"),
    "mv": mea(Q, "Measured Values", "Measured values"),
    "c_pass": mea(Q, "Char Pass"),
    "c_fail": mea(Q, "Char Fail"),
    "c_pass_pct": mea(Q, "Char Pass %"),
    "c_fail_pct": mea(Q, "Char Fail %"),
    "c_pass_bar": mea(Q, "Char Pass Bar"),
    "c_fail_bar": mea(Q, "Char Fail Bar"),
    "rl": mea(Q, "RL Violations", "Violations"),
    "rl_share": mea(Q, "RL Share", "Share"),
    "cpk_chars": mea(Q, "Cpk Chars", "Characteristics"),
    "cpk_pass_pct": mea(Q, "Cpk Char Pass %", "Cpk pass %"),
    "cpk_pass_bar": mea(Q, "Cpk Chars Pass Bar"),
    "cpk_fail_bar": mea(Q, "Cpk Chars Fail Bar"),
    "cpk_val": mea(Q, "Cpk Value", "Cpk"),
    "cpk_thr_val": mea(Q, "Cpk Threshold Value", "Threshold"),
    "cpk_status": mea(Q, "Cpk Status", "Status"),
    "cpk_status_color": mea(Q, "Cpk Status Color"),
}

# Slicers synced across pages (same field + same group name).
SLICER_DEF = {
    "plant": ("plant", "Dropdown", "Plant"),
    "part": ("part", "Dropdown", "Part"),
    "partname": ("q_partname", "Dropdown", "Part name"),
    "test": ("test", "Dropdown", "Test"),
    "char": ("char", "Dropdown", "Characteristic"),
    "reason": ("reason", "Dropdown", "Inspection reason"),
    "date": ("day", "Between", "Date"),
    "press": ("press", "Dropdown", "Press"),
    "kfl": ("kfl", "Dropdown", "Key field label"),
    "kpc": ("kpc", "Dropdown", "KPC"),
    "cpk_thr": ("cpk_thr", "Dropdown", "Cpk threshold"),
    "cpk_pf": ("cpk_pf", "Dropdown", "Cpk pass / fail"),
}
SEARCHABLE = {"part", "partname", "test", "char", "reason"}

NAV_ITEMS = [("overview", "Overview"), ("chars", "Characteristics"), ("rl", "Reaction limits"), ("cpk", "Cpk")]

# --------------------------------------------------------------------------- page geometry (1280 x 720)
X0, X1 = 210, 1265          # content area
ROW_SLICER_Y, ROW_SLICER_H = 64, 54
GAP = 8


def distribute(weights, x0=X0, x1=X1, gap=GAP):
    total = x1 - x0 - gap * (len(weights) - 1)
    unit = total / sum(weights)
    xs, x = [], x0
    for w in weights:
        xs.append((round(x, 1), round(w * unit, 1)))
        x += w * unit + gap
    return xs


def build(sections_by_key, bookmarks):
    pages = {k: Page(hexid(), t) for k, t in NAV_ITEMS}
    detail = Page(hexid(), "Reaction limits – details", hidden=True)
    names = {k: p.name for k, p in pages.items()}

    def common(p, key, title, slicers, panel_slicers, title_w=420):
        # side menu
        p.add(textbox([para([run("", 10, WHITE)])], vc=vc_plain(bg=NAVY)), 0, 0, 196, 720)
        p.add(textbox([para([run("OP", 22, WHITE, True), run("mobility", 22, WHITE)])]), 14, 16, 178, 40)
        p.add(textbox([para([run("Quality Dashboard", 11, WHITE, True)]),
                       para([run("Plant Visual Management", 10, NAV_SUB)])]), 14, 60, 178, 44)
        for i, (k, label) in enumerate(NAV_ITEMS):
            active = (k == key)
            p.add(button(label, fill=NAV_ACTIVE if active else None, text_color=NAVY if active else WHITE,
                         size=11, bold=active, align="left", link=link_page(names[k]),
                         hover_fill=None if active else WHITE), 14, 126 + i * 41, 168, 34)
        p.add(button("Clear all filters", outline=WHITE, text_color=WHITE, size=10, link=link_clear()),
              24, 645, 158, 29)
        p.add(textbox([para([run("ⓘ  Information", 10, WHITE)])]), 14, 684, 160, 24)
        # header
        p.add(textbox([para([run(title, 20, NAVY, True, "Segoe UI Semibold")])]), 204, 10, title_w, 44)
        p.add(visual("card", {"Values": [F["last_refresh"]]},
                     objects={"labels": [props(color=color(NAVY), fontSize=d(9), fontFamily=s("Segoe UI"))],
                              "categoryLabels": [props(show=b(False))]},
                     vc=vc_card(None, radius=14, shadow=False, pad=(0, 0, 6, 6), header=False)),
              1075, 18, 190, 30)
        # filter row (+ "More filters" button)
        weights = [w for _, w in slicers] + [0.62]
        pos = distribute(weights)
        for (sk, _), (x, w) in zip(slicers, pos):
            fk, mode, group = SLICER_DEF[sk]
            p.add(slicer(F[fk], mode, sync=group, search=sk in SEARCHABLE), x, ROW_SLICER_Y, w, ROW_SLICER_H)
        mx, mw = pos[-1]
        more_btn = p.add(button(f"More filters ({len(panel_slicers)})", fill=WHITE, size=10, bold=True,
                                radius=10), mx, ROW_SLICER_Y, mw, ROW_SLICER_H)
        def finish():
            add_more_filters_panel(p, title, panel_slicers, more_btn)
        return finish

    def add_more_filters_panel(p, title, panel_slicers, more_btn):
        """Added last so it sits above every other visual of the page."""
        panel = {}
        panel[p.add(button(None, fill=NAVY, fill_transp=72, radius=0, hidden=True), 0, 0, 980, 720)] = "actionButton"
        overlay = list(panel)[0]
        panel[p.add(textbox([para([run("More filters", 15, NAVY, True, "Segoe UI Semibold")]),
                             para([run("Opened with the “More filters” button. "
                                       "Selections apply to all pages.", 9, MUTED)])],
                            vc=dict(vc_plain(bg=WHITE), padding=[props(top=d(18), bottom=d(0), left=d(16), right=d(40))]),
                            hidden=True), 980, 0, 300, 720)] = "textbox"
        close_x = p.add(button("✕", size=13, text_color=NAVY, hidden=True), 1240, 14, 26, 26)
        panel[close_x] = "actionButton"
        y = 92
        for sk in panel_slicers:
            fk, mode, group = SLICER_DEF[sk]
            panel[p.add(slicer(F[fk], mode, sync=group, hidden=True, panel=True, search=sk in SEARCHABLE),
                        996, y, 268, 54)] = "slicer"
            y += 62
        panel[p.add(button("Reset", outline=NAVY, size=10, bold=True, link=link_clear(), hidden=True),
                    996, y + 8, 128, 32)] = "actionButton"
        close_btn = p.add(button("Close", fill=NAVY, text_color=WHITE, size=10, bold=True, hidden=True),
                          1136, y + 8, 128, 32)
        panel[close_btn] = "actionButton"
        bm_open = bookmark(f"{title} – More filters open", p.name, {n: (t, False) for n, t in panel.items()})
        bm_close = bookmark(f"{title} – More filters closed", p.name, {n: (t, True) for n, t in panel.items()})
        bookmarks.extend([bm_open, bm_close])
        # wire the buttons to the bookmarks (rewrite their visualLink)
        set_link(p, more_btn, link_bookmark(bm_open["name"]))
        for n in (overlay, close_x, close_btn):
            set_link(p, n, link_bookmark(bm_close["name"]))

    # ---------------- Page 1: Overview
    p = pages["overview"]
    finish = common(p, "overview", "Overview",
           [("plant", 1), ("part", 1.05), ("test", 1), ("reason", 1.05), ("date", 1.75)], ["press", "kfl"])
    gauge = visual("gauge", {"Y": [F["pass12"]], "TargetValue": [F["target"]]},
                   objects={"axis": [props(min=d(0), max=d(1))],
                            "dataPoint": [props(fill=color(BLUE), target=color(NAVY))],
                            "calloutValue": [props(show=b(True), color=color(BLUE), fontSize=d(24),
                                                   labelPrecision=l(1))],
                            "labels": [props(show=b(True), color=color(MUTED), fontSize=d(9))],
                            "target": [props(show=b(True), color=color(MUTED), fontSize=d(9))]},
                   vc=vc_card("Pass % vs target – last 12 months"))
    p.add(gauge, 210, 126, 253, 244)
    line = visual("lineChart", {"Category": [F["month"]], "Y": [F["insp_pass_pct"].as_("Pass %"), F["target"]]},
                  objects={
                      "categoryAxis": [props(axisType=s("Categorical"), showAxisTitle=b(False), gridlineShow=b(False),
                                             labelColor=color(MUTED), fontSize=d(9))],
                      "valueAxis": [props(showAxisTitle=b(False), gridlineShow=b(True), gridlineStyle=s("dotted"),
                                          gridlineColor=color(CARD_BORDER), labelColor=color(MUTED), end=d(1),
                                          fontSize=d(9))],
                      "legend": [props(show=b(True), position=s("TopLeft"), showTitle=b(False), fontSize=d(9))],
                      "dataPoint": [{"properties": {"fill": color(BLUE)}, "selector": meta(F["insp_pass_pct"].ref)},
                                    {"properties": {"fill": color(NAVY)}, "selector": meta(F["target"].ref)}],
                      "lineStyles": [{"properties": {"showMarker": b(True), "strokeWidth": l(2)},
                                      "selector": meta(F["insp_pass_pct"].ref)},
                                     {"properties": {"lineStyle": s("dashed"), "showMarker": b(False),
                                                     "strokeWidth": l(2)}, "selector": meta(F["target"].ref)}],
                      "labels": [props(show=b(True), color=color(TEXT), fontSize=d(9), labelPrecision=l(0)),
                                 {"properties": {"showSeries": b(False)}, "selector": meta(F["target"].ref)}],
                  },
                  vc=vc_card("Pass % per month"), order=[(F["month"], ASC)])
    p.add(line, 474, 126, 473, 244)
    p.add(donut(IP, "Test PassFail", F["insp"], "Pass & Fail %"), 958, 126, 307, 244)
    decomp = visual("decompositionTreeVisual",
                    {"Analyze": [F["insp_fail"].as_("Fail count")],
                     "ExplainBy": [F["part"].as_("Part"), F["test"], F["reason"]]},
                    vc=vc_card("Where do inspections fail? (click + to drill down)"))
    p.add(decomp, 210, 383, 642, 324)
    t_test = pass_fail_table(F["test"], F["insp_pass_pct"], F["insp_pass"], F["insp_fail"], F["insp_fail_pct"],
                             F["insp_fail"], "Results per test")
    t_part = pass_fail_table(F["part"].as_("Part"), F["insp_pass_pct"], F["insp_pass"], F["insp_fail"],
                             F["insp_fail_pct"], F["insp_fail"], "Results per part", hidden=True)
    n_test = p.add(t_test, 863, 383, 402, 324)
    n_part = p.add(t_part, 863, 383, 402, 324)
    # Part | Test switch: two pairs of buttons, one pair visible at a time
    sw = dict(size=9, radius=6)
    n_part_off = p.add(button("Part", fill="#F1F4F9", text_color=NAVY, **sw), 1164, 391, 46, 22)
    n_test_on = p.add(button("Test", fill=NAVY, text_color=WHITE, bold=True, **sw), 1212, 391, 46, 22)
    n_part_on = p.add(button("Part", fill=NAVY, text_color=WHITE, bold=True, hidden=True, **sw), 1164, 391, 46, 22)
    n_test_off = p.add(button("Test", fill="#F1F4F9", text_color=NAVY, hidden=True, **sw), 1212, 391, 46, 22)
    by_test = bookmark("Overview – Results per test", p.name, {
        n_test: ("tableEx", False), n_part: ("tableEx", True), n_part_off: ("actionButton", False),
        n_test_on: ("actionButton", False), n_part_on: ("actionButton", True), n_test_off: ("actionButton", True)})
    by_part = bookmark("Overview – Results per part", p.name, {
        n_test: ("tableEx", True), n_part: ("tableEx", False), n_part_off: ("actionButton", True),
        n_test_on: ("actionButton", True), n_part_on: ("actionButton", False), n_test_off: ("actionButton", False)})
    bookmarks.extend([by_test, by_part])
    set_link(p, n_part_off, link_bookmark(by_part["name"]))
    set_link(p, n_test_off, link_bookmark(by_test["name"]))
    finish()

    # ---------------- Page 2: Characteristics
    p = pages["chars"]
    finish = common(p, "chars", "Characteristics",
           [("plant", 0.85), ("part", 1.05), ("test", 0.95), ("char", 1.05), ("reason", 1.05), ("date", 1.7)],
           ["kpc", "kfl", "press"])
    p.add(kpi_card(F["c_pass_pct"].as_("Characteristic pass %"), "Characteristic pass %"), 210, 126, 253, 117)
    p.add(kpi_card(F["mv"], "Measured values"), 210, 253, 253, 117)
    line2 = visual("lineChart", {"Category": [F["mday"]],
                                 "Y": [F["c_fail"].as_("Fail"), F["c_pass"].as_("Pass")]},
                   objects={
                       "categoryAxis": [props(showAxisTitle=b(False), gridlineShow=b(False), labelColor=color(MUTED),
                                              fontSize=d(9))],
                       "valueAxis": [props(showAxisTitle=b(False), gridlineShow=b(True), gridlineStyle=s("dotted"),
                                           gridlineColor=color(CARD_BORDER), labelColor=color(MUTED), fontSize=d(9))],
                       "legend": [props(show=b(True), position=s("TopLeft"), showTitle=b(False), fontSize=d(9))],
                       "dataPoint": [{"properties": {"fill": color(ORANGE)}, "selector": meta(F["c_fail"].ref)},
                                     {"properties": {"fill": color(BLUE)}, "selector": meta(F["c_pass"].ref)}],
                       "lineStyles": [props(showMarker=b(True), strokeWidth=l(2))],
                   },
                   vc=vc_card("Measured values per day – Pass & Fail"), order=[(F["mday"], ASC)])
    p.add(line2, 474, 126, 791, 244)
    p.add(stacked_pass_fail(F["q_part"], F["c_fail_bar"], F["c_pass_bar"], F["mv"], "Part – Pass & Fail %"),
          210, 383, 337, 324)
    p.add(stacked_pass_fail(F["q_test"], F["c_fail_bar"], F["c_pass_bar"], F["mv"], "Test – Pass & Fail %"),
          556, 383, 337, 324)
    p.add(pass_fail_table(F["char"], F["c_pass_pct"], F["c_pass"], F["c_fail"], F["c_fail_pct"], F["c_fail_pct"],
                          "Results per characteristic"), 902, 383, 363, 324)
    finish()

    # ---------------- Page 3: Reaction limits
    p = pages["rl"]
    finish = common(p, "rl", "Reaction limits",
           [("plant", 1), ("part", 1.05), ("test", 1), ("char", 1.05), ("date", 1.75)], ["reason", "kfl", "kpc"])
    line3 = visual("lineChart", {"Category": [F["mday"]], "Y": [F["rl"]]},
                   objects={
                       "categoryAxis": [props(showAxisTitle=b(False), gridlineShow=b(False), labelColor=color(MUTED),
                                              fontSize=d(9))],
                       "valueAxis": [props(showAxisTitle=b(False), gridlineShow=b(True), gridlineStyle=s("dotted"),
                                           gridlineColor=color(CARD_BORDER), labelColor=color(MUTED), fontSize=d(9))],
                       "legend": [props(show=b(False))],
                       "dataPoint": [{"properties": {"fill": color(DARK_BLUE)}, "selector": meta(F["rl"].ref)}],
                       "lineStyles": [props(showMarker=b(False), strokeWidth=l(2))],
                   },
                   vc=vc_card("Reaction limit violations per day"), order=[(F["mday"], ASC)])
    p.add(line3, 210, 126, 692, 275)
    top15 = visual("barChart", {"Category": [F["char"]], "Y": [F["rl"]]},
                   objects={
                       "dataPoint": [props(fill=color(DARK_BLUE))],
                       "labels": [props(show=b(True), color=color(TEXT), fontSize=d(9), labelDisplayUnits=d(1),
                                        labelPosition=s("OutsideEnd"))],
                       "valueAxis": [props(show=b(False), gridlineShow=b(False))],
                       "categoryAxis": [props(show=b(True), showAxisTitle=b(False), fontSize=d(9),
                                              labelColor=color(MUTED))],
                       "legend": [props(show=b(False))],
                   },
                   vc=vc_card("Top 15 characteristics"), order=[(F["rl"], DESC)])
    p.add(top15, 914, 126, 351, 581, filters=[topn_filter(F["char"], F["rl"], 15)])
    tree = visual("treemap", {"Group": [F["q_part"]], "Values": [F["rl"]]},
                  objects={
                      "dataPoint": [{"properties": {"fill": {"solid": {"color": {"expr": {"FillRule": {
                          "Input": field_expr(F["rl"], entity=True),
                          "FillRule": {"linearGradient2": {
                              "min": {"color": {"Literal": {"Value": "'#9FB4CB'"}}},
                              "max": {"color": {"Literal": {"Value": "'" + DARK_BLUE + "'"}}},
                              "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
                          "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
                      "labels": [props(show=b(True), color=color(WHITE), fontSize=d(9))],
                      "categoryLabels": [props(show=b(True), color=color(WHITE), fontSize=d(9))],
                      "legend": [props(show=b(False))],
                  },
                  vc=vc_card("Violations by part"), order=[(F["rl"], DESC)])
    p.add(tree, 210, 413, 341, 294)
    p.add(button("Details  ›", fill=WHITE, outline=BLUE, text_color=BLUE, size=9, bold=True,
                 link=link_drill(detail.name)), 470, 420, 72, 22)
    rl_table = visual("tableEx", {"Values": [F["q_test"], F["rl"], F["rl_share"]]},
                      objects=table_objects([colfmt(F["rl"], bar=RL_LIGHT)]),
                      vc=vc_card("Violations by test"), order=[(F["rl"], DESC)])
    p.add(rl_table, 562, 413, 341, 294)
    finish()

    # ---------------- Page 4: Cpk (to be validated)
    p = pages["cpk"]
    finish = common(p, "cpk", "Cpk",
           [("plant", 1), ("partname", 1.05), ("test", 1), ("char", 1.05), ("date", 1.75)],
           ["reason", "cpk_thr", "cpk_pf"], title_w=70)
    p.add(textbox([para([run("To be validated", 9, "#C55A11", True, "Segoe UI Semibold")], "center")],
                  vc=vc_plain(bg="#FFF2CC", radius=12, border_color=LIGHT_ORANGE)), 274, 20, 104, 24)
    p.add(kpi_card(F["cpk_pass_pct"], "Cpk pass %"), 210, 126, 253, 117)
    p.add(donut(Q, "Cpk Pass/Fail", F["cpk_chars"], "Cpk Pass & Fail", "Percent of total"), 210, 252, 253, 196)
    p.add(stacked_pass_fail(F["q_partname"].as_("Part"), F["cpk_fail_bar"], F["cpk_pass_bar"], F["cpk_chars"],
                            "Part – Pass & Fail %"), 474, 126, 388, 322)
    p.add(stacked_pass_fail(F["q_test"], F["cpk_fail_bar"], F["cpk_pass_bar"], F["cpk_chars"],
                            "Test – Pass & Fail %"), 873, 126, 392, 322)
    status_rule = {"properties": {"fontColor": {"solid": {"color": {"expr": field_expr(F["cpk_status_color"],
                                                                                      entity=True)}}}},
                   "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                "metadata": F["cpk_status"].ref}}
    cpk_table = visual("tableEx",
                       {"Values": [F["char"], F["q_partname"].as_("Part"), F["q_test"], F["cpk_val"],
                                   F["cpk_thr_val"], F["mv"], F["cpk_status"]]},
                       objects=table_objects([colfmt(F["mv"], bar=LIGHT_BLUE)], extra_values=[status_rule]),
                       vc=vc_card("Characteristics – Cpk detail"), order=[(F["cpk_val"], ASC)])
    p.add(cpk_table, 210, 460, 1055, 247, filters=[not_blank_filter(col(Q, "Cpk"))])
    finish()

    # ---------------- Drill-through page: Reaction limits - details
    p = detail
    p.add(textbox([para([run("", 10, WHITE)])], vc=vc_plain(bg=NAVY)), 0, 0, 196, 720)
    p.add(textbox([para([run("OP", 22, WHITE, True), run("mobility", 22, WHITE)])]), 14, 16, 178, 40)
    p.add(textbox([para([run("Quality Dashboard", 11, WHITE, True)]),
                   para([run("Plant Visual Management", 10, NAV_SUB)])]), 14, 60, 178, 44)
    for i, (k, label) in enumerate(NAV_ITEMS):
        active = (k == "rl")
        p.add(button(label, fill=NAV_ACTIVE if active else None, text_color=NAVY if active else WHITE, size=11,
                     bold=active, align="left", link=link_page(names[k]), hover_fill=None if active else WHITE),
              14, 126 + i * 41, 168, 34)
    p.add(textbox([para([run("Reaction limit violations – details", 20, NAVY, True, "Segoe UI Semibold")])]),
          204, 10, 700, 44)
    p.add(button("‹  Back", fill=WHITE, outline=NAVY, size=10, bold=True, link=link_back(), radius=10),
          1165, 18, 100, 30)
    detail_table = visual("tableEx",
                          {"Values": [col(Q, "Date", "Date"), col(Q, "Inspection Number", "Inspection"),
                                      F["q_part"], F["q_test"], F["char"], col(Q, "Measured Value", "Value"),
                                      col(Q, "LSL", "LSL"), col(Q, "LCL", "LCL (reaction)"),
                                      col(Q, "UCL", "UCL (reaction)"), col(Q, "USL", "USL")]},
                          objects=table_objects([]),
                          vc=vc_card("Violations for the selected part (measured value inside the specification "
                                     "but outside the reaction limits)"),
                          order=[(col(Q, "Date"), DESC)])
    p.add(detail_table, 210, 64, 1055, 643)
    p.filters = [
        {"name": "Filter" + hexid(), "expression": field_expr(F["q_part"], entity=True), "type": "Categorical",
         "howCreated": 5, "isHiddenInViewMode": False},
        dict(in_filter(col(Q, "Is Reaction Limit Violation"), [1]), isHiddenInViewMode=True),
    ]

    return [pages[k] for k, _ in NAV_ITEMS] + [detail]


def set_link(page, visual_name, link):
    for c in page.containers:
        cfg = json.loads(c["config"])
        if cfg["name"] == visual_name:
            cfg["singleVisual"].setdefault("vcObjects", {})["visualLink"] = link
            c["config"] = json.dumps(cfg, ensure_ascii=False)
            return
    raise KeyError(visual_name)


def topn_filter(f, by, n):
    return {"name": "Filter" + hexid(), "expression": field_expr(f, entity=True),
            "filter": {"Version": 2,
                       "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": {
                           "Version": 2, "From": [{"Name": "q", "Entity": f.entity, "Type": 0}],
                           "Select": [dict(field_expr(f, "q"), Name="field")],
                           "OrderBy": [{"Direction": DESC, "Expression": field_expr(by, "q")}],
                           "Top": n}}}, "Type": 2},
                                {"Name": "q", "Entity": f.entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [field_expr(f, "q")],
                                                       "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
            "type": "TopN", "howCreated": 1, "isHiddenInViewMode": False}


def not_blank_filter(f):
    return {"name": "Filter" + hexid(), "expression": field_expr(f, entity=True),
            "filter": {"Version": 2, "From": [{"Name": "q", "Entity": f.entity, "Type": 0}],
                       "Where": [{"Condition": {"Not": {"Expression": {"Comparison": {
                           "ComparisonKind": 0, "Left": field_expr(f, "q"), "Right": {"Literal": {"Value": "null"}}}}}}}]},
            "type": "Advanced", "howCreated": 1, "isHiddenInViewMode": False}


def in_filter(f, values):
    def litv(v):
        return {"Literal": {"Value": f"{v}L" if isinstance(v, int) else "'" + v + "'"}}
    return {"name": "Filter" + hexid(), "expression": field_expr(f, entity=True),
            "filter": {"Version": 2, "From": [{"Name": "q", "Entity": f.entity, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [field_expr(f, "q")],
                                                       "Values": [[litv(v)] for v in values]}}}]},
            "type": "Categorical", "howCreated": 1, "isHiddenInViewMode": False}


# --------------------------------------------------------------------------- main
def main(src, dst):
    zin = zipfile.ZipFile(src)
    layout = json.loads(zin.read("Report/Layout").decode("utf-16-le"))

    bookmarks = []
    new_pages = build({}, bookmarks)
    sections = [pg.section(i) for i, pg in enumerate(new_pages)]

    # keep the previous pages, hidden, at the end
    for i, old in enumerate(sorted(layout["sections"], key=lambda x: x.get("ordinal", 0))):
        old = dict(old)
        old["displayName"] = "OLD – " + old["displayName"].strip()
        old["ordinal"] = len(sections)
        cfg = json.loads(old.get("config") or "{}")
        cfg["visibility"] = 1
        old["config"] = json.dumps(cfg, ensure_ascii=False)
        old.pop("id", None)
        sections.append(old)
    layout["sections"] = sections

    cfg = json.loads(layout["config"])
    cfg["activeSectionIndex"] = 0
    cfg["bookmarks"] = bookmarks
    layout["config"] = json.dumps(cfg, ensure_ascii=False)

    new_layout = json.dumps(layout, ensure_ascii=False).encode("utf-16-le")

    with zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            if info.filename == "SecurityBindings":
                continue  # must be dropped when the report is edited outside Power BI Desktop
            data = zin.read(info.filename)
            if info.filename == "Report/Layout":
                data = new_layout
            elif info.filename == "[Content_Types].xml":
                text = data.decode("utf-8-sig")
                text = text.replace('<Override PartName="/SecurityBindings" ContentType="" />', "")
                data = ("﻿" + text).encode("utf-8")
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    print(f"written {dst}: {len(new_pages)} new pages, {len(sections) - len(new_pages)} old pages kept hidden, "
          f"{len(bookmarks)} bookmarks")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
