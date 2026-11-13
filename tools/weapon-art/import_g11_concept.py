"""HK G11: approved pixel-art concept -> game sprites (body, magazine, cocking handle) + Spine skeleton.

Source: tools/weapon-art/reference/g11-approved.png (1983x793, dark flat background,
muzzle on the LEFT). Steps, reproducible, no repainting of the visible gun:
  1. background -> transparent: flood fill from the borders, plus closed areas of the
     background colour bigger than HOLE_MIN px (window of the scope mount, trigger guard);
  2. mirrored so the muzzle points right, like every weapon in the game (g11-hires.png);
  3. split into parts by rectangles in g11-hires.png pixels:
       magazine  - the top strip of the front section (it lies over the barrel, ribbed end in front);
       crank     - the round cocking handle at the rear (a disc of CRANK_RADIUS);
     under them the body gets a dark magazine well and a plain surface (copied from the column
     left of the handle), so that a removed magazine / a turning handle show no ghost;
  4. every part reduced on the SAME grid: alpha-aware BOX halving while the image is more than
     twice the target, then one bicubic step (keeps thin lines, no Lanczos ringing), hard alpha
     edge, sharpening, one shared palette of COLORS colours, lonely pixels removed;
  5. weapon-g11.json: root scale 0.4 (1 sprite px = 1 unit), the middle of the pistol grip is the
     origin (where the fist holds rifles, like FAMAS / AUG); the magazine hangs on pair-mag-travel
     (moved by the hand clips, see launcher/g11.py), the handle on its own bone g11-crank.
Size: G11 is 750 mm long; AUG (790 mm) is 109 px, FAMAS (757 mm) 101 px -> 100 px would match,
but GGY chose 120 px (variant "C", 2026-11-13) for more detail: 20 % bigger in the world.
Run with the project's Pillow Python:  python tools/weapon-art/import_g11_concept.py
"""
from collections import deque
from pathlib import Path
import json

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'tools/weapon-art/reference'
GAME = ROOT / 'data/packages/base/textures/GAME'
OUT = ROOT / 'build/g11'
SKELETON = ROOT / 'data/packages/base/contents/content/animations/weapon-g11.json'

WIDTH = 120
COLORS = 48
ALPHA_CUT = 120
BG_TOLERANCE = 10
HOLE_MIN = 1500

# hi-res (mirrored) pixels
MAG_BOX = (1106, 195, 1802, 302)        # x0, y0, x1, y1 (exclusive)
WELL_TOP = 252                          # the well: dark from here down, open above
CRANK_CENTRE = (502, 398)
CRANK_RADIUS = 89                       # the handle turns as a disc (the whole arch)
CRANK_BOX = (410, 304, 595, 492)        # old handle outline: painted over on the body
PLAIN_COLUMN = 396                      # body column copied over the handle
GRIP = (812, 590)                       # middle of the pistol grip -> skeleton origin
MUZZLE = (1800, 372)
WELL_COLOUR = (24, 25, 30, 255)


def background(src):
    """1 = background: reachable from the borders, or a large closed area of that colour."""
    W, H = src.size
    px = src.load()
    bg = px[0, 0]
    like = bytearray(1 if all(abs(px[x, y][c] - bg[c]) <= BG_TOLERANCE for c in range(3)) else 0
                     for y in range(H) for x in range(W))
    seen = bytearray(W * H)
    out = bytearray(W * H)
    for start in range(W * H):
        if not like[start] or seen[start]:
            continue
        region, q, edge = [], deque([start]), False
        seen[start] = 1
        while q:
            i = q.popleft()
            region.append(i)
            x, y = i % W, i // W
            if x in (0, W - 1) or y in (0, H - 1):
                edge = True
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < W and 0 <= ny < H:
                    j = ny * W + nx
                    if like[j] and not seen[j]:
                        seen[j] = 1
                        q.append(j)
        if edge or len(region) >= HOLE_MIN:
            for i in region:
                out[i] = 1
    return Image.frombytes('L', (W, H), bytes(0 if b else 255 for b in out))


def premul_resize(rgba, size, flt):
    r, g, b, a = rgba.split()
    pre = Image.merge('RGBA', [Image.composite(c, Image.new('L', rgba.size, 0), a) for c in (r, g, b)] + [a])
    small = pre.resize(size, flt)
    px = small.load()
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = px[x, y]
            px[x, y] = (0, 0, 0, 0) if a < ALPHA_CUT else (
                min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a), 255)
    return small


def reduce(rgba, size):
    while rgba.size[0] > size[0] * 2:
        rgba = premul_resize(rgba, (rgba.size[0] // 2, rgba.size[1] // 2), Image.BOX)
    small = premul_resize(rgba, size, Image.BICUBIC)
    # transparent pixels get the mean colour: sharpening must not see a black surround
    # (it drew a light halo round every part)
    rgb = small.convert('RGB')
    alpha = small.split()[3]
    opaque = [p for p, a in zip(rgb.getdata(), alpha.getdata()) if a]
    if opaque:
        mean = tuple(sum(c[i] for c in opaque) // len(opaque) for i in range(3))
        rgb = Image.composite(rgb, Image.new('RGB', size, mean), alpha)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.8, percent=120, threshold=2))
    out = rgb.convert('RGBA')
    out.putalpha(small.split()[3])
    return out


def inside(box, x, y):
    return box[0] <= x < box[2] and box[1] <= y < box[3]


def split(hi):
    """hi-res RGBA -> {'body': .., 'mag': .., 'crank': ..} on the same canvas"""
    W, H = hi.size
    src = hi.load()
    parts = {k: Image.new('RGBA', hi.size) for k in ('body', 'mag', 'crank')}
    body, mag, crank = (parts[k].load() for k in ('body', 'mag', 'crank'))
    for y in range(H):
        for x in range(W):
            p = src[x, y]
            if p[3] == 0:
                continue
            if inside(MAG_BOX, x, y):
                mag[x, y] = p
                if y >= WELL_TOP:
                    body[x, y] = WELL_COLOUR
            elif inside(CRANK_BOX, x, y):
                if (x - CRANK_CENTRE[0]) ** 2 + (y - CRANK_CENTRE[1]) ** 2 <= CRANK_RADIUS ** 2:
                    crank[x, y] = p
                plain = src[PLAIN_COLUMN, y]
                if plain[3]:
                    body[x, y] = plain
            else:
                body[x, y] = p
    return parts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(REF / 'g11-approved.png').convert('RGB')
    rgba = src.convert('RGBA')
    rgba.putalpha(background(src))
    rgba = rgba.transpose(Image.FLIP_LEFT_RIGHT)
    rgba = rgba.crop(rgba.getbbox())
    rgba.save(REF / 'g11-hires.png')
    k = WIDTH / rgba.size[0]
    size = (WIDTH, round(rgba.size[1] * k))

    reduced = {name: reduce(im, size) for name, im in split(rgba).items()}
    whole = reduce(rgba, size)

    opaque = [p[:3] for im in reduced.values() for p in im.getdata() if p[3]]
    sample = Image.new('RGB', (len(opaque), 1))
    sample.putdata(opaque)
    pal = sample.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)

    def gun(px, py):            # canvas pixel (centre) -> skeleton units, origin at the grip
        return round(px + .5 - GRIP[0] * k, 2), round(GRIP[1] * k - py - .5, 2)

    crank_bone = gun(CRANK_CENTRE[0] * k - .5, CRANK_CENTRE[1] * k - .5)
    bones_of = {'body': None, 'mag': 'pair-mag-travel', 'crank': 'g11-crank'}
    attachments = {}
    sprites = {}
    for name, im in reduced.items():
        q = im.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGBA')
        q.putalpha(im.split()[3])
        qp = q.load()
        W, H = q.size
        lonely = [(x, y) for y in range(H) for x in range(W) if qp[x, y][3] and not any(
            qp[x + dx, y + dy][3] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if (dx or dy) and 0 <= x + dx < W and 0 <= y + dy < H)]
        for x, y in lonely:
            qp[x, y] = (0, 0, 0, 0)
        bb = q.getbbox()
        part = q.crop(bb)
        sprite = 'g11-' + name
        part.save(GAME / (sprite + '.png'))
        sprites[name] = (q, bb)
        w, h = part.size
        cx, cy = gun(bb[0] + w / 2 - .5, bb[1] + h / 2 - .5)
        if name == 'crank':
            cx, cy = round(cx - crank_bone[0], 2), round(cy - crank_bone[1], 2)
        slot = {'body': 'body', 'mag': 'clip', 'crank': 'crank'}[name]
        attachments[slot] = {'default': {'name': sprite, 'x': cx, 'y': cy, 'width': w, 'height': h}}
        print('%-10s %3dx%-3d at %s' % (sprite, w, h, bb[:2]))

    # assembled preview (also the "whole" sprite for menus if ever needed)
    assembled = Image.new('RGBA', size)
    for name in ('body', 'mag', 'crank'):
        assembled.alpha_composite(sprites[name][0])
    assembled.save(OUT / 'assembled.png')
    assembled.resize((size[0] * 8, size[1] * 8), Image.NEAREST).save(OUT / 'assembled-x8.png')

    muzzle = gun(MUZZLE[0] * k, MUZZLE[1] * k)
    fire_x = muzzle[0] - 40
    centre = gun(size[0] / 2, size[1] / 2)
    skeleton = {
        'skeleton': {'hash': 'g11-approved', 'spine': '4.0.45', 'x': round(-GRIP[0] * k * .4, 2),
                     'y': round((GRIP[1] * k - size[1]) * .4, 2), 'width': size[0] * .4,
                     'height': round(size[1] * .4, 2), 'images': '../../../textures/GAME/', 'audio': ''},
        'bones': [
            {'name': 'root', 'scaleX': .4, 'scaleY': .4},
            {'name': 'center-bone', 'parent': 'root', 'x': centre[0], 'y': centre[1]},
            {'name': 'fire-bone', 'parent': 'root', 'length': round((muzzle[0] - fire_x) / 2.5, 3),
             'x': fire_x, 'y': muzzle[1], 'scaleX': 2.5, 'scaleY': 2.5},
            {'name': 'hook-bone', 'parent': 'root', 'length': 17.82, 'x': -20.0, 'y': 22.0},
            {'name': 'laser-bone', 'parent': 'root', 'length': 3.3, 'x': round(muzzle[0] - 14, 2),
             'y': round(muzzle[1] - 6, 2), 'scaleX': 2.5, 'scaleY': 2.5},
            {'name': 'pair-mag-travel', 'parent': 'root'},
            {'name': 'g11-crank', 'parent': 'root', 'x': crank_bone[0], 'y': crank_bone[1]},
        ],
        'slots': [
            {'name': 'body', 'bone': 'root', 'attachment': 'default'},
            {'name': 'clip', 'bone': 'pair-mag-travel', 'attachment': 'default'},
            {'name': 'crank', 'bone': 'g11-crank', 'attachment': 'default'},
        ],
        'skins': [{'name': 'weapon-default', 'attachments': attachments}],
        'animations': {
            'animation': {},
            # one full turn of the cocking handle (clockwise as seen), played by the "g11-crank" action
            'crank': {'bones': {'g11-crank': {'rotate': [
                {'time': 0}, {'time': .12, 'value': -90}, {'time': .24, 'value': -180},
                {'time': .36, 'value': -270}, {'time': .48, 'value': -359}, {'time': .49}]}}},
        },
    }
    SKELETON.write_text(json.dumps(skeleton, indent=1) + '\n', encoding='utf-8')
    print('grip at canvas px (%.1f, %.1f), muzzle %s, crank bone %s' % (GRIP[0] * k, GRIP[1] * k, muzzle, crank_bone))


if __name__ == '__main__':
    main()
