"""Design "Relief" of the report (chosen among the premium concepts): geometry and page-background artwork.

An evolution of design A with depth, in the spirit of Apple's interfaces:
- continuous corners (CSS corner-shape: squircle) on every card, box and button drawn in the background;
- floating navy rail with highlights and shadow, the active page as a raised white button;
- raised white cards (layered shadows, light from the top), filter boxes and the period track as inset wells;
- 3D icons on the key figures of Overview, the failure tile as a raised navy card;
- home page: raised page tiles, navy dock with isometric 3D columns, key figures as chips.
Visuals keep the Power BI rendering (Segoe UI, flat charts) on top of the artwork. Geometry is that of design A
(design_a.py), moved into the Relief content area by map_rect.
"""
import html
import math

import design as D
import design_a as DA

W, H = D.W, D.H
NAVY, BLUE, ORANGE = "#0E3472", "#2F6EBA", "#ED7D31"
TEXT, MUTED, MUTED2 = "#1B2A41", "#5A6B85", "#7A889C"
WELL = "#E6EBF2"  # colour of the inset wells (filter boxes, period track)
CANVAS = "#E9EEF4"

# --------------------------------------------------------------------------- geometry (Power BI px)
RAIL_BOX = (14, 14, 152, 692)  # floating navy rail
X0, X1 = 186, 1264
CONTENT_Y0, CONTENT_Y1 = 142, 706
FILTER_Y, FILTER_H = 84, 44
SLICER_TOP = 16  # the slicer visual sits under the name written in its well
PERIOD = (964, 22, 300, 36)  # inset track; the button slicer inside, 3 px in
NAV = {key: (26, 118 + i * 46, 128, 38) for i, (_, key) in enumerate(D.NAV)}
HOME_LINK = (26, 28, 128, 74)  # logo and "‹ Home"
CLEAR = (26, 590, 128, 38)
REFRESH_BOX = (26, 640, 128, 52)
REFRESH = (48, 643, 102, 46)  # the refresh card, right of the clock icon
DATE_W, MORE_W = 240, 128
CONTEXT = (X0, FILTER_Y, X1 - X0 - MORE_W - 10, FILTER_H)  # details page: the part chosen with "Details"
BACK = (X1 - MORE_W, FILTER_Y, MORE_W, FILTER_H)  # details page: back to Reaction limits
BACK_LINK = (X0, 21, 108, 32)  # "‹ Overview", raised, before the title of Failure breakdown

# Home page
DOCK = (728, 24, 528, 672)
HOME_TILES = {key: (64, 238 + i * 84, 640, 76) for i, (_, key) in enumerate(D.NAV)}
THUMB = (132, 60)  # page preview in each home tile
CHIP_W, CHIP_H = 221, 64
CHIPS = {key: (764 + (i % 2) * (CHIP_W + 14), 476 + (i // 2) * 76, CHIP_W, CHIP_H)
         for i, (key, _) in enumerate(D.HOME_FACTS)}
HOME_REFRESH = (764, 638, 456, 32)


def map_rect(x, y, w, h):
    """A rectangle of the content area of design A in the content area of Relief."""
    sx = (X1 - X0) / (DA.X1 - DA.X0)
    sy = (CONTENT_Y1 - CONTENT_Y0) / (DA.CONTENT_Y1 - DA.CONTENT_Y0)
    return (round(X0 + (x - DA.X0) * sx, 1), round(CONTENT_Y0 + (y - DA.CONTENT_Y0) * sy, 1), round(w * sx, 1),
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
    """The slicer visual inside its well (under the name)."""
    return (x + 5, FILTER_Y + SLICER_TOP, w - 10, FILTER_H - SLICER_TOP - 3)


def cards(page):
    """The white cards of a page, in Relief geometry."""
    spec = D.PAGES[page]
    out = [map_rect(*DA.map_rect(*r)) for k, r in spec["cards"].items() if not (page == "overview" and k == "decomp")]
    if page == "overview":
        out += [map_rect(*DA.KPI[k]) for k, _, _ in DA.KPIS]
    return out


# Overview: the Part / Test switch of "Results per part" (two textboxes in design A, at the right of the table title)
TOGGLES_A = (1145.7, 427.3, 2 * 49.3 + 2, 25.1)
TOGGLE_TRACK = tuple(round(v, 1) for v in (lambda r: (r[0] - 3, r[1] - 3, r[2] + 6, r[3] + 6))(map_rect(*TOGGLES_A)))


# --------------------------------------------------------------------------- artwork
def arcs(cx, cy, radii, a0, a1, color, opacity=0.35, width=1.0, dots=True):
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


def iso_columns(cx, cy, unit=33):
    """Isometric 3D columns on a plate (decoration): passes in blue, one failure in orange."""
    cos, sin = math.cos(math.radians(30)), math.sin(math.radians(30))

    def pt(x, y, z):
        return cx + (x - y) * unit * cos, cy + (x + y) * unit * sin - z * unit

    def poly(pts, fill, extra=""):
        return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{fill}" {extra}/>'
    out = [poly([pt(-0.6, -0.6, 0), pt(6.6, -0.6, 0), pt(6.6, 2.6, 0), pt(-0.6, 2.6, 0)], "rgba(255,255,255,.07)",
                'stroke="rgba(255,255,255,.22)" stroke-width="1"')]
    columns = [(0, 0, 2.2), (1.4, 0, 3.1), (2.8, 0, 2.6), (4.2, 0, 3.6), (5.6, 0, 3.0),
               (0, 1.4, 1.6), (1.4, 1.4, 2.3), (2.8, 1.4, 1.1), (4.2, 1.4, 2.7), (5.6, 1.4, 2.0)]
    for x, y, h in sorted(columns, key=lambda c: c[0] + c[1]):
        top, left, right = ("#FFC08A", "#F08A3E", "#C9601C") if (x, y) == (2.8, 1.4) else ("#9CC8FF", "#3F7FD3", "#22549E")
        s = 0.9
        out.append(poly([pt(x, y + s, 0), pt(x + s, y + s, 0), pt(x + s, y + s, h), pt(x, y + s, h)], left))
        out.append(poly([pt(x + s, y, 0), pt(x + s, y + s, 0), pt(x + s, y + s, h), pt(x + s, y, h)], right))
        out.append(poly([pt(x, y, h), pt(x + s, y, h), pt(x + s, y + s, h), pt(x, y + s, h)], top))
    return "".join(out)


def logo(name, left, top, width):
    path = D.BRAND / name
    if not path.exists():
        return ""
    return f'<img src="{D._data_uri(path)}" style="position:absolute;left:{left}px;top:{top}px;width:{width}px">'


def pebble(kind, key, size=34, glyph=17):
    """3D icon: rounded square with a gradient, a highlight and a coloured shadow."""
    return (f'<div class="pebble {kind}" style="width:{size}px;height:{size}px"><i></i>'
            f'{D.icon(key, glyph, "#FFFFFF", 1.8)}</div>')


def chevron(color, size=10):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 10 10"><path d="M2.5 3.8 5 6.3l2.5-2.5" fill="none" '
            f'stroke="{color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700'
         '&family=Inter:wght@400;500;600&display=swap">')
CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
body {{ position: relative; font-family: Inter, "Segoe UI", sans-serif; color: {TEXT}; background: {CANVAS};
        -webkit-font-smoothing: antialiased; }}
.bg {{ position: absolute; inset: 0; background: radial-gradient(900px 620px at 34% -14%, #FFFFFF 0%,
       rgba(255,255,255,0) 64%), linear-gradient(180deg, #EEF2F7 0%, #E2E8F0 100%); }}
.abs {{ position: absolute; }}
.rail, .card, .well, .raised, .nav, .pebble, .refresh, .tile, .chip, .dock, .go {{ corner-shape: squircle; }}
.rail {{ position: absolute; border-radius: 30px;
  background: linear-gradient(180deg, #1C4E98 0%, #0E3472 52%, #0A2756 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.20), inset 0 -2px 0 rgba(0,0,0,.18), 0 26px 50px -22px rgba(10,39,86,.70),
  0 4px 12px rgba(10,39,86,.22); }}
.home {{ position: absolute; font-size: 10.5px; color: rgba(255,255,255,.62); }}
.nav {{ position: absolute; display: flex; align-items: center; gap: 10px; padding-left: 13px; border-radius: 15px;
        font-size: 11.5px; font-weight: 500; color: rgba(255,255,255,.80); }}
.nav.on {{ background: linear-gradient(180deg, #FFFFFF 0%, #EAF0F8 100%); color: {NAVY}; font-weight: 600;
  box-shadow: 0 8px 16px -6px rgba(0,0,0,.45), inset 0 -1px 0 rgba(14,52,114,.10), inset 0 1px 0 #fff; }}
.refresh {{ position: absolute; border-radius: 15px; padding-left: 11px; display: flex; align-items: center;
  background: rgba(0,0,0,.16); box-shadow: inset 0 1px 3px rgba(0,0,0,.25), inset 0 -1px 0 rgba(255,255,255,.08); }}
.t1 {{ position: absolute; top: 20px; font: 600 27px/1.1 Outfit, "Segoe UI", sans-serif; color: {NAVY};
       letter-spacing: -.015em; }}
.q {{ position: absolute; top: 56px; font-size: 11.5px; color: #4D5F7C; }}
.well {{ position: absolute; border-radius: 15px; background: {WELL};
  box-shadow: inset 0 2px 5px rgba(16,40,80,.13), inset 0 -1px 0 rgba(255,255,255,.95); }}
.well b {{ position: absolute; left: 13px; top: 7px; font-size: 7.6px; font-weight: 600; letter-spacing: .11em;
           text-transform: uppercase; color: {MUTED2}; white-space: nowrap; }}
.raised {{ position: absolute; border-radius: 15px; display: flex; align-items: center; justify-content: center; gap: 7px;
  background: linear-gradient(180deg, #FFFFFF, #F3F6FA); color: {NAVY}; font: 600 10.5px Inter, sans-serif;
  box-shadow: 0 0 0 1px rgba(16,40,80,.06), 0 6px 14px -6px rgba(16,40,80,.32), inset 0 1px 0 #fff; }}
.raised i {{ font-style: normal; font-size: 9px; width: 17px; height: 17px; border-radius: 50%; display: grid;
             place-items: center; background: {NAVY}; color: #fff; }}
.card {{ position: absolute; border-radius: 28px; background: linear-gradient(180deg, #FFFFFF 0%, #FAFBFD 100%);
  box-shadow: inset 0 1px 0 #FFFFFF, 0 0 0 1px rgba(16,40,80,.05), 0 1px 2px rgba(16,40,80,.06),
  0 10px 22px -8px rgba(16,40,80,.16), 0 28px 52px -26px rgba(16,40,80,.28); }}
.kpi {{ position: absolute; display: flex; align-items: center; gap: 11px; font-size: 9.5px; font-weight: 600;
        letter-spacing: .09em; text-transform: uppercase; color: {NAVY}; }}
.pebble {{ position: relative; flex: none; border-radius: 12px; display: grid; place-items: center; overflow: hidden; }}
.pebble svg {{ position: relative; }}
.pebble i {{ position: absolute; inset: 0; background: radial-gradient(circle at 30% 18%, rgba(255,255,255,.55),
             rgba(255,255,255,0) 58%); }}
.pebble.navy {{ background: linear-gradient(160deg, #3F7BD0 0%, #0E3472 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), inset 0 -3px 6px rgba(0,0,0,.25), 0 9px 16px -7px rgba(14,52,114,.85); }}
.pebble.orange {{ background: linear-gradient(160deg, #FFAE66 0%, #E2651B 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.55), inset 0 -3px 6px rgba(150,50,0,.25), 0 9px 16px -7px rgba(226,101,27,.85); }}
.pebble.amber {{ background: linear-gradient(160deg, #FFCC6A 0%, #EC8810 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6), inset 0 -3px 6px rgba(150,80,0,.22), 0 9px 16px -7px rgba(236,136,16,.85); }}
.pebble.glass {{ background: linear-gradient(160deg, rgba(255,255,255,.28), rgba(255,255,255,.08));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), inset 0 0 0 1px rgba(255,255,255,.18), 0 10px 18px -8px rgba(0,0,0,.45); }}
.cta {{ position: absolute; border-radius: 28px; corner-shape: squircle; overflow: hidden; color: #fff;
  background: linear-gradient(180deg, rgba(255,255,255,.10) 0%, rgba(255,255,255,0) 42%),
  linear-gradient(120deg, #0E3472 0%, #1A4C96 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.28), inset 0 -2px 0 rgba(0,0,0,.18), 0 22px 40px -20px rgba(14,52,114,.75),
  0 3px 8px rgba(14,52,114,.2); }}
.cta-in {{ position: absolute; inset: 0; display: flex; align-items: center; gap: 18px; padding: 0 26px; }}
.cta b {{ display: block; font: 600 16px Outfit, sans-serif; }}
.cta span {{ display: block; max-width: 400px; margin-top: 5px; font-size: 10.5px; line-height: 1.45;
             color: rgba(255,255,255,.78); }}
.cta em {{ margin-left: auto; font: 600 11px Inter, sans-serif; font-style: normal; padding: 10px 18px; border-radius: 17px;
  white-space: nowrap; color: {NAVY}; background: linear-gradient(180deg, #FFFFFF, #E9EEF6);
  box-shadow: 0 8px 16px -6px rgba(0,0,0,.5), inset 0 1px 0 #fff, inset 0 -1px 0 rgba(14,52,114,.12); }}
"""


def rail_html(active):
    x, y, w, h = RAIL_BOX
    out = (f'<div class="rail" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
           f'{logo("logo_white.png", 34, 38, 108)}<div class="home" style="left:36px;top:84px">‹ Home</div>')
    for label, key in D.NAV:
        nx, ny, nw, nh = NAV[key]
        on = key == active
        out += (f'<div class="nav{" on" if on else ""}" style="left:{nx}px;top:{ny}px;width:{nw}px;height:{nh}px">'
                f'{D.icon(key, 16, NAVY if on else "rgba(255,255,255,.82)")}<span>{html.escape(label)}</span></div>')
    cx, cy, cw, ch = CLEAR
    rx, ry, rw, rh = REFRESH_BOX
    return out + (f'<div class="nav" style="left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px">'
                  f'{D.icon("clear", 15, "rgba(255,255,255,.75)")}<span>Clear filters</span></div>'
                  f'<div class="refresh" style="left:{rx}px;top:{ry}px;width:{rw}px;height:{rh}px">'
                  f'{D.icon("clock", 12, "rgba(255,255,255,.62)", 1.8)}</div>')


def overview_artwork():
    """Icons and names of the key figures, the failure tile, the track of the Part / Test switch."""
    out = ""
    for key, icon_name, label in DA.KPIS:
        x, y, w, h = map_rect(*DA.KPI[key])
        kind = {"failed": "navy", "rate": "orange", "gap": "amber"}[key]
        out += (f'<div class="kpi" style="left:{x + 18}px;top:{y + 13}px">{pebble(kind, icon_name, 30, 15)}'
                f'<span>{html.escape(label)}</span></div>')
    x, y, w, h = map_rect(*DA.FAILS_TILE)
    out += (f'<div class="cta" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
            f'<svg class="abs" style="left:0;top:0" width="{w}" height="{h}">'
            f'{arcs(w - 40, h + 30, [60, 84, 108, 132, 156, 180], 0, 180, "#FFFFFF", .5, 1)}</svg>'
            f'<div class="cta-in">{pebble("glass", "tree", 48, 24)}<div><b>Where do inspections fail?</b>'
            f'<span>Failed inspections by part › test › inspection reason, on a page of their own with the filters of '
            f'Overview.</span></div><em>Open the breakdown&nbsp; ›</em></div></div>')
    tx, ty, tw, th = TOGGLE_TRACK
    out += (f'<div class="well" style="left:{tx}px;top:{ty}px;width:{tw}px;height:{th}px;border-radius:11px;'
            f'box-shadow:inset 0 1px 3px rgba(16,40,80,.14), inset 0 -1px 0 rgba(255,255,255,.95)"></div>')
    return out


def page_html(page):
    spec = D.PAGES[page]
    deco = (f'<svg class="abs" style="left:0;top:0" width="{W}" height="{H}">'
            f'{arcs(1210, -30, [70, 96, 122, 148, 174], 190, 300, "#9AA8C0", .5, 1)}</svg>')
    header = ""
    title_x = X0
    if spec.get("back"):  # page opened from another page: "‹ <page>" before the title
        bx, by, bw, bh = BACK_LINK
        back = dict((k, label) for label, k in D.NAV)[spec["back"]]
        header += (f'<div class="raised" style="left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px">'
                   f'‹&nbsp; {html.escape(back)}</div>')
        title_x = bx + bw + 14
    header += (f'<div class="t1" style="left:{title_x}px">{html.escape(spec["title"])}</div>'
               f'<div class="q" style="left:{title_x + 2}px">{html.escape(spec["question"])}</div>')
    if page in D.PERIOD_PAGES:
        px, py, pw, ph = PERIOD
        header += f'<div class="well" style="left:{px}px;top:{py}px;width:{pw}px;height:{ph}px"></div>'
    boxes = ""
    if spec["slicers"]:
        slots = slicer_slots(page)
        for (x, w), (_, label, _) in zip(slots, spec["slicers"]):
            boxes += (f'<div class="well" style="left:{x}px;top:{FILTER_Y}px;width:{w}px;height:{FILTER_H}px">'
                      f'<b>{html.escape(label)}</b></div>')
        mx, mw = slots[-1]
        boxes += (f'<div class="raised" style="left:{mx}px;top:{FILTER_Y}px;width:{mw}px;height:{FILTER_H}px">'
                  f'{D.icon("clear", 14, NAVY, 1.7)}<span>More filters</span><i>{spec.get("more_count", 2)}</i></div>')
    if spec.get("context"):
        x, y, w, h = CONTEXT
        boxes += (f'<div class="well" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                  f'<b>{html.escape(spec["context"])}</b></div>')
        bx, by, bw, bh = BACK
        boxes += (f'<div class="raised" style="left:{bx}px;top:{by}px;width:{bw}px;height:{bh}px">‹&nbsp; Back</div>')
    plates = "".join(f'<div class="card" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
                     for x, y, w, h in cards(page))
    if page == "overview":
        plates += overview_artwork()
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>'
            f'<div class="bg"></div>{deco}{header}{boxes}{plates}{rail_html(spec.get("nav", page))}</body></html>')


HOME_CSS = f"""
.kick {{ position: absolute; font: 600 10px Inter, sans-serif; letter-spacing: .24em; text-transform: uppercase; color: {BLUE}; }}
.h {{ position: absolute; font: 700 38px/1.05 Outfit, sans-serif; letter-spacing: -.02em; color: {NAVY}; }}
.lead {{ position: absolute; font-size: 12px; color: #4D5F7C; }}
.tile {{ position: absolute; border-radius: 22px; display: flex; align-items: center; gap: 16px; padding: 0 16px 0 8px;
  background: linear-gradient(180deg, #FFFFFF, #FAFBFD); box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(16,40,80,.05),
  0 8px 18px -8px rgba(16,40,80,.18), 0 20px 40px -26px rgba(16,40,80,.25); }}
.thumb {{ flex: none; border-radius: 15px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(16,40,80,.12); }}
.thumb svg {{ display: block; }}
.tile .idx {{ font: 700 9.5px Inter, sans-serif; color: #A3B1C6; letter-spacing: .04em; }}
.tile b {{ display: block; font: 600 16px/1.15 Outfit, sans-serif; color: {NAVY}; margin-top: 1px; }}
.tile .qq {{ display: block; font-size: 10px; margin-top: 2px; color: {MUTED}; }}
.tile .hl {{ display: block; font-size: 8.6px; margin-top: 5px; color: {MUTED2}; }}
.go {{ margin-left: auto; width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center; flex: none;
  font: 600 17px Inter, sans-serif; color: #fff; background: linear-gradient(160deg, #3F7BD0 0%, #0E3472 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.5), inset 0 -3px 6px rgba(0,0,0,.25), 0 9px 16px -7px rgba(14,52,114,.85); }}
.guide {{ position: absolute; font-size: 9.5px; line-height: 1.7; color: {MUTED}; }}
.guide i {{ display: inline-block; width: 16px; height: 7px; border-radius: 4px; margin-right: 6px; }}
.dock {{ position: absolute; border-radius: 40px; overflow: hidden;
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,0) 30%),
  linear-gradient(160deg, #1C4E98 0%, #0E3472 50%, #0A2756 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.22), inset 0 -2px 0 rgba(0,0,0,.2), 0 34px 60px -28px rgba(10,39,86,.75),
  0 6px 16px rgba(10,39,86,.2); }}
.chip {{ position: absolute; border-radius: 20px; text-align: center; background: rgba(255,255,255,.07);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.14), inset 0 0 0 1px rgba(255,255,255,.08); }}
.chip b {{ position: absolute; left: 0; right: 0; top: 9px; font: 600 21px/28px "Segoe UI Semibold", Inter, sans-serif; color: #fff; }}
.chip span {{ position: absolute; left: 0; right: 0; top: 41px; font-size: 10px; color: rgba(255,255,255,.66); }}
.pill2 {{ position: absolute; border-radius: 16px; display: flex; align-items: center; padding-left: 14px;
  background: rgba(0,0,0,.18); box-shadow: inset 0 1px 3px rgba(0,0,0,.3); }}
.scene {{ position: absolute; perspective: 1200px; }}
.layer {{ position: absolute; inset: 0; transform-style: preserve-3d; }}
.glass {{ position: absolute; border-radius: 26px; corner-shape: squircle; border: 1px solid transparent;
  background: linear-gradient(160deg, rgba(255,255,255,.16), rgba(255,255,255,.05)) padding-box,
  linear-gradient(140deg, rgba(255,255,255,.55), rgba(255,255,255,.08) 45%, rgba(255,255,255,.35)) border-box;
  box-shadow: 0 34px 60px -24px rgba(0,0,0,.55); }}
.tag {{ position: absolute; display: flex; align-items: center; gap: 7px; padding: 6px 11px; border-radius: 13px;
  corner-shape: squircle; font: 600 9.5px Inter, sans-serif; color: #fff; white-space: nowrap;
  background: rgba(10,30,70,.55); box-shadow: inset 0 0 0 1px rgba(255,255,255,.18), 0 10px 20px -10px rgba(0,0,0,.6); }}
.tag i {{ width: 8px; height: 8px; border-radius: 50%; }}
.lbl {{ font: 600 9px Inter, sans-serif; fill: rgba(255,255,255,.72); letter-spacing: .06em; }}
"""
FACTS = {"plants": ("", "plants"), "months": ("12 months", "rolling history"), "values": ("", "measured values"),
         "daily": ("Daily", "refresh from Databricks")}
SKY, RED, AMBER = "#8EC5FF", "#FF6B6B", "#FFA45C"


# --------------------------------------------------------------------------- home illustrations (decoration, no data)
def _iso(cx, cy, unit):
    cos, sin = math.cos(math.radians(30)), math.sin(math.radians(30))
    return lambda x, y, z: (cx + (x - y) * unit * cos, cy + (x + y) * unit * sin - z * unit)


def _poly(pts, fill, extra=""):
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{fill}" {extra}/>'


def _prism(pt, x, y, z, dx, dy, dz, top, left, right, extra=""):
    """Box from (x, y, z) of size (dx, dy, dz): the three faces seen from the front."""
    return (_poly([pt(x, y + dy, z), pt(x + dx, y + dy, z), pt(x + dx, y + dy, z + dz), pt(x, y + dy, z + dz)], left, extra)
            + _poly([pt(x + dx, y, z), pt(x + dx, y + dy, z), pt(x + dx, y + dy, z + dz), pt(x + dx, y, z + dz)], right, extra)
            + _poly([pt(x, y, z + dz), pt(x + dx, y, z + dz), pt(x + dx, y + dy, z + dz), pt(x, y + dy, z + dz)], top, extra))


def art_columns():
    """Isometric columns (first Relief home)."""
    return f'<svg class="abs" style="left:728px;top:24px" width="528" height="440">{iso_columns(150, 178, 33)}</svg>'


def art_spc():
    """Control chart floating in perspective: tolerance (USL, LSL), reaction limits (UCL, LCL), mean, one value out of
    the reaction limits."""
    w, h = 400, 250
    lines = [(34, RED, "", "USL"), (66, AMBER, ' stroke-dasharray="6 5"', "UCL"), (128, "rgba(255,255,255,.7)",
             ' stroke-dasharray="3 5"', "X̄"), (190, AMBER, ' stroke-dasharray="6 5"', "LCL"), (222, RED, "", "LSL")]
    svg = "".join(f'<path d="M22 {y}H{w - 52}" stroke="{c}" stroke-width="1.6"{d}/>'
                  f'<text x="{w - 44}" y="{y + 3}" class="lbl">{lab}</text>' for y, c, d, lab in lines)
    ys = [128, 112, 140, 120, 150, 104, 132, 118, 146, 98, 126, 140, 58, 120, 136, 110, 144, 124, 102, 132]
    xs = [26 + i * (w - 86) / (len(ys) - 1) for i in range(len(ys))]
    pts = " L".join(f"{x:.1f} {y}" for x, y in zip(xs, ys))
    svg += (f'<path d="M{pts}" fill="none" stroke="{SKY}" stroke-width="2.2" stroke-linejoin="round"/>'
            + "".join(f'<circle cx="{x:.1f}" cy="{y}" r="{5 if y < 66 else 3.2}" fill="{AMBER if y < 66 else "#FFFFFF"}"'
                      f'{" stroke=\"rgba(255,164,92,.35)\" stroke-width=\"8\"" if y < 66 else ""}/>' for x, y in zip(xs, ys)))
    return ('<div class="scene" style="left:752px;top:92px;width:480px;height:360px"><div class="layer" '
            'style="transform:rotateY(-22deg) rotateX(12deg) rotateZ(2deg)">'
            f'<div class="glass" style="left:26px;top:30px;width:{w}px;height:{h}px;transform:translateZ(0)">'
            f'<svg width="{w}" height="{h}">{svg}</svg></div>'
            '<div class="tag" style="left:40px;top:-6px;transform:translateZ(70px)"><i style="background:#FFA45C"></i>'
            'Outside the reaction limits</div>'
            '<div class="tag" style="left:60px;top:272px;transform:translateZ(90px)"><i style="background:#8EC5FF"></i>'
            'Within tolerance · Cpk ≥ 1.33</div></div></div>')


def art_capability():
    """Capability: 3D histogram of measured values between the tolerance walls (LSL, USL), bell curve on top
    (oblique view: the bars face the reader, depth goes up to the right)."""
    ux, uz, vx, vy = 31, 30, 14, -9

    def pt(x, y, z):
        return 96 + x * ux + y * vx, 330 - z * uz + y * vy

    n, w, d = 11, 0.78, 1.0
    heights = [0.35 + 3.7 * math.exp(-((i - 5) / 2.2) ** 2) for i in range(n)]
    out = [_poly([pt(-1.2, -0.3, 0), pt(n + 0.4, -0.3, 0), pt(n + 0.4, 1.4, 0), pt(-1.2, 1.4, 0)], "rgba(255,255,255,.06)",
                 'stroke="rgba(255,255,255,.18)" stroke-width="1"')]
    walls = []
    for x0, label in ((-0.6, "LSL"), (n - 0.1, "USL")):
        walls.append(_poly([pt(x0, -0.3, 0), pt(x0, 1.4, 0), pt(x0, 1.4, 4.8), pt(x0, -0.3, 4.8)],
                           "rgba(255,107,107,.18)", 'stroke="rgba(255,107,107,.8)" stroke-width="1.2"'))
        lx, ly = pt(x0, 0.55, 5.1)
        walls.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="lbl" text-anchor="middle">{label}</text>')
    out.append(walls[0] + walls[1])
    for i, hh in enumerate(heights):
        tail = i in (0, n - 1)
        front, top, side = ("#F08A3E", "#FFC08A", "#C9601C") if tail else ("#4F8FE0", "#BFDCFF", "#2A5DA8")
        x = i
        out.append(_poly([pt(x, 0, 0), pt(x + w, 0, 0), pt(x + w, 0, hh), pt(x, 0, hh)], front)
                   + _poly([pt(x + w, 0, 0), pt(x + w, d, 0), pt(x + w, d, hh), pt(x + w, 0, hh)], side)
                   + _poly([pt(x, 0, hh), pt(x + w, 0, hh), pt(x + w, d, hh), pt(x, d, hh)], top))
    out.append(walls[2] + walls[3])
    curve = [pt(t / 4 + w / 2, 0.5, 0.35 + 3.7 * math.exp(-((t / 4 - 5) / 2.2) ** 2) + 0.3) for t in range(-3, 4 * n - 2)]
    out.append(f'<path d="M{" L".join(f"{a:.1f} {b:.1f}" for a, b in curve)}" fill="none" stroke="#FFFFFF" '
               f'stroke-width="2.2" stroke-opacity=".9"/>')
    mx, my = pt(5 + w / 2, 0.5, 4.75)
    out.append(f'<text x="{mx:.1f}" y="{my - 6:.1f}" class="lbl" text-anchor="middle">X̄</text>')
    return (f'<svg class="abs" style="left:728px;top:24px" width="528" height="440">{"".join(out)}</svg>'
            '<div class="tag" style="left:806px;top:404px"><i style="background:#8EC5FF"></i>'
            'Capable process: values centred between the limits</div>')


def art_plant():
    """Connected plant: injection press, conveyor, molded parts through an inspection gate, results to the dashboard."""
    pt = _iso(118, 222, 25)
    edge = 'stroke="rgba(255,255,255,.18)" stroke-width=".8"'
    out = [_poly([pt(-1, -0.6, 0), pt(13.4, -0.6, 0), pt(13.4, 5.2, 0), pt(-1, 5.2, 0)], "rgba(255,255,255,.05)",
                 'stroke="rgba(255,255,255,.16)" stroke-width="1"')]
    for i in range(1, 14):  # floor grid
        a, b = pt(i - 1, -0.6, 0), pt(i - 1, 5.2, 0)
        out.append(f'<path d="M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}" stroke="rgba(255,255,255,.06)"/>')
    # injection press: body, clamp unit, hopper
    out.append(_prism(pt, 0, 1.2, 0, 3.0, 2.6, 2.1, "#DCE8F8", "#8FAED6", "#5F83B8", edge))
    out.append(_prism(pt, 0.4, 1.7, 2.1, 1.3, 1.4, 0.9, "#EEF4FC", "#A9C2E3", "#7898C6", edge))
    out.append(_prism(pt, 2.1, 2.2, 2.1, 0.6, 0.6, 1.1, "#FFD2A8", "#F2A060", "#D0782E", edge))
    sx, sy = pt(3.0, 1.55, 1.75)  # screen on the press
    out.append(_poly([pt(3.0, 1.55, 1.75), pt(3.0, 2.45, 1.75), pt(3.0, 2.45, 1.05), pt(3.0, 1.55, 1.05)], "#0B2A5B",
                     'stroke="#8EC5FF" stroke-width="1"'))
    # conveyor
    out.append(_prism(pt, 3.0, 2.3, 0, 10.2, 1.2, 0.55, "#2C5FA8", "#173F7A", "#0F2F5E", edge))
    for i in range(1, 20):  # rollers
        a, b = pt(3.0 + i * 0.52, 2.3, 0.55), pt(3.0 + i * 0.52, 3.5, 0.55)
        out.append(f'<path d="M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}" stroke="rgba(255,255,255,.12)"/>')
    parts = [(4.0, "ok"), (5.8, "ok"), (9.0, "ok"), (11.2, "fail")]
    beam = _poly([pt(7.55, 2.2, 0.55), pt(7.55, 3.6, 0.55), pt(7.55, 3.6, 2.2), pt(7.55, 2.2, 2.2)],
                 "rgba(142,197,255,.22)", 'stroke="rgba(142,197,255,.6)" stroke-width="1"')
    gate = (_prism(pt, 7.4, 1.9, 0, 0.3, 0.3, 2.5, "#EEF4FC", "#A9C2E3", "#7898C6", edge)
            + _prism(pt, 7.4, 3.6, 0, 0.3, 0.3, 2.5, "#EEF4FC", "#A9C2E3", "#7898C6", edge)
            + _prism(pt, 7.4, 1.9, 2.5, 0.3, 2.0, 0.3, "#FFFFFF", "#BFD3EE", "#8AA9D3", edge))
    for x, state in parts[:2]:
        out.append(_prism(pt, x, 2.5, 0.55, 0.8, 0.8, 0.38, "#FFFFFF", "#C9D8EC", "#9DB4D6", edge))
    out.append(beam + gate)
    for x, state in parts[2:]:
        top, left, right = ("#FFFFFF", "#C9D8EC", "#9DB4D6") if state == "ok" else ("#FFC08A", "#F08A3E", "#C9601C")
        out.append(_prism(pt, x, 2.5, 0.55, 0.8, 0.8, 0.38, top, left, right, edge))
        bx, by = pt(x + 0.4, 2.9, 1.9)
        mark = ('<path d="M-4 0l3 3 5-6" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" '
                'stroke-linejoin="round"/>' if state == "ok" else
                '<path d="M-3.5 -3.5l7 7M3.5 -3.5l-7 7" stroke="#fff" stroke-width="2" stroke-linecap="round"/>')
        out.append(f'<g transform="translate({bx:.1f} {by:.1f})"><path d="M0 9V22" stroke="rgba(255,255,255,.35)"/>'
                   f'<circle r="10" fill="{"#2F6EBA" if state == "ok" else "#ED7D31"}" stroke="#fff" stroke-width="1.5"/>'
                   f'{mark}</g>')
    gx, gy = pt(7.55, 2.75, 2.8)
    out.append(f'<path d="M{gx:.1f} {gy:.1f} C{gx:.1f} {gy - 50:.1f} {gx - 40:.1f} {gy - 70:.1f} 196 112" '
               'fill="none" stroke="#8EC5FF" stroke-width="1.4" stroke-dasharray="4 4"/>')
    screen = ('<div class="glass" style="left:772px;top:84px;width:150px;height:92px;border-radius:18px">'
              '<svg width="150" height="92"><path d="M14 64 L36 52 L58 58 L80 40 L102 46 L124 30 L138 34" fill="none" '
              'stroke="#8EC5FF" stroke-width="2" stroke-linejoin="round"/><circle cx="124" cy="30" r="3" fill="#fff"/>'
              '<rect x="14" y="14" width="44" height="6" rx="3" fill="rgba(255,255,255,.55)"/>'
              '<rect x="14" y="74" width="80" height="5" rx="2.5" fill="rgba(255,255,255,.18)"/></svg></div>')
    return (f'<svg class="abs" style="left:728px;top:24px" width="528" height="440">{"".join(out)}</svg>{screen}'
            '<div class="tag" style="left:790px;top:428px"><i style="background:#8EC5FF"></i>Every part inspected · '
            'results every day in the dashboard</div>')


def art_car():
    """Exterior part inspection: a car in profile with measured points (gap and flush, fit, thickness), one out."""
    body = ("M44 150 C40 134 44 122 52 112 L66 84 C70 72 80 66 92 64 L150 52 C170 47 222 46 248 50 C266 53 286 66 300 78 "
            "L322 94 C352 98 392 102 412 108 C426 112 434 122 434 134 L436 150 L398 150 C398 128 382 112 360 112 "
            "C338 112 322 128 322 150 L148 150 C148 128 132 112 110 112 C88 112 72 128 72 150 Z")
    windows = ("M104 86 L128 62 C150 56 196 54 236 56 L236 86 Z M244 56 C262 58 278 68 292 82 L294 86 L244 86 Z")
    svg = (f'<g transform="translate(0 30)"><ellipse cx="240" cy="160" rx="210" ry="10" fill="rgba(0,0,0,.25)"/>'
           f'<path d="{body}" fill="rgba(255,255,255,.08)" stroke="#FFFFFF" stroke-width="1.8" stroke-linejoin="round"/>'
           f'<path d="{windows}" fill="rgba(142,197,255,.16)" stroke="rgba(255,255,255,.75)" stroke-width="1.2"/>'
           '<path d="M240 88 V146 M160 88 C158 110 158 130 160 146" stroke="rgba(255,255,255,.45)" stroke-width="1"/>'
           '<path d="M414 112 L428 116 L430 124 L416 122 Z" fill="#FFFFFF" fill-opacity=".85"/>'
           '<path d="M52 100 L60 92 L64 104 L54 110 Z" fill="#FF6B6B" fill-opacity=".85"/>'
           + "".join(f'<circle cx="{cx}" cy="150" r="{r}" fill="{f}" stroke="#FFFFFF" stroke-width="{sw}"/>'
                     for x in (110, 360) for cx, r, f, sw in [(x, 24, "#0A2756", 1.8), (x, 10, "rgba(255,255,255,.25)", 1)])
           + '</g>')
    points = [(430, 128, "ok", "Bumper fit", 352, 196), (318, 92, "ok", "Gap & flush", 290, 6),
              (240, 112, "fail", "Door gap", 196, 196), (58, 104, "ok", "Tailgate fit", 6, 6),
              (96, 84, "ok", "Paint thickness", 30, 196)]
    for x, y, state, label, tx, ty in points:
        c = "#8EC5FF" if state == "ok" else "#FFA45C"
        y += 30  # the car is drawn 30 px lower (room for the chips above)
        ey = ty + 24 if ty < y else ty
        svg += (f'<path d="M{x} {y} L{tx + 36} {ey}" stroke="{c}" stroke-opacity=".6" stroke-dasharray="3 3"/>'
                f'<circle cx="{x}" cy="{y}" r="9" fill="{c}" fill-opacity=".22"/>'
                f'<circle cx="{x}" cy="{y}" r="4" fill="{c}" stroke="#fff" stroke-width="1.2"/>')
    tags = "".join(f'<div class="tag" style="left:{tx}px;top:{ty}px"><i style="background:'
                   f'{"#8EC5FF" if s == "ok" else "#FFA45C"}"></i>{label}</div>' for _, _, s, label, tx, ty in points)
    return ('<div class="abs" style="left:758px;top:150px;width:470px;height:240px">'
            f'<svg width="470" height="230" style="position:absolute;left:0;top:0">{svg}</svg>{tags}</div>')


ARTS = {"columns": art_columns, "spc": art_spc, "capability": art_capability, "plant": art_plant, "car": art_car}
HOME_ART = "columns"  # illustration of the navy panel of the home page


def home_html(art=None):
    words = D.REPORT_TITLE.split(" ")
    lines = (" ".join(words[:-1]), words[-1]) if len(words) > 1 else (D.REPORT_TITLE,)
    tiles = ""
    for i, (label, key) in enumerate(D.NAV):
        x, y, w, h = HOME_TILES[key]
        question, highlights = D.HOME_PAGES[key]
        tiles += (f'<div class="tile" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                  f'<div class="thumb">{D.mini_preview(key, THUMB[0], THUMB[1])}</div><div>'
                  f'<div class="idx">0{i + 1}</div><b>{html.escape(label)}</b><span class="qq">{html.escape(question)}</span>'
                  f'<span class="hl">{html.escape(highlights)}</span></div><div class="go">›</div></div>')
    chips = "".join(f'<div class="chip" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><b>{FACTS[key][0]}</b>'
                    f'<span>{FACTS[key][1]}</span></div>' for key, _ in D.HOME_FACTS for x, y, w, h in [CHIPS[key]])
    dx, dy, dw, dh = DOCK
    rx, ry, rw, rh = HOME_REFRESH
    body = (f'{logo("logo_navy.png", 64, 34, 150)}<div class="kick" style="left:64px;top:98px">Quality</div>'
            f'<div class="h" style="left:62px;top:116px">{"<br>".join(html.escape(x) for x in lines)}</div>'
            f'<div class="lead" style="left:64px;top:208px">The daily review of quality results in series production, '
            f'for every plant. Choose a page:</div>{tiles}'
            f'<div class="guide" style="left:64px;top:672px"><i style="background:{BLUE}"></i>Pass &nbsp; '
            f'<i style="background:{ORANGE}"></i>Fail &nbsp; <i style="background:#1F4E79"></i>Reaction limits '
            f'&nbsp;·&nbsp; Cpk = min(USL − mean, mean − LSL) / 3σ &nbsp;·&nbsp; filters follow you from page to page</div>'
            f'<div class="dock" style="left:{dx}px;top:{dy}px;width:{dw}px;height:{dh}px"><svg width="{dw}" height="{dh}">'
            f'{arcs(dw, 0, [120, 170, 220, 270, 320, 370, 420], 180, 270, "#FFFFFF", .28, 1)}</svg></div>'
            f'{ARTS[art or HOME_ART]()}{logo("logo_white.png", 1082, 58, 130)}{chips}'
            f'<div class="pill2" style="left:{rx}px;top:{ry}px;width:{rw}px;height:{rh}px">'
            f'{D.icon("clock", 13, "rgba(255,255,255,.7)", 1.8)}</div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}{HOME_CSS}</style></head><body>'
            f'<div class="bg"></div>{body}</body></html>')


def render_html(page):
    return home_html() if page == "home" else page_html(page)
