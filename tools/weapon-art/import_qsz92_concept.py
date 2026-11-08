"""QSZ-92: approved pixel-art concept -> game sprite and Spine skeleton.

Source: tools/weapon-art/reference/qsz92-approved.png (1498x1050, flat dark
background). Same method as import_osv96_concept.py:
  1. background -> transparent (flood fill from the borders);
  2. alpha-aware BOX reduction to WIDTH game pixels, hard alpha edge, light
     sharpening, palette of COLORS colours, lone pixels removed;
  3. weapon-qsz92.json: root scale 0.4 (1 sprite px = 1 unit, like the Beretta,
     Makarov, CZ75), the pistol grip placed where the Beretta grip is, so the
     one-hand animations fit; fire/shell/center bones measured on the concept.
Run with the project's Pillow Python:  python tools/weapon-art/import_qsz92_concept.py
"""
from collections import deque
from pathlib import Path
import json

from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / 'tools/weapon-art/reference'
GAME = ROOT / 'data/packages/base/textures/GAME'
OUT = ROOT / 'build/qsz92'
ANIM = ROOT / 'data/packages/base/contents/content/animations'

WIDTH = 33          # QSZ-92 is 190 mm long; the Beretta 92 (217 mm) is 37 px
COLORS = 24
CONTRAST = 1.35
OUTLINE = (16, 17, 20, 255)  # dark 1 px outline, as on the stock pistols
ALPHA_CUT = 120
BG_TOLERANCE = 10
HOLE_MIN = 1500     # px of a closed background-coloured hole
# concept points (pixels of qsz92-approved.png)
BORE_Y = 205        # bore axis inside the slide
CHAMBER_X = 560     # where the fire bone starts (behind the ejection port)
PORT = (760, 150)   # ejection port, where the cases fly out
LASER_FRONT = (1385, 352)  # front of the dust cover and the bottom of the frame rail
MAG_KEEP = 6        # sprite rows at the bottom of the grip taken for the long magazine
MAG_BASE = 2        # of them, the baseplate
MAG_EXTRA = 4       # sprite rows added: 30 rounds instead of 20


def cutout(src):
    """Background = every background-coloured area touching the border, plus closed
    holes of background colour bigger than HOLE_MIN pixels (the trigger guard opening)."""
    W, H = src.size
    px = src.load()
    bg = px[0, 0]
    isbg = bytearray(1 if all(abs(p[c] - bg[c]) <= BG_TOLERANCE for c in range(3)) else 0 for p in src.getdata())
    seen = bytearray(W * H)
    out = bytearray(W * H)
    for start in range(W * H):
        if not isbg[start] or seen[start]:
            continue
        region, q, edge = [], deque([start]), False
        seen[start] = 1
        while q:
            i = q.popleft()
            region.append(i)
            x, y = i % W, i // W
            edge = edge or x in (0, W - 1) or y in (0, H - 1)
            for j in ((i + 1) if x + 1 < W else -1, (i - 1) if x else -1, (i + W) if y + 1 < H else -1, (i - W) if y else -1):
                if j >= 0 and isbg[j] and not seen[j]:
                    seen[j] = 1
                    q.append(j)
        if edge or len(region) >= HOLE_MIN:
            for i in region:
                out[i] = 1
    return Image.frombytes('L', (W, H), bytes(0 if s else 255 for s in out))


def reduce(rgba, size):
    small = rgba.resize(size, Image.Resampling.BOX)  # RGBA BOX = premultiplied
    px = small.load()
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, a = px[x, y]
            px[x, y] = (0, 0, 0, 0) if a < ALPHA_CUT else (r, g, b, 255)
    rgb = small.convert('RGB').filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=2))
    out = rgb.convert('RGBA')
    out.putalpha(small.getchannel('A'))
    return out


def hand_point(alpha, width, height):
    """First row below the frame where the grip is all that is left (opaque pixels
    only in the left 45%), two rows lower; the centre of the grip there."""
    a = alpha.load()
    for y in range(height // 3, height):
        xs = [x for x in range(width) if a[x, y]]
        if xs and max(xs) < width * 0.45:
            row = min(y + 2, height - 1)
            xs = [x for x in range(width) if a[x, row]]
            return (min(xs) + max(xs) + 1) / 2, row
    raise RuntimeError('grip not found')


def extended_mag(sprite, w, h):
    """Bottom of the grip, MAG_EXTRA rows longer: the rows just above the baseplate
    are repeated, each repeat shifted along the grip's tilt; the baseplate stays at
    the bottom. Returns the piece and its top-left corner in sprite pixels."""
    a = sprite.getchannel('A').load()
    grip = int(w * 0.45)
    centres = []
    for y in range(h - 10, h - 2):
        xs = [x for x in range(grip) if a[x, y]]
        if xs:
            centres.append((y, (min(xs) + max(xs)) / 2))
    n = len(centres)
    my = sum(y for y, _ in centres) / n
    mx = sum(x for _, x in centres) / n
    slope = sum((y - my) * (x - mx) for y, x in centres) / sum((y - my) ** 2 for y, _ in centres)
    src = sprite.crop((0, h - MAG_KEEP, grip, h))
    body_rows = MAG_KEEP - MAG_BASE  # rows of magazine body kept above the baseplate
    piece = Image.new('RGBA', (grip + MAG_EXTRA, MAG_KEEP + MAG_EXTRA))
    piece.alpha_composite(src.crop((0, 0, grip, body_rows)), (0, 0))
    row = src.crop((0, body_rows - 1, grip, body_rows))
    for k in range(MAG_EXTRA):
        piece.alpha_composite(row, (max(0, round(slope * (k + 1))), body_rows + k))
    piece.alpha_composite(src.crop((0, body_rows, grip, MAG_KEEP)), (max(0, round(slope * MAG_EXTRA)), body_rows + MAG_EXTRA))
    bb = piece.getbbox()
    return piece.crop(bb), (bb[0], h - MAG_KEEP + bb[1])


def beretta_hand():
    """The same point on the Beretta, in its root units."""
    s = json.loads((ANIM / 'weapon-beretta.json').read_text(encoding='utf-8'))
    att = next(iter(s['skins'][0]['attachments']['body'].values()))
    im = Image.open(GAME / (att['name'] + '.png')).convert('RGBA')
    gx, gy = hand_point(im.getchannel('A'), im.width, im.height)
    left, top = att['x'] - att['width'] / 2, att['y'] + att['height'] / 2
    return left + gx, top - gy - 0.5


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    src = Image.open(REF / 'qsz92-approved.png').convert('RGB')
    alpha = cutout(src)
    box = alpha.getbbox()
    rgba = src.convert('RGBA')
    rgba.putalpha(alpha)
    hires = rgba.crop(box)
    hires.save(REF / 'qsz92-skin-hires.png')
    scale = WIDTH / hires.width
    size = (WIDTH, round(hires.height * scale))
    im = reduce(hires, size)
    # at 1/39 the concept turns grey and soft; the stock pistols are crisp, so
    # lift the contrast before the palette and draw their 1 px dark outline after
    a = im.getchannel('A')
    im = ImageEnhance.Contrast(im.convert('RGB')).enhance(CONTRAST).convert('RGBA')
    im.putalpha(a)
    # shared look with the other new guns: one palette, no lone pixels
    pal = im.convert('RGB').quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT)
    q = im.convert('RGB').quantize(palette=pal, dither=Image.Dither.NONE).convert('RGBA')
    q.putalpha(im.getchannel('A'))
    qp = q.load()
    lonely = [(x, y) for y in range(size[1]) for x in range(size[0]) if qp[x, y][3] and not any(
        qp[x + dx, y + dy][3] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
        if (dx or dy) and 0 <= x + dx < size[0] and 0 <= y + dy < size[1])]
    for x, y in lonely:
        qp[x, y] = (0, 0, 0, 0)
    edge = [(x, y) for y in range(size[1]) for x in range(size[0]) if qp[x, y][3] and any(
        not (0 <= x + dx < size[0] and 0 <= y + dy < size[1]) or not qp[x + dx, y + dy][3]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in edge:
        qp[x, y] = OUTLINE
    q = q.crop(q.getbbox())
    q.save(GAME / 'qsz92-skin.png')
    w, h = q.size

    # place the sprite: our grip point on the Beretta grip point, whole pixels
    gx, gy = hand_point(q.getchannel('A'), w, h)
    bx, by = beretta_hand()
    left = round(bx - gx)
    top = round(by + gy + 0.5)

    def unit(cx, cy):  # concept pixel -> root units
        return left + (cx - box[0]) * scale, top - (cy - box[1]) * scale

    muzzle_x = left + w
    fire_x, bore = unit(CHAMBER_X, BORE_Y)
    shell = unit(*PORT)

    # 30-round magazine: the bottom of the grip lengthened along the grip's tilt
    mag, mag_box = extended_mag(q, w, h)
    mag.save(GAME / 'qsz92-clip-extended.png')
    mw, mh = mag.size
    clip_att = {'name': 'qsz92-clip-extended', 'x': left + mag_box[0] + mw / 2, 'y': top - mag_box[1] - mh / 2,
                'width': mw, 'height': mh}
    # laser: the FNX-45 unit (12x6) under the dust cover, front flush with the frame
    lx = round(unit(LASER_FRONT[0], 0)[0]) - 12
    ly = round(unit(0, LASER_FRONT[1])[1])
    laser_att = {'name': 'fnx45-laser', 'x': lx + 6, 'y': ly - 3, 'width': 12, 'height': 6}
    skeleton = {
        'skeleton': {'hash': 'qsz92-approved', 'spine': '4.0.36', 'x': left * .4, 'y': (top - h) * .4,
                     'width': w * .4, 'height': h * .4, 'images': '../../../textures/GAME/', 'audio': ''},
        'bones': [
            {'name': 'root', 'scaleX': .4, 'scaleY': .4},
            {'name': 'center-bone', 'parent': 'root', 'x': left + w / 2, 'y': top - h / 2},
            {'name': 'fire-bone', 'parent': 'root', 'length': round((muzzle_x - fire_x) / 2.5, 3),
             'x': round(fire_x, 3), 'y': round(bore, 3), 'scaleX': 2.5, 'scaleY': 2.5},
            {'name': 'laser-bone', 'parent': 'root', 'length': 3.54, 'x': lx + 11,
             'y': ly - 3, 'scaleX': 2, 'scaleY': 2},
            {'name': 'shell-bone', 'parent': 'root', 'length': 1.8, 'rotation': 91.36,
             'x': round(shell[0], 3), 'y': round(shell[1], 3), 'scaleX': 2.5, 'scaleY': 2.5},
        ],
        # clip and laser are empty until an attachment switches them on
        'slots': [{'name': 'body', 'bone': 'root', 'attachment': 'default'},
                  {'name': 'clip', 'bone': 'root'}, {'name': 'laser', 'bone': 'root'}],
        'skins': [{'name': 'weapon-default', 'attachments': {
            'body': {'default': {'name': 'qsz92-skin', 'x': left + w / 2, 'y': top - h / 2, 'width': w, 'height': h}},
            'clip': {'extended': clip_att},
            'laser': {'on': laser_att}}}],
        'animations': {'animation': {}},
    }
    (ANIM / 'weapon-qsz92.json').write_text(json.dumps(skeleton, indent=1) + '\n', encoding='utf-8')
    prev = Image.new('RGBA', (w + 8, h + 8), (58, 62, 68, 255))
    prev.alpha_composite(q, (4, 4))
    prev.resize((prev.width * 8, prev.height * 8), Image.Resampling.NEAREST).save(OUT / 'preview-8x.png')
    print('sprite %dx%d (scale 1/%.1f), left %d top %d, grip %s -> Beretta %s'
          % (w, h, 1 / scale, left, top, (gx, gy), (round(bx, 2), round(by, 2))))


if __name__ == '__main__':
    main()
