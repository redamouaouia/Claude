"""Design A of the report on the OPmobility templates ("Rail marine"): geometry and page-background artwork.

- Navy rail on the left (150 px): white logo, Home link, page buttons (the active page in a white pill), Clear
  filters, the last refresh at the bottom.
- White page. Header: title and question, the period filter (light), the concentric arcs of the templates at the top
  right, a hairline. Filters in grey boxes with their name inside, then More filters.
- Content: the cards of design.PAGES, moved to the new content area (map_rect); white with a thin border.
- Home: the pages on the left (white), key figures on a navy panel with the arcs (template cover).
Colours of the templates: navy #0E3472, light grey #F4F6F8. Data colours are unchanged (Pass blue, Fail orange).
Titles in Outfit (geometric, close to the logo), text in Inter: page backgrounds only; visuals keep Segoe UI.
"""
import html
import math

import design as D

W, H = D.W, D.H
NAVY, GREY, LINE = "#0E3472", "#F4F6F8", "#E3E8EF"
TEXT, MUTED, MUTED2, BLUE, ORANGE = "#1B2A41", "#5A6B85", "#8794A8", "#2F6EBA", "#ED7D31"

# --------------------------------------------------------------------------- geometry (Power BI px)
RAIL = 150
X0, X1 = 178, 1252
HEAD_H = 66
FILTER_Y, FILTER_H = 78, 42
SLICER_TOP = 15  # the slicer visual sits under the name written in its box
CONTENT_Y0, CONTENT_Y1 = 134, 706
PERIOD = (746, 17, 240, 32)
NAV = {key: (12, 104 + i * 44, RAIL - 24, 36) for i, (_, key) in enumerate(D.NAV)}
HOME_LINK = (12, 18, RAIL - 24, 74)  # logo and "‹ Home"
CLEAR = (12, 604, RAIL - 24, 36)
REFRESH = (14, 652, RAIL - 28, 46)
DATE_W, MORE_W = 236, 118
CONTEXT = (X0, FILTER_Y, X1 - X0 - MORE_W - 10, FILTER_H)  # details page: the part chosen with "Details"
BACK = (X1 - MORE_W, FILTER_Y, MORE_W, FILTER_H)

# Home page
HOME_SPLIT = 790
HOME_TILES = {key: (64, 276 + i * 76, 660, 64) for i, (_, key) in enumerate(D.NAV)}
HOME_FACT_X, HOME_FACT_W = 838, 120  # value column of the key figures (centred), labels after it
HOME_FACT_Y = {key: 466 + i * 46 for i, (key, _) in enumerate(D.HOME_FACTS)}
HOME_REFRESH = (838, 662, 330, 30)


def map_rect(x, y, w, h):
    """A rectangle of the content area of design.py (V12) in the content area of design A."""
    sx = (X1 - X0) / (D.X1 - D.X0)
    sy = (CONTENT_Y1 - CONTENT_Y0) / (D.H - 16 - D.ROW2_Y)
    return (round(X0 + (x - D.X0) * sx, 1), round(CONTENT_Y0 + (y - D.ROW2_Y) * sy, 1), round(w * sx, 1),
            round(h * sy, 1))


def slicer_slots(page):
    """x/width of each slicer, then of "More filters" (or of Back on the details page)."""
    items = D.PAGES[page]["slicers"]
    if not items:
        return [(X1 - MORE_W, MORE_W)]
    gap = 10
    free = X1 - X0 - gap * len(items) - DATE_W - MORE_W
    flex = sum(w for name, _, w in items if name not in ("Date", "Month"))
    out, x = [], X0
    for name, _, w in items:
        width = DATE_W if name in ("Date", "Month") else round(free * w / flex, 1)
        out.append((round(x, 1), width))
        x += width + gap
    out.append((round(x, 1), MORE_W))
    return out


def slicer_rect(x, w):
    """The slicer visual inside its box (under the name)."""
    return (x + 4, FILTER_Y + SLICER_TOP, w - 8, FILTER_H - SLICER_TOP - 2)


# --------------------------------------------------------------------------- artwork
def arcs(cx, cy, radii, a0, a1, color, opacity=0.35, dots=True, width=1.1):
    """Concentric arcs of the templates (degrees, 0 = right, counter-clockwise), with small dots."""
    out = []
    for i, r in enumerate(radii):
        x0, y0 = cx + r * math.cos(math.radians(a0)), cy - r * math.sin(math.radians(a0))
        x1, y1 = cx + r * math.cos(math.radians(a1)), cy - r * math.sin(math.radians(a1))
        op = opacity * (0.55 + 0.45 * (i % 3) / 2)
        out.append(f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 {1 if abs(a1 - a0) > 180 else 0} 0 {x1:.1f} {y1:.1f}" '
                   f'fill="none" stroke="{color}" stroke-opacity="{op:.2f}" stroke-width="{width}"/>')
        if dots:
            a = math.radians(a0 + (a1 - a0) * (0.25 + 0.5 * ((i * 37) % 10) / 10))
            out.append(f'<circle cx="{cx + r * math.cos(a):.1f}" cy="{cy - r * math.sin(a):.1f}" r="2.2" '
                       f'fill="{color}" fill-opacity="{min(1, op * 1.6):.2f}"/>')
    return "".join(out)


def logo(name, left, top, width):
    path = D.BRAND / name
    if not path.exists():
        return ""
    return f'<img src="{D._data_uri(path)}" style="position:absolute;left:{left}px;top:{top}px;width:{width}px">'


FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700'
         '&family=Inter:wght@400;500;600&display=swap">')
CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
body {{ position: relative; font-family: Inter, "Segoe UI", sans-serif; color: {TEXT}; background: #fff; }}
.abs {{ position: absolute; }}
.rail {{ position: absolute; left: 0; top: 0; width: {RAIL}px; height: {H}px; background: {NAVY}; }}
.nav {{ position: absolute; display: flex; align-items: center; gap: 10px; padding-left: 12px; border-radius: 10px;
        font-size: 11.5px; color: rgba(255,255,255,.80); }}
.nav.on {{ background: #fff; color: {NAVY}; font-weight: 600; }}
.home {{ position: absolute; left: 24px; top: 70px; font-size: 10.5px; color: rgba(255,255,255,.62); }}
.rule {{ position: absolute; left: 24px; width: {RAIL - 48}px; height: 1px; background: rgba(255,255,255,.14); }}
.t1 {{ position: absolute; left: {X0}px; top: 15px; font: 600 25px/1.1 Outfit, "Segoe UI", sans-serif; color: {NAVY};
       letter-spacing: -.01em; }}
.q {{ position: absolute; left: {X0 + 2}px; top: 45px; font-size: 11.5px; color: {MUTED}; }}
.hair {{ position: absolute; left: {RAIL}px; top: {HEAD_H}px; width: {W - RAIL}px; height: 1px; background: #EDF0F4; }}
.track {{ position: absolute; border-radius: 16px; background: {GREY}; box-shadow: inset 0 0 0 1px {LINE}; }}
.box {{ position: absolute; border-radius: 8px; background: {GREY}; }}
.box b {{ position: absolute; left: 10px; top: 6px; font-size: 7.8px; font-weight: 600; letter-spacing: .1em;
          text-transform: uppercase; color: {MUTED2}; white-space: nowrap; }}
.plate {{ position: absolute; border-radius: 12px; background: #fff; box-shadow: inset 0 0 0 1px {LINE},
          0 1px 2px rgba(14,52,114,.04); }}
"""


def page_html(page):
    spec = D.PAGES[page]
    active = spec.get("nav", page)
    nav = "".join(
        f'<div class="nav{" on" if key == active else ""}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
        f'{D.icon(key, 16, NAVY if key == active else "rgba(255,255,255,.80)")}<span>{html.escape(label)}</span></div>'
        for label, key in D.NAV for x, y, w, h in [NAV[key]])
    cx, cy, cw, ch = CLEAR
    rail = (f'<div class="rail"></div>{logo("logo_white.png", 24, 24, 102)}<div class="home">‹ Home</div>{nav}'
            f'<div class="rule" style="top:{cy - 10}px"></div>'
            f'<div class="nav" style="left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px">'
            f'{D.icon("clear", 15, "rgba(255,255,255,.70)")}<span>Clear filters</span></div>'
            f'<div class="rule" style="top:{REFRESH[1] - 6}px"></div>')
    header = (f'<svg class="abs" style="left:{RAIL}px;top:0" width="{W - RAIL}" height="{HEAD_H}">'
              f'{arcs(W - RAIL - 70, HEAD_H, [24, 38, 52, 66, 80, 94, 108], 0, 180, "#9AA8C0", .55, True, .9)}</svg>'
              f'<div class="t1">{html.escape(spec["title"])}</div><div class="q">{html.escape(spec["question"])}</div>'
              f'<div class="hair"></div>')
    if page in D.PERIOD_PAGES:
        px, py, pw, ph = PERIOD
        header += f'<div class="track" style="left:{px}px;top:{py}px;width:{pw}px;height:{ph}px"></div>'
    boxes = ""
    if spec["slicers"]:
        for (x, w), (_, label, _) in zip(slicer_slots(page), spec["slicers"]):
            boxes += (f'<div class="box" style="left:{x}px;top:{FILTER_Y}px;width:{w}px;height:{FILTER_H}px">'
                      f'<b>{html.escape(label)}</b></div>')
    if spec.get("context"):
        x, y, w, h = CONTEXT
        boxes += (f'<div class="box" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                  f'<b>{html.escape(spec["context"])}</b></div>')
    plates = "".join(f'<div class="plate" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
                     for x, y, w, h in (map_rect(*r) for r in spec["cards"].values()))
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>'
            f'{header}{boxes}{plates}{rail}</body></html>')


HOME_CSS = f"""
.kick {{ position: absolute; font: 600 10px Inter, sans-serif; letter-spacing: .22em; color: {BLUE};
         text-transform: uppercase; }}
.h {{ position: absolute; font: 700 36px/1.08 Outfit, sans-serif; color: {NAVY}; letter-spacing: -.01em; }}
.lead {{ position: absolute; font-size: 12px; color: {MUTED}; }}
.tile {{ position: absolute; border-radius: 12px; display: flex; align-items: center; gap: 16px; padding: 0 18px;
         background: #fff; box-shadow: inset 0 0 0 1px {LINE}; }}
.tile .ic {{ width: 38px; height: 38px; border-radius: 10px; background: {NAVY}; display: grid; place-items: center;
             flex: none; }}
.tile b {{ display: block; font: 600 14px Outfit, sans-serif; color: {NAVY}; }}
.tile span {{ display: block; font-size: 10.5px; color: {MUTED}; margin-top: 3px; }}
.tile em {{ margin-left: auto; font-style: normal; font-size: 20px; color: {NAVY}; }}
.panel {{ position: absolute; left: {HOME_SPLIT}px; top: 0; width: {W - HOME_SPLIT}px; height: {H}px; background: {NAVY}; }}
.fact {{ position: absolute; left: {HOME_FACT_X}px; height: 32px; display: flex; align-items: center;
         font-size: 11px; color: rgba(255,255,255,.78); }}
.fact b {{ width: {HOME_FACT_W}px; text-align: center; font: 600 21px "Segoe UI Semibold", Outfit, sans-serif; color: #fff; }}
.fact span {{ position: absolute; left: {HOME_FACT_W + 14}px; white-space: nowrap; }}
.pill {{ position: absolute; border-radius: 15px; background: rgba(255,255,255,.10);
         box-shadow: inset 0 0 0 1px rgba(255,255,255,.2); display: flex; align-items: center; padding-left: 10px; }}
.guide {{ position: absolute; font-size: 9.5px; color: {MUTED}; line-height: 1.7; }}
.guide i {{ display: inline-block; width: 16px; height: 7px; border-radius: 4px; margin: 0 6px 0 0; vertical-align: 0; }}
"""
FACTS = {"plants": ("", "plants"), "months": ("12 months", "rolling history"), "values": ("", "measured values"),
         "daily": ("Daily", "refresh from Databricks")}


def home_html():
    title = D.REPORT_TITLE
    words = title.split(" ")
    lines = (" ".join(words[:-1]), words[-1]) if len(words) > 1 else (title,)
    tiles = "".join(
        f'<div class="tile" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
        f'<div class="ic">{D.icon(key, 18, "#FFFFFF")}</div><div><b>{html.escape(label)}</b>'
        f'<span>{html.escape(D.HOME_PAGES[key][0])}</span></div><em>›</em></div>'
        for label, key in D.NAV for x, y, w, h in [HOME_TILES[key]])
    facts = "".join(f'<div class="fact" style="top:{HOME_FACT_Y[key]}px"><b>{FACTS[key][0]}</b>'
                    f'<span>{FACTS[key][1]}</span></div>' for key, _ in D.HOME_FACTS)
    rx, ry, rw, rh = HOME_REFRESH
    body = (f'{logo("logo_navy.png", 64, 42, 150)}<div class="kick" style="left:64px;top:112px">Quality</div>'
            f'<div class="h" style="left:62px;top:132px">{"<br>".join(html.escape(x) for x in lines)}</div>'
            f'<div class="lead" style="left:64px;top:226px">The daily review of quality results in series production, '
            f'for every plant. Choose a page:</div>{tiles}'
            f'<div class="guide" style="left:64px;top:662px"><i style="background:{BLUE}"></i>Pass &nbsp; '
            f'<i style="background:{ORANGE}"></i>Fail &nbsp; <i style="background:#1F4E79"></i>Reaction limits '
            f'&nbsp;·&nbsp; Cpk = min(USL − mean, mean − LSL) / 3σ &nbsp;·&nbsp; filters follow you from page to page</div>'
            f'<div class="panel"><svg width="{W - HOME_SPLIT}" height="{H}">'
            f'{arcs(0, 430, [150, 190, 228, 262, 300, 334, 372, 410, 448], 0, 90, "#FFFFFF", .32)}</svg></div>'
            f'{logo("logo_white.png", 1094, 46, 130)}{facts}'
            f'<div class="pill" style="left:{rx}px;top:{ry}px;width:{rw}px;height:{rh}px">'
            f'{D.icon("clock", 13, "rgba(255,255,255,.72)", 1.7)}</div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}{HOME_CSS}</style></head><body>'
            f'{body}</body></html>')


def render_html(page):
    return home_html() if page == "home" else page_html(page)
