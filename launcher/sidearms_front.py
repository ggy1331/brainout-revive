"""Machine pistols with the magazine in front of the grip (and the P50 with its magazine on top):
the Colt 1911 approach adapted to their loading. Called from sidearms.build.

The magazine is the weapon's own clip slot (with its default / extended attachments), moved onto
pair-mag-travel and drawn behind the body. The part that sits inside the magazine well is not in
the original art, so `tools/weapon-art/front_mag_sprites.py` makes fm-<sprite> copies extended
upward along the magazine axis by DEPTH rows; they replace the clip attachments here.

  hold: a fist on the pistol grip (grip bone shift), the support fist on the magazine /
    foregrip / magazine well (SUPPORT); low stance at the chest, high stance (RMB) arms out
  reload: support fist to the magazine, pulled out along its axis, into the pouch, a fresh one
    from the pouch, pushed in; the hand ends on the cocking handle (RACK)
  fetch (only after an empty magazine): the cocking handle is pulled back and let go
  P50: the top cover is flipped open at its rear latch first and pushed shut after the
    magazine is in (its own open / close animations)
Timings come from the weapon's reload / fetch sounds (SOUNDS).
"""
from math import sin, pi, cos, radians

from pair_refinement import ARMS, direction
from pair_refinement import offset
from colt1911 import (Author, world_scale, lerp, ease, bump, eye_line, straight,
                      GROUND, GRAVITY, RACK_PITCH)

# sprite px of the default body sprite (row 0 = top):
#   grip    centre of the pistol grip (the shooting fist closes there)
#   axis    magazine axis in gun space, degrees, from the bottom of the magazine into the gun
#   depth   rows the magazine continues inside the well (drawn by front_mag_sprites.py)
#   support (point, fist angle relative to the gun) of the support hand while holding
#   rack    (cocking handle, how far it goes back in px)
#   sight   row of the sight line (top of the rear sight / carry handle)
HANDGUARD = -52            # fist angle of the rifle support hand (actor hold-weapon-2hands)
FRONT = {
    "scorpion": dict(grip=(5, 22), axis=107, depth=3, sight=0, support=((26.5, 19.5), 112), rack=((24, 3), 6)),
    "tec9": dict(grip=(6, 15), axis=90, depth=7, sight=1, support=((20.5, 18.5), 112), rack=((23, 4), 6)),
    "mp5k": dict(grip=(7, 25), axis=105, depth=6, sight=2, support=((42.5, 21), 112), rack=((40, 6), 6)),   # foregrip
    "mat49": dict(grip=(6, 17), axis=90, depth=12, sight=0, support=((27, 21), 112), rack=((30, 5), 7)),
    # an M16 derivative: the support hand under the handguard like on a rifle
    "k23p": dict(grip=(28, 25), axis=92, depth=5, sight=1, support=((60, 13.5), HANDGUARD), rack=((32, 6), 6)),
    # top magazine: pulled up out of its channel once the cover is open
    "p50": dict(grip=(13, 20), axis=-60, depth=0, sight=0, support=((40, 13.5), HANDGUARD), rack=((9, 7), 5),
                cover=dict(latch=(6, 3), hinge=(58.15, 8.68), length=54)),
}
# reload sound: magazine out, magazine seated; fetch sound: handle back, handle forward (seconds)
SOUNDS = {
    "mp5-reload-snd": (.14, .92), "tec9-reload-snd": (.36, 1.37), "p50-reload": (.70, 1.41),
    "mp5-fetch-snd": (.19, .29), "tec9-fetch-snd": (.14, .25), "ak74-fetch-snd": (.21, .31),
}
P50_OPEN, P50_CLOSE = .36, 1.76      # cover latch and cover shut in p50-reload
COVER_ANGLE = 12.0                   # P50: the top cover lifts at the rear (was a 90 degree flip)
POUCH, POUCH_ANGLE = complex(-8.6, -3.4), 175.0
# hands space (x up the chest, -y forward). These are carried like the original two-handed
# guns (actor hold-weapon-2hands / aim-weapon-2hands), lower than the pistols:
# low stance at the belly, the high stance where a pistol's low stance is
HOLD = complex(-4.8, -8.3), -89.5
AIM = complex(-1.6, -9.9), -88.0
WORK = complex(-3.6, -7.9), -61.5


def clip_slot(model):
    return next(s for s in model["slots"] if s["name"] in ("clip", "magazine"))


def body_attachment(model, comp_skin):
    body = next(s for s in model["slots"] if s["name"] == "body")
    skin = next((s for s in model["skins"] if s["name"] == comp_skin), model["skins"][0])
    return skin["attachments"]["body"][body["attachment"]]


class Gun:
    """Sprite px of the body sprite -> root space after the grip shift."""

    def __init__(self, att, grip):
        self.sx = att.get("scaleX", 1)
        self.sy = att.get("scaleY", 1)
        self.left = att["x"] - att["width"] * self.sx / 2
        self.top = att["y"] + att["height"] * self.sy / 2
        self.grip = self.plain(grip)

    def plain(self, xy):
        return complex(self.left + (xy[0] + .5) * self.sx, self.top - (xy[1] + .5) * self.sy)

    def at(self, xy):
        return self.plain(xy) - self.grip


def extended(att, depth, axis, name):
    """The clip attachment of an fm- sprite: `depth` rows added on top, shifted along the axis."""
    if not depth:
        return dict(att)
    lean = cos(radians(axis)) / sin(radians(axis))       # columns per row going up
    shift = round(depth * lean)
    a = dict(att, name=name, path=name)
    a["height"] = att["height"] + depth
    a["width"] = att["width"] + abs(shift)
    a["y"] = round(att["y"] + depth / 2, 3)
    a["x"] = round(att["x"] + shift / 2, 3)
    return a


def model_changes(model, wid, f, comp_skin):
    root = model["bones"][0]["name"]
    gun = Gun(body_attachment(model, comp_skin), f["grip"])
    if not any(b["name"] == "grip" for b in model["bones"]):
        for b in model["bones"][1:]:
            if b.get("parent") == root:
                b["parent"] = "grip"
        model["bones"].insert(1, {"name": "grip", "parent": root,
                                  "x": round(-gun.grip.real, 3), "y": round(-gun.grip.imag, 3)})
        for s in model["slots"]:
            if s["bone"] == root:
                s["bone"] = "grip"
    if not any(b["name"] == "pair-mag-travel" for b in model["bones"]):
        model["bones"].append({"name": "pair-mag-travel", "parent": "grip"})
    clip = clip_slot(model)
    clip["bone"] = "pair-mag-travel"
    model["slots"].remove(clip)
    model["slots"].insert(0, clip)                     # behind the body: the well hides its top
    for skin in model["skins"]:
        atts = skin.get("attachments", {}).get(clip["name"], {})
        for key, att in list(atts.items()):
            sprite = att.get("path", att.get("name", key))
            if f["depth"] and not sprite.startswith("fm-"):
                atts[key] = extended(att, f["depth"], f["axis"], "fm-" + sprite)
    if "cover" in f:
        anims = model.setdefault("animations", {})
        anims["open"] = {"bones": {"upper": {"rotate": [{}, {"time": .12, "value": -COVER_ANGLE}]}}}
        anims["close"] = {"bones": {"upper": {"rotate": [{"value": -COVER_ANGLE}, {"time": .1}]}}}
    return gun


def magazine_geometry(model, f, gun, comp_skin):
    """(grab point in root space after the shift, magazine attachment, its centre) of the default skin."""
    clip = clip_slot(model)
    skin = next((s for s in model["skins"] if s["name"] == comp_skin), model["skins"][0])
    att = skin["attachments"][clip["name"]][clip["attachment"]]
    centre = complex(att["x"], att["y"]) - gun.grip
    half = att["height"] / 2 - .5
    grab = centre + complex(0, -half if f["axis"] > 0 else half)
    return grab, att, centre


def add_hand_magazine(actor, setup, wid, f, att, centre, grab, gpx, name=None):
    """The magazine in the support fist: held at `grab`, the fist along the magazine axis."""
    if "sa-mag-hold" not in setup:
        actor["bones"].append({"name": "sa-mag-hold", "parent": "holder-secondary"})
        setup["sa-mag-hold"] = actor["bones"][-1]
    names = [s["name"] for s in actor["slots"]]
    if "sa-mag-hand" not in names:
        actor["slots"].insert(names.index("gpalm2") + 1, {"name": "sa-mag-hand", "bone": "sa-mag-hold"})
    k = gpx / world_scale(setup, ("hand2", "palm2", "holder-secondary"))
    pos = (centre - grab) * direction(-f["axis"]) * k
    sprite = att.get("path", att.get("name"))
    default = next(s for s in actor["skins"] if s["name"] == "default")
    default["attachments"].setdefault("sa-mag-hand", {})[name or "fm-" + wid] = {
        "name": sprite, "path": sprite, "x": round(pos.real, 3), "y": round(pos.imag, 3),
        "rotation": round(att.get("rotation", 0) - f["axis"], 2),
        "scaleX": round(k * att.get("scaleX", 1), 4), "scaleY": round(k * att.get("scaleY", 1), 4),
        "width": att["width"], "height": att["height"]}


def timings(item, sounds):
    rel, seat = SOUNDS[sounds["reload"]]
    back, fwd = SOUNDS[sounds["fetch"]]
    tail = (P50_CLOSE + .3) if sounds["reload"] == "p50-reload" else seat + .3
    D = round(max(item["primary"].get("reloadTime", 1), tail), 3)
    F = round(max(item["primary"].get("fetchTime", .4), fwd + .35), 3)
    return rel, seat, back, fwd, D, F


def reachable(au, arm, point, margin=.97):
    """The fist can get there: the arm neither over-stretched nor folded past its limit."""
    upper, palm, holder = [au.setup[n] for n in arm]
    origin = offset(upper) + offset(au.carry[arm[0]]["translate"][0])
    a, b = abs(offset(palm)), abs(offset(holder))
    d = abs((point - origin) / upper.get("scaleX", 1))
    return (a * a + b * b - 2 * a * b * .85) ** .5 <= d <= (a + b) * margin


def fit(au, pose, points):
    """Slide the gun along its barrel (as little as possible) until the support fist
    reaches every point it has to work at in this pose."""
    a, p = pose
    for i in range(201):
        k = (i + 1) // 2 * (-1 if i % 2 else 1) * .1
        b = a + direction(p) * k
        if reachable(au, ARMS[0], b, .995) and all(reachable(au, ARMS[1], au.on_gun(b, p, q)) for q in points):
            return b, p
    return a, p


class Path:
    """Keyed support-fist path: (time, where, fist angle, magazine fraction out).
    `where` is a gun point (complex, root space) or ("world", point)."""

    def __init__(self, keys):
        self.keys = keys

    def at(self, t, on, p):
        keys = self.keys
        i = max(j for j, k in enumerate(keys) if k[0] <= t)
        k0 = keys[i]
        k1 = keys[min(i + 1, len(keys) - 1)]
        f = ease(t, k0[0], k1[0]) if k1 is not k0 else 0

        def place(k):
            where = k[1]
            return where[1] if isinstance(where, tuple) else on(where)

        a, b = place(k0), place(k1)
        arc = complex(.6, 0) * sin(pi * f) if (isinstance(k0[1], tuple) or isinstance(k1[1], tuple)) else 0
        return lerp(a, b, f) + arc, lerp(k0[2](p), k1[2](p), f), lerp(k0[3], k1[3], f)


def solo_clips(au, wid, states, f, T, grab, sounds):
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    axis = f["axis"]
    sp, sa = f["support"]
    support = g.at(sp)
    rp, rlen = f["rack"]
    rack = g.at(rp)
    hold_at, hold_pitch = fit(au, f.get("hold", HOLD), [support])
    aim_at, aim_pitch = fit(au, eye_line(au, f.get("aim", AIM)[0], g.at((f["grip"][0], f["sight"]))), [support])
    # the reload / rack pose: the magazine, the cocking handle and its pulled-back end in reach
    work_at, work_pitch = fit(au, f.get("work", WORK), [grab, rack, rack - rlen * g.sx])
    f["poses"] = (hold_at, hold_pitch), (aim_at, aim_pitch), (work_at, work_pitch)
    travel = rlen * g.sx
    out = direction(axis + 180)
    W = "solo-weapon-%s-" % wid

    def two(a, p):
        return (a, p), (au.on_gun(a, p, support), p + sa)

    def still(a, p):
        return lambda t: (*two(a, p), {})

    def shot(a0, p0):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
            return (*two(a0 + complex(.35, .45) * k, p0 + 6 * k), {})
        return frame

    for state, fn, d in (("hold", still(hold_at, hold_pitch), .08), ("aim", still(aim_at, aim_pitch), .08),
                         ("hit", shot(hold_at, hold_pitch), .1), ("aimHit", shot(aim_at, aim_pitch), .1)):
        if states.get(state):
            au.clip(W + states[state], d, fn)

    mag_out = f["mag_out"]
    S = lambda p: p + sa                       # fist angles relative to the gun pitch
    M = lambda p: p + axis
    R = lambda p: p - 25
    P = lambda p: POUCH_ANGLE
    pulled = grab + out * mag_out
    cover = f.get("cover")
    reach = max(.1, min(.3, rel * .55))
    rel = max(rel, reach + .15)               # a quick release click: the pull still takes its time
    trip = max(.3, seat_t - rel - .14)
    t_pouch = rel + .01 + trip * .38
    t_fresh = t_pouch + trip * .14
    t_line = seat_t - .12
    keys = [(0, support, S, 0)]
    events = [(rel, "unloaded"), (seat_t, "loaded")]
    if cover:
        latch = g.at(cover["latch"])
        keys += [(P50_OPEN - .1, latch, R, 0), (P50_OPEN + .04, latch + complex(0, 1.5), R, 0)]
        reach = rel - .16
        keys += [(reach, grab, M, 0)]
        events.append((P50_OPEN, "open"))
    else:
        keys += [(reach, grab, M, 0)]
    keys += [(rel, pulled, M, 1), (t_pouch, ("world", POUCH), P, 1),
             (t_fresh, ("world", POUCH + complex(-.7, 0)), P, 1), (t_line, pulled, M, 1),
             (seat_t, grab, M, 0)]
    if cover:
        hinge = g.at(cover["hinge"])
        arm = cover["length"] * .7 * g.sx
        up = hinge + direction(180 - COVER_ANGLE) * arm             # the rear of the lifted cover
        shut = hinge - arm
        keys += [(P50_CLOSE - .12, up + complex(-1.5, 0), R, 0), (P50_CLOSE, up, R, 0),
                 (P50_CLOSE + .14, shut, R, 0), (D, rack, R, 0)]
        events.append((P50_CLOSE, "close"))
    else:
        over = rack + complex(3 * g.sx, 5 * g.sy)
        keys += [(seat_t + (D - seat_t) * .55, over, R, 0), (D, rack, R, 0)]
    path = Path(keys)

    def reload(t):
        k = ease(t, 0, min(.2, reach))
        a, p = lerp(hold_at, work_at, k), lerp(hold_pitch, work_pitch, k)
        on = lambda q: au.on_gun(a, p, q)
        s, ang, frac = path.at(t, on, p)
        return (a, p), (s, ang), {"pair-magazine-left": out * mag_out * frac}

    hand = f.get("hand", "fm-" + wid)
    if states.get("reload"):
        t_take = rel + .01
        au.clip(W + states["reload"], D, reload, sorted(events), {
            "pair-magazine-left": {"attachment": [
                {"name": "magazine"}, {"time": round(t_take, 4), "name": None},
                {"time": round(t_line, 4), "name": "magazine"}]},
            "sa-mag-hand": {"attachment": [
                {"name": None}, {"time": round(t_take, 4), "name": hand}, {"time": round(t_pouch, 4), "name": None},
                {"time": round(t_fresh - .02, 4), "name": hand}, {"time": round(t_line, 4), "name": None}]},
        })

    event = max(0, back - .06)

    def fetch(t):
        k = ease(t, fwd + .1, F)
        a, p = lerp(work_at, hold_at, k), lerp(work_pitch, hold_pitch, k)
        on = lambda q: au.on_gun(a, p, q)
        if t < fwd:
            s, ang = on(rack + complex(-travel, 0) * ease(t, event, back)), p - 25
        elif t < fwd + .1:
            j = ease(t, fwd, fwd + .1)
            s, ang = on(rack + complex(-travel - 3 * g.sx * j, 2 * g.sy * j)), p - 25 + 10 * j
        else:
            s = lerp(on(rack + complex(-travel - 3 * g.sx, 2 * g.sy)), on(support), k)
            ang = lerp(p - 15, p + sa, k)
        return (a, p), (s, ang), {}

    if states.get("fetch"):
        au.clip(W + states["fetch"], F, fetch)


def akimbo_clips(au, wid, f, T, grab):
    """Both arms out, barrels parallel. One-handed reload: the magazine drops to the ground,
    the gun is seated on a fresh magazine standing in the belt pouch (P50: cover opened on the
    belt first and shut after), then racked on the belt edge (only when it was empty)."""
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    axis = f["axis"]
    mag_out = f["mag_out"]
    out = direction(axis + 180)
    aim = (straight(au, ARMS[0], -.2), -89.0), (straight(au, ARMS[1], -.8), -89.0)
    belts = complex(-9.6, -3.6), complex(-9.4, -7.4)
    pouches = belts
    P = "sa-%s-" % wid
    au.clip(P + "akimbo", .08, lambda t: (aim[0], aim[1], {}))

    def hit(t):
        k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
        return tuple((a + complex(.3, .4) * k, p + 6 * k) for a, p in aim) + ({},)

    au.clip(P + "akimbo-hit", .1, hit)
    cover = f.get("cover")
    seat_pitch = -axis                      # the magazine axis points straight down into the pouch
    if cover:
        # P50: a top magazine can't go onto a belt pouch without pointing the muzzle at yourself;
        # the gun, muzzle up-forward, is pushed back onto a magazine standing in a chest pouch
        pouches = complex(-3.4, -4.4), complex(-3.2, -7.0)
        seat_pitch = -90 - axis
    rel = max(rel, .25)
    t_down = rel + .1
    t_line = max(t_down + .15, seat_t - .12)
    t_open = max(.05, rel - .2)
    t_shut = min(D - .2, seat_t + .15)
    event = max(0, back - .06)
    markers = ("pair-magazine-left", "pair-magazine-right")
    for arm in (0, 1):
        own, other = aim[arm], aim[1 - arm]
        pouch_base = pouches[arm]
        marker = markers[arm]
        above = pouch_base - direction(seat_pitch) * (grab + out * mag_out) * au.gpx
        rack_at = belts[arm] + complex(3.2, -1.0)

        def gun(t, own=own, above=above, pouch_base=pouch_base, rack_at=rack_at):
            tilt = ease(t, 0, max(.06, rel - .04)) * (1 - ease(t, t_down, t_line))
            start = own[0] + complex(.4, .6) * tilt, own[1] + 35 * tilt
            if t < t_down:
                return start
            if t < t_line:
                k = ease(t, t_down, t_line)
                return lerp(start[0], above, k), lerp(start[1], seat_pitch, k)
            if t < seat_t:
                k = ease(t, t_line, seat_t)
                return pouch_base - direction(seat_pitch) * (grab + out * mag_out * (1 - k)) * au.gpx, seat_pitch
            k = ease(t, seat_t, D)
            rest = pouch_base - direction(seat_pitch) * grab * au.gpx
            return lerp(rest, rack_at, k), lerp(seat_pitch, RACK_PITCH, k)

        a0, p0 = gun(rel)
        drop_at = au.on_gun(a0, p0, grab + out * mag_out)
        landed = rel + ((max(0, drop_at.real - GROUND)) * 2 / GRAVITY) ** .5

        def frame(t, arm=arm, gun=gun, other=other, marker=marker, drop_at=drop_at, landed=landed):
            a, p = gun(t)
            if t < rel:
                mag = out * mag_out * ease(t, max(0, rel - .1), rel)
            elif t < landed:
                dt = t - rel
                world = drop_at - .5 * GRAVITY * dt * dt
                mag = (world - a) / (direction(p) * au.gpx) - grab
            elif t < t_line:
                mag = out * mag_out
            elif t < seat_t:
                mag = out * mag_out * (1 - ease(t, t_line, seat_t))
            else:
                mag = 0j
            lift = ease(t, 0, .2)
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {marker: mag}

        prefix = "" if arm == 0 else "offhand/"
        side = "left" if arm == 0 else "right"
        events = [(rel, prefix + "unloaded"), (seat_t, prefix + "loaded")]
        if cover:
            events += [(t_open, prefix + "open"), (t_shut, prefix + "close")]
        slots = {marker: {"attachment": [{"name": "magazine"}, {"time": round(landed, 4), "name": None},
                                         {"time": round(t_line, 4), "name": "magazine"}]}}
        au.clip("pair-%s-%sreload" % (side, P), D, frame, sorted(events), slots, markers=markers)

        def rack(t, own=own, other=other, rack_at=rack_at, arm=arm):
            press = complex(-.7, 0) * ease(t, event, back) * (1 - ease(t, fwd, fwd + .06))
            k = ease(t, fwd + .06, F)
            a, p = lerp(rack_at, own[0], k) + press, lerp(RACK_PITCH, own[1], k)
            lift = 1 - k
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {}

        au.clip("pair-%s-%srack" % (side, P), F, rack, markers=markers)


def pair_changes(pair, wid, T):
    rel, seat, back, fwd, D, F = T
    content_changes(pair, T)
    for comp in pair["components"]:
        if comp.get("class", "").endswith("SecondaryWeaponSlotComponent"):
            comp["properties"]["reloadTime"] = D
            comp["properties"]["fetchTime"] = F
    states = next(c for c in pair["components"] if "states" in c and "animation" in c)["states"]
    P = "sa-%s-" % wid
    states.update(hold=P + "akimbo", aim=P + "akimbo", hit=P + "akimbo-hit", aimHit=P + "akimbo-hit",
                  reload=P + "reload", fetch=P + "rack")


def content_changes(item, T):
    rel, seat, back, fwd, D, F = T
    item["primary"]["reloadTime"] = D
    item["primary"]["fetchTime"] = F
    for comp in item["components"]:
        if comp.get("class", "").endswith("InstrumentActionsComponent"):
            # the magazine stays in the gun and travels with pair-mag-travel instead of blinking
            comp["actions"] = [a for a in comp.get("actions", []) if a.get("type") != "updateSlot"]


def far_gun_behind(actor):
    """Akimbo: the gun in the far hand (slot-secondary) is drawn behind the body, under the far
    glove like the near gun is under the near one."""
    slots = actor["slots"]
    moving = [s for s in slots if s["name"] in ("pair-magazine-right", "slot-secondary")]
    if not moving or not any(s["name"] == "ghand2" for s in slots):
        return
    for s in moving:
        slots.remove(s)
    i = next(i for i, s in enumerate(slots) if s["name"] == "ghand2")
    slots[i:i] = moving


def build(src_names, read, content, actor, setup, changes, encode, animation_path):
    import json
    far_gun_behind(actor)
    for wid, f in FRONT.items():
        item = content.get("weapon-" + wid)
        if item is None:
            continue
        comp, path = animation_path(content, item)
        if path not in src_names:
            continue
        fx = next(c for c in item["components"] if c.get("class", "").endswith("InstrumentEffectsComponent"))
        T = timings(item, fx)
        model = json.loads(read(path))
        skin = comp.get("skin", "weapon-default")
        gun = model_changes(model, wid, f, skin)
        grab, att, centre = magazine_geometry(model, f, gun, skin)
        f = dict(f, mag_out=att["height"] * att.get("scaleY", 1) + 1)
        changes[path] = encode(model)
        gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
        add_hand_magazine(actor, setup, wid, f, att, centre, grab, gpx)
        au = Author(actor, gun, gpx)
        solo_clips(au, wid, dict(comp["states"]), f, T, grab, fx)
        content_changes(item, T)
        pair = content.get("paired-weapon-" + wid)
        if pair:
            pcomp, ppath = animation_path(content, pair)
            if ppath in src_names and ppath != path:
                pmodel = json.loads(read(ppath))
                model_changes(pmodel, wid, f, pcomp.get("skin", "weapon-default"))
                changes[ppath] = encode(pmodel)
            akimbo_clips(au, wid, f, T, grab)
            pair_changes(pair, wid, T)
