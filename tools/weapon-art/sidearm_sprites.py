"""Find the parts of a pistol sprite and split it into frame / slide / magazine.

Used by launcher/sidearms.py (the generic version of launcher/colt1911.py) and runnable:

    python tools/weapon-art/sidearm_sprites.py beretta [more ids...] [--sheet out.png]

Geometry (sprite pixels, row 0 = top) found from the alpha mask of the pistol's default skin:
  slide_rows  rows of the slide: the rows that reach close to the muzzle (>= SLIDE_REACH of width)
  hammer      columns left of it stay on the frame (hammer, beavertail)
  base_row    bottom row of the grip; base_cols = magazine base plate pixels in it
  grip        middle of the grip (the fist closes there)
  axis        magazine axis in gun space (degrees, from the base plate up into the grip),
              from the slope of the front edge of the grip
  front       front of the grip under the trigger guard (support fist), rear = slide serrations
The same split is applied to every skin of the weapon (same silhouette).
Outputs (textures/GAME): sa-<weapon>-frame-<n>.png, sa-<weapon>-slide-<n>.png, sa-<weapon>-mag.png
"""
from pathlib import Path
import math
import sys
from PIL import Image

GAME = Path(__file__).resolve().parents[2] / "data/packages/base/textures/GAME"
SLIDE_REACH = .88


def opaque(px, x, y):
    return px[x, y][3] > 0


def analyse(img, overrides=None):
    o = dict(overrides or {})
    w, h = img.size
    px = img.load()
    rows = [[x for x in range(w) if opaque(px, x, y)] for y in range(h)]
    reach = [max(r) if r else -1 for r in rows]
    slide = [y for y in range(h) if reach[y] >= SLIDE_REACH * (w - 1)]
    top = o.get("slide_top", min(slide))
    bottom = o.get("slide_bottom", max(y for y in slide if y < h * .6))
    hammer = o.get("hammer", max(3, round(w * .12)))
    left = round(w * .45)
    def run(y):
        # the first solid run of pixels from the left: the grip itself, not the trigger guard
        xs = [x for x in rows[y] if x < left]
        if not xs:
            return []
        out = [xs[0]]
        for x in xs[1:]:
            if x != out[-1] + 1:
                break
            out.append(x)
        return out

    grip_rows = [y for y in range(bottom + 1, h) if len(run(y)) >= 3]
    base_row = o.get("base_row", max(grip_rows))
    base = run(base_row)
    # front edge of the grip over its lower part -> magazine axis
    lower = [y for y in grip_rows if y >= base_row - max(6, (base_row - bottom) // 2)]
    fronts = [(max(run(y)), y) for y in lower if run(y)]
    n = len(fronts)
    mx = sum(f[0] for f in fronts) / n
    my = sum(f[1] for f in fronts) / n
    cov = sum((f[0] - mx) * (f[1] - my) for f in fronts)
    var = sum((f[1] - my) ** 2 for f in fronts) or 1
    slope = cov / var                      # sprite columns per row going down
    # going up one row the edge moves -slope columns; gun space has y up
    axis = o.get("axis", math.degrees(math.atan2(1, -slope)))
    # grip middle: the pixels of the grip half way between the slide and the base
    mid_rows = [y for y in grip_rows if y <= (bottom + base_row) / 2 + 3 and y >= (bottom + base_row) / 2 - 3]
    pts = [(x, y) for y in mid_rows for x in run(y)]
    grip = o.get("grip", (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)))
    front_row = o.get("front_row", round(bottom + (base_row - bottom) * .35))
    fr = run(front_row) or run(front_row + 1)
    front = o.get("front", (max(fr) + .5, front_row))
    rear = o.get("rear", (hammer + 2, (top + bottom) / 2))
    mag_w = max(3, round(len(base) * .55))
    mag_len = max(10, round((base_row - bottom) * .85))
    extra = {k: o[k] for k in ("box", "fixed_mag", "pivot", "support", "support_angle") if k in o}
    return dict(extra, size=(w, h), slide_top=top, slide_bottom=bottom, hammer=hammer, base_row=base_row,
                base_cols=(min(base), max(base)), base=((min(base) + max(base)) / 2 + .5, base_row + .5),
                axis=axis, grip=grip, front=front, rear=rear, mag=(mag_w, mag_len))


def split(img, g):
    w, h = img.size
    px = img.load()
    frame = img.copy()
    slide = Image.new("RGBA", img.size)
    fpx, spx = frame.load(), slide.load()
    if "box" in g:
        x0, y0, x1, y1 = g["box"]
        cells = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)]
    else:
        cells = [(x, y) for y in range(0, g["slide_bottom"] + 1) for x in range(g["hammer"], w)]
    for x, y in cells:
        if px[x, y][3] > 0:
            spx[x, y] = px[x, y]
            fpx[x, y] = (0, 0, 0, 0)
    solid = [px[x, y] for y in range(h) for x in range(w) if px[x, y][3] == 255]
    dark = min(solid, key=lambda c: c[0] + c[1] + c[2]) if solid else (30, 30, 30, 255)
    barrel = (min(255, dark[0] + 18), min(255, dark[1] + 18), min(255, dark[2] + 18), 255)
    b = g["slide_bottom"] if "box" not in g else -1
    for y in range(max(0, b - 3), b):
        for x in range(g["hammer"] + 10, w - 2):
            if fpx[x, y][3] == 0:
                fpx[x, y] = barrel
    lo, hi = g["base_cols"]
    plate = [px[x, g["base_row"]] for x in range(lo, hi + 1)]
    if not g.get("fixed_mag"):
        for x in range(lo, hi + 1):
            fpx[x, g["base_row"]] = (0, 0, 0, 0)
    return frame, slide, plate, dark


def stripper_clip(rounds=5):
    """A stripper clip seen from the side: brass rounds stacked on a steel strip (upright)."""
    brass, tip, steel = (186, 150, 70, 255), (150, 110, 60, 255), (90, 92, 96, 255)
    img = Image.new("RGBA", (6, rounds * 2 + 1))
    p = img.load()
    for i in range(rounds):
        y = i * 2
        for x in range(1, 5):
            p[x, y] = brass
        p[5, y] = tip
    for y in range(rounds * 2 + 1):
        p[0, y] = steel
    return img


def magazine(g, plate, dark):
    mw, ml = g["mag"]
    body = (min(255, dark[0] + 30), min(255, dark[1] + 30), min(255, dark[2] + 32), 255)
    edge = (min(255, dark[0] + 62), min(255, dark[1] + 62), min(255, dark[2] + 66), 255)
    brass = (176, 140, 64, 255)
    w = max(mw + 2, len(plate))
    img = Image.new("RGBA", (w, ml + 1))
    p = img.load()
    left = (w - mw) // 2
    for y in range(ml):
        for x in range(left, left + mw):
            p[x, y] = edge if x == left else body
    p[left + mw // 2, 0] = brass
    for i, c in enumerate(plate[:w]):
        p[i + (w - len(plate[:w])) // 2, ml] = c if c[3] else dark
    for x in range(w):
        if p[x, ml][3] == 0:
            p[x, ml] = dark
    return img


def build(weapon, skins, overrides=None, out=GAME):
    """skins: [(skin index, sprite name)]; returns the geometry of the default sprite."""
    default = Image.open(GAME / (skins[0][1] + ".png")).convert("RGBA")
    g = analyse(default, overrides)
    mag = None
    done = []
    for n, name in skins:
        img = Image.open(GAME / (name + ".png")).convert("RGBA")
        if img.size != default.size:
            continue      # another silhouette: this skin keeps its whole-pistol sprite
        done.append(n)
        frame, slide, plate, dark = split(img, g)
        frame.save(out / ("sa-%s-frame-%d.png" % (weapon, n)))
        slide.save(out / ("sa-%s-slide-%d.png" % (weapon, n)))
        if mag is None:
            mag = stripper_clip() if g.get("fixed_mag") else magazine(g, plate, dark)
    mag.save(out / ("sa-%s-mag.png" % weapon))
    g["mag_img"] = mag.size
    g["split"] = done
    return g


def sheet(ids, path):
    from PIL import ImageDraw
    tiles = []
    for wid in ids:
        img = Image.open(GAME / (wid + "-skin.png")).convert("RGBA")
        g = analyse(img)
        frame, slide, plate, dark = split(img, g)
        s = 8
        W, H = img.size
        canvas = Image.new("RGBA", (W * 3 + 20, H + 10), (60, 64, 60, 255))
        whole = frame.copy(); whole.alpha_composite(slide)
        tint = Image.new("RGBA", img.size)
        tp = tint.load(); sp = slide.load()
        for y in range(H):
            for x in range(W):
                if sp[x, y][3]:
                    tp[x, y] = (255, 60, 60, 140)
        lo, hi = g["base_cols"]
        for x in range(lo, hi + 1):
            tp[x, g["base_row"]] = (60, 120, 255, 255)
        over = whole.copy(); over.alpha_composite(tint)
        back = frame.copy(); s2 = Image.new("RGBA", img.size); s2.paste(slide, (-4, 0)); back.alpha_composite(s2)
        canvas.alpha_composite(whole, (2, 5)); canvas.alpha_composite(over, (W + 8, 5)); canvas.alpha_composite(back, (2 * W + 14, 5))
        big = canvas.resize((canvas.width * s, canvas.height * s), Image.NEAREST)
        d = ImageDraw.Draw(big)
        ox = (W + 8) * s; oy = 5 * s
        for (x, y), col in ((g["grip"], "yellow"), (g["front"], "cyan"), (g["rear"], "magenta"), (g["base"], "blue")):
            cx, cy = ox + x * s, oy + y * s
            d.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), outline=col, width=2)
        bx, by = g["base"]
        a = math.radians(g["axis"])
        d.line((ox + bx * s, oy + by * s, ox + (bx + 14 * math.cos(a)) * s, oy + (by - 14 * math.sin(a)) * s), fill="yellow", width=2)
        d.text((4, 2), "%s axis %.0f" % (wid, g["axis"]), fill="white")
        tiles.append(big)
    W = max(t.width for t in tiles)
    H = sum(t.height for t in tiles)
    out = Image.new("RGBA", (W, H), (40, 40, 40, 255))
    y = 0
    for t in tiles:
        out.paste(t, (0, y)); y += t.height
    out.save(path)




# --- the whole family: python tools/weapon-art/sidearm_sprites.py --all [base.zip] ----------------
FAMILY = {
    # weapon id: overrides of the automatic geometry (sprite pixels)
    "aps": {}, "baltiets": {}, "beretta": {}, "browning": {}, "cz75": {}, "desert": {},
    "desert50ae": {}, "fiveseven": {}, "fnx45": {}, "fort12": {}, "jericho": {}, "makarov": {},
    "mp443": {}, "ots33": {}, "p99": {}, "pistol": {}, "pistol-s": {}, "qsz92": {}, "sigsauer": {},
    "taurus": {"base_row": 23, "axis": 76}, "tt": {}, "usp": {"slide_bottom": 6}, "usp-match": {"slide_bottom": 7},
    "vp70": {},
    # Beretta 93R: the support hand on the folding foregrip in front of the trigger guard
    "m93r": {"support": (31.0, 17.5), "support_angle": 115},
    # Luger: the toggle (rear upper receiver) folds up around its front joint
    "luger": {"box": (0, 0, 15, 4), "pivot": (15.5, 4.5)},
    # Mauser C96: fixed magazine in front of the trigger guard, loaded from stripper clips
    # through the top with the bolt (its ears at the rear) held back
    "mauser": {"box": (2, 0, 13, 2), "fixed_mag": True, "base_row": 20},
}
GEOMETRY = Path(__file__).resolve().parents[2] / "launcher" / "sidearms_geometry.json"


def build_all(zip_path):
    import json
    import zipfile
    z = zipfile.ZipFile(zip_path)
    content = json.loads(z.read("content.json"))["content"]
    out = {}
    for wid, over in FAMILY.items():
        item = content["weapon-" + wid]
        comp = next(c for c in item["components"] if "states" in c and "animation" in c)
        model = json.loads(z.read("content/" + content[comp["animation"]]["animation"].split(":")[1]))
        body = next(s for s in model["slots"] if s["name"] in ("body", "weapon-default"))
        skins = []
        for i, skin in enumerate(model["skins"]):
            att = skin.get("attachments", {}).get(body["name"], {}).get(body.get("attachment"))
            if att:
                skins.append((i, skin["name"], att.get("path", att.get("name", body.get("attachment")))))
        default = next((s for s in skins if s[1] == comp.get("skin", "weapon-default")), skins[0])
        ordered = [default] + [s for s in skins if s is not default]
        g = build(wid, [(i, sprite) for i, _, sprite in ordered], over)
        g["skins"] = {name: i for i, name, _ in skins if i in g["split"]}
        g["body_slot"] = body["name"]
        out[wid] = g
        print(wid, "axis %.0f" % g["axis"], "skins", len(skins))
    GEOMETRY.write_text(json.dumps(out, indent=1))
    print(GEOMETRY)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--all":
        build_all(args[1] if len(args) > 1 else
                  Path(__file__).resolve().parents[2] / "build/base-client-premod.zip")  # before sidearms.py
        sys.exit(0)
    if "--sheet" in args:
        i = args.index("--sheet")
        path = args[i + 1]
        del args[i:i + 2]
        sheet(args, path)
        print(path)
    else:
        for wid in args:
            print(wid, analyse(Image.open(GAME / (wid + "-skin.png")).convert("RGBA")))
