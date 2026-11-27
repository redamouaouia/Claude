"""More filters (client feedback): the More filters button shows how many of its filters have a selection.

One set of measures per panel, as the panels differ from page to page: the number of filters of the panel with a
selection, the text of the badge (that number, empty when none) and its colour (Fail orange, or white: the badge
disappears on the white button).
"""
Q = "'Quality Tracker'"
PANELS = {  # set: (pages, columns of the More filters panel)
    "1": (("overview", "chars", "fails"), [f"{Q}[KPC]", f"{Q}[Press]", f"{Q}[Process Name]"]),
    "2": (("rl",), [f"{Q}[Inspection Reason]", f"{Q}[KPC]", f"{Q}[Process Name]"]),
    "3": (("cpk",), [f"{Q}[Inspection Reason]", "'Cpk Threshold'[Threshold]", "'Cpk Status'[Status]",
                     f"{Q}[Process Name]"]),
    "4": (("trend",), [f"{Q}[Inspection Reason]", "'Cpk Threshold'[Threshold]", f"{Q}[Process Name]"]),
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
        (f"More Filters Badge {key}", f'VAR n = [{count}]\nRETURN\n\tIF(n > 0, FORMAT(n, "0"), "")', None, FOLDER,
         "Text of the badge of the More filters button: the number of filters with a selection, empty when none.",
         None),
        (f"More Filters Badge Color {key}", f'IF([{count}] > 0, "#ED7D31", "#FFFFFF")', None, FOLDER,
         "Colour of the badge: Fail orange when a filter of the panel has a selection, else white (not visible).",
         None),
    ]
