"""Shared geometry and the page-background artwork for Quality Dashboard V3.

The backgrounds are drawn in HTML/CSS and rendered at 2x (2560 x 1440) with Chromium. Every white card plate,
filter label and title in the artwork sits exactly under the native Power BI visual that uses the same
coordinates below, so the two layers line up.
"""
import base64
import html
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BRAND = HERE / "out" / "brand"  # white logo files made by make_logo_assets.py (not stored in the repository)

# --------------------------------------------------------------------------- canvas geometry (Power BI px)
W, H = 1280, 720
RAIL_W = 96
X0, X1 = 124, 1256
BAND_H = 184
LABEL_Y, SLICER_Y, SLICER_H = 91, 104, 36
ROW2_Y, ROW2_H = 156, 254
ROW3_Y, ROW3_H = 424, 280
GAP = 16

NAV = [("Overview", "overview"), ("Characteristics", "chars"), ("Reaction limits", "rl"), ("Cpk", "cpk")]
NAV_TILES = {k: (10, 96 + i * 74, 76, 64) for i, (_, k) in enumerate(NAV)}
BADGE = (20, 16, 56, 56)  # company symbol at the top of the rail: the Home button of every page
CLEAR_TILE = (10, 636, 76, 64)
REFRESH_PILL = (966, 22, 290, 26)
PERIOD_TRACK = (966, 54, 290, 26)  # period filter (Day, WTD, MTD, YTD, Year), under the refresh time
PERIOD_PAGES = ("overview", "chars", "rl", "cpk")
DATE_W, MORE_W = 250, 132  # fixed widths: two date boxes, and the full "More filters · N" label


def distribute(weights, x0=X0, x1=X1, gap=10):
    total = x1 - x0 - gap * (len(weights) - 1)
    unit = total / sum(weights)
    out, x = [], x0
    for w in weights:
        out.append((round(x, 1), round(w * unit, 1)))
        x += w * unit + gap
    return out


PAGES = {
    "overview": {
        "title": "Overview",
        "question": "How many inspections pass, and where do they fail?",
        "slicers": [("Plant", "Plant", 0.8), ("Part", "Part · inspection plan", 1.2), ("Test", "Test", 1.1),
                    ("Inspection Reason", "Inspection reason", 1.1), ("Date", "Date", 1.45)],
        "more_count": 2,
        # The Pass & Fail % donut was removed at the client's request: the monthly line takes its place.
        "cards": {
            "hero": (X0, ROW2_Y, 300, ROW2_H),
            "line": (440, ROW2_Y, X1 - 440, ROW2_H),
            "decomp": (X0, ROW3_Y, 760, ROW3_H),
            "table": (900, ROW3_Y, 356, ROW3_H),
        },
    },
    "chars": {
        "title": "Characteristics",
        "question": "How do measured values evolve, and which characteristics fail?",
        "slicers": [("Plant", "Plant", 0.75), ("Part", "Part · inspection plan", 1.1), ("Test", "Test", 1.0),
                    ("Characteristic", "Characteristic", 1.15), ("Inspection Reason", "Inspection reason", 1.05),
                    ("Date", "Date", 1.4)],
        "more_count": 2,
        "cards": {
            "kpi1": (X0, ROW2_Y, 300, 121),
            "kpi2": (X0, ROW2_Y + 133, 300, 121),
            "line": (440, ROW2_Y, 816, ROW2_H),
            "bars_part": (X0, ROW3_Y, 364, ROW3_H),
            "bars_test": (504, ROW3_Y, 364, ROW3_H),
            "table": (884, ROW3_Y, 372, ROW3_H),
        },
    },
    # Page 3, laid out as the mockup of the specification: violations per day, top 15 characteristics on the
    # right, violations by part (with the Details button) and by test.
    "rl": {
        "title": "Reaction limits",
        "question": "Where are measurements getting close to the limit?",
        "slicers": [("Plant", "Plant", 0.8), ("Part", "Part · inspection plan", 1.2), ("Test", "Test", 1.1),
                    ("Characteristic", "Characteristic", 1.25), ("Date", "Date", 1.45)],
        "more_count": 2,
        "cards": {
            "line": (X0, ROW2_Y, 756, ROW2_H),
            "top15": (896, ROW2_Y, 360, ROW2_H + ROW3_H + (ROW3_Y - ROW2_Y - ROW2_H)),
            "treemap": (X0, ROW3_Y, 370, ROW3_H),
            "table": (510, ROW3_Y, 370, ROW3_H),
        },
    },
    # Drill-through page opened by "Details" on "Violations by part": the list of violations of that part.
    "rl_details": {
        "title": "Reaction limit details",
        "question": "Which measured values are outside the reaction limits?",
        "nav": "rl",
        "slicers": [],
        "context": "Selection",
        "cards": {
            "table": (X0, ROW2_Y, X1 - X0, ROW2_H + ROW3_H + (ROW3_Y - ROW2_Y - ROW2_H)),
        },
    },
}
PAGES["cpk"] = {
    # Page 4, laid out as the mockup of the specification. Its rules are still to be validated.
    "title": "Cpk",
    "status": "To be validated",
    "question": "Which parts, tests and characteristics are capable?",
    "slicers": [("Plant", "Plant", 0.8), ("Part", "Part · inspection plan", 1.2), ("Test", "Test", 1.1),
                ("Characteristic", "Characteristic", 1.25), ("Date", "Date", 1.45)],
    "more_count": 3,
    # The detail table gets the most room; Cpk pass % and the donut share one card (as the hero and the gauge of
    # page 1), the figure on top.
    "cards": {
        "kpi": (X0, ROW2_Y, 300, 230),
        "bars_part": (440, ROW2_Y, 400, 230),
        "bars_test": (856, ROW2_Y, 400, 230),
        "table": (X0, ROW2_Y + 230 + GAP, X1 - X0, H - 16 - (ROW2_Y + 230 + GAP)),
    },
}
FORMER_DONUT = (956, ROW2_Y, 300, ROW2_H)  # Overview donut until V9 (restyle.py), removed by add_period_filter.py
CPK_FIGURE_H = 128  # height of the Cpk pass % figure in its card (as the hero of page 1: below, it gets cut)
PAGES["home"] = {
    # Home page: concept B of the proposals. Hero on the left, the pages on the right, a reading guide below.
    "title": "Quality Dashboard",
    "question": "Plant Visual Management",
    "nav": "home",
    "slicers": [],
    "cards": {},
}
HOME_HERO = (RAIL_W, 0, 520, H)
HOME_ROWS = {key: (648, 96 + i * 112, 608, 100) for i, (_, key) in enumerate(NAV)}  # one row per page
HOME_GUIDE = (648, 548, 608, 156)
HOME_FACTS = [("plants", "Plants"), ("months", None), ("values", "Home Measured Values"), ("daily", None)]
HOME_FACT_Y = {key: 470 + i * 40 for i, (key, _) in enumerate(HOME_FACTS)}  # one line per fact
HOME_FACT_VALUE = (136, 130, 32)  # x, width, height of a live value (Power BI card) in the facts list
HOME_REFRESH = (138, 664, 300, 26)
CONTEXT = (X0, SLICER_Y, 820, SLICER_H)          # details page: the part chosen with "Details"
BACK = (X1 - MORE_W, SLICER_Y, MORE_W, SLICER_H)  # details page: back to Reaction limits


def slicer_slots(page):
    """x/width of each slicer, then of the "More filters" button. Date and the button get fixed widths."""
    items = PAGES[page]["slicers"]
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


# --------------------------------------------------------------------------- artwork
ICONS = {
    "overview": '<rect x="3.5" y="3.5" width="7" height="7" rx="2"/><rect x="13.5" y="3.5" width="7" height="7" rx="2"/>'
                '<rect x="3.5" y="13.5" width="7" height="7" rx="2"/><rect x="13.5" y="13.5" width="7" height="7" rx="2"/>',
    "chars": '<rect x="2.5" y="7.5" width="19" height="9" rx="2"/><path d="M6.5 7.5v3.2M10 7.5v2M13.5 7.5v3.2M17 7.5v2"/>',
    "rl": '<path d="M2.5 8.5h19" stroke-dasharray="2.2 2.2"/><path d="M6 20.5v-6M10 20.5v-8.5M14 20.5v-16M18 20.5v-6.5"/>',
    "cpk": '<path d="M2.5 19.5h19"/><path d="M4 19.5c3.5 0 4.3-12 8-12s4.5 12 8 12"/>'
           '<path d="M5.5 4.5v15M18.5 4.5v15" stroke-dasharray="2 2"/>',
    "clear": '<path d="M4 5h15l-5.8 6.6V17l-3.4 1.8v-7.2z"/><path d="M16.6 14.6l4 4M20.6 14.6l-4 4"/>',
    "glyph": '<path d="M3 6.5h18M3 17.5h18" stroke-dasharray="2.2 2.2"/>'
             '<path d="M3 12c1.6-3.4 3.2-3.4 4.8 0s3.2 3.4 4.8 0 3.2-3.4 4.8 0 2.4 2.6 3.6 1.4"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7.5V12l3 2"/>',
}


def icon(name, size, color, sw=1.6):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def tolerance_motif():
    """USL / LSL band with a measurement signal: one value out of the reaction limits, in Fail orange."""
    pts, import_math = [], __import__("math")
    for i in range(0, 61):
        x = 6 + i * 6.4
        y = 36 + 12.5 * import_math.sin(i * 0.52) * (0.55 + 0.45 * import_math.cos(i * 0.11))
        pts.append((x, y))
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.7" fill="rgba(255,255,255,.55)"/>'
                   for i, (x, y) in enumerate(pts) if i % 6 == 3)
    return f'''
    <svg class="motif" width="400" height="74" viewBox="0 0 400 74">
      <defs><linearGradient id="fade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
        <stop offset=".25" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
        <mask id="m"><rect width="400" height="74" fill="url(#fade)"/></mask></defs>
      <g mask="url(#m)">
        <rect x="0" y="14" width="400" height="44" fill="rgba(255,255,255,.035)"/>
        <path d="M0 14H400M0 58H400" stroke="rgba(255,255,255,.22)" stroke-dasharray="4 5" stroke-width="1"/>
        <path d="M0 36H400" stroke="rgba(255,255,255,.08)" stroke-width="1"/>
        <path d="{path}" fill="none" stroke="rgba(255,255,255,.30)" stroke-width="1.4" stroke-linejoin="round"/>
        {dots}
        <circle cx="294" cy="6.5" r="5.5" fill="rgba(237,125,49,.24)"/>
        <circle cx="294" cy="6.5" r="2.5" fill="#ED7D31"/>
      </g>
      <text x="398" y="10" text-anchor="end" class="tl">USL</text>
      <text x="398" y="70" text-anchor="end" class="tl">LSL</text>
    </svg>'''


def _data_uri(path):
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def badge_html():
    """Tile at the top of the rail: the company symbol, in white, between two dashed limit lines (USL / LSL),
    a nod to the tolerance band of the header. Without the logo files, the tolerance glyph."""
    symbol = BRAND / "symbol_white.png"
    if not symbol.exists():
        return f'<div class="glyph">{icon("glyph", 26, "rgba(255,255,255,.92)", 1.5)}</div>'
    return (f'<div class="badge"><i class="lim top"></i><i class="lim bottom"></i>'
            f'<img src="{_data_uri(symbol)}" alt=""></div>')


def eyebrow_html():
    rest = "Quality Dashboard &nbsp;·&nbsp; Plant Visual Management"
    logo = BRAND / "logo_white.png"
    if not logo.exists():
        return f'<div class="eyebrow">OPmobility &nbsp;·&nbsp; {rest}</div>'
    return f'<div class="eyebrow brand"><img src="{_data_uri(logo)}" alt=""><span>{rest}</span></div>'


def page_html(page):
    spec = PAGES[page]
    slots = slicer_slots(page)
    labels = "".join(
        f'<div class="flabel" style="left:{x + 2}px;top:{LABEL_Y}px;width:{w}px">{html.escape(lbl)}</div>'
        for (x, w), (_, lbl, _) in zip(slots, spec["slicers"]))
    if spec.get("context"):
        labels += (f'<div class="flabel" style="left:{CONTEXT[0] + 2}px;top:{LABEL_Y}px;width:{CONTEXT[2]}px">'
                   f'{html.escape(spec["context"])}</div>')
    plates = "".join(f'<div class="plate" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
                     for x, y, w, h in spec["cards"].values())
    tiles = ""
    for label, key in NAV:
        x, y, w, h = NAV_TILES[key]
        active = " active" if key == spec.get("nav", page) else ""
        tiles += (f'<div class="tile{active}" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                  f'{icon(key, 22, "#FFFFFF" if active else "rgba(255,255,255,.70)")}'
                  f'<span>{label}</span></div>')
    cx, cy, cw, ch = CLEAR_TILE
    tiles += (f'<div class="tile" style="left:{cx}px;top:{cy}px;width:{cw}px;height:{ch}px">'
              f'{icon("clear", 21, "rgba(255,255,255,.70)")}<span>Clear filters</span></div>')
    rx, ry, rw, rh = REFRESH_PILL
    ticks = "".join(f'<line x1="{8 - (5 if i % 5 == 0 else 2.5)}" x2="8" y1="{i * 8 + .5}" y2="{i * 8 + .5}"/>'
                    for i in range(0, H // 8 + 1))
    status = ""
    if spec.get("status"):
        width = 15 + 17.5 * len(spec["title"])  # title in Barlow Semi Condensed 33 px
        status = f'<div class="status" style="left:{X0 + width:.0f}px">{html.escape(spec["status"])}</div>'
    track = ""
    if page in PERIOD_PAGES:
        px, py, pw, ph = PERIOD_TRACK
        track = f'<div class="track" style="left:{px}px;top:{py}px;width:{pw}px;height:{ph}px"></div>'
    header = (f'<div class="band">{tolerance_motif()}</div>{eyebrow_html()}'
              f'<h1>{html.escape(spec["title"])}</h1>{status}<div class="q">{html.escape(spec["question"])}</div>'
              f'<div class="pill">{icon("clock", 13, "rgba(255,255,255,.72)", 1.7)}</div>{track}{labels}{plates}')
    return f'''<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@600;700&family=Inter:wght@400;500;600&display=swap">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html, body {{ width: {W}px; height: {H}px; overflow: hidden; }}
  body {{ position: relative; font-family: Inter, "Segoe UI", sans-serif;
         background: linear-gradient(180deg, #F5F8FC 0%, #EDF2F8 55%, #E7EDF5 100%); }}
  .dots {{ position: absolute; left: {RAIL_W}px; top: {BAND_H}px; right: 0; bottom: 0;
          background-image: radial-gradient(rgba(11,42,91,.085) 0.9px, transparent 1.2px); background-size: 18px 18px;
          background-position: 6px 4px; }}
  .band {{ position: absolute; left: {RAIL_W}px; top: 0; right: 0; height: {BAND_H}px; overflow: hidden;
          background:
            radial-gradient(520px 230px at 86% -18%, rgba(110,170,235,.40), transparent 70%),
            radial-gradient(460px 220px at 18% 140%, rgba(47,110,186,.30), transparent 72%),
            linear-gradient(115deg, #0A2756 0%, #0E336D 48%, #1A4C92 100%); }}
  .band::after {{ content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 1px; background: rgba(255,255,255,.07); }}
  .motif {{ position: absolute; left: {552 - RAIL_W}px; top: 4px; }}
  .tl {{ font: 600 7.5px Inter, sans-serif; letter-spacing: .14em; fill: rgba(255,255,255,.42); }}
  .rail {{ position: absolute; left: 0; top: 0; width: {RAIL_W}px; height: {H}px;
          background: radial-gradient(160px 220px at 50% -40px, rgba(110,170,235,.32), transparent 75%),
                      linear-gradient(180deg, #0E3373 0%, #0A2A5E 42%, #061A3C 100%); }}
  .ruler {{ position: absolute; left: {RAIL_W - 8}px; top: 0; }}
  .ruler line {{ stroke: rgba(255,255,255,.13); stroke-width: 1; }}
  .glyph {{ position: absolute; left: 24px; top: 20px; width: 48px; height: 48px; border-radius: 14px;
           border: 1px solid rgba(255,255,255,.22); background: rgba(255,255,255,.06);
           display: grid; place-items: center; }}
  .badge {{ position: absolute; left: 20px; top: 16px; width: 56px; height: 56px; border-radius: 16px; overflow: hidden;
           border: 1px solid rgba(255,255,255,.26);
           background: radial-gradient(46px 40px at 50% 46%, rgba(111,168,232,.45), transparent 72%),
                       linear-gradient(150deg, rgba(255,255,255,.18), rgba(255,255,255,.04));
           box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 12px 24px -10px rgba(0,0,0,.6);
           display: grid; place-items: center; }}
  .badge img {{ width: 38px; position: relative; filter: drop-shadow(0 1px 2px rgba(6,26,60,.45)); }}
  .badge .lim {{ position: absolute; left: 5px; right: 5px; height: 0; border-top: 1px dashed rgba(255,255,255,.34);
                -webkit-mask-image: linear-gradient(90deg, transparent, #000 22%, #000 78%, transparent); }}
  .badge .lim.top {{ top: 10px; }}
  .badge .lim.bottom {{ bottom: 10px; }}
  .eyebrow.brand {{ display: flex; align-items: center; gap: 9px; top: 12px; }}
  .eyebrow.brand img {{ height: 15px; opacity: .95; }}
  .eyebrow.brand span::before {{ content: "·"; margin-right: 9px; }}
  .tile {{ position: absolute; border-radius: 14px; display: flex; flex-direction: column; align-items: center;
          justify-content: center; gap: 7px; color: rgba(255,255,255,.66); font-size: 9.5px; font-weight: 500;
          letter-spacing: .01em; }}
  .tile span {{ text-align: center; line-height: 1.15; padding: 0 3px; }}
  .tile.active {{ background: rgba(255,255,255,.13); box-shadow: inset 0 0 0 1px rgba(255,255,255,.10); color: #fff; }}
  .tile.active::before {{ content: ""; position: absolute; left: -10px; top: 18px; bottom: 18px; width: 3px;
                         border-radius: 0 3px 3px 0; background: #6FA8E8; }}
  .eyebrow {{ position: absolute; left: {X0}px; top: 16px; font-size: 9.5px; font-weight: 600; letter-spacing: .17em;
             color: rgba(255,255,255,.56); text-transform: uppercase; }}
  h1 {{ position: absolute; left: {X0 - 2}px; top: 28px; font: 700 33px/1 "Barlow Semi Condensed", "Segoe UI", sans-serif;
       color: #fff; letter-spacing: .005em; }}
  .q {{ position: absolute; left: {X0}px; top: 65px; font-size: 12px; color: rgba(255,255,255,.72); }}
  .pill {{ position: absolute; left: {rx}px; top: {ry}px; width: {rw}px; height: {rh}px; border-radius: {rh / 2}px;
          background: rgba(255,255,255,.10); box-shadow: inset 0 0 0 1px rgba(255,255,255,.16);
          display: flex; align-items: center; padding-left: 10px; }}
  .track {{ position: absolute; border-radius: 13px; background: rgba(255,255,255,.07);
           box-shadow: inset 0 0 0 1px rgba(255,255,255,.16); }}
  .flabel {{ position: absolute; font-size: 8.8px; font-weight: 600; letter-spacing: .13em; text-transform: uppercase;
            color: rgba(255,255,255,.62); white-space: nowrap; overflow: hidden; }}
  .plate {{ position: absolute; border-radius: 16px; background: #fff;
           box-shadow: 0 1px 2px rgba(11,42,91,.07), 0 10px 28px -6px rgba(11,42,91,.16), 0 2px 8px rgba(11,42,91,.04); }}
  .homelbl {{ position: absolute; left: 0; width: {RAIL_W}px; top: 76px; text-align: center; font-size: 8px;
             font-weight: 600; letter-spacing: .16em; color: rgba(255,255,255,.55); }}
  .homelbl.on {{ color: #fff; }}
  .badge.on {{ box-shadow: inset 0 1px 0 rgba(255,255,255,.22), 0 0 0 3px rgba(111,168,232,.45),
                         0 12px 24px -10px rgba(0,0,0,.6); }}
  .status {{ position: absolute; top: 36px; height: 20px; padding: 0 10px; border-radius: 10px; display: flex;
            align-items: center; font-size: 9px; font-weight: 600; letter-spacing: .04em; color: #FFD9BF;
            background: rgba(237,125,49,.18); box-shadow: inset 0 0 0 1px rgba(237,125,49,.75); }}
{HOME_CSS if page == "home" else ""}
</style></head><body>
  <div class="dots"></div>
  {home_body() if page == "home" else header}
  <div class="rail"></div>
  <svg class="ruler" width="8" height="{H}">{ticks}</svg>
  {badge_html().replace('class="badge"', 'class="badge on"') if page == "home" else badge_html()}
  <div class="homelbl{" on" if page == "home" else ""}">HOME</div>
  {tiles}
</body></html>'''


HOME_CSS = f"""
  .dots {{ top: 0; }}
  .hero {{ position: absolute; left: {HOME_HERO[0]}px; top: 0; width: {HOME_HERO[2]}px; height: {H}px; overflow: hidden;
          background: radial-gradient(520px 360px at 20% 0%, rgba(110,170,235,.35), transparent 70%),
                      radial-gradient(420px 300px at 100% 100%, rgba(47,110,186,.35), transparent 72%),
                      linear-gradient(160deg, #0A2756 0%, #0E336D 55%, #133F80 100%); }}
  .hero .motif {{ position: absolute; left: -30px; top: 318px; transform: scale(1.22); transform-origin: left top; opacity: .9; }}
  .hero .logo {{ position: absolute; left: 40px; top: 46px; height: 34px; }}
  .hero .kicker {{ position: absolute; left: 42px; top: 120px; font-size: 9.5px; font-weight: 600; letter-spacing: .2em;
                  color: rgba(255,255,255,.56); text-transform: uppercase; }}
  .hero h1 {{ left: 40px; top: 148px; font-size: 54px; line-height: .95; }}
  .hero .lead {{ position: absolute; left: 42px; top: 270px; width: 420px; font-size: 12.5px; line-height: 1.6;
                color: rgba(255,255,255,.75); }}
  .fact {{ position: absolute; left: 42px; display: flex; align-items: center; height: 32px; font-size: 10.5px;
          color: rgba(255,255,255,.82); }}
  .fact b {{ font: 600 15px "Segoe UI Semibold", Inter, sans-serif; color: #fff; width: 130px; }}
  .fact span {{ position: absolute; left: 140px; white-space: nowrap; }}
  .hpill {{ position: absolute; left: {HOME_REFRESH[0] - RAIL_W}px; top: {HOME_REFRESH[1]}px; width: {HOME_REFRESH[2]}px;
           height: {HOME_REFRESH[3]}px; border-radius: 13px; background: rgba(255,255,255,.10);
           box-shadow: inset 0 0 0 1px rgba(255,255,255,.16); display: flex; align-items: center; padding-left: 10px; }}
  .start {{ position: absolute; left: 650px; top: 34px; }}
  .start b {{ display: block; font: 700 21px "Barlow Semi Condensed", "Segoe UI", sans-serif; color: #0B2A5B; }}
  .start span {{ display: block; margin-top: 3px; font-size: 10px; color: #7A889C; }}
  .row {{ position: absolute; display: flex; align-items: center; gap: 18px; padding: 0 18px; }}
  .row .idx {{ font: 700 10.5px Inter, sans-serif; color: #A3B1C6; }}
  .row .name {{ font: 600 15px "Segoe UI Semibold", Inter, sans-serif; color: #0B2A5B; margin-top: 1px; }}
  .row .qq {{ font-size: 9.5px; color: #5A6B85; margin-top: 3px; }}
  .row .hl {{ font-size: 8.8px; color: #7A889C; margin-top: 6px; }}
  .row .go {{ width: 34px; height: 34px; border-radius: 17px; background: #0B2A5B; color: #fff; display: grid;
             place-items: center; font-size: 15px; flex: none; }}
  .row .tbv {{ display: inline-block; margin-left: 8px; padding: 2px 7px; border-radius: 8px; font: 600 8px Inter;
              color: #B4541B; background: #FDEBDD; vertical-align: 2px; }}
  .guide {{ position: absolute; padding: 16px 20px; }}
  .guide b.t {{ font: 600 12px "Segoe UI Semibold", Inter, sans-serif; color: #0B2A5B; }}
  .legend {{ display: flex; gap: 22px; margin-top: 12px; font-size: 9.5px; color: #1B2A41; }}
  .legend i {{ display: inline-block; width: 18px; height: 8px; border-radius: 4px; margin-right: 7px; vertical-align: -1px; }}
  .defs {{ margin-top: 12px; font-size: 9px; line-height: 1.75; color: #5A6B85; }}
  .defs b {{ color: #1B2A41; }}
"""

HOME_PAGES = {  # page key: (question, highlights)
    "overview": ("How many inspections pass, and where do they fail?",
                 "Pass % vs the 95 % target · Pass & Fail by part and by test · where inspections fail"),
    "chars": ("How do measured values evolve, and which characteristics fail?",
              "Measured values per day · Pass & Fail % by part and by test · results per characteristic"),
    "rl": ("Where are measurements getting close to the limit?",
           "Violations per day · top 15 characteristics · details: value, limits, tolerance"),
    "cpk": ("Which parts, tests and characteristics are capable?",
            "Cpk pass % · Cpk by part and by test · Cpk of each characteristic"),
}


def mini_preview(key, w, h):
    """Small drawing of a page, in its colours (decoration only, not data)."""
    blue, orange, rl, navy = "#2F6EBA", "#ED7D31", "#1F4E79", "#0B2A5B"
    wave = [.62, .58, .66, .6, .7, .45, .6, .62, .64, .57, .66, .7, .63]

    def line(vals, x0, y0, ww, hh, color, area=True):
        pts = [(x0 + i * ww / (len(vals) - 1), y0 + hh - v * hh) for i, v in enumerate(vals)]
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        a = f'<path d="{d} L{x0 + ww:.1f} {y0 + hh} L{x0} {y0 + hh} Z" fill="{color}" fill-opacity=".12"/>' if area else ""
        return a + f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>'

    s = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" rx="9" fill="#F3F6FB"/>'
    if key == "overview":
        s += (f'<path d="M14 {h - 14} A20 20 0 0 1 54 {h - 14}" fill="none" stroke="#DCE5F2" stroke-width="7"/>'
              f'<path d="M14 {h - 14} A20 20 0 0 1 49 {h - 26}" fill="none" stroke="{blue}" stroke-width="7"/>'
              f'<path d="M66 12H{w - 10}" stroke="{navy}" stroke-opacity=".4" stroke-dasharray="3 3"/>'
              + line(wave, 66, 16, w - 76, h - 28, blue))
    elif key == "chars":
        s += line(wave[::-1], 10, 8, w - 20, (h - 16) * .5, blue)
        for i, frac in enumerate((.9, .74, .6)):
            y = 10 + (h - 16) * .6 + i * 7
            s += (f'<rect x="10" y="{y:.0f}" width="{(w - 20) * frac * .8:.0f}" height="4.5" rx="2" fill="{blue}"/>'
                  f'<rect x="{10 + (w - 20) * frac * .8:.0f}" y="{y:.0f}" width="{(w - 20) * .1:.0f}" height="4.5" rx="2" fill="{orange}"/>')
    elif key == "rl":
        s += line([.2, .5, .45, .8, .62, .9, .55, .7, .4, .65], 10, 10, w * .55, h - 20, rl, area=False)
        x0, tw, th = w * .62, w * .38 - 10, h - 20
        s += (f'<rect x="{x0:.0f}" y="10" width="{tw * .55:.0f}" height="{th:.0f}" rx="3" fill="{rl}"/>'
              f'<rect x="{x0 + tw * .58:.0f}" y="10" width="{tw * .42:.0f}" height="{th * .55:.0f}" rx="3" fill="#3E6C9E"/>'
              f'<rect x="{x0 + tw * .58:.0f}" y="{10 + th * .58:.0f}" width="{tw * .42:.0f}" height="{th * .42:.0f}" rx="3" fill="#7C9CC6"/>')
    else:
        cx, base = w * .5, h - 12
        s += (f'<path d="M10 {base} C{cx - 30} {base} {cx - 22} 12 {cx} 12 S{cx + 30} {base} {w - 10} {base}" fill="{blue}" '
              f'fill-opacity=".14" stroke="{blue}" stroke-width="1.8"/>'
              f'<path d="M{w * .16:.0f} 8V{base}M{w * .84:.0f} 8V{base}" stroke="{orange}" stroke-dasharray="3 3"/>')
    return s + "</svg>"


def home_body():
    logo = BRAND / "logo_white.png"
    logo_html = (f'<img class="logo" src="{_data_uri(logo)}" alt="">' if logo.exists()
                 else '<div class="kicker" style="top:56px">OPmobility</div>')
    facts = {"plants": ("", "plants"), "months": ("12 months", "rolling history"),
             "values": ("", "measured values"), "daily": ("Daily", "refresh from Databricks")}
    fact_html = "".join(
        f'<div class="fact" style="top:{HOME_FACT_Y[k]}px"><b>{facts[k][0]}</b><span>{facts[k][1]}</span></div>'
        for k, _ in HOME_FACTS)
    rows = ""
    for i, (label, key) in enumerate(NAV):
        x, y, w, h = HOME_ROWS[key]
        question, highlights = HOME_PAGES[key]
        tbv = '<span class="tbv">To be validated</span>' if PAGES[key].get("status") else ""
        rows += (f'<div class="plate row" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px">'
                 f'{mini_preview(key, 150, 76)}<div style="flex:1"><div class="idx">0{i + 1}</div>'
                 f'<div class="name">{html.escape(label)}{tbv}</div><div class="qq">{html.escape(question)}</div>'
                 f'<div class="hl">{html.escape(highlights)}</div></div><div class="go">›</div></div>')
    gx, gy, gw, gh = HOME_GUIDE
    guide = (f'<div class="plate guide" style="left:{gx}px;top:{gy}px;width:{gw}px;height:{gh}px">'
             f'<b class="t">Reading guide</b><div class="legend">'
             f'<span><i style="background:#2F6EBA"></i>Pass</span><span><i style="background:#ED7D31"></i>Fail</span>'
             f'<span><i style="background:#1F4E79"></i>Reaction limits</span>'
             f'<span><i style="width:22px;height:0;border-top:2px dashed #0B2A5B;border-radius:0"></i>Target 95 %</span></div>'
             f'<div class="defs"><b>Inspection</b> one result per test on a part · <b>Measured value</b> one characteristic '
             f'measured once<br><b>Violation</b> a value that passes but is outside the reaction (alert) limits · '
             f'<b>Cpk</b> process capability, min(USL − mean, mean − LSL) / 3σ<br>'
             f'Results not assessed or not evaluated are left out of the percentages</div></div>')
    return (f'<div class="hero">{tolerance_motif()}{logo_html}<div class="kicker">Plant Visual Management</div>'
            f'<h1>Quality<br>Dashboard</h1><div class="lead">The daily review of quality results in series production: '
            f'inspections, measured values, reaction limits and capability, for every plant.</div>{fact_html}'
            f'<div class="hpill">{icon("clock", 13, "rgba(255,255,255,.72)", 1.7)}</div></div>'
            f'<div class="start"><b>Where do you want to start?</b><span>Each page answers one question. '
            f'Filters follow you from page to page.</span></div>{rows}{guide}')
