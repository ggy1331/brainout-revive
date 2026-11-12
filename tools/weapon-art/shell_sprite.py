"""A 12 gauge shell seen from the side, for the Super Shorty reload (launcher/sidearms_special.py):
brass head on the left, red hull to the right (the shell lies along the gun, crimp forward).

    python tools/weapon-art/shell_sprite.py      -> textures/GAME/sa-shell-12.png (7x3)

Also splits the Super Shorty "holder" sprites (barrel + magazine tube + pump + folding grip in one
picture) so only the pump and its grip slide when it is worked:
    sa-shorty-barrel     barrel, tube cap and clamp (rows 0-3, and rows 4-8 from column 17)
    sa-shorty-pump-off / -on   the pump (rows 4-8 before column 17) with the folded / unfolded grip
"""
from pathlib import Path
from PIL import Image

GAME = Path(__file__).resolve().parents[2] / "data/packages/base/textures/GAME"

BRASS, BRASS_DARK = (205, 170, 80, 255), (150, 115, 50, 255)
HULL, HULL_DARK, HULL_LIGHT = (170, 40, 35, 255), (115, 25, 25, 255), (205, 75, 60, 255)


def shell():
    img = Image.new("RGBA", (7, 3))
    p = img.load()
    for y in range(3):
        p[0, y] = BRASS_DARK                  # rim
        p[1, y] = BRASS if y < 2 else BRASS_DARK
        for x in range(2, 7):
            p[x, y] = HULL_LIGHT if y == 0 else HULL if y == 1 else HULL_DARK
    p[6, 1] = HULL_DARK                        # crimp
    return img


def pump_part(x, y):
    return (4 <= y <= 8 and x < 17) or y >= 9


def split_holder():
    for state in ("off", "on"):
        img = Image.open(GAME / ("supershorty-holder-%s.png" % state)).convert("RGBA")
        pump, barrel = Image.new("RGBA", img.size), Image.new("RGBA", img.size)
        src = img.load()
        for y in range(img.height):
            for x in range(img.width):
                (pump if pump_part(x, y) else barrel).putpixel((x, y), src[x, y])
        pump.save(GAME / ("sa-shorty-pump-%s.png" % state))
        if state == "off":
            barrel.save(GAME / "sa-shorty-barrel.png")


if __name__ == "__main__":
    out = GAME / "sa-shell-12.png"
    shell().save(out)
    split_holder()
    print(out)
