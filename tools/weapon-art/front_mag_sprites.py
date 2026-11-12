"""Full-length magazines for the front-magazine machine pistols (launcher/sidearms_front.py).

The original clip sprites show only the part under the magazine well. This makes fm-<sprite>.png
for every clip sprite of those weapons (all skins, default and extended): `depth` rows are added
under the top rows (feed lips stay on top), following the magazine axis, so a magazine pulled
out of the gun or held in the hand has its full length. The extra part stays behind the body
while the magazine is seated.

    python tools/weapon-art/front_mag_sprites.py [base-client-premod.zip]
"""
from math import cos, sin, radians
from pathlib import Path
import json
import sys
import zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "launcher"))
from sidearms_front import FRONT, clip_slot          # noqa: E402

GAME = ROOT / "data/packages/base/textures/GAME"


def lengthen(img, depth, axis):
    w, h = img.size
    lean = cos(radians(axis)) / sin(radians(axis))
    shift = round(depth * lean)
    r = min(2, h // 3)                     # rows kept on top (feed lips)
    out = Image.new("RGBA", (w + abs(shift), h + depth))
    base = max(0, -shift)

    def put(src_row, dst_row, disp):
        for x in range(w):
            px = img.getpixel((x, src_row))
            if px[3]:
                out.putpixel((base + x + disp, dst_row), px)

    for j in range(h + depth):
        if j <= r:
            put(j, j, shift)
        elif j <= r + depth:
            put(r, j, round((r + depth + 1 - j) * lean))
        else:
            put(j - depth, j, 0)
    return out


def build_all(zip_path):
    z = zipfile.ZipFile(zip_path)
    content = json.loads(z.read("content.json"))["content"]
    for wid, f in FRONT.items():
        if not f["depth"]:
            continue
        item = content["weapon-" + wid]
        comp = next(c for c in item["components"] if "states" in c and "animation" in c)
        model = json.loads(z.read("content/" + content[comp["animation"]]["animation"].split(":")[1]))
        slot = clip_slot(model)["name"]
        for skin in model["skins"]:
            for key, att in skin.get("attachments", {}).get(slot, {}).items():
                sprite = att.get("path", att.get("name", key))
                img = Image.open(GAME / (sprite + ".png")).convert("RGBA")
                lengthen(img, f["depth"], f["axis"]).save(GAME / ("fm-" + sprite + ".png"))
                print(wid, "fm-" + sprite)


if __name__ == "__main__":
    build_all(sys.argv[1] if len(sys.argv) > 1 else ROOT / "build/base-client-premod.zip")
