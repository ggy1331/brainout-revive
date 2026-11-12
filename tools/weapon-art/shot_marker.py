"""shot-marker.png: the arc around the player that tells roughly where an unseen enemy is shooting
from (CSGame.received(OtherPlayerBulletLaunch)). Same layout as damage-marker.png (256x256,
centred on the player, the arc on the left = the shot comes from the left, rotated by the game),
but wider, yellow, broken into dashes and fading at the ends - it is only a rough direction.

    python tools/weapon-art/shot_marker.py
"""
from math import cos, sin, radians, hypot, atan2, degrees
from pathlib import Path
from PIL import Image

OUT = Path(__file__).resolve().parents[2] / "data/packages/base/textures/GAME/shot-marker.png"


def main():
    size, c = 256, 127.5
    img = Image.new("RGBA", (size, size))
    p = img.load()
    half = 22.0                                     # degrees each side
    for y in range(size):
        for x in range(size):
            dx, dy = x + .5 - c, y + .5 - c
            r = hypot(dx, dy)
            a = degrees(atan2(dy, -dx))             # 0 = straight left
            if abs(a) > half:
                continue
            fade = 1 - (abs(a) / half) ** 2         # soft ends
            dash = int((a + half) / 4.4) % 2 == 0   # broken arc: only a rough direction
            if 116 <= r < 119 and dash:
                p[x, y] = (255, 214, 90, int(230 * fade))
            elif 110 <= r < 116:
                p[x, y] = (255, 170, 40, int(90 * fade))
    img.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
