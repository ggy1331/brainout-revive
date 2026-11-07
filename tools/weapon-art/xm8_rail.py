"""
XM8 body without the carry handle / built-in red dot, with a Picatinny rail on top (xm8-skin-rail.png).
Any scope upgrade of the XM8 swaps the body to this picture (see gunsmith.py, "body_for_scopes").

Run after pixelize_xm8.py (it starts from the game-size xm8-skin.png):
  ..\\brainout\\build\\pyenv\\Scripts\\python.exe tools\\weapon-art\\xm8_rail.py
"""
import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GAME = os.path.join(ROOT, "data", "packages", "base", "textures", "GAME")

CUT_X = (0, 49)       # columns of the carry handle + sight housing (picture pixels)
CUT_ROWS = 10         # rows 0..CUT_ROWS-1 are removed there
BAR_X = (49, 58)      # front end of the handle bar that runs into the handguard
BAR_ROWS = (5, 7)
RAIL_X = (8, 48)
RAIL_TOP = 10         # teeth row; the solid base is the next row

TOOTH = [(58, 58, 60, 255), (30, 30, 32, 255)]
BASE = (40, 40, 42, 255)
BASE_HI = (70, 70, 74, 255)


def main():
    im = Image.open(os.path.join(GAME, "xm8-skin.png")).convert("RGBA")
    px = im.load()
    for x in range(CUT_X[0], CUT_X[1] + 1):
        for y in range(CUT_ROWS):
            px[x, y] = (0, 0, 0, 0)
    for x in range(BAR_X[0], BAR_X[1] + 1):
        for y in range(BAR_ROWS[0], BAR_ROWS[1] + 1):
            px[x, y] = (0, 0, 0, 0)
    # the handle opening under the bar becomes part of the receiver top: paint the rail over it
    for x in range(RAIL_X[0], RAIL_X[1] + 1):
        px[x, RAIL_TOP] = TOOTH[x % 2]
        px[x, RAIL_TOP + 1] = BASE_HI if x % 4 == 0 else BASE
    # rail ends
    for y in (RAIL_TOP, RAIL_TOP + 1):
        px[RAIL_X[0] - 1, y] = (24, 24, 26, 255)
    im.save(os.path.join(GAME, "xm8-skin-rail.png"))
    print("saved xm8-skin-rail.png", im.size)


if __name__ == "__main__":
    main()
