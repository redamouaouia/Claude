"""Quality Dashboard V12: home page without the navigation rail; model and data kept.

Usage:  python update_home_page.py <V11 .pbix saved by Power BI Desktop> [<output .pbix>]

The rows of the home page open the pages, so the rail of the analysis pages (page tiles, Clear filters) is not
repeated there: its buttons are removed and the hero panel goes to the left edge. The visuals of the home page are
built again (rows, refresh time, live figures), every page background is replaced by the current render (out/bg_*.png,
see the README); the other pages, the data model and its data are kept as they are.
Output: out/Quality_Dashboard_V12.pbix by default (git-ignored).
"""
import pathlib
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_home_and_cpk as H  # noqa: E402  (home page builder)
import add_period_filter as PF  # noqa: E402  (page titles, backgrounds)
import add_reaction_limits as A  # noqa: E402  (page index, checks, .pbix writer, model fields)
import pbit_package as pkg  # noqa: E402


def main(src_path, dst):
    zin = zipfile.ZipFile(src_path)
    defs = pkg.definitions(zin)
    order = defs["pages/pages.json"]["pageOrder"]
    keys = {}
    for pid in order:
        title = defs[f"pages/{pid}/page.json"]["displayName"]
        if title not in PF.TITLES:
            sys.exit(f"unexpected page '{title}'")
        keys[PF.TITLES[title]] = pid
    page_keys = {pid: k for k, pid in keys.items()}
    src = {v["name"]: v for k, v in defs.items() if k.startswith(f"pages/{keys['chars']}/visuals/")}
    idx = A.index_page(src, page_keys)
    missing = [r for r in ("nav:overview", "x_btn", "refresh") if r not in idx]
    if missing:
        sys.exit(f"page Characteristics: could not find {missing}")

    home = keys["home"]
    gone = [k for k in defs if k.startswith(f"pages/{home}/visuals/")]
    for k in gone:
        del defs[k]
    built = H.build_home_page(src, idx, keys)
    for i, v in enumerate(built):
        v["position"]["z"] = v["position"]["tabOrder"] = i * 1000
        defs[f"pages/{home}/visuals/{v['name']}/visual.json"] = v
    images, old = PF.set_backgrounds(defs, keys)

    problems = A.checks(defs, order)
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    used, missing_fields = pkg.report_fields(defs, A.model_fields(src_path))
    if missing_fields:
        sys.exit("fields missing from the model of the .pbix: " + ", ".join(sorted({f"{e}[{p}]" for e, p, _ in missing_fields})))
    A.write_pbix(zin, defs, images, old, dst)
    print(f"home page: {len(gone)} visuals replaced by {len(built)} (no navigation rail); {len(images)} backgrounds; "
          f"report fields OK ({len(used)}); written {dst} ({pathlib.Path(dst).stat().st_size:,} bytes)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / "Quality_Dashboard_V12.pbix"))
