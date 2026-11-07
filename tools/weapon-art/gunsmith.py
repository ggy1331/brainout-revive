"""
"Gunsmith": lots of attachments for AK-74, M4A1, MP5, SVD and Glock (test client, branch xm8).

Parts are existing pictures of other weapons (textures/GAME). For every weapon the script
  1) adds slots / attachments to its Spine skeleton (every skin of the weapon),
  2) writes upgrade files to smart/Weapons/<weapon>/Upgrades/Gunsmith/,
  3) adds the upgrades to the weapon's Store Item.txt (one row per slot in the modification menu).
It always starts from the committed (git HEAD) skeleton and Store Item, so it can be re-run.

Placement uses anchor points of each weapon (root coordinates, y up):
  rail    - bottom of the part sits on the rail, centred at x
  muzzle  - left end of the part where the muzzle device starts (the suppressor covers the flash hider /
            muzzle brake, like the original game mounts them), centred vertically on the barrel
  under   - top of the part hangs under the handguard / barrel, centred at x
  clip    - top-left corner like the weapon's own magazine (curved mags insert the same way)
  at      - explicit centre (x, y)

Run from the brainout-xm8 root:
  ..\\brainout\\build\\pyenv\\Scripts\\python.exe tools\\weapon-art\\gunsmith.py
Then: scripts/make_data.py client + server. Preview: build/gunsmith/<weapon>.png
"""
import json
import os
import re
import subprocess
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE = os.path.join(ROOT, "data", "packages", "base")
GAME = os.path.join(BASE, "textures", "GAME")
ANIM = os.path.join(BASE, "contents", "content", "animations")
WEAP = os.path.join(BASE, "smart", "Weapons")
OUT = os.path.join(ROOT, "build", "gunsmith")

SILENCED_SHOTS = """[
                pistol-shoot-s-1, pistol-shoot-smoke
                pistol-shoot-s-2, pistol-shoot-smoke
                pistol-shoot-s-3, pistol-shoot-smoke
            ]"""

# ---------------------------------------------------------------- what goes where
# kind: scope | silencer | grip | light | laser | clip | bipod | plain
# props: game upgrade properties ("+N" add, "=N" set)

GUNS = {
    "ak74": {
        "folder": "ak74", "skeleton": "weapon-ak74",
        "anchors": {"rail": (13, 20), "side": (8.5, 17), "muzzle": (92, None), "grip": (45, 12),
                    "tac": (64, 14.5), "clip": "clip-default"},
        "slots_after": {"silencer": "body", "tactical": "body", "grip": "body"},
        "parts": [
            ("scope", "pkas", "ak105-scope-pkas", "side", "ITEM_UPGRADE_SCOPE_PKAS", "scope", {"accuracy": "+12", "aim-distance": "+8"}),
            ("scope", "elcan", "ak12-scope-elcan", "rail", "ITEM_UPGRADE_SCOPE_ELCAN", "scope", {"accuracy": "+14", "aim-distance": "+18"}),
            ("scope", "eot", "famas-scope-eot", "rail", "ITEM_UPGRADE_SCOPE_EOT", "scope", {"accuracy": "+14", "aim-distance": "+6"}),
            ("scope", "po4x34", "groza-scope-po4x34", "rail", "ITEM_UPGRADE_SCOPE_PO4X34", "scope", {"accuracy": "+15", "aim-distance": "+25"}),
            ("scope", "1p86", "vssm-scope-1p86", "rail", "ITEM_UPGRADE_SCOPE_1P86", "scope", {"accuracy": "+18", "aim-distance": "+32", "speed-coef": "=0.95"}),
            ("silencer", "pbs1", "ak74m-2-silencer", "muzzle", "ITEM_UPGRADE_GS_PBS1", "silencer", {"damage": "-5"}),
            ("silencer", "tgp", "aksu-silencer", "muzzle", "ITEM_UPGRADE_GS_TGP", "silencer", {"damage": "-4", "accuracy": "+4"}),
            ("silencer", "dtk", "ak9-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_HEAVY", "silencer", {"damage": "-3", "recoil": "-5"}),
            ("grip", "angled", "ak12-holder", "grip", "ITEM_UPGRADE_GS_GRIP_ANGLED", "grip", {"recoil": "-8", "accuracy": "+4"}),
            ("grip", "vertical", "aksu-holder-on", "grip", "ITEM_UPGRADE_HOLDER", "grip", {"recoil": "-12"}),
            ("grip", "rk", "pecheneg-holder", "grip", "ITEM_UPGRADE_GS_GRIP_RAIL", "grip", {"recoil": "-15", "speed-coef": "=0.97"}),
            ("tactical", "light", "aek-light", "tac", "ITEM_UPGRADE_LIGHT", "light", {"accuracy": "+4"}),
            ("tactical", "light2", "sigsauer-light", "tac", "ITEM_UPGRADE_GS_LIGHT_COMPACT", "light", {"accuracy": "+2"}),
            ("tactical", "laser", "kiparis-laser", "tac", "ITEM_UPGRADE_LASER", "laser", {"accuracy": "+10"}),
            ("tactical", "laser2", "fnx45-laser", "tac", "ITEM_UPGRADE_GS_LASER_IR", "laser", {"accuracy": "+8", "aim-distance": "+4"}),
            ("clip", "rpk45", "rpk74-clip-extended", "clip", "ITEM_UPGRADE_GS_MAG45", "clip", {"clip-size": "+15", "reload-time": "+0.2"}),
            ("clip", "drum95", "rpk16-clip-extended", "clip", "ITEM_UPGRADE_GS_DRUM", "clip", {"clip-size": "+65", "reload-time": "+0.9", "speed-coef": "=0.92"}),
        ],
        "extra": {"gl": ["gs-ak74-gl-gp30"]},
    },
    "m4a1": {
        "folder": "m4a1", "skeleton": "weapon-m4a1",
        "anchors": {"rail": (11, 19), "muzzle": (70, None), "grip": (32, 11.5), "tac": (45, 12.5),
                    "clip": "clip-default"},
        "slots_after": {"silencer": "body", "tactical": "body"},
        "parts": [
            ("scope", "eot", "m4a1-scope-eot", "rail", "ITEM_UPGRADE_SCOPE_EOT", "scope", {"accuracy": "+14", "aim-distance": "+6"}),
            ("scope", "aimpoint", "g36c-scope-aimpoint", "rail", "ITEM_UPGRADE_SCOPE_AIMPOINT", "scope", {"accuracy": "+12", "aim-distance": "+5"}),
            ("scope", "susat", "lr300-scope-susat", "rail", "ITEM_UPGRADE_SCOPE_SUSAT", "scope", {"accuracy": "+15", "aim-distance": "+22"}),
            ("scope", "redfield", "m14-scope-redfield", "rail", "ITEM_UPGRADE_SCOPE_REDFIELD", "scope", {"accuracy": "+18", "aim-distance": "+32", "speed-coef": "=0.95"}),
            ("silencer", "sig", "sig552-silencer", "muzzle", "ITEM_UPGRADE_SILENCER", "silencer", {"damage": "-5"}),
            ("silencer", "scar", "scarl-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_QD", "silencer", {"damage": "-4", "accuracy": "+4"}),
            ("silencer", "colt", "colt-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_HEAVY", "silencer", {"damage": "-3", "recoil": "-5"}),
            ("holder", "angled", "ar57-holder", "grip", "ITEM_UPGRADE_GS_GRIP_ANGLED", "grip", {"recoil": "-8", "accuracy": "+4"}),
            ("holder", "angled-tan", "scar-holder", "grip", "ITEM_UPGRADE_GS_GRIP_ANGLED", "grip", {"recoil": "-9", "accuracy": "+3"}),
            ("holder", "stubby", "qbs-holder", "grip", "ITEM_UPGRADE_GS_GRIP_STUBBY", "grip", {"recoil": "-6", "accuracy": "+6"}),
            ("tactical", "light", "ar57-light", "tac", "ITEM_UPGRADE_LIGHT", "light", {"accuracy": "+3"}),
            ("tactical", "light2", "sigsauer-light", "tac", "ITEM_UPGRADE_GS_LIGHT_COMPACT", "light", {"accuracy": "+2"}),
            ("tactical", "laser", "sr47-laser", "tac", "ITEM_UPGRADE_LASER", "laser", {"accuracy": "+10"}),
            ("tactical", "laser2", "kiparis-laser", "tac", "ITEM_UPGRADE_GS_LASER_IR", "laser", {"accuracy": "+8", "aim-distance": "+4"}),
            ("clip", "mag40", "m16a3-clip-extended", "clip", "ITEM_UPGRADE_GS_MAG40", "clip", {"clip-size": "+10", "reload-time": "+0.15"}),
            ("clip", "cmag", "g36-clip-extended", "clip", "ITEM_UPGRADE_GS_CMAG", "clip", {"clip-size": "+70", "reload-time": "+1", "speed-coef": "=0.92"}),
        ],
        # the M203 for the M4A1 exists in the game files but was never offered (cut content)
        "extra": {"holder": ["upgrade-m4a1-gl-m203"]},
    },
    "mp5": {
        "folder": "mp5", "skeleton": "weapon-mp5",
        "anchors": {"rail": (16, 21.8), "muzzle": (54, None), "tac": (48, 12.5), "clip": "default"},
        "slots_after": {"silencer": "body", "tactical": "holder"},
        "parts": [
            ("scope", "aimpoint", "g36c-scope-aimpoint", "rail", "ITEM_UPGRADE_SCOPE_AIMPOINT", "scope", {"accuracy": "+12", "aim-distance": "+5"}),
            ("scope", "truglo", "fn2000-scope-truglo", "rail", "ITEM_UPGRADE_SCOPE_TRUGLO", "scope", {"accuracy": "+10", "aim-distance": "+4"}),
            ("scope", "holo", "m4a1-scope-eot", "rail", "ITEM_UPGRADE_GS_HOLO_TAN", "scope", {"accuracy": "+13", "aim-distance": "+6"}),
            ("scope", "acog", "sig552-scope-acog", "rail", "ITEM_UPGRADE_SCOPE_ACOG", "scope", {"accuracy": "+15", "aim-distance": "+18"}),
            ("silencer", "mp7", "mp7-silencer", "muzzle", "ITEM_UPGRADE_SILENCER", "silencer", {"damage": "-4"}),
            ("silencer", "long", "mp9-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_LONG", "silencer", {"damage": "-3", "accuracy": "+5"}),
            ("silencer", "short", "svu-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_QD", "silencer", {"damage": "-5", "recoil": "-3"}),
            ("tactical", "light", "mp7a2-light", "tac", "ITEM_UPGRADE_LIGHT", "light", {"accuracy": "+3"}),
            ("tactical", "light2", "keltec-light", "tac", "ITEM_UPGRADE_GS_LIGHT_COMPACT", "light", {"accuracy": "+2"}),
            ("tactical", "laser", "kiparis-laser", "tac", "ITEM_UPGRADE_LASER", "laser", {"accuracy": "+10"}),
            ("clip", "mag40", "mp5k-clip-extended", "clip", "ITEM_UPGRADE_EXTENDED_CLIP", "clip", {"clip-size": "+10", "reload-time": "+0.1"}),
            ("clip", "mag50", "mp5sd6-clip-extended", "clip", "ITEM_UPGRADE_GS_MAG50", "clip", {"clip-size": "+20", "reload-time": "+0.3"}, (-2, 1)),
        ],
    },
    "svd": {
        "folder": "svd", "skeleton": "weapon-svd",
        "anchors": {"rail": (13, 14.2), "pso": (14, 14.5), "muzzle": (125, None), "bipod": (100, 10),
                    "tac": (88, 10)},
        "slots_after": {"silencer": "body", "bipod": "body", "tactical": "body"},
        "parts": [
            ("scope", "1p86", "vssm-scope-1p86", "rail", "ITEM_UPGRADE_SCOPE_1P86", "scope", {"aim-distance": "+30", "accuracy": "+10"}),
            ("scope", "po4x34", "groza-scope-po4x34", "rail", "ITEM_UPGRADE_SCOPE_PO4X34", "scope", {"aim-distance": "+22", "accuracy": "+8"}),
            ("scope", "pkas", "ak105-scope-pkas", "pso", "ITEM_UPGRADE_SCOPE_PKAS", "scope", {"aim-distance": "+6", "accuracy": "+8"}, (0, -3)),
            ("scope", "sv98", "sv98-scope-optical", "rail", "ITEM_UPGRADE_GS_SCOPE_POSP", "scope", {"aim-distance": "+40", "accuracy": "+12", "speed-coef": "=0.95"}),
            ("scope", "vssk", "vssk-scope-optical", "rail", "ITEM_UPGRADE_GS_SCOPE_TACTICAL", "scope", {"aim-distance": "+45", "accuracy": "+14", "speed-coef": "=0.93"}),
            ("silencer", "long", "m110-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_LONG", "silencer", {"damage": "-8"}),
            ("silencer", "short", "svu-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_QD", "silencer", {"damage": "-10", "recoil": "-5"}),
            ("bipod", "on", "sniper-bipod", "bipod", "ITEM_UPGRADE_BIPOD", "bipod", {"recoil": "-20", "accuracy": "+8"}),
            ("tactical", "laser", "sr47-laser", "tac", "ITEM_UPGRADE_LASER", "laser", {"accuracy": "+8"}),
        ],
    },
    "pistol": {
        "folder": "glock 17", "skeleton": "weapon-pistol",
        "anchors": {"rail": (7, 13.5), "muzzle": (24, 9.7), "tac": (17.6, 6.76), "clip": "extended"},
        "slots_after": {},
        "parts": [
            ("scope", "truglo", "fn2000-scope-truglo", "rail", "ITEM_UPGRADE_SCOPE_TRUGLO", "scope", {"accuracy": "+10", "aim-distance": "+4"}),
            ("scope", "micro", "fnx45-scope", "rail", "ITEM_UPGRADE_GS_SCOPE_MICRO", "scope", {"accuracy": "+8", "aim-distance": "+2"}),
            ("barrel", "s57", "fiveseven-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_QD", "silencer", {"damage": "-3"}),
            ("barrel", "colt", "colt-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_HEAVY", "silencer", {"damage": "-2", "recoil": "-4"}),
            ("light", "light", "sigsauer-light", "tac", "ITEM_UPGRADE_LIGHT", "light", {"accuracy": "+3"}),
            ("light", "light2", "taurus-light", "tac", "ITEM_UPGRADE_GS_LIGHT_COMPACT", "light", {"accuracy": "+2"}),
            ("light", "laser2", "fnx45-laser", "tac", "ITEM_UPGRADE_GS_LASER_IR", "laser", {"accuracy": "+8"}),
        ],
    },
    # our XM8: a scope needs the carry handle with its built-in red dot gone -> every scope also swaps
    # the body to xm8-skin-rail (tools/weapon-art/xm8_rail.py)
    "xm8": {
        "folder": "xm8", "skeleton": "weapon-xm8",
        "anchors": {"rail": (17, 19.26), "muzzle": (78, None), "grip": (54, 10.3), "tac": (63, 15),
                    "clip": "default"},
        "slots_after": {"grip": "body", "tactical": "body", "scope": "body"},
        "body_for_scopes": ("rail", "xm8-skin-rail"),
        "remove": ["recoil"],  # balance: no recoil chain, like the M4A1 (base recoil 35 in Weapon.txt)
        "parts": [
            ("scope", "aimpoint", "g36c-scope-aimpoint", "rail", "ITEM_UPGRADE_SCOPE_AIMPOINT", "scope", {"accuracy": "+12", "aim-distance": "+5"}),
            ("scope", "eot", "m4a1-scope-eot", "rail", "ITEM_UPGRADE_SCOPE_EOT", "scope", {"accuracy": "+14", "aim-distance": "+6"}),
            ("scope", "acog", "sig552-scope-acog", "rail", "ITEM_UPGRADE_SCOPE_ACOG", "scope", {"accuracy": "+15", "aim-distance": "+18"}),
            ("scope", "susat", "lr300-scope-susat", "rail", "ITEM_UPGRADE_SCOPE_SUSAT", "scope", {"accuracy": "+15", "aim-distance": "+22"}),
            ("scope", "elcan", "ak12-scope-elcan", "rail", "ITEM_UPGRADE_SCOPE_ELCAN", "scope", {"accuracy": "+14", "aim-distance": "+18"}),
            ("scope", "redfield", "m14-scope-redfield", "rail", "ITEM_UPGRADE_SCOPE_REDFIELD", "scope", {"accuracy": "+18", "aim-distance": "+32", "speed-coef": "=0.95"}),
            ("silencer", "scar", "scarl-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_QD", "silencer", {"damage": "-4", "accuracy": "+4"}),
            ("silencer", "colt", "colt-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_HEAVY", "silencer", {"damage": "-3", "recoil": "-5"}),
            ("silencer", "long", "mp9-silencer", "muzzle", "ITEM_UPGRADE_GS_SILENCER_LONG", "silencer", {"damage": "-3", "accuracy": "+5"}),
            ("grip", "angled", "ak12-holder", "grip", "ITEM_UPGRADE_GS_GRIP_ANGLED", "grip", {"recoil": "-8", "accuracy": "+4"}),
            ("grip", "vertical", "tar21-holder", "grip", "ITEM_UPGRADE_HOLDER", "grip", {"recoil": "-12"}),
            ("grip", "stubby", "qbs-holder", "grip", "ITEM_UPGRADE_GS_GRIP_STUBBY", "grip", {"recoil": "-6", "accuracy": "+6"}),
            ("tactical", "light", "ar57-light", "tac", "ITEM_UPGRADE_LIGHT", "light", {"accuracy": "+3"}),
            ("tactical", "light2", "sigsauer-light", "tac", "ITEM_UPGRADE_GS_LIGHT_COMPACT", "light", {"accuracy": "+2"}),
            ("tactical", "laser", "sr47-laser", "tac", "ITEM_UPGRADE_LASER", "laser", {"accuracy": "+10"}),
            ("tactical", "laser2", "kiparis-laser", "tac", "ITEM_UPGRADE_GS_LASER_IR", "laser", {"accuracy": "+8", "aim-distance": "+4"}),
            ("clip", "mag40", "m16a3-clip-extended", "clip", "ITEM_UPGRADE_GS_MAG40", "clip", {"clip-size": "+10", "reload-time": "+0.15"}),
            ("clip", "cmag", "g36-clip-extended", "clip", "ITEM_UPGRADE_GS_CMAG", "clip", {"clip-size": "+70", "reload-time": "+1", "speed-coef": "=0.92"}),
        ],
    },
}

# new names (RU, EN); other languages get the EN text
NAMES = {
    "ITEM_UPGRADE_GS_PBS1": ("Глушитель ПБС-1", "PBS-1 Suppressor"),
    "ITEM_UPGRADE_GS_TGP": ("Глушитель ТГП-А", "TGP-A Suppressor"),
    "ITEM_UPGRADE_GS_SILENCER_HEAVY": ("Тяжёлый глушитель", "Heavy Suppressor"),
    "ITEM_UPGRADE_GS_SILENCER_QD": ("Быстросъёмный глушитель", "QD Suppressor"),
    "ITEM_UPGRADE_GS_SILENCER_LONG": ("Длинный глушитель", "Long Suppressor"),
    "ITEM_UPGRADE_GS_GRIP_ANGLED": ("Наклонная рукоятка", "Angled Grip"),
    "ITEM_UPGRADE_GS_GRIP_RAIL": ("Цевьё с рукояткой", "Rail Handguard with Grip"),
    "ITEM_UPGRADE_GS_GRIP_STUBBY": ("Короткая рукоятка", "Stubby Grip"),
    "ITEM_UPGRADE_GS_LIGHT_COMPACT": ("Компактный фонарь", "Compact Flashlight"),
    "ITEM_UPGRADE_GS_LASER_IR": ("ЛЦУ", "Laser Aiming Module"),
    "ITEM_UPGRADE_GS_MAG45": ("Магазин РПК на 45", "45-rd RPK Magazine"),
    "ITEM_UPGRADE_GS_DRUM": ("Барабанный магазин", "Drum Magazine"),
    "ITEM_UPGRADE_GS_MAG40": ("Магазин на 40", "40-rd Magazine"),
    "ITEM_UPGRADE_GS_CMAG": ("Сдвоенный барабан C-Mag", "C-Mag Twin Drum"),
    "ITEM_UPGRADE_GS_MAG50": ("Магазин на 50", "50-rd Magazine"),
    "ITEM_UPGRADE_GS_HOLO_TAN": ("Голографический прицел (песочный)", "Holographic Sight (tan)"),
    "ITEM_UPGRADE_GS_SCOPE_POSP": ("Прицел ПОСП 8х42", "POSP 8x42 Scope"),
    "ITEM_UPGRADE_GS_SCOPE_TACTICAL": ("Тактический прицел 10х", "10x Tactical Scope"),
    "ITEM_UPGRADE_GS_SCOPE_MICRO": ("Микро-коллиматор", "Micro Red Dot"),
}
DESC = {"scope": "ITEM_UPGRADE_SCOPE_OPTICAL_DESC", "silencer": "ITEM_UPGRADE_SILENCER_DESC",
        "grip": "ITEM_UPGRADE_HOLDER_DESC", "light": "ITEM_UPGRADE_LIGHT_DESC", "laser": "ITEM_UPGRADE_LASER_DESC",
        "clip": "ITEM_UPGRADE_EXTENDED_CLIP_DESC", "bipod": "ITEM_UPGRADE_BIPOD_DESC"}


def git_head(path):
    rel = os.path.relpath(path, ROOT).replace("\\", "/")
    return subprocess.run(["git", "show", "HEAD:" + rel], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")


def skins_of(d):
    sk = d["skins"]
    if isinstance(sk, dict):
        return [(k, v) for k, v in sk.items()]
    for s in sk:
        s.setdefault("attachments", {})
    return [(s["name"], s["attachments"]) for s in sk]


def solid_bbox(im):
    """bbox of the solid part: rows/columns with at least 2 clearly opaque pixels (faint edges ignored)."""
    a = im.split()[3].point(lambda v: 255 if v > 160 else 0)
    w, h = im.size
    px = a.load()
    rows = [y for y in range(h) if sum(1 for x in range(w) if px[x, y]) >= 2]
    cols = [x for x in range(w) if sum(1 for y in range(h) if px[x, y]) >= 1]
    if not rows or not cols:
        return im.getbbox()
    return cols[0], rows[0], cols[-1] + 1, rows[-1] + 1


def mount_centre(im, bottom):
    """x (picture pixels) of the middle of the scope mount: solid pixels in the 2 lowest solid rows."""
    px = im.load()
    cols = [x for x in range(im.width) for y in (bottom - 1, bottom - 2)
            if 0 <= y < im.height and px[x, y][3] > 160]
    if not cols:
        return im.width / 2
    return (min(cols) + max(cols) + 1) / 2


def barrel_y(default_atts, mx):
    """Height of the bore: middle of the barrel in the body picture just behind the muzzle device."""
    body = next(iter(default_atts["body"].values()))
    im = Image.open(os.path.join(GAME, body["name"] + ".png")).convert("RGBA")
    left = body["x"] - body["width"] / 2
    top = body["y"] + body["height"] / 2
    centres = []
    for rx in range(int(mx) - 4, int(mx)):
        px = int(rx - left)
        if not 0 <= px < im.width:
            continue
        rows = [py for py in range(im.height) if im.getpixel((px, py))[3] > 160]
        if not rows:
            continue
        runs, cur = [], [rows[0]]
        for r in rows[1:]:
            if r == cur[-1] + 1:
                cur.append(r)
            else:
                runs.append(cur)
                cur = [r]
        runs.append(cur)
        run = runs[-1]  # lowest run = the barrel; columns where it merges with a sight post are skipped
        if len(run) <= 4:
            centres.append(top - (run[0] + run[-1] + 1) / 2)
    centres.sort()
    return centres[len(centres) // 2]  # median


def place(img_name, anchor, gun, default_atts):
    im = Image.open(os.path.join(GAME, img_name + ".png")).convert("RGBA")
    w, h = im.size
    l, t, r, b = solid_bbox(im)
    a = gun["anchors"]
    if anchor == "clip":
        ref = default_atts["clip"][gun["anchors"]["clip"]]
        left = ref["x"] - ref["width"] / 2
        top = ref["y"] + ref["height"] / 2
        cx, cy = left + w / 2, top - h / 2
    elif anchor == "muzzle":
        mx, my = a["muzzle"]
        if my is None:
            my = barrel_y(default_atts, mx)
        cx = mx + w / 2 - l
        cy = my - h / 2 + (t + b) / 2
    elif anchor in ("grip", "tac", "bipod") and anchor in a:
        ux, uy = a[anchor]
        cx = ux + w / 2 - (l + r) / 2
        cy = uy - h / 2 + t
        if anchor == "bipod":
            cx = ux + w / 2 - l  # hangs from its left end
    elif anchor == "side":
        # side-mounted optic: same placement as the weapon's own side-mount scope
        sx, sy = a["side"]
        cx, cy = sx, sy
    elif anchor == "pso":
        ref = default_atts["scope"]["pso"]
        # align the bracket bottom and the rear of the PSO
        cx = ref["x"] - ref["width"] / 2 + w / 2
        cy = (ref["y"] - ref["height"] / 2) + h / 2
    else:  # rail
        rx, ry = a["rail"]
        cx = rx + w / 2 - mount_centre(im, b)  # the mount, not the middle of a long scope, sits at x
        cy = ry - h / 2 + b
    # keep texture pixels on the same pixel grid as the body (avoids blurry / half-pixel parts)
    body = next(iter(default_atts["body"].values()))
    gx = (body["x"] - body["width"] / 2) % 1
    gy = (body["y"] - body["height"] / 2) % 1
    cx = round(cx - w / 2 - gx) + gx + w / 2
    cy = round(cy - h / 2 - gy) + gy + h / 2
    return {"name": img_name, "x": round(cx, 4), "y": round(cy, 4), "width": w, "height": h}


def props_block(props):
    return "\n".join('    %s = "%s"' % kv for kv in props.items())


def upgrade_text(uid, key, att, img, name, kind, props, gun_id, extra_replace=None):
    replaces = "\n".join("            %s = %s" % kv for kv in [(key, att)] + list((extra_replace or {}).items()))
    comps = ["""    {
        class = content.components.ReplaceSlotComponent
        classToReplace = data.components.WeaponAnimationComponentData
        replace = {
%s
        }
        tag = client
    }""" % replaces, """    {
        big-icon = %s
        class = content.components.IconComponent
        tag = client
    }""" % img]
    props = dict(props)
    if kind == "silencer":
        comps.append("""    {
        class = content.components.SuppressBulletAttachmentsComponent
        suppress = fire-bone
        tag = client
    }
    {
        class = content.components.ReplaceInstrumentEffectsComponent
        replace = {
            shoot = %s
        }
        tag = client
    }""" % SILENCED_SHOTS)
        props["silent"] = "=1"
    elif kind == "laser":
        comps.append("""    {
        class = content.components.LaserComponent
        tag = client
    }""")
    elif kind == "light":
        comps.append("""    {
        class = content.components.InstrumentLightComponent
        color = 333333FF
        cone = 14
        distance = 60
        rays = 32
        soft = 12
        tag = client
    }""")
    return """// Generated by tools/weapon-art/gunsmith.py - edit the script, not this file.
access = byDefault
class = content.upgrades.Upgrade
components = [
%s
]
description = %s
id = %s
name = %s
properties = {
%s
}
""" % ("\n".join(comps), DESC.get(kind, "ITEM_UPGRADE_HOLDER_DESC"), uid, name, props_block(props))


GP30 = """// Generated by tools/weapon-art/gunsmith.py: GP-30 for the AK-74 (its picture was already in the skeleton)
access = byDefault
class = content.upgrades.Upgrade
components = [
    {
        class = content.components.ReplaceSlotComponent
        classToReplace = data.components.WeaponAnimationComponentData
        replace = {
            gl = gp30
        }
        tag = client
    }
    {
        big-icon = ak74-gl-gp30
        class = content.components.IconComponent
        tag = client
    }
    {
        class = content.components.ReplaceInstrumentEffectsComponent
        replace = {
            reloadSecondary = [
                [
                    {
                        attachTo = fire-secondary-bone
                        object = gl-insert-1
                    }
                ]
            ]
            shootSecondary = [
                [
                    {
                        attachTo = fire-secondary-bone
                        object = shoot-flash-1
                    }
                    {
                        attachTo = fire-secondary-bone
                        object = pistol-shoot-smoke
                    }
                    {
                        attachTo = fire-secondary-bone
                        object = gl-shoot-1
                    }
                    {
                        attachTo = fire-secondary-bone
                        object = pistol-shoot-fire-1
                    }
                ]
            ]
        }
        tag = client
    }
    {
        class = content.components.SecondaryWeaponSlotComponent
        icon = icon-shop-special-gl
        properties = {
            accuracy = 35
            aimDistance = 30
            allowedBullets = grenade-bullet
            clipSize = 1
            damage = 500
            fire-rate = 120
            recoil = 29
            reloadTime = 1.8
            shootModes = single
        }
    }
]
description = ITEM_UPGRADE_GL_GP30_DESC
id = gs-ak74-gl-gp30
name = ITEM_UPGRADE_GL_GP30
properties = {
    speed-coef = "=0.95"
}
"""


def add_to_store(text, additions):
    """additions: key -> [upgrade ids]; appends to `upgrades = { ... }` of the instrument."""
    m = re.search(r"(\n(\s*)upgrades\s*=\s*\{)(.*?)(\n\s*\})", text, re.S)
    if not m:
        raise RuntimeError("no upgrades block")
    head, indent, body, tail = m.group(1), m.group(2), m.group(3), m.group(4)
    inner = indent + "    "
    for key, ids in additions.items():
        line = re.search(r"(\n[ \t]*%s[ \t]*=[ \t]*)([^\n]*)" % re.escape(key), body)
        if line:
            body = body[:line.end(2)] + ", " + ", ".join(ids) + body[line.end(2):]
        else:
            body += "\n%s%s = %s" % (inner, key, ", ".join(ids))
    return text[:m.start()] + head + body + tail + text[m.end():]


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for gid, gun in GUNS.items():
        skel_path = os.path.join(ANIM, gun["skeleton"] + ".json")
        d = json.loads(git_head(skel_path))
        skins = skins_of(d)
        default_atts = dict(skins)["weapon-default"]
        slot_names = [s["name"] for s in d["slots"]]
        # new slots, drawn right after the given slot
        for slot, after in gun["slots_after"].items():
            if slot not in slot_names:
                i = slot_names.index(after) + 1 if after in slot_names else len(slot_names)
                d["slots"].insert(i, {"name": slot, "bone": "root"})
                slot_names.insert(i, slot)
        if gun.get("body_for_scopes"):
            variant, img = gun["body_for_scopes"]
            for _, atts in skins:
                body_atts = atts["body"]
                body_atts[variant] = dict(next(iter(body_atts.values())), name=img)
        for p in gun["parts"]:
            if p[0] not in slot_names:
                d["slots"].append({"name": p[0], "bone": "root"})
                slot_names.append(p[0])

        folder = os.path.join(WEAP, gun["folder"])
        updir = os.path.join(folder, "Upgrades", "Gunsmith")
        os.makedirs(updir, exist_ok=True)
        for f in os.listdir(updir):
            if f.endswith(".txt"):
                os.remove(os.path.join(updir, f))

        additions = {}
        for part in gun["parts"]:
            key, var, img, anchor, name, kind, props = part[:7]
            dx, dy = part[7] if len(part) > 7 else (0, 0)
            att_name = "gs-" + var
            att = place(img, anchor, gun, default_atts)
            att["x"] += dx
            att["y"] += dy
            for _, atts in skins:
                atts.setdefault(key, {})[att_name] = dict(att)
            uid = "gs-%s-%s-%s" % (gid, key, var)
            with open(os.path.join(updir, "%s %s.txt" % (key, var)), "w", encoding="utf-8") as f:
                extra = None
                if kind == "scope" and gun.get("body_for_scopes"):
                    extra = {"body": gun["body_for_scopes"][0]}
                f.write(upgrade_text(uid, key, att_name, img, name, kind, props, gid, extra))
            additions.setdefault(key, []).append(uid)
            total += 1
        if gid == "ak74":
            with open(os.path.join(updir, "gl gp30.txt"), "w", encoding="utf-8") as f:
                f.write(GP30)
        for key, ids in gun.get("extra", {}).items():
            additions.setdefault(key, []).extend(ids)

        with open(skel_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")
        store = os.path.join(folder, "Store Item.txt")
        text = git_head(store).replace("\r\n", "\n")
        # upgrade rows taken away from the weapon (e.g. XM8: no recoil chain, like the M4A1)
        for key in gun.get("remove", []):
            text = re.sub(r"\n[ \t]*%s[ \t]*=[^\n]*" % re.escape(key), "", text, count=1)
        with open(store, "w", encoding="utf-8", newline="\n") as f:
            f.write(add_to_store(text, additions))
        print(gid, sum(len(v) for v in additions.values()), "attachments")
    add_names()
    print("total generated", total)


def add_names():
    p = os.path.join(BASE, "localization", "input.json")
    raw = open(p, encoding="utf-8").read()
    # make_data reads input.json in the Windows code page (cp1251), so every non-ASCII letter must be
    # written as a \uXXXX escape, like all original strings. Our entries are rewritten on every run.
    raw = re.sub(r'    "ITEM_UPGRADE_GS_[A-Z0-9_]+": \{[^}]*\},\n', "", raw)
    data = json.loads(raw)
    langs = list(data["ITEM_UPGRADE_SILENCER"].keys())
    block = ""
    for k, (ru, en) in NAMES.items():
        if k in data:
            continue
        vals = {l: (ru if l == "RU" else en) for l in langs}
        block += '    "%s": {\n' % k + ",\n".join('        "%s": %s' % (l, json.dumps(v))
                                               for l, v in vals.items()) + "\n    },\n"
    if block:
        anchor = '    "ITEM_UPGRADE_SILENCER": {'
        assert raw.count(anchor) == 1
        raw = raw.replace(anchor, block + anchor)
        json.loads(raw)
        open(p, "w", encoding="utf-8", newline="").write(raw)


def preview():
    """build/gunsmith/<gun>.png: the weapon with each attachment on, one per tile, 4x."""
    from PIL import ImageDraw
    S = 4
    for gid, gun in GUNS.items():
        d = json.load(open(os.path.join(ANIM, gun["skeleton"] + ".json"), encoding="utf-8"))
        atts = dict(skins_of(d))["weapon-default"]
        base = {s["name"]: s.get("attachment") for s in d["slots"]}
        tiles = [("default", dict(base))]
        for key, var, *_ in gun["parts"]:
            sel = dict(base); sel[key] = "gs-" + var
            if key == "scope" and gun.get("body_for_scopes"):
                sel["body"] = gun["body_for_scopes"][0]
            tiles.append((key + "/" + var, sel))
        boxes = []
        for _, sel in tiles:
            for s in d["slots"]:
                a = atts.get(s["name"], {}).get(sel.get(s["name"]) or "")
                if a:
                    boxes.append((a["x"] - a["width"] / 2, a["y"] - a["height"] / 2, a["x"] + a["width"] / 2, a["y"] + a["height"] / 2))
        x0 = min(b[0] for b in boxes) - 2; y0 = min(b[1] for b in boxes) - 2
        x1 = max(b[2] for b in boxes) + 2; y1 = max(b[3] for b in boxes) + 2
        W, H = int(x1 - x0) * S, int(y1 - y0) * S + 14
        cols = 3
        sheet = Image.new("RGB", (W * cols, H * ((len(tiles) + cols - 1) // cols)), (58, 58, 62))
        dr = ImageDraw.Draw(sheet)
        for i, (label, sel) in enumerate(tiles):
            c = Image.new("RGBA", (int(x1 - x0), int(y1 - y0)), (0, 0, 0, 0))
            for s in d["slots"]:
                a = atts.get(s["name"], {}).get(sel.get(s["name"]) or "")
                if not a:
                    continue
                im = Image.open(os.path.join(GAME, a.get("name") + ".png")).convert("RGBA")
                c.alpha_composite(im, (int(round(a["x"] - a["width"] / 2 - x0)), int(round(y1 - (a["y"] + a["height"] / 2)))))
            ox, oy = (i % cols) * W, (i // cols) * H
            sheet.paste(c.resize((c.width * S, c.height * S), Image.NEAREST), (ox, oy + 14), c.resize((c.width * S, c.height * S), Image.NEAREST))
            dr.text((ox + 4, oy + 1), label, fill=(255, 255, 140))
        sheet.save(os.path.join(OUT, gid + ".png"))


if __name__ == "__main__":
    main()
    preview()
