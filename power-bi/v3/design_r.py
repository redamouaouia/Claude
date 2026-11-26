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
HOME_TILES = {key: (64, 270 + i * 74, 600, 62) for i, (_, key) in enumerate(D.NAV)}
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
.h {{ position: absolute; font: 700 40px/1.06 Outfit, sans-serif; letter-spacing: -.02em; color: {NAVY}; }}
.lead {{ position: absolute; font-size: 12px; color: #4D5F7C; }}
.tile {{ position: absolute; border-radius: 22px; display: flex; align-items: center; gap: 16px; padding: 0 16px 0 14px;
  background: linear-gradient(180deg, #FFFFFF, #FAFBFD); box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(16,40,80,.05),
  0 8px 18px -8px rgba(16,40,80,.18), 0 20px 40px -26px rgba(16,40,80,.25); }}
.tile b {{ display: block; font: 600 15px Outfit, sans-serif; color: {NAVY}; }}
.tile span {{ display: block; font-size: 10.5px; margin-top: 3px; color: {MUTED}; }}
.go {{ margin-left: auto; width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-size: 15px;
       flex: none; background: #EEF2F7; color: {NAVY}; box-shadow: inset 0 1px 2px rgba(16,40,80,.12); }}
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
"""
FACTS = {"plants": ("", "plants"), "months": ("12 months", "rolling history"), "values": ("", "measured values"),
         "daily": ("Daily", "refresh from Databricks")}


def home_html():
    words = D.REPORT_TITLE.split(" ")
    lines = (" ".join(words[:-1]), words[-1]) if len(words) > 1 else (D.REPORT_TITLE,)
    tiles = "".join(
        f'<div class="tile" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">{pebble("navy", key, 40, 19)}'
        f'<div><b>{html.escape(label)}</b><span>{html.escape(D.HOME_PAGES[key][0])}</span></div><div class="go">›</div></div>'
        for label, key in D.NAV for x, y, w, h in [HOME_TILES[key]])
    chips = "".join(f'<div class="chip" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"><b>{FACTS[key][0]}</b>'
                    f'<span>{FACTS[key][1]}</span></div>' for key, _ in D.HOME_FACTS for x, y, w, h in [CHIPS[key]])
    dx, dy, dw, dh = DOCK
    rx, ry, rw, rh = HOME_REFRESH
    body = (f'{logo("logo_navy.png", 64, 44, 150)}<div class="kick" style="left:64px;top:112px">Quality</div>'
            f'<div class="h" style="left:62px;top:132px">{"<br>".join(html.escape(x) for x in lines)}</div>'
            f'<div class="lead" style="left:64px;top:236px">The daily review of quality results in series production, '
            f'for every plant. Choose a page:</div>{tiles}'
            f'<div class="guide" style="left:64px;top:650px"><i style="background:{BLUE}"></i>Pass &nbsp; '
            f'<i style="background:{ORANGE}"></i>Fail &nbsp; <i style="background:#1F4E79"></i>Reaction limits '
            f'&nbsp;·&nbsp; Cpk = min(USL − mean, mean − LSL) / 3σ &nbsp;·&nbsp; filters follow you from page to page</div>'
            f'<div class="dock" style="left:{dx}px;top:{dy}px;width:{dw}px;height:{dh}px"><svg width="{dw}" height="{dh}">'
            f'{arcs(dw, 0, [120, 170, 220, 270, 320, 370, 420], 180, 270, "#FFFFFF", .28, 1)}{iso_columns(150, 178, 33)}'
            f'</svg></div>{logo("logo_white.png", 1082, 58, 130)}{chips}'
            f'<div class="pill2" style="left:{rx}px;top:{ry}px;width:{rw}px;height:{rh}px">'
            f'{D.icon("clock", 13, "rgba(255,255,255,.7)", 1.8)}</div>')
    return (f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{CSS}{HOME_CSS}</style></head><body>'
            f'<div class="bg"></div>{body}</body></html>')


def render_html(page):
    return home_html() if page == "home" else page_html(page)
