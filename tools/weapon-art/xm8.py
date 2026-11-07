"""
Pixel art of the XM8 (our new weapon), drawn from code so it can be tweaked and redrawn.
Slim XM8 silhouette, based on the approved side-profile concept.
Parts keep the G36 skeleton anchors: body 89x39, magazine 13x17, stock 36x22.

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
    # Low receiver and elongated, gently tapered fore-end. The muzzle axis,
    # magazine well and grip stay where the existing animation expects them.
    c.poly([(4, 17), (10, 15), (14, 14), (22, 14), (24, 16),
            (49, 16), (53, 11), (61, 11), (70, 13), (76, 15), (79, 18),
            (78, 22), (40, 22), (37, 24), (36, 27), (22, 27),
            (21, 24), (4, 24)], "o")
    c.shade(4, 21, 78, 24, -1)
    c.line([(24, 20), (39, 20), (43, 18), (68, 18)], "o")
    c.shade(24, 20, 39, 20, -1)

    # Narrow carry-handle bridge, with open air underneath (not a tall shell).
    c.poly([(21, 8), (49, 8), (61, 9), (70, 11), (75, 13),
            (78, 17), (76, 19), (71, 15), (65, 13), (57, 11),
            (23, 10)], "o")
    c.line([(24, 8), (49, 8), (60, 9)], "o")
    c.shade(24, 8, 60, 8, 1)
    # Rear support for the compact integral sight, as on the real XM8.
    c.poly([(11, 15), (14, 8), (14, 6), (23, 6), (23, 10),
            (25, 16), (23, 19), (10, 19)], "o")
    c.rect(12, 3, 24, 7, "o")
    c.rect(11, 4, 12, 7, "k")
    c.rect(24, 4, 25, 7, "k")
    c.px(24, 4, "l", 3)
    c.shade(14, 6, 23, 7, -1)
    c.px(16, 11, "s", 1)
    c.px(16, 10, "s", 4)

    # Vents and shallow rubber insert follow the slim nose, rather than
    # making the whole handguard a thick block.
    for vx, vy in ((54, 13), (60, 13), (66, 14), (71, 15)):
        c.rect(vx, vy, vx + 2, vy, "k")
    c.poly([(43, 19), (74, 19), (77, 21), (76, 22), (41, 22)], "k")
    for gx in range(45, 75, 3):
        c.line([(gx, 20), (gx - 1, 21)], "k")
        c.shade(gx, 20, gx, 20, 1)
    c.rect(25, 17, 39, 18, "k")
    c.rect(25, 17, 27, 18, "s")
    c.px(26, 17, "s", 4)
    c.px(15, 21, "k", 1)
    c.px(16, 21, "s", 3)

    # Olive raked pistol grip with the small black heel of the concept.
    c.poly([(6, 24), (11, 24), (11, 26), (8, 32), (6, 37),
            (3, 38), (1, 37), (3, 30), (5, 25)], "o")
    c.poly([(2, 34), (7, 35), (6, 37), (3, 38), (1, 37)], "k")
    c.shade(4, 28, 8, 31, -1)
    # Trigger guard remains a separate readable opening.
    c.poly([(9, 23), (22, 23), (22, 27), (12, 27), (10, 26)], "o")
    c.rect(12, 24, 20, 25, None)
    c.rect(14, 24, 14, 25, "k")
    c.px(15, 24, "k", 1)

    # Keep the original muzzle endpoint and suppressor fit.
    c.rect(79, 16, 88, 17, "s")
    c.rect(85, 16, 88, 18, "s")
    c.px(88, 16, "s", 1)
    c.px(88, 18, "s", 1)
    c.px(86, 16, "s", 1)
    c.px(86, 17, "s", 1)
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
    # Slim telescoping stock, not the previous triangular G36 frame.
    c.poly([(2, 6), (10, 7), (19, 7), (26, 6), (35, 3),
            (35, 12), (9, 12), (6, 14), (5, 20), (2, 20)], "o")
    c.poly([(15, 6), (24, 5), (30, 3), (35, 2), (35, 5),
            (26, 8), (15, 8)], "k")
    for x in (7, 10, 13):
        c.line([(x, 8), (x + 1, 10)], "o")
        c.shade(x, 8, x + 1, 10, -1)
    c.poly([(0, 4), (2, 3), (3, 5), (5, 6), (4, 13),
            (3, 21), (0, 21)], "k")
    c.shade(0, 3, 1, 21, -1)
    return c.render()


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, img in (("xm8-skin", body()), ("xm8-clip-default", magazine()), ("xm8-butt-default", stock())):
        img.save(os.path.join(OUT, name + ".png"))
        print("saved", name, img.size)
