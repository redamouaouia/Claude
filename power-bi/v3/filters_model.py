"""More filters (client feedback): the More filters button shows when its filters have a selection.

One pair of measures per panel, as the panels differ from page to page: the number of filters of the panel with a
selection, and the colour of the outline of the button (Fail orange when there is one, else white: no change on the
white button).
"""
Q = "'Quality Tracker'"
PANELS = {  # set: (pages, columns of the More filters panel)
    "1": (("overview", "chars", "fails"), [f"{Q}[KPC]", f"{Q}[Press]"]),
    "2": (("rl",), [f"{Q}[Inspection Reason]", f"{Q}[KPC]"]),
    "3": (("cpk",), [f"{Q}[Inspection Reason]", "'Cpk Threshold'[Threshold]", "'Cpk Status'[Status]"]),
    "4": (("trend",), [f"{Q}[Inspection Reason]", "'Cpk Threshold'[Threshold]"]),
}
FOLDER = "More filters"


def set_of(page_key):
    return next(k for k, (pages, _) in PANELS.items() if page_key in pages)


FILTER_MEASURES = []  # (name, expression, format, folder, description, dynamic format)
for key, (pages, columns) in PANELS.items():
    count = f"More Filters On {key}"
    names = ", ".join(c.split("[")[1].rstrip("]") for c in columns)
    FILTER_MEASURES += [
        (count, " +\n".join(f"INT(ISFILTERED({c}))" for c in columns), "0", FOLDER,
         f"Filters of the More filters panel ({names}) with a selection; pages: {', '.join(pages)}.", None),
        (f"More Filters Outline {key}", f'IF([{count}] > 0, "#ED7D31", "#FFFFFF")', None, FOLDER,
         "Outline of the More filters button: Fail orange when a filter of its panel has a selection, else white.",
         None),
    ]
