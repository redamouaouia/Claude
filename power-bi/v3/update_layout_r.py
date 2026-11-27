"""Plant visual management dashboard V17 / V18: Overview with the key figures on top, filters centred in their wells.

Usage:  python update_layout_r.py <Relief .pbix (or .pbit)> [<output>]

- Overview: Pass rate, Failed inspections, Fail rate and Gap to target in the first row (key figures); below, the
  cumulative pass % and the failure tile on the left, the gauge (titled, with the period chosen) and the results table
  with its Part / Test switch on the right.
- Filter row of every page (V18: the wells keep their size, 44 px): slicers 30 px high under their name, responsive
  off, so that the value of a list is centred and the date range shows its two dates (at 25 px, responsive, Power BI
  folded it into a filter icon).
Render the Relief backgrounds first (README, step 11): every page background is replaced. Model, data and every other
setting are kept: the output has the type of the input (default: out/Plant visual management dashboard V17.<ext>).
"""
import json
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_period_filter as PF  # noqa: E402  (page titles)
import add_reaction_limits as A  # noqa: E402  (checks, writer, model fields)
import apply_design_r as AR  # noqa: E402  (Relief placement and backgrounds)
import pbit_package as pkg  # noqa: E402

OUT_NAME = "Plant visual management dashboard V17"


def main(src_path, dst):
    zin = zipfile.ZipFile(src_path)
    defs = pkg.definitions(zin)
    order = defs["pages/pages.json"]["pageOrder"]
    keys = {PF.TITLES[defs[f"pages/{p}/page.json"]["displayName"]]: p for p in order}
    page_keys = {pid: k for k, pid in keys.items()}
    if "PlantVMRelief" not in json.dumps(defs[f"pages/{keys['overview']}/page.json"].get("objects", {})):
        sys.exit("this report is not in the Relief design")

    AR.arrange_overview(defs, keys["overview"], page_keys)
    for key, pid in keys.items():
        if key != "home":
            print(f"{key:11s} filter row: {AR.place_filter_row(defs, pid, key)} visuals")
    images, old = AR.set_backgrounds(defs, keys)

    problems = A.checks(defs, order)
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    if "DataModelSchema" in zin.namelist():
        pkg.check_fields(defs, json.loads(zin.read("DataModelSchema").decode("utf-16-le")))
    else:
        used, missing = pkg.report_fields(defs, A.model_fields(src_path))
        if missing:
            sys.exit("fields missing from the model: " + ", ".join(sorted({f"{e}[{p}]" for e, p, _ in missing})))
    A.write_pbix(zin, defs, images, old, dst)
    print(f"written {dst} ({pathlib.Path(dst).stat().st_size:,} bytes)")


if __name__ == "__main__":
    src = sys.argv[1]
    main(src, sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / f"{OUT_NAME}{pathlib.Path(src).suffix}"))
