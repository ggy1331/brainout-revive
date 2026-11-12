"""Draw the Akimbo perk icon in the style of the stock perk icons (icon-shop-special-*).

    python tools/weapon-art/akimbo_perk_icon.py [out.png]

Stock perk icons: a pixel silhouette drawn with 2x2 px "cells" — white (255,255,255,255)
and a translucent beige shade (254,241,204,~158) — on a transparent canvas with an
18 px margin filled by a soft gold glow (248,184,0) that fades from alpha ~60 to 0.
Here: two pistols — the front one white, pointing right, the back one beige,
pointing left (like the white/beige halves of the Anonymous mask).
"""
from pathlib import Path
import math
import sys
from PIL import Image

CELL = 2
MARGIN = 18
WHITE = (255, 255, 255, 255)
SHADE = (254, 241, 204, 158)
GOLD = (248, 184, 0)

# a Colt M1911 pointing right: '#' = body, '+' = detail (beige on the white pistol;
# the beige back pistol is drawn solid). Hammer spur at the back, rear/front sights,
# slide serrations and ejection port, beavertail, round trigger guard, grip panels.
PISTOL = [
    "..#..........#.",
    "##############.",
    ".#+#+#####+++#.",
    ".#############.",
    ".############..",
    "#####.+..#.....",
    ".####..###.....",
    ".####..........",
    ".#++#..........",
    ".#++#..........",
    ".#++#..........",
    ".####..........",
]


def cells(shape, dx, dy, mirror=False, mark="#"):
    w = max(len(r) for r in shape)
    out = set()
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch == mark:
                out.add((((w - 1 - x) if mirror else x) + dx, y + dy))
    return out


def glow_alpha(d):
    # fitted to the stock icons: ~60 at the edge, ~30 at 5 px, ~13 at 10 px, ~3 at 15 px
    return 64 * math.exp(-d / 7 - (d / 16) ** 2)


def build():
    BX, BY, FX, FY = 5, 0, 0, 6
    back = cells(PISTOL, BX, BY, mirror=True) | cells(PISTOL, BX, BY, mirror=True, mark="+")  # beige, solid, pointing left
    front = cells(PISTOL, FX, FY)                           # white, pointing right, lower
    front_detail = cells(PISTOL, FX, FY, mark="+")          # beige details on the white one
    # a one-cell transparent gap where the front pistol covers the back one
    whole_front = front | front_detail
    near = {(x + ox, y + oy) for x, y in whole_front for ox in (-1, 0, 1) for oy in (-1, 0, 1)}
    back -= near

    allc = back | whole_front
    w = (max(x for x, _ in allc) + 1) * CELL + 2 * MARGIN
    h = (max(y for _, y in allc) + 1) * CELL + 2 * MARGIN
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()

    solid = []
    for group, color in ((back, SHADE), (front, WHITE), (front_detail, SHADE)):
        for cx, cy in group:
            for oy in range(CELL):
                for ox in range(CELL):
                    p = (MARGIN + cx * CELL + ox, MARGIN + cy * CELL + oy)
                    px[p] = color
                    solid.append(p)

    for y in range(h):
        for x in range(w):
            if px[x, y][3]:
                continue
            d = min(math.hypot(x - sx, y - sy) for sx, sy in solid)
            a = int(round(glow_alpha(d)))
            if a > 0:
                px[x, y] = GOLD + (a,)
    return img


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / \
        "data/packages/base/textures/ICONS/icon-shop-special-akimbo.png"
    img = build()
    img.save(out)
    print(out, img.size)
