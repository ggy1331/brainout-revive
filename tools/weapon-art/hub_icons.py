"""Icons for the square hub buttons next to chat / GitHub (LobbyMenu), in the style of
icon-blog / icon-chat: a white pixel glyph with coloured details, a pale shadow down-left and a
soft glow of the button's colour.

    python tools/weapon-art/hub_icons.py   -> textures/ICONS/icon-dummy-add.png, icon-dummy-remove.png,
                                              icon-update.png (52x48)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / "data/packages/base/textures/ICONS"
W, H = 52, 48
WHITE = (255, 255, 255, 255)


def mannequin(d, dark):
    """A training dummy on its stand, seen from the front."""
    cx = 22
    d.ellipse((cx - 4, 8, cx + 4, 16), fill=WHITE)                  # head
    d.rectangle((cx - 1, 16, cx + 1, 17), fill=WHITE)               # neck
    d.polygon([(cx - 8, 18), (cx + 8, 18), (cx + 6, 29), (cx - 6, 29)], fill=WHITE)   # torso
    d.rectangle((cx - 3, 21, cx + 3, 23), fill=dark)                # target ring band
    d.rectangle((cx - 1, 20, cx + 1, 24), fill=dark)
    d.rectangle((cx - 1, 29, cx + 1, 36), fill=WHITE)               # pole
    d.rectangle((cx - 7, 37, cx + 7, 39), fill=WHITE)               # base


def badge(d, dark, symbol):
    x0, y0 = 30, 26
    d.rectangle((x0, y0, x0 + 11, y0 + 11), fill=WHITE)
    d.rectangle((x0 + 1, y0 + 1, x0 + 10, y0 + 10), fill=dark)
    if symbol == "+":
        d.rectangle((x0 + 5, y0 + 3, x0 + 6, y0 + 8), fill=WHITE)
        d.rectangle((x0 + 3, y0 + 5, x0 + 8, y0 + 6), fill=WHITE)
    else:
        for i in range(6):
            d.rectangle((x0 + 3 + i, y0 + 3 + i, x0 + 3 + i, y0 + 3 + i), fill=WHITE)
            d.rectangle((x0 + 4 + i, y0 + 3 + i, x0 + 4 + i, y0 + 3 + i), fill=WHITE)
            d.rectangle((x0 + 8 - i, y0 + 3 + i, x0 + 8 - i, y0 + 3 + i), fill=WHITE)
            d.rectangle((x0 + 7 - i, y0 + 3 + i, x0 + 7 - i, y0 + 3 + i), fill=WHITE)


def refresh(d, dark):
    """Two arrows chasing each other round a circle."""
    box = (12, 10, 40, 38)
    d.arc(box, 200, 340, fill=WHITE, width=4)
    d.arc(box, 20, 160, fill=WHITE, width=4)
    d.polygon([(36, 9), (43, 17), (33, 18)], fill=WHITE)            # head, top right
    d.polygon([(16, 39), (9, 31), (19, 30)], fill=WHITE)            # head, bottom left
    d.rectangle((24, 22, 28, 26), fill=dark)                         # centre dot


def icon(draw_glyph, glow, dark):
    glyph = Image.new("RGBA", (W, H))
    draw_glyph(ImageDraw.Draw(glyph))
    alpha = glyph.getchannel("A")
    out = Image.new("RGBA", (W, H))
    # glow: the silhouette spread and blurred, in the button's colour
    halo = alpha.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(4))
    halo = halo.point(lambda v: min(110, int(v * 1.8)))
    out.paste(Image.new("RGBA", (W, H), glow + (255,)), (0, 0), halo)
    # pale shadow down-left, like the newspaper icon
    shadow = Image.new("RGBA", (W, H))
    shadow.paste(Image.new("RGBA", (W, H), (160, 156, 186, 255)), (-2, 2), alpha)
    out.alpha_composite(shadow)
    out.alpha_composite(glyph)
    return out


def main():
    dummy_dark, remove_dark, update_dark = (120, 70, 20, 255), (130, 30, 30, 255), (30, 90, 130, 255)
    icon(lambda d: (mannequin(d, dummy_dark), badge(d, dummy_dark, "+")), (240, 150, 40), dummy_dark).save(
        OUT / "icon-dummy-add.png")
    icon(lambda d: (mannequin(d, remove_dark), badge(d, remove_dark, "x")), (230, 60, 50), remove_dark).save(
        OUT / "icon-dummy-remove.png")
    icon(lambda d: refresh(d, update_dark), (60, 180, 230), update_dark).save(OUT / "icon-update.png")
    print(OUT)


if __name__ == "__main__":
    main()
