"""Render a frame of the player rig (actor.json) with a weapon attached, straight from a
built base.zip — for checking hand poses and magazine paths without starting the game.

    python tools/weapon-art/spine_preview.py base.zip out.png --clip solo-weapon-colt-reload-1hand
        [--times 0,0.2,0.4] [--weapon weapon-colt] [--skin bear] [--scale 6]

Spine 4.0 subset: bone rotate/translate timelines (linear), slot attachment timelines,
region attachments. The weapon skeleton hangs on the holder-primary bone (slot-primary),
like SkeletonRenderer.update does in the game.
"""
from pathlib import Path
import argparse
import io
import json
import math
import zipfile
from PIL import Image


MARK = False


def load_atlas(z, name):
    regions = {}
    text = z.read('content/textures/%s.atlas' % name).decode('utf-8')
    page = None
    cur = None
    for line in text.splitlines():
        if not line.strip():
            page = None
            continue
        if page is None:
            page = Image.open(io.BytesIO(z.read('content/textures/' + line.strip()))).convert('RGBA')
            continue
        if ':' not in line:
            cur = {'page': page}
            regions[line.strip()] = cur
            continue
        k, v = [s.strip() for s in line.split(':', 1)]
        if cur is not None:
            cur[k] = v
    out = {}
    for n, r in regions.items():
        if 'xy' not in r:
            continue
        x, y = map(int, r['xy'].split(','))
        w, h = map(int, r['size'].split(','))
        if r.get('rotate') == 'true':
            img = r['page'].crop((x, y, x + h, y + w)).rotate(90, expand=True)
        else:
            img = r['page'].crop((x, y, x + w, y + h))
        ox, oy = map(int, r.get('offset', '0,0').split(','))
        ow, oh = map(int, r.get('orig', '%d,%d' % (w, h)).split(','))
        full = Image.new('RGBA', (ow, oh))
        full.paste(img, (ox, oh - h - oy))
        out[n] = full
    return out


def sample(keys, t, field, default):
    if not keys:
        return default
    if t <= keys[0].get('time', 0):
        return keys[0].get(field, default)
    for a, b in zip(keys, keys[1:]):
        ta, tb = a.get('time', 0), b.get('time', 0)
        if ta <= t <= tb:
            if a.get('curve') == 'stepped' or tb == ta:
                return a.get(field, default)
            f = (t - ta) / (tb - ta)
            return a.get(field, default) + (b.get(field, default) - a.get(field, default)) * f
    return keys[-1].get(field, default)


class Rig:
    def __init__(self, data):
        self.data = data
        self.bones = {b['name']: b for b in data['bones']}
        self.order = [b['name'] for b in data['bones']]

    def pose(self, clip, t, parent=None):
        anim = self.data['animations'].get(clip, {}) if clip else {}
        tl = anim.get('bones', {})
        world = {}
        for n in self.order:
            b = self.bones[n]
            r = b.get('rotation', 0) + sample(tl.get(n, {}).get('rotate', []), t, 'value', 0)
            x = b.get('x', 0) + sample(tl.get(n, {}).get('translate', []), t, 'x', 0)
            y = b.get('y', 0) + sample(tl.get(n, {}).get('translate', []), t, 'y', 0)
            sx = b.get('scaleX', 1) * sample(tl.get(n, {}).get('scale', []), t, 'x', 1)
            sy = b.get('scaleY', 1) * sample(tl.get(n, {}).get('scale', []), t, 'y', 1)
            la, lb = math.cos(math.radians(r)) * sx, math.cos(math.radians(r + 90)) * sy
            lc, ld = math.sin(math.radians(r)) * sx, math.sin(math.radians(r + 90)) * sy
            p = world[b['parent']] if 'parent' in b else parent
            if p is None:
                world[n] = (la, lb, lc, ld, x, y)
            else:
                pa, pb, pc, pd, px, py = p
                world[n] = (pa * la + pb * lc, pa * lb + pb * ld, pc * la + pd * lc, pc * lb + pd * ld,
                            pa * x + pb * y + px, pc * x + pd * y + py)
        slots = {}
        st = anim.get('slots', {})
        for s in self.data['slots']:
            att = s.get('attachment')
            keys = st.get(s['name'], {}).get('attachment')
            if keys:
                for k in keys:
                    if k.get('time', 0) <= t + 1e-6:
                        att = k.get('name')
            slots[s['name']] = att
        return world, slots

    def attachment(self, skin_names, slot, name):
        for sk in skin_names:
            for s in self.data['skins']:
                if s['name'] == sk:
                    a = s.get('attachments', {}).get(slot, {}).get(name)
                    if a is not None:
                        return a
        return None


def draw(canvas, origin, scale, matrix, att, region):
    if region is None or att.get('type', 'region') != 'region':
        return
    a, b, c, d, wx, wy = matrix
    w, h = att.get('width', region.width), att.get('height', region.height)
    sx, sy = att.get('scaleX', 1), att.get('scaleY', 1)
    r = math.radians(att.get('rotation', 0))
    # local corner -> bone space -> world -> canvas, inverse map for PIL affine
    def to_world(u, v):  # u,v in attachment-local (centered) units
        lx = att.get('x', 0) + (u * sx) * math.cos(r) - (v * sy) * math.sin(r)
        ly = att.get('y', 0) + (u * sx) * math.sin(r) + (v * sy) * math.cos(r)
        X = a * lx + b * ly + wx
        Y = c * lx + d * ly + wy
        return origin[0] + X * scale, origin[1] - Y * scale
    # affine from image pixel (px,py) to canvas: image (0,0)=top-left -> local (-w/2, h/2)
    p0 = to_world(-w / 2, h / 2)
    px = to_world(-w / 2 + w, h / 2)
    py = to_world(-w / 2, h / 2 - h)
    ax, ay = (px[0] - p0[0]) / region.width, (px[1] - p0[1]) / region.width
    bx, by = (py[0] - p0[0]) / region.height, (py[1] - p0[1]) / region.height
    det = ax * by - bx * ay
    if abs(det) < 1e-9:
        return
    ia, ib, ic, id_ = by / det, -bx / det, -ay / det, ax / det
    tx, ty = -(ia * p0[0] + ib * p0[1]), -(ic * p0[0] + id_ * p0[1])
    layer = region.transform(canvas.size, Image.AFFINE, (ia, ib, tx, ic, id_, ty), resample=Image.NEAREST)
    canvas.alpha_composite(layer)


def render(zpath, clip, t, weapon_json, weapon_skin, actor_skin, scale=6, size=(420, 420), weapon_clip=None,
           weapon_t=0, override=None, paired=False):
    z = zipfile.ZipFile(zpath)
    actor = json.loads(z.read('content/animations/actor.json'))
    if override:
        actor['animations'].update(override)
    rig = Rig(actor)
    regions = {}
    for name in ('GAME', 'PIXELED'):
        try:
            regions.update(load_atlas(z, name))
        except KeyError:
            pass
    # sprites not packed yet: take them straight from the source folder
    src = Path(__file__).resolve().parents[2] / 'data/packages/base/textures/GAME'
    for p in list(src.glob('colt1911-*.png')) + list(src.glob('sa-*.png')) + list(src.glob('fm-*.png')) + list(src.glob('sa-shell-*.png')) + list(src.glob('g11-*.png')):
        regions.setdefault(p.stem, Image.open(p).convert('RGBA'))
    world, slots = rig.pose(clip, t)
    canvas = Image.new('RGBA', size, (70, 74, 70, 255))
    origin = (size[0] * 0.42, size[1] * 0.45)
    gun = None
    if weapon_json:
        gun = Rig(json.loads(z.read(weapon_json)) if isinstance(weapon_json, str) else weapon_json)
    hooks = {'slot-primary': 'pair-magazine-left'}
    if paired:
        hooks['slot-secondary'] = 'pair-magazine-right'
    anim_bones = actor['animations'].get(clip, {}).get('bones', {})
    order = list(actor['slots'])
    for key in actor['animations'].get(clip, {}).get('drawOrder', []):
        if key.get('time', 0) <= t + 1e-6:
            order = list(actor['slots'])
            moved = {o['slot']: o['offset'] for o in key.get('offsets', [])}
            names = [sl['name'] for sl in order]
            rest = [sl for sl in order if sl['name'] not in moved]
            final = [None] * len(order)
            for n, off in moved.items():
                final[names.index(n) + off] = order[names.index(n)]
            it = iter(rest)
            order = [f if f is not None else next(it) for f in final]
    for s in order:
        name = slots.get(s['name'])
        if s['name'] in hooks and gun is not None:
            marker_name = hooks[s['name']]
            tl = anim_bones.get(marker_name, {}).get('translate', [])
            mx, my = sample(tl, t, 'x', 0), sample(tl, t, 'y', 0)
            hide = (abs(mx) > .01 or abs(my) > .01) and slots.get(marker_name) is None
            if 'pair-mag-travel' in gun.bones:
                gun.bones['pair-mag-travel']['x'] = mx
                gun.bones['pair-mag-travel']['y'] = my
                gun.bones['pair-mag-travel']['scaleX'] = gun.bones['pair-mag-travel']['scaleY'] = 0.0001 if hide else 1
            gworld, gslots = gun.pose(weapon_clip, weapon_t, parent=world[s['bone']])
            for gs in gun.data['slots']:
                gname = gslots.get(gs['name'])
                if gname is None:
                    continue
                att = gun.attachment([weapon_skin, 'default'], gs['name'], gname)
                if att is None:
                    continue
                draw(canvas, origin, scale, gworld[gs['bone']], att, regions.get(att.get('path', att.get('name', gname))))
            continue
        if s['name'].startswith('pair-magazine-'):
            continue  # hidden in game when the pistol has its own magazine
        if name is None or s['name'].startswith('phy-'):
            continue
        att = rig.attachment([actor_skin, 'default'], s['name'], name)
        if att is None:
            continue
        draw(canvas, origin, scale, world[s['bone']], att, regions.get(att.get('path', att.get('name', name))))
    if MARK:   # debug: where the fists (holder bones) are
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        for n, col in (('holder-primary', 'red'), ('holder-secondary', 'cyan')):
            x, y = world[n][4], world[n][5]
            X, Y = origin[0] + x * scale, origin[1] - y * scale
            d.ellipse((X - 4, Y - 4, X + 4, Y + 4), outline=col, width=2)
    return canvas


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('zip')
    ap.add_argument('out')
    ap.add_argument('--clip', default='solo-weapon-colt-hold-weapon-1hand')
    ap.add_argument('--times', default='0')
    ap.add_argument('--weapon', default='content/animations/weapon-colt.json')
    ap.add_argument('--wskin', default='weapon-default')
    ap.add_argument('--skin', default='bear')
    ap.add_argument('--scale', type=float, default=6)
    a = ap.parse_args()
    frames = [render(a.zip, a.clip, float(t), a.weapon, a.wskin, a.skin, a.scale) for t in a.times.split(',')]
    W = sum(f.width for f in frames)
    sheet = Image.new('RGBA', (W, frames[0].height))
    x = 0
    for f in frames:
        sheet.paste(f, (x, 0))
        x += f.width
    sheet.save(a.out)
    print(a.out, sheet.size)
