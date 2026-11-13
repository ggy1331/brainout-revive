"""Weapon families: one base weapon in the shop, the other models of the family are its conversions.

    python conversions.py source-base.zip result-base.zip      (run from the launcher folder)

Runs last in build_packages (after every other stage that touches weapons).

For every family (FAMILIES):
  * a conversion upgrade per model ("conversion" row of the base weapon's modification menu):
    conversion = the model's weapon, convertsFrom / conversionBase = old loadouts that selected the
    model are translated to base + conversion (ShopCart), ammo = the model's own ammo when it differs
    from the base weapon's (another calibre, an RPK's bigger stock of rounds);
  * the models' own shop items are hidden (enabled = false);
  * attachments are shared: every visual upgrade of any model of the family (scopes, suppressors,
    grips, lights / lasers, magazines, the GP-30) is offered on the base weapon and fits every model.
    Each one gets its own attachment "cv-<upgrade id>" in the slot of its kind in every family skeleton
    (names like "extended" or "on" mean different pictures on different models). On its own model it
    keeps its original place; on the others it is moved by the difference of the models' anchor
    points (ANCHORS: scope rail, muzzle, grip, tactical rail; magazines: the default magazine's
    top-left corner) and snapped to the body's pixel grid.
  * upgrades that only make sense on their own model are left out (MODEL_ONLY: the AK-74 metal stock,
    the AKS-74U handguard grip, the RPK-16 bipod).
Preview: python conversions.py --preview OUT_DIR   (needs build/packages-client/8-g11.zip from build_packages)
"""
from copy import deepcopy
import json
import os
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gameplay_package import encode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "weapon-art"))
import gunsmith  # noqa: E402  (barrel_y: the height of the bore in a body picture)

# base -> members (conversions, menu order); borrow: other families' bases whose attachments are
# offered too (the AKMS takes the AK-74 gunsmith set: the same Kalashnikov mounts)
FAMILIES = {
    "ak74": {"members": ["aksu", "ak74m", "akm74-2", "ak105", "ak105bullpup", "ak12", "rpk74", "rpk16"]},
    "akm": {"members": ["ak15", "a762", "tul1"], "borrow": ["ak74"]},
    # AR-15 / AR-10 (M16A2 has its M203 drawn into the body: no second launcher on it)
    "m16": {"members": ["ar15", "m16a3", "m4a1", "m4a1-desert", "car15", "hk416", "lr300", "sgi5k",
                        "gilboa-snake", "ares-shrike", "aac", "sr47", "ar57", "hk417", "rsaas", "m110"]},
}

# root coordinates, y up. rail: where a scope's mount sits; muzzle: start of the muzzle device,
# bore height (None = measured in the body picture); grip / tac: under the handguard / the barrel
ANCHORS = {
    "ak74":  {"rail": (13, 20), "muzzle": (92, 15), "grip": (45, 12), "tac": (64, 14.5)},
    "aksu":  {"rail": (13, 18), "muzzle": (57, 13.34), "grip": (44, 11.5), "tac": (50, 12)},
    "ak12":  {"rail": (13, 21), "muzzle": (96, None), "grip": (43, 12), "tac": (66, 14.5)},
    "ak15":  {"rail": (13, 18.2), "muzzle": (88, None), "grip": (49.5, 10.2), "tac": (66, 12)},
    "rpk74": {"rail": (13, 18), "muzzle": (107, None), "grip": (45, 9), "tac": (64, 10)},
    "rpk16": {"rail": (13, 18), "muzzle": (101, None), "grip": (45, 10), "tac": (78, 14)},
    "ak74m": {"rail": (14.5, 18.8), "muzzle": (95, None), "grip": (45.5, 10.3), "tac": (65.5, 13.3)},
    "akm74-2": {"rail": (13, 18.5), "muzzle": (85.76, 13.46), "grip": (45, 10.5), "tac": (64, 13),
                "gl": (53.41, 8.54)},
    "ak105": {"rail": (13, 18), "muzzle": (72.5, 13), "grip": (45.5, 7), "tac": (62, 11)},
    "ak105bullpup": {"rail": (8, 17.5), "muzzle": (40, 11.7), "grip": (28.5, 9.3), "tac": (38, 12)},
    "akm":   {"rail": (13, 20), "muzzle": (85, 13.8), "grip": (45, 12), "tac": (62, 14), "gl": (54, 8.88)},
    "a762":  {"rail": (13, 18.5), "muzzle": (89, None), "grip": (45, 10), "tac": (66, 12)},
    "tul1":  {"rail": (13, 17.1), "muzzle": (105, 11.7), "grip": (45, 8), "tac": (64, 9)},
}
# the GP-30 hangs this far from the grip anchor (AK-74), unless a model has its own "gl" point
GL_FROM_GRIP = complex(48.77 - 45, 9.65 - 12)
ANCHORS["ak74"]["gl"] = (48.77, 9.65)
# a model's own slot for a kind (the AK-74M's grip is its "holder" slot), and slot defaults changed
# so that shared attachments don't double up (the AK-74M's magnifier would hang behind any scope)
AR_HOLDER = ["ar15", "m4a1", "m4a1-desert", "hk416", "lr300", "sr47", "ar57", "gilboa-snake",
             "ares-shrike", "hk417", "rsaas", "sgi5k"]
SLOT_ALIAS = {"ak74m": {"grip": "holder"}, "ar57": {"tactical": "light"}}
for _m in AR_HOLDER:
    SLOT_ALIAS.setdefault(_m, {})["grip"] = "holder"      # their grips live in "holder" (default or empty)
for _m in ("ar15", "aac", "hk417", "rsaas"):
    SLOT_ALIAS.setdefault(_m, {})["scope"] = "optic"      # the "scope" slot shows their top rail: keep it
# kinds a model can't take (AR-57: a P90 magazine on top; M16A2: the M203 is part of its body)
NO_KIND = {"ar57": {"clip"}, "m16": {"gl"}}
DEFAULTS = {"ak74m": {"cap": None, "holder": None}}

# upgrade row key -> (slot in the skeletons, anchor)
KINDS = {
    "scope": ("scope", "rail"), "silencer": ("silencer", "muzzle"), "grip": ("grip", "grip"),
    "on": ("grip", "grip"), "holder": ("grip", "grip"), "tactical": ("tactical", "tac"),
    "clip": ("clip", "clip"), "gl": ("gl", "gl"), "laser": ("tactical", "tac"),
}
MODEL_ONLY = {"upgrade-ak74-butt-old", "upgrade-aksu-holder", "upgrade-rpk16-holder", "upgrade-ak105-holder",
              "upgrade-m16a3-holder"}
ONE_OF = {"gl"}     # one launcher per family is enough (five models had their own M203)
# where a new slot goes: drawn behind the body (gl) or over it
BEHIND = {"gl"}


def as_list(v):
    return v if isinstance(v, list) else [v]


def model_path(c, weapon_id):
    w = c[weapon_id]
    anim = next(comp["animation"] for comp in w["components"] if "animation" in comp)
    return "content/" + c[anim]["animation"].split(":", 1)[1]


SKIN_OF = {}   # id(skeleton) -> the name of the weapon's default skin in it (M4A1 Desert: "weapon-desert")


def note_skin(c, model, skel):
    w = c[c["sl-pri-" + model]["instrument"]["id"]]
    SKIN_OF[id(skel)] = c.get(w.get("defaultSkin"), {}).get("data", "weapon-default")
    return skel


def default_atts(skel):
    name = SKIN_OF.get(id(skel), "weapon-default")
    return next(s for s in skel["skins"] if s["name"] == name)["attachments"]


def px(skel):
    """root units per texture pixel (1 for most weapons; the M110 is drawn at 0.35)"""
    return next(iter(default_atts(skel)["body"].values())).get("scaleX", 1)


AUTO = {}


def auto_anchors(skel):
    """anchors measured in the body picture(s): rail = top of the body above the magazine, muzzle =
    right end minus a muzzle device, at the bore height; grip / tac = bottom of the handguard a third /
    0.6 of the way from the magazine to the muzzle"""
    from PIL import Image
    if id(skel) in AUTO:
        return AUTO[id(skel)]
    atts = default_atts(skel)
    shown = {sl["name"]: sl.get("attachment") for sl in skel["slots"]}
    pixels = []                                # opaque pixels of the body (and a separate barrel) in root units
    for slot in ("body", "barrel"):
        a = atts.get(slot, {}).get(shown.get(slot))
        if not a:
            continue
        im = Image.open(os.path.join(gunsmith.GAME, a.get("name", shown[slot]) + ".png")).convert("RGBA")
        k = a.get("scaleX", 1)
        x0, y0 = a.get("x", 0) - a["width"] * k / 2, a.get("y", 0) + a["height"] * k / 2
        al = im.split()[3].load()
        for i in range(im.width):
            for j in range(im.height):
                if al[i, j] > 160:
                    pixels.append((x0 + (i + .5) * k, y0 - (j + .5) * k))
    k = px(skel)
    clip = next(iter(a for n, a in atts["clip"].items() if n == shown.get("clip"))) if "clip" in atts and shown.get("clip") \
        else None
    cx = clip.get("x", 0) if clip else min(p[0] for p in pixels) + 0.4 * (max(p[0] for p in pixels) - min(p[0] for p in pixels))

    def column(x):
        return [p[1] for p in pixels if abs(p[0] - x) <= k * 1.5]

    right = max(p[0] for p in pixels)
    mx = right - 6 * k
    near = sorted({round(p[1] / k) for p in pixels if mx - 4 * k <= p[0] <= mx})
    runs, cur = [], []
    for r in near:
        if cur and r != cur[-1] + 1:
            runs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        runs.append(cur)
    thin = [r for r in runs if len(r) <= 4] or runs
    bore = sum(thin[0]) / len(thin[0]) * k if thin else 0
    rx = cx - 2 * k
    res = {"rail": (rx, max(column(rx)) + k / 2), "muzzle": (mx, bore)}
    for kind, f, extra in (("grip", 0.33, 0), ("tac", 0.6, k)):
        x = cx + f * (mx - cx)
        res[kind] = (x, min(column(x)) - k / 2 + extra)
    AUTO[id(skel)] = res
    return res


def anchor_point(model, skel, kind):
    atts = default_atts(skel)
    if kind == "clip":
        ref = next(iter(a for n, a in atts["clip"].items() if n in ("clip-default", "default")))
        return complex(ref.get("x", 0) - ref["width"] / 2, ref.get("y", 0) + ref["height"] / 2)
    table = ANCHORS[model] if model in ANCHORS else auto_anchors(skel)
    if kind == "gl" and "gl" not in table:
        return anchor_point(model, skel, "grip") + GL_FROM_GRIP * px(skel)
    x, y = table[kind]
    if y is None:
        y = gunsmith.barrel_y(atts, x)
    return complex(x, y)


def snap(att, skel):
    """the part's corner on the same pixel grid as the body (no half-pixel blur)"""
    body = next(iter(default_atts(skel)["body"].values()))
    k = body.get("scaleX", 1)
    gx = (body.get("x", 0) - body["width"] * k / 2) % k
    gy = (body.get("y", 0) - body["height"] * k / 2) % k
    w, h = att["width"] * k, att["height"] * k
    att["x"] = round(round((att["x"] - w / 2 - gx) / k) * k + gx + w / 2, 4)
    att["y"] = round(round((att["y"] - h / 2 - gy) / k) * k + gy + h / 2, 4)


def ensure_slot(skel, slot):
    names = [s["name"] for s in skel["slots"]]
    if slot in names:
        return
    if slot in BEHIND:
        skel["slots"].insert(0, {"name": slot, "bone": "root"})
    else:
        skel["slots"].insert(names.index("body") + 1, {"name": slot, "bone": "root"})


def family(c, skeletons, base, members, borrow=()):
    models = [base] + members
    items = {m: c["sl-pri-" + m] for m in models + list(borrow)}
    for m, slots in DEFAULTS.items():
        if m in models:
            for sl in skeletons[m]["slots"]:
                if sl["name"] in slots:
                    if slots[sl["name"]] is None:
                        sl.pop("attachment", None)
                    else:
                        sl["attachment"] = slots[sl["name"]]
    weapons = {m: items[m]["instrument"]["id"] for m in models}
    base_item = items[base]
    rows = base_item["instrument"].setdefault("upgrades", {})

    # 1. shared upgrades, in menu order: the base weapon's first, then each model's
    shared = []                                    # (upgrade id, source model, original slot, original name, kind)
    for m in models + list(borrow):
        for key, ups in items[m]["instrument"].get("upgrades", {}).items():
            if key not in KINDS:
                continue
            for u in as_list(ups):
                if u in MODEL_ONLY or any(s[0] == u for s in shared):
                    continue
                key_u = "gl" if any(comp["class"].endswith("SecondaryWeaponSlotComponent")
                                    for comp in c[u]["components"]) else key
                if key_u in ONE_OF and any(KINDS[k][0] == KINDS[key_u][0] for *_, k in shared):
                    continue
                rep = next(comp for comp in c[u]["components"] if comp["class"].endswith("ReplaceSlotComponent"))
                # the entry that is in this model's skeleton (a shared one lists every slot it lives in)
                # (the AKMS GP-30 also swaps the stock buffer: the entry of the kind's slot is the part)
                here = [(sl, n) for sl, n in rep["replace"].items() if n in default_atts(skeletons[m]).get(sl, {})]
                slot, name = next((e for e in here if e[0] in (KINDS[key_u][0], key) or e[1].startswith("cv-")), here[0])
                img = default_atts(skeletons[m])[slot][name].get("name", name)
                if any(KINDS[k][0] == KINDS[key_u][0] and default_atts(skeletons[sm])[ss][sn].get("name", sn) == img
                       for _, sm, ss, sn, k in shared):
                    continue                       # the same picture is already offered (e.g. three Cobras)
                shared.append((u, m, slot, name, key_u))

    # 2. attachments in every skeleton of the family, the upgrades point at them
    for u, src, slot, name, key in shared:
        new_slot, anchor = KINDS[key]
        att_name = "cv-" + u
        original = default_atts(skeletons[src])[slot][name]
        a_src = anchor_point(src, skeletons[src], anchor)
        slots_used = set()
        for m in models:
            skel = skeletons[m]
            if new_slot in NO_KIND.get(m, ()):
                continue
            slot_m = SLOT_ALIAS.get(m, {}).get(new_slot, new_slot)
            slots_used.add(slot_m)
            ensure_slot(skel, slot_m)
            att = dict(original)
            att.setdefault("name", name)
            if m != src:
                # same offset from the anchor in texture pixels, at the target's pixel scale
                ks, kd = px(skeletons[src]), px(skel)
                rel = (complex(original.get("x", 0), original.get("y", 0)) - a_src) / ks
                pos = anchor_point(m, skel, anchor) + rel * kd
                att["x"], att["y"] = pos.real, pos.imag
                scale = original.get("scaleX", 1) / ks * kd
                if abs(scale - 1) > 1e-6:
                    att["scaleX"] = att["scaleY"] = round(scale, 4)
                else:
                    att.pop("scaleX", None)
                    att.pop("scaleY", None)
                snap(att, skel)
            for s in skel["skins"]:
                s.setdefault("attachments", {}).setdefault(slot_m, {})[att_name] = dict(att)
        rep = next(comp for comp in c[u]["components"] if comp["class"].endswith("ReplaceSlotComponent"))
        # every slot this attachment lives in (an upgrade shared by two families keeps both sets)
        kept = {k: v for k, v in rep["replace"].items() if v == att_name or (k != slot and not v.startswith("cv-"))}
        kept.update({sl: att_name for sl in slots_used})
        rep["replace"] = kept

    # 3. the base weapon's menu: every shared upgrade under the row of its slot
    for row in [k for k in rows if k in KINDS]:
        del rows[row]
    for u, src, slot, name, key in shared:
        row = KINDS[key][0]
        rows.setdefault(row, [])
        rows[row] = as_list(rows[row]) + [u]

    # 4. conversions; the models' own shop items are hidden
    base_ammo = next((i for i in base_item.get("items", []) if i["id"].startswith("bullet-")), None)
    conversions = []
    for m in members:
        cid = "conversion-%s-%s" % (base, m)
        body = next(iter(default_atts(skeletons[m])["body"].values()))
        up = {"class": "content.upgrades.Upgrade", "access": "byDefault", "name": items[m]["name"],
              "description": DESC_KEY,
              "properties": {}, "conversion": weapons[m], "convertsFrom": "sl-pri-" + m,
              "conversionBase": "sl-pri-" + base,
              "components": [{"class": "content.components.IconComponent", "tag": "client",
                              "big-icon": body.get("name", "")}]}
        ammo = next((i for i in items[m].get("items", []) if i["id"].startswith("bullet-")), None)
        if ammo and ammo != base_ammo:
            up["ammo"] = {"id": ammo["id"], "amount": ammo["amount"]}
        c[cid] = up
        conversions.append(cid)
        for key in ("sl-pri-" + m, "sl-pri-%s-slot2" % m):
            if key in c:
                c[key]["enabled"] = False
    rows["conversion"] = conversions
    return shared


def apply(c, skeletons):
    """c: content dict; skeletons: model -> skeleton dict (client) or None (server: content only)"""
    if skeletons is None:
        # the server has no skeletons, but needs the same content: run on throw-away copies
        skeletons = {m: note_skin(c, m, json.loads(t)) for m, t in SERVER_SKELETONS.items()}
    report = {}
    for base, f in FAMILIES.items():
        report[base] = family(c, skeletons, base, f["members"], f.get("borrow", ()))
    return report


SERVER_SKELETONS = {}
DESC_KEY = "MENU_CONVERSION_DESC"
DESC = {"RU": "Переделка базового оружия в другую модель семейства. Все обвесы семейства подходят.",
        "EN": "Converts the base weapon into another model of its family. All family attachments fit."}


def build(source, destination):
    with ZipFile(source) as src:
        names = src.namelist()
        data = json.loads(src.read("content.json"))
        c = data["content"]
        changes = {}
        models = {m for base, f in FAMILIES.items() for m in [base] + f["members"]}
        paths = {m: model_path(c, c["sl-pri-" + m]["instrument"]["id"]) for m in models}
        if all(p in names for p in paths.values()):
            skeletons = {m: note_skin(c, m, json.loads(src.read(p))) for m, p in paths.items()}
            apply(c, skeletons)
            for m, p in paths.items():
                changes[p] = encode(skeletons[m])
        else:
            # server package: skeletons come from the source tree (same content changes)
            root = Path(__file__).resolve().parents[1] / "data" / "packages" / "base" / "contents"
            for m, p in paths.items():
                SERVER_SKELETONS[m] = (root / p).read_text(encoding="utf-8")
            apply(c, None)
        changes["content.json"] = encode(data)
        if "data/texts.json" in names:
            texts = json.loads(src.read("data/texts.json"))
            texts["data"][DESC_KEY] = dict(DESC)
            changes["data/texts.json"] = encode(texts)
        if "__H" in names:
            hashes = json.loads(src.read("__H"))
            hashes.update({name: zlib.crc32(d) for name, d in changes.items()})
            changes["__H"] = encode(hashes)
        with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=3) as out:
            for entry in src.infolist():
                out.writestr(entry, changes[entry.filename] if entry.filename in changes else src.read(entry))


def preview(out_dir):
    """one sheet per kind: rows = models, columns = the shared upgrades of that kind"""
    from PIL import Image, ImageDraw
    root = Path(__file__).resolve().parents[1]
    z = ZipFile(root / "build/packages-client/8-g11.zip")      # the package before this stage
    c = json.loads(z.read("content.json"))["content"]
    allm = {m for base, f in FAMILIES.items() for m in [base] + f["members"]}
    skel = {m: note_skin(c, m, json.loads(z.read(model_path(c, c["sl-pri-" + m]["instrument"]["id"])))) for m in allm}
    report = apply(c, skel)
    game = root / "data/packages/base/textures/GAME"
    VIEW = {"scope": (-12, 62, 4, 36), "silencer": (40, 150, -2, 28), "clip": (0, 50, -28, 16)}
    os.makedirs(out_dir, exist_ok=True)

    def draw(m, sel, view):
        X0, X1, Y0, Y1 = view
        S = 4
        d = skel[m]
        atts = default_atts(d)
        can = Image.new("RGBA", ((X1 - X0) * S, (Y1 - Y0) * S), (60, 64, 60, 255))
        for s in d["slots"]:
            a = sel.get(s["name"], s.get("attachment"))
            at = atts.get(s["name"], {}).get(a) if a else None
            if not at:
                continue
            p = game / (at.get("name", a) + ".png")
            if not p.exists():
                continue
            im = Image.open(p).convert("RGBA")
            k = at.get("scaleX", 1)
            im = im.resize((max(1, round(im.width * S * k)), max(1, round(im.height * S * k))), Image.NEAREST)
            x = at.get("x", 0) - at["width"] * k / 2
            y = at.get("y", 0) + at["height"] * k / 2
            can.alpha_composite(im, (int(round((x - X0) * S)), int(round((Y1 - y) * S))))
        return can

    for base, shared in report.items():
        models = [base] + FAMILIES[base]["members"]
        by_slot = {}
        for u, src, slot, name, key in shared:
            by_slot.setdefault(KINDS[key][0], []).append(u)
        for slot, ups in by_slot.items():
            view = VIEW.get(slot, (10, 110, -6, 26))
            tiles = [[draw(m, {SLOT_ALIAS.get(m, {}).get(slot, slot): "cv-" + u}, view) for u in ups] for m in models]
            w, h = tiles[0][0].size
            sheet = Image.new("RGBA", (w * len(ups), h * len(models)))
            dr = ImageDraw.Draw(sheet)
            for r, row in enumerate(tiles):
                for col, t in enumerate(row):
                    sheet.paste(t, (col * w, r * h))
                    dr.text((col * w + 3, r * h + 3), "%s / %s" % (models[r], ups[col][-18:]), fill="yellow")
            sheet.save(os.path.join(out_dir, "conv-%s-%s.png" % (base, slot)))
            print(base, slot, len(ups))


if __name__ == "__main__":
    if sys.argv[1] == "--preview":
        preview(sys.argv[2])
    else:
        build(Path(sys.argv[1]), Path(sys.argv[2]))
