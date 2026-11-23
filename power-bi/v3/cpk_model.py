"""Model additions of V3 page 4 (Cpk) and of the home page.

Cpk follows the method of the QDA report (Cpk query of the specification, "matches Excel"):
- one Cpk per plant, part, test and characteristic, on variable characteristics with a Pass or Fail result;
- X bar = mean of the measured values; R bar = mean of the moving ranges |x(i) - x(i-1)|, values in time order;
- sigma = R bar / 1.128 (d2 for moving ranges of 2 values);
- Cpk = min(USL - X bar, X bar - LSL) / (3 sigma), or the one side that has a limit.
Databricks returns sums per month (and inspection reason), so that Power BI recomputes Cpk for the months selected.
The table has no Cpk threshold (CPMIN of the QDA statistical method): it is chosen in the report, 1.33 by default.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "v2"))
import build_template as bt  # noqa: E402

CPK = "Cpk"
SOURCE = bt.SOURCE_TABLE
PART = ("CASE WHEN endswith(key_inspection_plan_plant, concat('_', plant)) "
        "THEN left(key_inspection_plan_plant, length(key_inspection_plan_plant) - length(plant) - 1) "
        "ELSE key_inspection_plan_plant END")
GROUP = "PARTITION BY Plant, Part, Test, Characteristic ORDER BY date_time, Inspection"
CPK_SQL_LINES = [
    "WITH v AS (",
    "  SELECT",
    "    plant AS Plant,",
    f"    {PART} AS Part,",
    "    process AS Test,",
    "    characteristic AS Characteristic,",
    "    NULLIF(trim(reason_for_inspection), '') AS Reason,",
    "    CAST(date_trunc('MONTH', posting_date) AS DATE) AS Month,",
    "    date_time,",
    "    key_order_inspection_plan_index_plant AS Inspection,",
    "    characteristic_value_num AS X,",
    "    usl_inspection_plan AS USL,",
    "    lsl_inspection_plan AS LSL",
    f"  FROM {SOURCE}",
    "  WHERE posting_date >= DATE'{start}' AND posting_date < DATE'{end}'",
    "    AND characteristic_type = 'variable'",
    "    AND characteristic_status IN ('OK', 'KO')",
    "    AND characteristic_value_num IS NOT NULL",
    "    AND characteristic_value_num < 100000",
    "    AND (usl_inspection_plan IS NOT NULL OR lsl_inspection_plan IS NOT NULL)",
    "), r AS (",
    "  SELECT *,",
    f"    abs(X - lag(X) OVER ({GROUP})) AS MR,",
    f"    last_value(USL) OVER ({GROUP} ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS LastUSL,",
    f"    last_value(LSL) OVER ({GROUP} ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS LastLSL",
    "  FROM v",
    ")",
    "SELECT",
    "  Plant AS `Plant`, Part AS `Part`, Test AS `Test`, Characteristic AS `Characteristic`,",
    "  Reason AS `Inspection Reason`, Month AS `Month`,",
    "  concat_ws(' | ', Plant, Part, Test, Characteristic) AS `Group`,",
    "  count(*) AS `Values`, sum(X) AS `Sum Value`, count(MR) AS `Moving Ranges`, sum(MR) AS `Sum Moving Range`,",
    "  max(LastUSL) AS `USL`, max(LastLSL) AS `LSL`",
    "FROM r",
    "GROUP BY Plant, Part, Test, Characteristic, Reason, Month",
]

CPK_COLUMNS = [  # (name, TMDL dataType, M type, hidden, format)
    ("Plant", "string", "type text", False, None),
    ("Part", "string", "type text", False, None),
    ("Test", "string", "type text", False, None),
    ("Characteristic", "string", "type text", False, None),
    ("Inspection Reason", "string", "type text", False, None),
    ("Month", "dateTime", "type date", False, "MMM yy"),
    ("Group", "string", "type text", True, None),
    ("Values", "int64", "Int64.Type", True, "#,0"),
    ("Sum Value", "double", "type number", True, None),
    ("Moving Ranges", "int64", "Int64.Type", True, "#,0"),
    ("Sum Moving Range", "double", "type number", True, None),
    ("USL", "double", "type number", True, "0.####"),
    ("LSL", "double", "type number", True, "0.####"),
]
CPK_INFO = {
    "Group": (None, "Plant | part | test | characteristic: one Cpk per group."),
    "Values": (None, "Measured values of the group in the month (variable characteristics, Pass or Fail)."),
    "Sum Value": (None, "Sum of the measured values, for X bar."),
    "Moving Ranges": (None, "Number of moving ranges |x(i) - x(i-1)|, values in time order."),
    "Sum Moving Range": (None, "Sum of the moving ranges, for R bar."),
    "USL": (None, "Upper specification limit of the last measurement of the group."),
    "LSL": (None, "Lower specification limit of the last measurement of the group."),
}


def cpk_source_m():
    lines = [f"        {bt.m_text(x)}," for x in CPK_SQL_LINES]
    i = next(n for n, x in enumerate(CPK_SQL_LINES) if "{start}" in x)
    lines[i] = ('        "  WHERE posting_date >= DATE\'" & StartDate & "\' AND posting_date < DATE\'" & EndDate & "\'",')
    lines[-1] = lines[-1].rstrip(",")
    types = ",\n        ".join("{" + bt.m_text(c[0]) + ", " + c[2] + "}" for c in CPK_COLUMNS)
    return "\n".join([
        "let",
        "    // Cpk sums per month: Power BI recomputes Cpk for the months selected.",
        '    StartDate = Date.ToText(Date.From(RangeStart), [Format = "yyyy-MM-dd"]),',
        '    EndDate = Date.ToText(Date.From(RangeEnd), [Format = "yyyy-MM-dd"]),',
        "    Sql = Text.Combine({",
        *lines,
        '    }, "#(lf)"),',
        "    Source = Databricks.Query(DatabricksHost, DatabricksHttpPath,"
        " [Catalog = null, Database = null, EnableAutomaticProxyDiscovery = null]),",
        "    Result = Source(Sql),",
        "    Typed = Table.TransformColumnTypes(Result, {",
        "        " + types,
        "    })",
        "in",
        "    Typed",
    ])


def cpk_sql(start, end):
    return "\n".join(CPK_SQL_LINES).replace("{start}", start).replace("{end}", end)


C = "'Cpk'"
GROUPS = f"FILTER(ADDCOLUMNS(VALUES({C}[Group]), \"@cpk\", [Cpk Value]), NOT ISBLANK([@cpk]))"
CPK_MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Cpk Measured Values", f"SUM({C}[Values])", "#,0", "Cpk", "Measured values used for Cpk.", None),
    ("Cpk X Bar", f"DIVIDE(SUM({C}[Sum Value]), SUM({C}[Values]))", "0.####", "Cpk\\Details",
     "Mean of the measured values.", None),
    ("Cpk Sigma", f"DIVIDE(DIVIDE(SUM({C}[Sum Moving Range]), SUM({C}[Moving Ranges])), 1.128)", "0.####",
     "Cpk\\Details", "Short-term standard deviation: mean moving range / 1.128.", None),
    # Written for speed: plain sums and DIVIDE (blank when sigma is 0 or missing), one pass, no nested measures.
    ("Cpk Value",
     f"VAR xbar = DIVIDE(SUM({C}[Sum Value]), SUM({C}[Values]))\n"
     f"VAR sigma = DIVIDE(SUM({C}[Sum Moving Range]), SUM({C}[Moving Ranges])) / 1.128\n"
     f"VAR usl = MAX({C}[USL])\nVAR lsl = MAX({C}[LSL])\n"
     "VAR up = DIVIDE(usl - xbar, 3 * sigma)\nVAR down = DIVIDE(xbar - lsl, 3 * sigma)\nRETURN\n"
     "\tSWITCH(\n\t\tTRUE(),\n\t\tISBLANK(usl) && ISBLANK(lsl), BLANK(),\n\t\tISBLANK(usl), down,\n"
     "\t\tISBLANK(lsl), up,\n\t\tMIN(up, down)\n\t)",
     "0.00", "Cpk", "Cpk of one plant, part, test and characteristic (one Cpk group), on the months selected.",
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

# Incremental refresh: Quality Tracker as set by the user (12 months, last 7 days refreshed); Cpk by month.
QT_POLICY = ("month", 12, "day", 7)
CPK_POLICY = ("month", 12, "month", 1)


def extra_tables():
    return [
        dict(name=CPK, columns=CPK_COLUMNS, measures=CPK_MEASURES, source_m=cpk_source_m(), info=CPK_INFO,
             policy=CPK_POLICY),
        dict(name="Cpk Threshold", columns=[("Threshold", "double", "type number", False, "0.00")], measures=[],
             source_m="let\n    Source = #table(type table [Threshold = number], {{1}, {1.33}, {1.67}, {2}})\nin\n    Source"),
        dict(name="Cpk Status", columns=[("Status", "string", "type text", False, None),
                                         ("Order", "int64", "Int64.Type", True, "0")], measures=[],
             source_m='let\n    Source = #table(type table [Status = text, Order = Int64.Type], {{"Pass", 1}, {"Fail", 2}})'
                      "\nin\n    Source",
             sort_by={"Status": "Order"}),
    ]
