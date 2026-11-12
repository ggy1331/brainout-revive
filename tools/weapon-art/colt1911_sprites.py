"""Split the Colt M1911 sprites into frame / slide / magazine for the animated reload.

    python tools/weapon-art/colt1911_sprites.py

For every Colt skin (textures/GAME/colt-*.png, one picture of the whole pistol):
  colt1911-frame-<skin>.png  the pistol without the slide and without the magazine base plate;
                             a dark barrel strip is drawn under the slide (seen when it is back)
  colt1911-slide-<skin>.png  the slide (top rows from the hammer forward), same canvas size
and one shared magazine colt1911-mag.png (upright: feed lips on top, base plate at the bottom).
Same canvas size as the source, so the attachments keep the old x / y / width / height.
"""
from pathlib import Path
from PIL import Image

GAME = Path(__file__).resolve().parents[2] / "data/packages/base/textures/GAME"
SKINS = {
    "default": "colt-skin", "harding": "colt-skin-harding", "judge": "colt-skin-judge",
    "pigeon": "colt-skin-pigeon", "pro": "colt-pro-skin", "rassel": "colt-skin-rassel",
}
HAMMER_COLS = 5          # columns left of this stay on the frame (hammer, grip safety)
SLIDE_PROBE_COL = 33     # a column that only the slide covers (the frame ends further back)
MAG_LEN, MAG_W = 15, 4   # magazine body in gun pixels


def split(src):
    im = Image.open(src).convert("RGBA")
    w, h = im.size
    px = im.load()
    # the slide = every row down to the last one that reaches the probe column
    last_slide = max(y for y in range(h) if px[SLIDE_PROBE_COL, y][3] > 0)
    slide = Image.new("RGBA", im.size)
    frame = im.copy()
    fpx, spx = frame.load(), slide.load()
    for y in range(last_slide + 1):
        for x in range(HAMMER_COLS, w):
            if px[x, y][3] > 0:
                spx[x, y] = px[x, y]
                fpx[x, y] = (0, 0, 0, 0)
    # barrel under the slide: visible only while the slide is back
    dark = min((px[x, y] for y in range(h) for x in range(w) if px[x, y][3] == 255),
               key=lambda c: c[0] + c[1] + c[2])
    barrel = (dark[0] + 18, dark[1] + 18, dark[2] + 18, 255)
    for y in range(last_slide - 4, last_slide - 1):
        for x in range(HAMMER_COLS + 14, w - 2):
            if fpx[x, y][3] == 0:
                fpx[x, y] = barrel
    # the magazine base plate = the bottom row of the grip (right of the back strap)
    base_y = max(y for y in range(h) for x in range(12) if px[x, y][3] > 0)
    plate = [(x, px[x, base_y]) for x in range(HAMMER_COLS - 1, 12) if px[x, base_y][3] > 0]
    for x, _ in plate:
        fpx[x, base_y] = (0, 0, 0, 0)
    return frame, slide, plate, dark


def magazine(plate, dark):
    # upright magazine: steel body, a lighter edge, feed lips, the base plate from the sprite
    body = (dark[0] + 30, dark[1] + 30, dark[2] + 32, 255)
    edge = (dark[0] + 62, dark[1] + 62, dark[2] + 66, 255)
    brass = (176, 140, 64, 255)
    w = max(MAG_W + 2, len(plate))
    img = Image.new("RGBA", (w, MAG_LEN + 1))
    p = img.load()
    left = (w - MAG_W) // 2
    for y in range(MAG_LEN):
        for x in range(left, left + MAG_W):
            p[x, y] = edge if x == left else body
    p[left + 1, 0] = brass          # top round in the feed lips
    p[left + 2, 0] = brass
    for i, (_, c) in enumerate(plate[:w]):
        p[i, MAG_LEN] = c
    for x in range(w):
        if p[x, MAG_LEN][3] == 0:
            p[x, MAG_LEN] = dark
    return img


def main():
    mag = None
    for skin, name in SKINS.items():
        frame, slide, plate, dark = split(GAME / (name + ".png"))
        frame.save(GAME / ("colt1911-frame-%s.png" % skin))
        slide.save(GAME / ("colt1911-slide-%s.png" % skin))
        if skin == "default":
            mag = magazine(plate, dark)
    mag.save(GAME / "colt1911-mag.png")
    print("ok", GAME)


if __name__ == "__main__":
    main()
