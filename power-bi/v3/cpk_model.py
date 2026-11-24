"""Cpk measures of V3 page 4 and the measures of the home page.

Cpk follows the method of the QDA report (Cpk query of the specification, "matches Excel"):
- one Cpk per plant, part, test and characteristic, on variable characteristics with a Pass or Fail result;
- X bar = mean of the measured values; R bar = mean of the moving ranges |x(i) - x(i-1)|, values in time order;
- sigma = R bar / 1.128 (d2 for moving ranges of 2 values);
- Cpk = min(USL - X bar, X bar - LSL) / (3 sigma), or the one side that has a limit.
Databricks writes the sums on Quality Tracker itself (columns "Cpk ...", see build_template.SQL_LINES): one row per
characteristic, inspection reason and day carries the sums of that day. Power BI adds them up for the days selected
and recomputes Cpk, so the Cpk page has the same filters as the other pages.
Besides Quality Tracker, the model only has two small lists for the report: the Cpk thresholds offered in More
filters (1.33 when none is chosen: CPMIN of the QDA statistical method is not in the data) and the Pass / Fail
statuses of the donut.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "v2"))
import build_template as bt  # noqa: E402

C = f"'{bt.T}'"
GROUPS = f"FILTER(ADDCOLUMNS(VALUES({C}[Cpk Group]), \"@cpk\", [Cpk Value]), NOT ISBLANK([@cpk]))"
CPK_MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Cpk Measured Values", f"SUM({C}[Cpk Value Count])", "#,0", "Cpk", "Measured values used for Cpk.", None),
    ("Cpk X Bar", f"DIVIDE(SUM({C}[Cpk Value Sum]), SUM({C}[Cpk Value Count]))", "0.####", "Cpk\\Details",
     "Mean of the measured values.", None),
    ("Cpk Sigma", f"DIVIDE(DIVIDE(SUM({C}[Cpk Range Sum]), SUM({C}[Cpk Range Count])), 1.128)", "0.####",
     "Cpk\\Details", "Short-term standard deviation: mean moving range / 1.128.", None),
    # Written for speed: plain sums and DIVIDE (blank when sigma is 0 or missing), one pass, no nested measures.
    ("Cpk Value",
     f"VAR xbar = DIVIDE(SUM({C}[Cpk Value Sum]), SUM({C}[Cpk Value Count]))\n"
     f"VAR sigma = DIVIDE(SUM({C}[Cpk Range Sum]), SUM({C}[Cpk Range Count])) / 1.128\n"
     f"VAR usl = MAX({C}[Cpk USL])\nVAR lsl = MAX({C}[Cpk LSL])\n"
     "VAR up = DIVIDE(usl - xbar, 3 * sigma)\nVAR down = DIVIDE(xbar - lsl, 3 * sigma)\nRETURN\n"
     "\tSWITCH(\n\t\tTRUE(),\n\t\tISBLANK(usl) && ISBLANK(lsl), BLANK(),\n\t\tISBLANK(usl), down,\n"
     "\t\tISBLANK(lsl), up,\n\t\tMIN(up, down)\n\t)",
     "0.00", "Cpk", "Cpk of one plant, part, test and characteristic (one Cpk group), on the days selected.",
     None),
    ("Cpk Threshold", "SELECTEDVALUE('Cpk Threshold'[Threshold], 1.33)", "0.00", "Cpk",
     "Threshold chosen in More filters, 1.33 when none is chosen.", None),
    ("Cpk Characteristics", f"COUNTROWS({GROUPS})", "#,0", "Cpk", "Characteristics that have a Cpk.", None),
    ("Cpk Pass", f"VAR t = [Cpk Threshold]\nVAR g = {GROUPS}\nRETURN\n\tIF(NOT ISEMPTY(g), COUNTROWS(FILTER(g, [@cpk] >= t)) + 0)",
     "#,0", "Cpk", "Characteristics with Cpk at or above the threshold.", None),
    ("Cpk Fail", f"VAR t = [Cpk Threshold]\nVAR g = {GROUPS}\nRETURN\n\tIF(NOT ISEMPTY(g), COUNTROWS(FILTER(g, [@cpk] < t)) + 0)",
     "#,0", "Cpk", "Characteristics with Cpk below the threshold.", None),
    ("Cpk Pass %", f"VAR t = [Cpk Threshold]\nVAR g = {GROUPS}\nRETURN\n\tDIVIDE(COUNTROWS(FILTER(g, [@cpk] >= t)), COUNTROWS(g))",
     "0.0%", "Cpk", "Share of characteristics with Cpk at or above the threshold.", None),
    ("Cpk Fail %", "VAR p = [Cpk Pass %]\nRETURN\n\tIF(NOT ISBLANK(p), 1 - p)", "0.0%", "Cpk", None, None),
    ("Cpk Pass Of Total",
     'VAR n = [Cpk Characteristics]\nRETURN\n\tIF(n > 0, FORMAT([Cpk Pass], "#,0") & " of " & FORMAT(n, "#,0") & " characteristics", "")',
     None, "Cpk", "Under Cpk pass %: characteristics at or above the threshold, out of those that have a Cpk.", None),
    ("Cpk Pass Bar", "[Cpk Pass]", None, "Cpk\\Bars", "Bar length = characteristics, label = share.",
     '"""" & FORMAT([Cpk Pass %], "0.0%") & """"'),
    ("Cpk Fail Bar", "[Cpk Fail]", None, "Cpk\\Bars", None, '"""" & FORMAT([Cpk Fail %], "0.0%") & """"'),
    ("Cpk Status", "VAR c = [Cpk Value]\nRETURN\n\tIF(NOT ISBLANK(c), IF(c >= [Cpk Threshold], \"Pass\", \"Fail\"))",
     None, "Cpk", None, None),
    ("Cpk Status Label", "SWITCH([Cpk Status], \"Pass\", \"✔ Pass\", \"Fail\", \"✖ Fail\")", None, "Cpk", None, None),
    ("Cpk Status Color", "SWITCH([Cpk Status], \"Pass\", \"#2F6EBA\", \"Fail\", \"#ED7D31\")", None, "Cpk\\Details",
     "Colour of the status label.", None),
    ("Cpk Status Count", "SWITCH(SELECTEDVALUE('Cpk Status'[Status]), \"Pass\", [Cpk Pass], \"Fail\", [Cpk Fail])",
     "#,0", "Cpk", "Characteristics per status, for the donut.", None),
    # Detail table: Top 100 by this measure = the 100 lowest Cpk with the status chosen (Pass / Fail filter or
    # donut). Blank otherwise, so those characteristics drop out before the Top 100 is taken.
    ("Cpk Detail Rank",
     "VAR c = [Cpk Value]\nVAR s = IF(c >= [Cpk Threshold], \"Pass\", \"Fail\")\nRETURN\n"
     "\tIF(\n\t\tNOT ISBLANK(c) && (NOT ISFILTERED('Cpk Status'[Status]) || s IN VALUES('Cpk Status'[Status])),\n"
     "\t\t-c\n\t)", "0.00", "Cpk\\Details",
     "Minus the Cpk when the status is the one chosen: the detail table keeps its Top 100.", None),
]
DETAIL_ROWS = 100  # characteristics listed in the detail table: the lowest Cpk first

HOME_MEASURES = [
    ("Plants", "DISTINCTCOUNT('Quality Tracker'[Plant])", "#,0", "Report", "Plants in the data.", None),
    ("Home Measured Values", "FORMAT([Measured Values] / 1000000, \"0.0\") & \" M\"", None, "Report",
     "Measured values in millions, for the home page.", None),
]

# Incremental refresh of Quality Tracker, as set by the user: 12 months kept, the last 7 days refreshed.
QT_POLICY = ("month", 12, "day", 7)


def extra_tables():
    """The two lists of the Cpk page (no link to Quality Tracker: measures read them)."""
    return [
        dict(name="Cpk Threshold", columns=[("Threshold", "double", "type number", False, "0.00")], measures=[],
             source_m="let\n    Source = #table(type table [Threshold = number], {{1}, {1.33}, {1.67}, {2}})\nin\n    Source"),
        dict(name="Cpk Status", columns=[("Status", "string", "type text", False, None),
                                         ("Order", "int64", "Int64.Type", True, "0")], measures=[],
             source_m='let\n    Source = #table(type table [Status = text, Order = Int64.Type], {{"Pass", 1}, {"Fail", 2}})'
                      "\nin\n    Source",
             sort_by={"Status": "Order"}),
    ]
