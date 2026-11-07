"""
Pixel art of the XM8 (our new weapon), drawn from code so it can be tweaked and redrawn.
Parts follow the G36 skeleton (same anchor points): body 89x39, magazine 13x17, stock 36x22.

Run:  build\\pyenv\\Scripts\\python.exe tools\\weapon-art\\xm8.py
Writes data/packages/base/textures/GAME/xm8-*.png
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "data", "packages", "base", "textures", "GAME")

# materials: list of shades from darkest to lightest
OLIVE = [(40, 41, 31), (58, 59, 44), (78, 79, 59), (98, 99, 75), (114, 115, 88), (132, 132, 101), (156, 154, 119)]
BLACK = [(16, 16, 16), (24, 24, 24), (32, 32, 32), (41, 41, 41), (52, 52, 52), (66, 66, 66), (96, 96, 96)]
STEEL = [(20, 20, 22), (34, 34, 37), (50, 50, 54), (66, 66, 70), (82, 82, 86), (104, 104, 108), (140, 140, 145)]
LENS = [(10, 14, 18), (18, 26, 34), (28, 44, 58), (40, 66, 88), (60, 96, 124), (96, 140, 170), (170, 210, 230)]
MATS = {"o": OLIVE, "k": BLACK, "s": STEEL, "l": LENS}
BASE = {"o": 4, "k": 2, "s": 3, "l": 3}


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.mat = [[None] * w for _ in range(h)]
        self.adj = [[0] * w for _ in range(h)]  # manual shade offsets
        self.fixed = {}  # (x, y) -> exact shade index

    def poly(self, pts, m):
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).polygon(pts, fill=255, outline=255)
        for y in range(self.h):
            for x in range(self.w):
                if im.getpixel((x, y)):
                    self.mat[y][x] = m

    def rect(self, x0, y0, x1, y1, m):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.mat[y][x] = m

    def line(self, pts, m, width=1):
        im = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(im).line(pts, fill=255, width=width)
        for y in range(self.h):
            for x in range(self.w):
                if im.getpixel((x, y)):
                    self.mat[y][x] = m

    def shade(self, x0, y0, x1, y1, d):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.adj[y][x] += d

    def px(self, x, y, m, s):
        self.mat[y][x] = m
        self.fixed[(x, y)] = s

    def render(self):
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        M = self.mat

        def same(x, y, m):
            return 0 <= x < self.w and 0 <= y < self.h and M[y][x] == m

        for y in range(self.h):
            for x in range(self.w):
                m = M[y][x]
                if m is None:
                    continue
                if (x, y) in self.fixed:
                    s = self.fixed[(x, y)]
                else:
                    s = BASE[m] + self.adj[y][x]
                    if not same(x, y - 1, m):
                        s += 2          # lit top edge
                    elif not same(x, y - 2, m):
                        s += 1
                    if not same(x, y + 1, m):
                        s -= 2          # shadowed bottom edge
                    elif not same(x, y + 2, m):
                        s -= 1
                    if not same(x - 1, y, m) or not same(x + 1, y, m):
                        s -= 1          # side outline
                s = max(0, min(6, s))
                img.putpixel((x, y), MATS[m][s] + (255,))
        return img


def body():
    c = Canvas(89, 39)
    # --- olive shell: rear sight housing, top ridge (carry handle), front slope, rounded nose
    c.poly([(4, 11), (6, 8), (8, 4), (10, 3), (21, 3), (23, 5), (24, 6), (58, 6), (61, 7),
            (70, 12), (75, 13), (78, 15), (79, 17), (78, 20), (76, 22), (40, 22), (37, 24),
            (36, 27), (22, 27), (21, 24), (4, 24)], "o")
    # trigger guard loop under the receiver
    c.poly([(9, 23), (22, 23), (22, 27), (12, 27), (10, 26)], "o")
    c.rect(12, 24, 20, 25, None)          # opening of the guard
    c.rect(14, 24, 14, 25, "k")           # trigger
    c.px(15, 24, "k", 1)
    # opening under the carry handle
    c.rect(27, 8, 47, 9, None)
    c.shade(27, 10, 47, 10, -1)
    # body lower half a bit darker (two-tone shell)
    c.shade(4, 16, 78, 22, -1)
    c.shade(36, 23, 40, 27, -1)
    # side groove along the receiver
    for x in range(24, 70):
        c.adj[14][x] -= 2
    for x in range(24, 70):
        c.adj[15][x] += 1
    # vents on the front of the handguard
    for vx in (50, 55, 60, 65):
        c.rect(vx, 10, vx + 2, 11, "k")
    # black rubber strip on the lower handguard
    c.poly([(41, 18), (73, 18), (75, 20), (74, 22), (40, 22), (39, 20)], "k")
    for gx in range(43, 73, 3):
        c.shade(gx, 19, gx, 21, 1)
    # ejection port & bolt handle slot
    c.rect(26, 12, 33, 12, "k")
    c.px(26, 12, "k", 0)
    # optic: lens at the front of the housing, rear aperture
    c.rect(20, 4, 22, 7, "k")
    c.px(21, 5, "l", 4)
    c.px(21, 6, "l", 2)
    c.rect(9, 4, 10, 6, "k")
    # fire selector
    c.px(11, 20, "k", 1)
    c.px(12, 20, "k", 3)
    # --- barrel & flash hider
    c.rect(79, 16, 88, 17, "s")
    c.rect(84, 15, 88, 18, "s")
    c.px(88, 15, "s", 1)
    c.px(88, 18, "s", 1)
    c.px(86, 16, "s", 1)
    c.px(86, 17, "s", 1)
    # --- black pistol grip, slanted like the G36 one
    c.poly([(6, 24), (11, 24), (11, 26), (8, 32), (6, 37), (3, 38), (1, 37), (3, 30), (5, 25)], "k")
    c.shade(2, 31, 9, 31, 1)
    c.shade(1, 35, 7, 35, 1)
    return c.render()


def magazine():
    c = Canvas(13, 17)
    c.poly([(1, 0), (10, 0), (11, 6), (12, 15), (5, 15), (3, 8)], "k")
    # translucent window: rounds visible through the side
    for y in (3, 5, 7, 9, 11):
        c.px(6 + y // 5, y, "s", 4)
        c.px(7 + y // 5, y, "s", 5)
    c.rect(5, 15, 12, 16, "k")
    c.shade(5, 15, 12, 16, 1)
    return c.render()


def stock():
    c = Canvas(36, 22)
    # outer shape: thick top bar, slanted lower strut, butt pad
    c.poly([(1, 4), (3, 3), (35, 3), (35, 9), (27, 9), (11, 15), (7, 20), (1, 20)], "k")
    # cut-out
    c.poly([(7, 7), (27, 7), (24, 8), (10, 13), (7, 14)], None)
    # adjustment notches on the top bar
    for x in range(10, 32, 4):
        c.px(x, 4, "k", 4)
    # rubber butt pad
    c.rect(0, 3, 3, 21, "k")
    c.shade(0, 3, 1, 21, -1)
    # olive collar where it meets the receiver
    c.rect(32, 2, 35, 10, "o")
    return c.render()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, img in (("xm8-skin", body()), ("xm8-clip-default", magazine()), ("xm8-butt-default", stock())):
        img.save(os.path.join(OUT, name + ".png"))
        print("saved", name, img.size)
