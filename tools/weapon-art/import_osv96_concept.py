"""OSV-96: approved pixel-art concept -> game sprites and Spine skeleton.

Source: tools/weapon-art/reference/osv96-approved.png (2000x667, dark flat
background). Steps, all reproducible, no repainting:
  1. background -> transparent (flood fill from the borders);
  2. the concept is split into parts by hand-drawn regions: optical scope with
     its mount, box magazine, folded bipod; everything else is the body;
  3. every part is reduced on the SAME pixel grid (the whole canvas is reduced,
     then cropped), alpha-aware BOX average, hard alpha edge, light sharpening,
     one shared palette - same method as pixelize_xm8.py;
  4. weapon-osv96.json: root scale 0.4 (native, 1 sprite px = 1 unit), the pistol
     grip sits where the M82 grip is, so the hand animations of the M82 fit.
Run with the project's Pillow Python:  python tools/weapon-art/import_osv96_concept.py
"""
from collections import deque
from pathlib import Path
import json

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'tools/weapon-art/reference'
GAME = ROOT / 'data/packages/base/textures/GAME'
OUT = ROOT / 'build/osv96'
SKELETON = ROOT / 'data/packages/base/contents/content/animations/weapon-osv96.json'

WIDTH = 192          # whole rifle (with scope) in game pixels; M82 is 160
COLORS = 28
ALPHA_CUT = 120
BG_TOLERANCE = 10

# Part regions in concept pixels (polygons). Order matters: first match wins.
PARTS = [
    # scope + rings + mount base, everything above the receiver rail
    ('osv96-scope-optical', 'scope', 'optical',
     [(355, 165), (870, 165), (870, 270), (727, 270), (727, 298), (355, 298)]),
    # box magazine under the receiver (hidden while reloading)
    ('osv96-clip-default', 'clip', 'default',
     [(456, 399), (764, 399), (764, 470), (456, 470)]),
    # folded bipod under the barrel
    ('osv96-bipod', 'bipod', 'on',
     [(860, 367), (1135, 367), (1135, 445), (860, 445)]),
]
BODY = ('osv96-skin', 'body', 'body')

# Where the M82 pistol grip is (root units) and where ours is (sprite px of the
# whole reduced rifle): the body is placed so the two coincide.
M82_GRIP = (-2.54, -2.73)
OUR_GRIP_PX = (39, 29)


def cutout(src):
    W, H = src.size
    px = src.load()
    bg = px[0, 0]
    seen = bytearray(W * H)
    q = deque([(x, y) for x in range(W) for y in (0, H - 1)] + [(x, y) for y in range(H) for x in (0, W - 1)])
    while q:
        x, y = q.popleft()
        i = y * W + x
        if seen[i]:
            continue
        p = px[x, y]
        if any(abs(p[c] - bg[c]) > BG_TOLERANCE for c in range(3)):
            continue
        seen[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < W and 0 <= ny < H and not seen[ny * W + nx]:
                q.append((nx, ny))
    return Image.frombytes('L', (W, H), bytes(0 if s else 255 for s in seen))


def reduce(rgba, size):
    r, g, b, a = rgba.split()
    pre = Image.merge('RGBA', [Image.composite(c, Image.new('L', rgba.size, 0), a) for c in (r, g, b)] + [a])
    small = pre.resize(size, Image.BOX)
    px = small.load()
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = px[x, y]
            px[x, y] = (0, 0, 0, 0) if a < ALPHA_CUT else (min(255, r * 255 // a), min(255, g * 255 // a), min(255, b * 255 // a), 255)
    rgb = small.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    out = rgb.convert('RGBA')
    out.putalpha(small.split()[3])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(REF / 'osv96-approved.png').convert('RGB')
    alpha = cutout(src)
    box = alpha.getbbox()
    scale = WIDTH / (box[2] - box[0])
    size = (WIDTH, round((box[3] - box[1]) * scale))

    # split the alpha into parts
    taken = Image.new('L', src.size, 0)
    masks = {}
    for name, slot, key, poly in PARTS:
        region = Image.new('L', src.size, 0)
        ImageDraw.Draw(region).polygon(poly, fill=255)
        m = Image.composite(alpha, Image.new('L', src.size, 0), region)
        m = Image.composite(Image.new('L', src.size, 0), m, taken)
        taken = Image.composite(Image.new('L', src.size, 255), taken, m)
        masks[(name, slot, key)] = m
    masks[BODY] = Image.composite(Image.new('L', src.size, 0), alpha, taken)

    # reduce every part on the same grid
    reduced = {}
    for part, m in masks.items():
        rgba = src.convert('RGBA')
        rgba.putalpha(m)
        rgba.crop(m.getbbox()).save(REF / (part[0] + '-hires.png'))
        reduced[part] = reduce(rgba.crop(box), size)

    # one shared palette
    opaque = [p[:3] for im in reduced.values() for p in im.getdata() if p[3]]
    sample = Image.new('RGB', (len(opaque), 1))
    sample.putdata(opaque)
    pal = sample.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)

    left = round(M82_GRIP[0] - OUR_GRIP_PX[0] - .5)
    top = round(M82_GRIP[1] + OUR_GRIP_PX[1] + .5)
    attachments = {}
    whole = Image.new('RGBA', size)
    for (name, slot, key), im in reduced.items():
        q = im.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGBA')
        q.putalpha(im.split()[3])
        # drop single pixels with no neighbours (edges of a neighbouring part)
        qp = q.load()
        lonely = [(x, y) for y in range(size[1]) for x in range(size[0]) if qp[x, y][3] and not any(
            qp[x + dx, y + dy][3] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if (dx or dy) and 0 <= x + dx < size[0] and 0 <= y + dy < size[1])]
        for x, y in lonely:
            qp[x, y] = (0, 0, 0, 0)
        bb = q.getbbox()
        part = q.crop(bb)
        part.save(GAME / (name + '.png'))
        whole.alpha_composite(q)
        w, h = part.size
        attachments.setdefault(slot, {})[key] = {
            'name': name, 'x': left + bb[0] + w / 2, 'y': top - bb[1] - h / 2, 'width': w, 'height': h}
        print('%-22s %3dx%-3d at sprite px %s' % (name, w, h, bb[:2]))
    whole.save(OUT / 'assembled.png')

    def unit(px, py):
        return left + px + .5, top - py - .5

    muzzle = unit(191, 16)
    fire_x = unit(110, 16)[0]
    shell = unit(66, 16)
    laser = unit(100, 21)
    center = unit(WIDTH / 2, size[1] / 2)
    skeleton = {
        'skeleton': {'hash': 'osv96-approved', 'spine': '4.0.45', 'x': left * .4, 'y': (top - size[1]) * .4,
                     'width': size[0] * .4, 'height': size[1] * .4, 'images': '../../../textures/GAME/', 'audio': ''},
        'bones': [
            {'name': 'root', 'scaleX': .4, 'scaleY': .4},
            {'name': 'center-bone', 'parent': 'root', 'x': center[0], 'y': center[1]},
            {'name': 'fire-bone', 'parent': 'root', 'length': round((muzzle[0] - fire_x) / 2.5, 3),
             'x': fire_x, 'y': muzzle[1], 'scaleX': 2.5, 'scaleY': 2.5},
            # sling point, same place relative to the grip as on the M82
            {'name': 'hook-bone', 'parent': 'root', 'length': 43.9, 'rotation': -0.95, 'x': -3.63, 'y': 21.15},
            {'name': 'laser-bone', 'parent': 'root', 'length': 3.3, 'x': laser[0], 'y': laser[1], 'scaleX': 2.5, 'scaleY': 2.5},
            {'name': 'shell-bone', 'parent': 'root', 'length': 3.75, 'rotation': 90, 'x': shell[0], 'y': shell[1], 'scaleX': 2.5, 'scaleY': 2.5},
        ],
        'slots': [
            {'name': 'clip', 'bone': 'root', 'attachment': 'default'},
            {'name': 'body', 'bone': 'root', 'attachment': 'body'},
            {'name': 'scope', 'bone': 'root'},
            {'name': 'bipod', 'bone': 'root'},
        ],
        'skins': [{'name': 'weapon-default', 'attachments': attachments}],
        'animations': {'animation': {}},
    }
    SKELETON.write_text(json.dumps(skeleton, indent=1) + '\n', encoding='utf-8')
    print('skeleton: left %d top %d, muzzle %s' % (left, top, muzzle))


if __name__ == '__main__':
    main()
