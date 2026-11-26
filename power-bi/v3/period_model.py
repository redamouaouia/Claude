"""Period filter of the V3 report (client request): Day, WTD, MTD, YTD and Year, and the full model of the report.

- Day: the last 24 hours. Measurement times are the local time of each plant, so the 24 hours are counted back from
  the latest measurement of each plant (Databricks flags those rows in 'Quality Tracker'[Period Key]).
- WTD, MTD, YTD: since Monday, the 1st of the month, the 1st of January.
- Year: the last 12 months (chosen by default in the report).
The table Period is rebuilt at each refresh, from the day of the refresh (UTC): for each period, the values of
'Quality Tracker'[Period Key] it keeps (date as yyyymmdd x 10, + 1 for the last 24 hours of the plant). A slicer on
Period[Period] filters Quality Tracker through the relationship, so every visual follows it.
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cpk_model as cm  # noqa: E402
import cumul_model as cu  # noqa: E402
import overview_model as om  # noqa: E402
import trend_model as tm  # noqa: E402

bt = cm.bt
PERIOD = "Period"
PERIODS = [  # (value shown in the slicer, label of the selection)
    ("Day", "Last 24 hours"), ("WTD", "Week to date"), ("MTD", "Month to date"), ("YTD", "Year to date"),
    ("Year", "Last 12 months"),
]
DEFAULT_PERIOD = "Year"

PERIOD_M = "\n".join([
    "let",
    "    // Periods counted from the day of the refresh (UTC). Plants ahead of UTC can already be on the next day.",
    "    Today = Date.From(DateTimeZone.RemoveZone(DateTimeZone.FixedUtcNow())),",
    "    LastDay = Date.AddDays(Today, 1),",
    "    DateKey = (d as date) as number => (Date.Year(d) * 10000 + Date.Month(d) * 100 + Date.Day(d)) * 10,",
    "    Days = (first as date) as list => List.Dates(first, Duration.Days(LastDay - first) + 1, #duration(1, 0, 0, 0)),",
    "    // every value of the days: last 24 hours of the plant (+ 1) or not (+ 0)",
    "    AllKeys = (first as date) as list => List.Combine(List.Transform(Days(first), (d) => {DateKey(d), DateKey(d) + 1})),",
    "    Periods = {",
    '        {"Day", 1, List.Transform(Days(Date.AddDays(Today, -4)), (d) => DateKey(d) + 1)},',
    '        {"WTD", 2, AllKeys(Date.StartOfWeek(Today, Day.Monday))},',
    '        {"MTD", 3, AllKeys(Date.StartOfMonth(Today))},',
    '        {"YTD", 4, AllKeys(Date.StartOfYear(Today))},',
    '        {"Year", 5, AllKeys(Date.AddDays(Date.AddMonths(Today, -12), 1))}',
    "    },",
    "    Rows = List.Combine(List.Transform(Periods, (p) => List.Transform(p{2}, (k) => {p{0}, p{1}, k}))),",
    '    Result = #table(type table [Period = text, Order = Int64.Type, #"Period Key" = Int64.Type], Rows)',
    "in",
    "    Result",
])

PERIOD_TABLE = dict(
    name=PERIOD,
    columns=[("Period", "string", "type text", False, None), ("Order", "int64", "Int64.Type", True, "0"),
             ("Period Key", "int64", "Int64.Type", True, "0")],
    measures=[], source_m=PERIOD_M, sort_by={"Period": "Order"},
    info={"Period": (None, "Day = last 24 hours, WTD = week to date, MTD = month to date, YTD = year to date, "
                           "Year = last 12 months (default)."),
          "Period Key": (None, "Value of 'Quality Tracker'[Period Key] kept by the period.")})

# Quality Tracker is filtered by Period: many to many on Period Key, one direction.
RELATIONSHIPS = [(bt.T, "Period Key", PERIOD, "Period Key", "many")]

PERIOD_MEASURES = [
    ("Period Label",
     "SWITCH(\n\tSELECTEDVALUE('Period'[Period]),\n"
     + "".join(f'\t"{v}", "{label}",\n' for v, label in PERIODS) + '\t"All loaded data"\n)',
     None, "Report", "The period chosen in the period filter, in words (subtitle of the Pass rate figure).", None),
]


def write_model(work, settings):
    """The whole model of the report: Quality Tracker with all its measures, the two Cpk lists and Period."""
    measures = (cm.CPK_MEASURES + cm.HOME_MEASURES + PERIOD_MEASURES + tm.TREND_MEASURES + om.OVERVIEW_MEASURES
                + cu.CUMUL_MEASURES)
    return bt.write_model(work, settings, extra_measures=measures,
                          extra_tables=cm.extra_tables() + [PERIOD_TABLE], policy=cm.QT_POLICY,
                          relationships=RELATIONSHIPS)
