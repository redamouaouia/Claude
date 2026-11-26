"""Plant visual management dashboard: the Relief home page again (page tiles with previews, illustration of the navy
panel), in a .pbix or a .pbit of the Relief design.

Usage:  python update_home_r.py <Relief .pbix or .pbit> [<output>]

Render out/bg_r_home.png first (README). The page tiles move to the geometry of design_r.py (their buttons get a light
navy tint on hover and the corners of the tiles); the key figures and the last refresh stay in their chips. Only the
home background image is replaced. The other pages, the model (and the data of a .pbix) are kept: the output has the
type of the input (default: out/Plant visual management dashboard V16.<ext>).
"""
import json
import pathlib
import secrets
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import add_period_filter as PF  # noqa: E402  (page titles)
import add_reaction_limits as A  # noqa: E402  (checks, writer, backgrounds)
import apply_design_r as AR  # noqa: E402  (home visuals onto the Relief geometry)
import design as D  # noqa: E402
import design_r as DR  # noqa: E402
import pbit_package as pkg  # noqa: E402
from restyle import B, C, I, N, SEL, S  # noqa: E402

OUT_NAME = "Plant visual management dashboard V16"
HOVER = {"id": "hover"}


def tile_buttons(defs, pid):
    """Hover of the page tiles: light navy tint with the corners of the tile."""
    n = 0
    for k, v in defs.items():
        if k.startswith(f"pages/{pid}/visuals/") and v["visual"]["visualType"] == "actionButton":
            o = v["visual"]["objects"]
            o["fill"] = [SEL({"show": B(False), "fillColor": C("#FFFFFF"), "transparency": N(0)}, {"id": "default"}),
                         SEL({"show": B(True), "fillColor": C(DR.NAVY), "transparency": N(95)}, HOVER)]
            o["shape"] = [SEL({"tileShape": S("rectangleRounded"), "roundEdge": I(22)}, {"id": "default"})]
            n += 1
    return n


def main(src_path, dst):
    zin = zipfile.ZipFile(src_path)
    defs = pkg.definitions(zin)
    order = defs["pages/pages.json"]["pageOrder"]
    keys = {PF.TITLES[defs[f"pages/{p}/page.json"]["displayName"]]: p for p in order
            if defs[f"pages/{p}/page.json"]["displayName"] in PF.TITLES}
    page_keys = {pid: k for k, pid in keys.items()}
    home = keys["home"]
    background = defs[f"pages/{home}/page.json"]["objects"]["background"][0]["properties"]["image"]["image"]
    old_item = background["url"]["expr"]["ResourcePackageItem"]["ItemName"]
    if "PlantVMRelief" not in old_item:
        sys.exit("this report is not in the Relief design (run apply_design_r.py first)")

    moved = AR.redesign_home(defs, home, page_keys)
    hovers = tile_buttons(defs, home)
    item = f"PlantVMReliefHome{secrets.token_hex(6)}.png"
    images = {item: (HERE / "out" / "bg_r_home.png").read_bytes()}
    A.set_background(defs[f"pages/{home}/page.json"], D.PAGES["home"]["title"], item)
    for package in defs["report.json"]["resourcePackages"]:
        if package["name"] == "RegisteredResources":
            package["items"] = [i for i in package["items"] if i["name"] != old_item] + [
                {"name": item, "path": item, "type": "Image"}]

    problems = A.checks(defs, order)
    if problems:
        print("\n".join(problems))
        sys.exit("report check failed")
    if "DataModelSchema" in zin.namelist():  # template: fields against its model
        pkg.check_fields(defs, json.loads(zin.read("DataModelSchema").decode("utf-16-le")))
    else:
        used, missing = pkg.report_fields(defs, A.model_fields(src_path))
        if missing:
            sys.exit("fields missing from the model: " + ", ".join(sorted({f"{e}[{p}]" for e, p, _ in missing})))
    A.write_pbix(zin, defs, images, [old_item], dst)
    print(f"home page: {moved} visuals placed, {hovers} tile buttons; background {item}; written {dst} "
          f"({pathlib.Path(dst).stat().st_size:,} bytes)")


if __name__ == "__main__":
    src = sys.argv[1]
    main(src, sys.argv[2] if len(sys.argv) > 2 else str(HERE / "out" / f"{OUT_NAME}{pathlib.Path(src).suffix}"))
