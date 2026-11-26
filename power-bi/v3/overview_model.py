"""Measures of the key figures of Overview (client request): failed inspections, fail rate, gap to the target.

- Failed inspections and fail rate: [Inspections Fail] and [Inspection Fail %], already in the model.
- Gap to target: pass rate minus the target ([Pass % Target], 95 %) in percentage points, e.g. "−2.7 pp"; blank
  without assessed inspections. Its colour: orange (Fail) below the target, blue (Pass) at or above it.
"""
OVERVIEW_MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Pass % Gap",
     "VAR _pass = [Inspection Pass %]\nRETURN\n\tIF(NOT ISBLANK(_pass), (_pass - [Pass % Target]) * 100)",
     '+0.0" pp";"−"0.0" pp";0.0" pp"', "Inspections",
     "Pass rate minus the target (Pass % Target, 95 %), in percentage points: negative below the target.", None),
    ("Pass % Gap Color",
     'IF([Pass % Gap] < 0, "#ED7D31", "#2F6EBA")', None, "Inspections",
     "Colour of the gap to the target: orange (Fail) below the target, blue (Pass) at or above it.", None),
]
