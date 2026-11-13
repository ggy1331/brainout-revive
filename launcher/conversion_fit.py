"""Fitting a moved attachment to the target gun by its pixels (used by conversions.py).

An attachment moved from its own model to another by the anchor points lands roughly right; this
settles it the way it sat on its own model, measured on the pixels of both guns:
  scope              the bottom of its mount over the top of the gun under it (the same gap or, for
                     a scope on a side bracket, the same overlap);
  grip / tactical /  its top against the bottom of the gun above it (handguard, barrel);
  gl
  silencer           centred on the bore at the muzzle, starting the same distance from the end of
                     the barrel (over the flash hider like on its own model).
measure() is also the check: report() lists every model x attachment that is still off.
"""
import os

from PIL import Image

import gunsmith

_IMG = {}
_BODY = {}


def solid(name):
    """(width, height, [(i, j)] solid pixels) of a texture"""
    if name not in _IMG:
        im = Image.open(os.path.join(gunsmith.GAME, name + ".png")).convert("RGBA")
        al = im.split()[3].load()
        _IMG[name] = (im.width, im.height,
                      [(i, j) for i in range(im.width) for j in range(im.height) if al[i, j] > 160])
    return _IMG[name]


def points(att, default_name=None):
    """centres of the attachment's solid pixels in root units"""
    w, h, px = solid(att.get("name", default_name))
    k = att.get("scaleX", 1)
    x0, y0 = att.get("x", 0) - att["width"] * k / 2, att.get("y", 0) + att["height"] * k / 2
    return [(x0 + (i + .5) * k, y0 - (j + .5) * k) for i, j in px], k


def body(skel, atts, shown, not_body, key):
    """solid pixels of every part of the gun shown by default (cached per skeleton)"""
    if key in _BODY:
        return _BODY[key]
    pts = []
    for slot, name in shown.items():
        if slot in not_body or not name:
            continue
        a = atts.get(slot, {}).get(name)
        if a:
            pts += points(a, name)[0]
    cols = {}
    for x, y in pts:
        cols.setdefault(round(x * 4) / 4, []).append(y)
    _BODY[key] = (pts, cols)
    return _BODY[key]


def _column(cols, x, k):
    out = []
    for cx, ys in cols.items():
        if abs(cx - x) <= k / 2 + 1e-6:
            out += ys
    return out


def measure(kind, att, gun):
    """kind: scope | grip | silencer; gun = (pts, cols, k). None if it can't be measured."""
    pts, cols, k = gun
    P, ka = points(att)
    if not P:
        return None
    if kind == "scope":
        bottom = min(y for x, y in P)
        mount = sorted({x for x, y in P if y <= bottom + 1.5 * ka})
        tops = [max(c) for c in (_column(cols, x, k) for x in mount) if c]
        if not tops:
            return {"float": True}
        return {"gap": bottom - max(tops)}
    if kind == "grip":
        top = max(y for x, y in P)
        row = sorted({x for x, y in P if y >= top - 0.5 * ka})
        gaps = []
        for x in row:
            ys = sorted(_column(cols, x, k))
            runs, cur = [], []
            for y in ys:
                if cur and y - cur[-1] > k * 1.01:
                    runs.append(cur)
                    cur = []
                cur.append(y)
            if cur:
                runs.append(cur)
            # the part of the gun right above the attachment: the lowest run reaching above its top
            above = [r for r in runs if r[-1] > top + 0.01]
            if above:
                gaps.append(min(above, key=lambda r: r[-1])[0] - top)
        if not gaps:
            return {"float": True}
        return {"gap": min(gaps)}
    if kind == "silencer":
        left = min(x for x, y in P)
        near = [y for x, y in P if x <= left + 1.5 * ka]
        cy = sum(near) / len(near)
        # the bore: thin runs (a barrel, <= 4 px) in the columns around the start of the silencer,
        # the one nearest to it; the end of the barrel: the last pixel on that line
        thin = []
        for cx, ys in cols.items():
            if not left - 20 * k <= cx <= left + 20 * k:
                continue
            ys = sorted(ys)
            run = [ys[0]]
            for y in ys[1:] + [None]:
                if y is not None and y - run[-1] <= k * 1.01:
                    run.append(y)
                    continue
                if (run[-1] - run[0]) / k <= 3.01 and abs((run[0] + run[-1]) / 2 - cy) <= 5 * k:
                    thin.append((run[0] + run[-1]) / 2)
                if y is not None:
                    run = [y]
        if not thin:
            return {"float": True}
        thin.sort(key=lambda b: abs(b - cy))
        cands = [b for b in thin if abs(b - thin[0]) <= k * 0.6]
        bore = sorted(cands)[len(cands) // 2]
        line = [x for x, y in pts if abs(y - bore) <= k * 0.6 and x <= left + 40 * k]
        if not line:
            return {"float": True}
        return {"dx": left - max(line), "dy": cy - bore}
    return None


KIND = {"scope": "scope", "optic": "scope", "silencer": "silencer", "grip": "grip", "holder": "grip",
        "tactical": "grip", "light": "grip", "laser": "grip"}   # launchers (gl) wrap the barrel: anchor only
LIMIT = 12          # pixels: a bigger correction means the measure is wrong, keep the anchor place


def settle(kind, att, gun, ref, snap=lambda a: None):
    """move att (in place) so that measure() on this gun matches ref (measured on its own model);
    snap keeps it on the gun's pixel grid after every step (what is measured is what is drawn)"""
    if not ref or ref.get("float"):
        return False
    k = gun[2]
    for _ in range(3):
        cur = measure(kind, att, gun)
        if not cur or cur.get("float"):
            return False
        if kind in ("scope", "grip"):
            d = ref["gap"] - cur["gap"]
            if abs(d) > LIMIT * k:
                return False
            att["y"] = att.get("y", 0) + (d if kind == "scope" else -d)
            snap(att)
            continue
        else:
            dy, dx = ref["dy"] - cur["dy"], ref["dx"] - cur["dx"]
            if abs(dy) > LIMIT * k or abs(dx) > 3 * LIMIT * k:
                return False
            att["y"] = att.get("y", 0) + dy
            att["x"] = att.get("x", 0) + dx
        snap(att)
    return True


def off(kind, cur, ref, k):
    """why a fitted attachment is still wrong (None = fine)"""
    if cur is None:
        return None
    if cur.get("float"):
        return None if ref and ref.get("float") else "no gun under/behind it"
    if not ref or ref.get("float"):
        return None
    if kind in ("scope", "grip"):
        if abs(cur["gap"] - ref["gap"]) > 1.5 * k:
            return "gap %.1f px (own model %.1f)" % (cur["gap"] / k, ref["gap"] / k)
    else:
        if abs(cur["dy"] - ref["dy"]) > 1.5 * k or abs(cur["dx"] - ref["dx"]) > 2.5 * k:
            return "bore %.1f / start %.1f px (own model %.1f / %.1f)" % (
                cur["dy"] / k, cur["dx"] / k, ref["dy"] / k, ref["dx"] / k)
    return None
