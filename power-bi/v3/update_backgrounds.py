"""Quality Dashboard V3: replace the page backgrounds of a .pbix with the current renders, nothing else.

Usage:  python update_backgrounds.py <.pbix saved by Power BI Desktop> [<output .pbix>]

Renders expected in out/ (see README): bg_overview.png, bg_chars.png, bg_rl.png, bg_rl_details.png.
The data model, its data, the refresh policy, the visuals, filters and bookmarks are kept as they are.
Output: out/Quality_Dashboard_V4.pbix by default (git-ignored).
"""
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_reaction_limits as A  # noqa: E402  (checks, background setter, .pbix writer)
import design as D  # noqa: E402
import pbit_package as pkg  # noqa: E402

KEYS = {D.PAGES[k]["title"]: k for k in D.PAGES}


def main(src, dst):
    zin = zipfile.ZipFile(src)
    defs = pkg.definitions(zin)
    order = defs["pages/pages.json"]["pageOrder"]
    images = {}
    for pid in order:
        page = defs[f"pages/{pid}/page.json"]
        key = KEYS.get(page["displayName"])
        if not key:
            sys.exit(f"no background for page '{page['displayName']}'")
        item = f"QualityDashboard{A.BG_NAMES[key]}{secrets.token_hex(6)}.png"
        images[item] = (HERE / "out" / f"bg_{key}.png").read_bytes()
        A.set_background(page, D.PAGES[key]["title"], item)
    report = defs["report.json"]
    old = [i["name"] for p in report["resourcePackages"] if p["name"] == "RegisteredResources" for i in p["items"]]
    report["resourcePackages"] = [p for p in report["resourcePackages"] if p["name"] != "RegisteredResources"] + [
        {"name": "RegisteredResources", "type": "RegisteredResources",
         "items": [{"name": n, "path": n, "type": "Image"} for n in images]}]
    problems = A.checks(defs, order)
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    A.write_pbix(zin, defs, images, old, dst)
    print(f"written {dst} ({pathlib.Path(dst).stat().st_size:,} bytes): {len(images)} backgrounds replaced")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / "Quality_Dashboard_V4.pbix"))
