"""
XM8: turn the approved hi-res artwork into game-size pixel art (1 texture pixel = 1 game unit,
like every original weapon). Codex's design stays, only the resolution changes.

Input:  tools/weapon-art/reference/xm8-{skin,butt-default,clip-default}-hires.png
        (parts cut from xm8-approved.png by import_xm8_concept.py)
Output: data/packages/base/textures/GAME/xm8-*.png and attachment sizes in weapon-xm8.json
Preview: build/xm8-pixel/preview.png

Run from the brainout-xm8 root:
  ..\\brainout\\build\\pyenv\\Scripts\\python.exe tools\\weapon-art\\pixelize_xm8.py

Steps per part: premultiplied box downscale (each game pixel = average colour of its block),
hard alpha edge, light sharpening, one shared palette for all parts, then small hand fixes
(FIXES below) where averaging smeared tiny details.
"""
import json
import os
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "tools", "weapon-art", "reference")
GAME = os.path.join(ROOT, "data", "packages", "base", "textures", "GAME")
SKELETON = os.path.join(ROOT, "data", "packages", "base", "contents", "content", "animations", "weapon-xm8.json")
OUT = os.path.join(ROOT, "build", "xm8-pixel")

# same scale as import_xm8_concept.py: game units per hi-res pixel
SCALE = (83.79 - 23.15) / (1718 - 905)
PARTS = {"xm8-skin": ("body", "body"), "xm8-butt-default": ("butt", "default"), "xm8-clip-default": ("clip", "default")}
COLORS = 28
ALPHA_CUT = 120

# hand fixes after the automatic pass.
# FILL: part -> [(x0, y0, x1, y1), (sx, sy)] - paint the rectangle with the colour of pixel (sx, sy).
#   The "XM8" logo is ~10 game pixels wide: averaged it becomes a dark smudge, so it is painted over
#   with the body colour (the logo stays on the hi-res concept).
FILL = {"xm8-skin": [((11, 13, 20, 13), (25, 13)), ((12, 14, 20, 16), (25, 13))]}
# FIXES: part -> [(x, y, RGBA or None to clear)]
FIXES = {}


def downscale(im):
    w = max(1, round(im.width * SCALE))
    h = max(1, round(im.height * SCALE))
    # premultiply so transparent background does not darken the edges
    r, g, b, a = im.split()
    pre = Image.merge("RGBA", [Image.composite(c, Image.new("L", im.size, 0), a) for c in (r, g, b)] + [a])
    small = pre.resize((w, h), Image.BOX)
    px = small.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < ALPHA_CUT:
                px[x, y] = (0, 0, 0, 0)
            else:
                k = 255.0 / a
                px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)), 255)
    rgb = small.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    out = Image.merge("RGBA", list(rgb.split()) + [small.split()[3]])
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    small = {}
    for name in PARTS:
        small[name] = downscale(Image.open(os.path.join(REF, name + "-hires.png")).convert("RGBA"))

    # one palette for all parts, built from their opaque pixels
    strip_w = sum(im.width for im in small.values())
    strip = Image.new("RGB", (strip_w, max(im.height for im in small.values())), (0, 0, 0))
    x = 0
    opaque = []
    for im in small.values():
        strip.paste(im.convert("RGB"), (x, 0))
        opaque += [p[:3] for p in im.getdata() if p[3]]
        x += im.width
    sample = Image.new("RGB", (len(opaque), 1))
    sample.putdata(opaque)
    pal = sample.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)

    data = json.load(open(SKELETON, encoding="utf-8"))
    skins = data["skins"]
    atts = (skins[0]["attachments"] if isinstance(skins, list) else skins["weapon-default"])
    for name, im in small.items():
        q = im.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE).convert("RGBA")
        alpha = im.split()[3]
        q.putalpha(alpha)
        px = q.load()
        for (x0, y0, x1, y1), (sx, sy) in FILL.get(name, []):
            col = px[sx, sy]
            for yy in range(y0, y1 + 1):
                for xx in range(x0, x1 + 1):
                    if px[xx, yy][3]:
                        px[xx, yy] = col
        for (fx, fy, col) in FIXES.get(name, []):
            px[fx, fy] = col if col else (0, 0, 0, 0)
        q.save(os.path.join(GAME, name + ".png"))
        slot, att = PARTS[name]
        a = atts[slot][att]
        a["width"], a["height"] = q.width, q.height
        print(name, q.size)
    with open(SKELETON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    # preview assembled at 8x via the skeleton
    parts = []
    for name, (slot, att) in PARTS.items():
        a = atts[slot][att]
        parts.append((a["x"], a["y"], Image.open(os.path.join(GAME, name + ".png"))))
    sil = atts["silencer"]["on"]
    minx = min(cx - im.width / 2 for cx, cy, im in parts) - 2
    maxx = max(cx + im.width / 2 for cx, cy, im in parts) + 2
    miny = min(cy - im.height / 2 for cx, cy, im in parts) - 2
    maxy = max(cy + im.height / 2 for cx, cy, im in parts) + 2
    W, H = int(maxx - minx) + 1, int(maxy - miny) + 1
    canvas = Image.new("RGBA", (W, H), (45, 45, 48, 255))
    order = ["xm8-butt-default", "xm8-skin", "xm8-clip-default"]
    by = {n: p for n, p in zip(PARTS, parts)}
    for n in order:
        cx, cy, im = by[n]
        canvas.alpha_composite(im, (int(round(cx - im.width / 2 - minx)), int(round(maxy - (cy + im.height / 2)))))
    canvas.resize((W * 8, H * 8), Image.NEAREST).save(os.path.join(OUT, "preview.png"))
    print("preview", os.path.join(OUT, "preview.png"))


if __name__ == "__main__":
    main()
