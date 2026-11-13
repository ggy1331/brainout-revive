"""shot-marker.png: the arc around the player that tells roughly where an unseen enemy is shooting
from (CSGame.received(OtherPlayerBulletLaunch)). Same layout as damage-marker.png (256x256,
centred on the player, the arc on the left = the shot comes from the left, rotated by the game),
but wider, bright yellow with a dark edge, in long dashes, fading only at the ends - a rough direction.

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
    half = 24.0                                     # degrees each side
    for y in range(size):
        for x in range(size):
            dx, dy = x + .5 - c, y + .5 - c
            r = hypot(dx, dy)
            a = degrees(atan2(dy, -dx))             # 0 = straight left
            if abs(a) > half:
                continue
            fade = 1 - (abs(a) / half) ** 3         # soft ends, most of the arc at full strength
            dash = (a + half) % 7.0 < 5.0           # long dashes, short gaps: still a rough direction
            if 114 <= r < 120 and dash:
                p[x, y] = (255, 236, 110, int(255 * fade))      # bright core
            elif 120 <= r < 122 and dash:
                p[x, y] = (45, 28, 0, int(190 * fade))          # dark edge: readable on light maps
            elif 106 <= r < 114:
                p[x, y] = (255, 180, 40, int(150 * fade * (r - 106) / 8))   # glow towards the centre
    img.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
