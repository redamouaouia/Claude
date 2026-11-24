"""Measures of page 5, Trend chart: measured values of one characteristic against its limits, and its Cpk.

Part, Test and Characteristic are mandatory: the trend needs exactly one Cpk group (plant, part, test and
characteristic) in the filters. Otherwise the chart stays empty and its subtitle says what to select.
- Points: 'Quality Tracker'[Measured Value] by [Measured At] (each value that enters the Cpk, in time order).
- Lines: USL / LSL (specification limits), UCL / LCL (reaction or control limits) of the last measurement, X bar.
- Cards: reaction limit violations, Cpk against the threshold of More filters (1.33 if none) with Pass / Fail.
"""
Q = "'Quality Tracker'"
AT = f"{Q}[Measured At]"
GROUPS = "[Trend Groups]"


def _limit(column):
    return f"IF({GROUPS} = 1, CALCULATE(MAX({Q}[{column}]), REMOVEFILTERS({AT})))"


TREND_MEASURES = [  # (name, expression, format, folder, description, dynamic format)
    ("Trend Groups", f"CALCULATE(DISTINCTCOUNTNOBLANK({Q}[Cpk Group]), REMOVEFILTERS({AT}))", "#,0", "Trend",
     "Plant, part, test and characteristic combinations (Cpk groups) in the filters: the trend needs exactly one.",
     None),
    ("Trend Value", f"IF({GROUPS} = 1, AVERAGE({Q}[Measured Value]))", "0.####", "Trend",
     "Measured value at each time (average when several values share the same time).", None),
    ("Trend USL", _limit("Cpk USL"), "0.####", "Trend", "Upper specification limit (last measurement).", None),
    ("Trend LSL", _limit("Cpk LSL"), "0.####", "Trend", "Lower specification limit (last measurement).", None),
    ("Trend UCL", _limit("Cpk UCL"), "0.####", "Trend", "Upper reaction (control) limit (last measurement).", None),
    ("Trend LCL", _limit("Cpk LCL"), "0.####", "Trend", "Lower reaction (control) limit (last measurement).", None),
    ("Trend Mean", f"IF({GROUPS} = 1, CALCULATE([Cpk X Bar], REMOVEFILTERS({AT})))", "0.####", "Trend",
     "Mean of the measured values (X bar).", None),
    # The value axis covers the values and every limit line (Power BI does not widen it for constant lines).
    ("Trend Axis Min",
     f"VAR lo = MINX({{CALCULATE(MIN({Q}[Measured Value]), REMOVEFILTERS({AT})), [Trend LSL], [Trend LCL]}}, [Value])\n"
     f"VAR hi = MAXX({{CALCULATE(MAX({Q}[Measured Value]), REMOVEFILTERS({AT})), [Trend USL], [Trend UCL]}}, [Value])\n"
     f"RETURN\n\tIF({GROUPS} = 1, lo - IF(hi > lo, (hi - lo) * 0.08, 1))", "0.####", "Trend\\Axis", None, None),
    ("Trend Axis Max",
     f"VAR lo = MINX({{CALCULATE(MIN({Q}[Measured Value]), REMOVEFILTERS({AT})), [Trend LSL], [Trend LCL]}}, [Value])\n"
     f"VAR hi = MAXX({{CALCULATE(MAX({Q}[Measured Value]), REMOVEFILTERS({AT})), [Trend USL], [Trend UCL]}}, [Value])\n"
     f"RETURN\n\tIF({GROUPS} = 1, hi + IF(hi > lo, (hi - lo) * 0.08, 1))", "0.####", "Trend\\Axis", None, None),
    ("Trend Subtitle",
     f"VAR g = {GROUPS}\n"
     f"VAR c = CALCULATE(SELECTEDVALUE({Q}[Characteristic]), REMOVEFILTERS({AT}), KEEPFILTERS(NOT ISBLANK({Q}[Cpk Group])))\n"
     f"VAR p = CALCULATE(SELECTEDVALUE({Q}[Part]), REMOVEFILTERS({AT}), KEEPFILTERS(NOT ISBLANK({Q}[Cpk Group])))\n"
     f"VAR t = CALCULATE(SELECTEDVALUE({Q}[Test]), REMOVEFILTERS({AT}), KEEPFILTERS(NOT ISBLANK({Q}[Cpk Group])))\n"
     f"VAR n = CALCULATE(COUNT({Q}[Measured Value]), REMOVEFILTERS({AT}))\n"
     "RETURN\n\tSWITCH(\n\t\tTRUE(),\n"
     '\t\tg = 0, "No measured value of a variable characteristic in the current filters",\n'
     '\t\tg > 1, "Select one part, one test and one characteristic (filters marked *)",\n'
     '\t\tc & " · " & p & " · " & t & " · " & FORMAT(n, "#,0") & " measured values"\n\t)',
     None, "Trend", "Subtitle of the trend chart: what it shows, or what to select.", None),
    ("Trend Cpk", f"IF({GROUPS} = 1, [Cpk Value])", "0.00", "Trend", "Cpk of the characteristic shown.", None),
    ("Trend Title",
     f'IF({GROUPS} = 1, "Trend chart – measured values vs limits", '
     '"Trend chart – select one part, one test and one characteristic")',
     None, "Trend", "Title of the trend chart: says what to select while the chart is empty.", None),
    ("Trend Cpk Goal",
     'VAR goal = "Goal " & FORMAT([Cpk Threshold], "0.00")\nRETURN\n'
     f'\tIF({GROUPS} = 1, goal & " · " & [Cpk Status Label], goal & " · select one characteristic")',
     None, "Trend", "Subtitle of the Cpk card: threshold (More filters, 1.33 if none) and Pass / Fail.", None),
]
