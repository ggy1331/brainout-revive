"""
XM8 "Sand" skin (desert tan, like the XM8 in Battlefield: Bad Company 2): a recolour of the olive plastic only.
Black rubber, metal and the magazine stay as they are.

Makes  textures/GAME/xm8-{skin,skin-rail,butt-default,clip-default}-sand.png
       textures/ICONS/icon-weapon-xm8-sand.png  (32x16 colour swatch for the skin button)
and adds skin "weapon-sand" to weapon-xm8.json + skin-weapon-xm8-sand to Store Item.txt.

Run AFTER gunsmith.py (gunsmith rebuilds the skeleton and Store Item from git HEAD):
  ..\\brainout\\build\\pyenv\\Scripts\\python.exe tools\\weapon-art\\xm8_sand.py
"""
import colorsys
import json
import os
import re
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE = os.path.join(ROOT, "data", "packages", "base")
GAME = os.path.join(BASE, "textures", "GAME")
ICONS = os.path.join(BASE, "textures", "ICONS")
SKELETON = os.path.join(BASE, "contents", "content", "animations", "weapon-xm8.json")
STORE = os.path.join(BASE, "smart", "Weapons", "xm8", "Store Item.txt")

PARTS = ["xm8-skin", "xm8-skin-rail", "xm8-butt-default", "xm8-clip-default"]
SAND_HUE = 36 / 360      # desert tan
SAND_SAT = 0.34
LIFT = 1.32              # tan is lighter than olive
LIFT_ADD = 0.06


def is_olive(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.10 <= h <= 0.24 and s >= 0.10 and v >= 0.12


def recolour(im):
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if a == 0 or not is_olive(r, g, b):
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            v2 = min(1.0, v * LIFT + LIFT_ADD)
            s2 = min(0.6, SAND_SAT * (0.7 + s))
            nr, ng, nb = colorsys.hsv_to_rgb(SAND_HUE, s2, v2)
            px[x, y] = (round(nr * 255), round(ng * 255), round(nb * 255), a)
    return out


def main():
    for name in PARTS:
        src = os.path.join(GAME, name + ".png")
        if not os.path.exists(src):
            continue
        recolour(Image.open(src).convert("RGBA")).save(os.path.join(GAME, name + "-sand.png"))
        print("saved", name + "-sand")

    # skin button swatch: a piece of the receiver (vents + rubber strip), like the other skins' icons
    body = Image.open(os.path.join(GAME, "xm8-skin-sand.png")).convert("RGBA")
    icon = body.crop((44, 6, 76, 22))
    icon.save(os.path.join(ICONS, "icon-weapon-xm8-sand.png"))

    # skeleton: weapon-sand = weapon-default with the recoloured pictures
    d = json.load(open(SKELETON, encoding="utf-8"))
    skins = d["skins"]
    default = next(s for s in skins if s["name"] == "weapon-default")
    sand = json.loads(json.dumps(default))
    sand["name"] = "weapon-sand"
    for slot in sand["attachments"].values():
        for a in slot.values():
            if a.get("name") in PARTS and os.path.exists(os.path.join(GAME, a["name"] + "-sand.png")):
                a["name"] = a["name"] + "-sand"
    d["skins"] = [s for s in skins if s["name"] != "weapon-sand"] + [sand]
    with open(SKELETON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")

    # Store Item: offer the skin
    text = open(STORE, encoding="utf-8").read()
    if "skin-weapon-xm8-sand" not in text:
        text = re.sub(r"(\n\s*skins\s*=\s*skin-weapon-xm8-default)", r"\1, skin-weapon-xm8-sand", text, count=1)
        open(STORE, "w", encoding="utf-8", newline="\n").write(text)
    print("skin weapon-sand added")


if __name__ == "__main__":
    main()
