"""Cumulative measures (client request): every visual shows the cumulative of the selected period.

The figures, gauges and tables already add up the whole selection (period filter, date filter and every other filter).
The charts over time (by month or by day) and the cards with a trend line use these measures: at each point, the total
from the start of the selection up to that point. In a card (no date in context) they give the total of the selection,
so the figure stays the cumulative of the period and its trend line becomes a cumulative line.
- ALLSELECTED(Date) keeps what the slicers select on Date and drops the date of the axis point;
- the period filter acts through the table Period, so it stays as it is;
- REMOVEFILTERS(Month) drops the month of the axis point on a chart by month.
"""
Q = "'Quality Tracker'"


def cumul(measure):
    return (f"VAR _last = MAX({Q}[Date])\nRETURN\n\tIF(\n\t\tNOT ISBLANK(_last),\n\t\tCALCULATE(\n\t\t\t[{measure}],\n"
            f"\t\t\tALLSELECTED({Q}[Date]),\n\t\t\tREMOVEFILTERS({Q}[Month]),\n\t\t\t{Q}[Date] <= _last\n\t\t)\n\t)")


CUMUL_MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Inspection Pass % Cumul", cumul("Inspection Pass %"), "0.0%", "Cumulative",
     "Inspection pass rate from the start of the selection (period, dates, filters) up to each point.", None),
    ("Char Pass % Cumul", cumul("Char Pass %"), "0.0%", "Cumulative",
     "Characteristic pass rate from the start of the selection up to each point.", None),
    ("Measured Values Cumul", cumul("Measured Values"), "#,0", "Cumulative",
     "Measured values from the start of the selection up to each point.", None),
    ("Char Pass Cumul", cumul("Char Pass"), "#,0", "Cumulative",
     "Measured values within tolerance from the start of the selection up to each point.", None),
    ("Char Fail Cumul", cumul("Char Fail"), "#,0", "Cumulative",
     "Measured values out of tolerance from the start of the selection up to each point.", None),
    ("RL Violations Cumul", cumul("RL Violations"), "#,0", "Cumulative",
     "Values outside the reaction limits from the start of the selection up to each point.", None),
]
