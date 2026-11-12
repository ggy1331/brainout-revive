"""Colt M1911: separate slide and magazine, a proper grip, two-hand / akimbo holds, staged reloads.

    python colt1911.py source-base.zip result-base.zip      (run from the launcher folder)

Runs last in build_packages (after finalize_sidearms). Needs the sprites made by
tools/weapon-art/colt1911_sprites.py (packed by make_data into the GAME atlas).
Preview any clip with tools/weapon-art/spine_preview.py.

Weapon skeletons (weapon-colt.json and paired-weapon-colt.json):
  grip  new bone between the root and everything else: the pistol is shifted so that the fist
        (the holder bone) closes on the middle of the grip, not on its bottom edge
  body  -> colt1911-frame-<skin>  (no slide, no magazine base plate, a barrel under the slide)
  slide -> colt1911-slide-<skin>; animations "rack" and "cycle"
  clip  -> "mag" = colt1911-mag inside the grip (behind the frame) on pair-mag-travel, moved by the
           pair-magazine-left/right marker of the arm clips (WeaponAnimationComponentData)
Player rig (actor.json): the colt1911-mag-hand slot on the support fist (magazine carried in hand).

Single pistol (solo-weapon-colt-*): two-hand hold / aim, shots with the slide cycling,
reload = tilt, the magazine drops into the support hand, into the pouch, a fresh one out,
lined up and pushed in, the support hand racks the slide; fetch = the rack alone.
Akimbo (paired-weapon-colt): both arms forward, shots kick, each pistol reloads one-handed:
the magazine drops away, the pistol is seated onto a fresh magazine standing in the belt pouch,
the slide is racked on the belt edge; the other pistol is held out of the way.
"""
from copy import deepcopy
from math import sin, pi
import json
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gameplay_package import encode
from pair_refinement import ACTOR, ARMS, direction
from paired_reload_art import solve, smooth

WEAPON = "weapon-colt"
PAIRED = "paired-weapon-colt"
MODELS = ("content/animations/weapon-colt.json", "content/animations/paired-weapon-colt.json")
SKINS = {
    "weapon-default": "default", "weapon-harding": "harding", "weapon-judge": "judge",
    "weapon-pigeon": "pigeon", "weapon-pro": "pro", "weapon-rassel": "rassel",
}
RELOAD_TIME = 1.25         # s: staged reload with the pouch (the rack is the separate fetch)
PAIRED_RELOAD_TIME = 1.2   # s: one-handed reload of one akimbo pistol
FETCH_TIME = .6            # s: racking the slide (only after an empty magazine), timed to colt-fetch
MAG_AXIS = 75.0            # magazine axis in gun space, from the base plate up into the grip
MAG_OUT = 17.0             # gun px the magazine travels to leave the grip
SLIDE_TRAVEL = 5.0         # gun px
MAG_IMG = (6, 16)          # colt1911-mag.png
GRIP_CENTRE = complex(4.0, 4.5)   # middle of the grip, sprite space of the old layout
GRIP = -GRIP_CENTRE               # the shift that puts it on the fist


def lerp(a, b, f):
    return a + (b - a) * f


def ease(t, t0, t1):
    return smooth((t - t0) / max(1e-5, t1 - t0))


def bump(t, t0, t1):
    return sin(pi * min(1, max(0, (t - t0) / max(1e-5, t1 - t0))))


class Gun:
    """Points on the pistol, in its root space after the grip shift (gun px)."""

    def __init__(self, model):
        body = next(s for s in model["skins"] if s["name"] == "weapon-default")["attachments"]["body"]["default"]
        self.left = body["x"] - body["width"] / 2
        self.top = body["y"] + body["height"] / 2
        self.shift = GRIP if any(b["name"] == "grip" for b in model["bones"]) else 0j

    def px(self, col, row):
        return complex(self.left + col + .5, self.top - row - .5) + self.shift


def model_changes(model):
    bones = {b["name"]: b for b in model["bones"]}
    if "grip" not in bones:
        root = model["bones"][0]["name"]
        for b in model["bones"][1:]:
            if b.get("parent") == root:
                b["parent"] = "grip"
        model["bones"].insert(1, {"name": "grip", "parent": root, "x": GRIP.real, "y": GRIP.imag})
        for s in model["slots"]:
            if s["bone"] == root:
                s["bone"] = "grip"
    bones = {b["name"]: b for b in model["bones"]}
    if "slide" not in bones:
        model["bones"].append({"name": "slide", "parent": "grip"})
    slots = model["slots"]
    names = [s["name"] for s in slots]
    if "slide" not in names:
        slots.insert(names.index("body") + 1, {"name": "slide", "bone": "slide", "attachment": "default"})
    clip = next(s for s in slots if s["name"] == "clip")
    clip["attachment"] = "mag"
    slots.remove(clip)
    slots.insert(0, clip)          # the magazine sits behind the frame

    gun = Gun(model)
    base = gun.px(7.0, 24) - gun.shift      # in the shifted bone space the attachment is unshifted
    centre = base + direction(MAG_AXIS) * (MAG_IMG[1] / 2 - .5)
    for skin in model["skins"]:
        att = skin.setdefault("attachments", {})
        body = att.get("body", {}).get("default")
        name = SKINS.get(skin["name"])
        if body and name:
            body["name"] = body["path"] = "colt1911-frame-" + name
            att["slide"] = {"default": dict(body, name="colt1911-slide-" + name, path="colt1911-slide-" + name)}
        att.setdefault("clip", {})["mag"] = {
            "name": "colt1911-mag", "path": "colt1911-mag",
            "x": round(centre.real, 3), "y": round(centre.imag, 3), "rotation": MAG_AXIS - 90,
            "width": MAG_IMG[0], "height": MAG_IMG[1]}

    anims = model.setdefault("animations", {})
    # played from the colt-rack event (fetch t = .03): back in .08 s with the sound, held, slams
    # forward at fetch t = .19-.22, when colt-fetch.mp3 clacks
    pull = [{"time": round(.08 * i / 6, 4), "x": round(-SLIDE_TRAVEL * smooth(i / 6), 3)} for i in range(7)]
    anims["rack"] = {"bones": {"slide": {"translate": pull + [
        {"time": .16, "x": -SLIDE_TRAVEL}, {"time": .18, "x": -SLIDE_TRAVEL * .35}, {"time": .19}]}}}
    anims["cycle"] = {"bones": {"slide": {"translate": [
        {"time": 0}, {"time": .03, "x": -SLIDE_TRAVEL}, {"time": .075}]}}}
    return gun


def world_scale(setup, names):
    s = 1
    for n in names:
        s *= setup[n].get("scaleX", 1)
    return s


class Author:
    def __init__(self, actor, gun, gun_scale):
        self.actor = actor
        self.setup = {b["name"]: b for b in actor["bones"]}
        self.clips = actor["animations"]
        self.gun = gun
        self.gpx = gun_scale
        seed = self.clips["paired-extend"]["bones"]
        self.carry = {a[0]: {"translate": [{}]} for a in ARMS}
        hold = complex(-.22, -10.2)
        for arm, pos, rot in ((ARMS[0], hold, -89.5), (ARMS[1], hold + complex(-.5, -.8), -80)):
            neutral = {n: dict(seed[n]) for n in arm}
            neutral[arm[0]]["translate"] = [{}]
            solve(self.carry, self.setup, neutral, arm, 0, pos, rot)

    def on_gun(self, anchor, pitch, p):
        return anchor + direction(pitch) * p * self.gpx

    def clip(self, name, duration, frame, events=(), slots=None, markers=("pair-magazine-left",), fps=30):
        """frame(t) -> ((pos, angle) of the front fist, (pos, angle) of the back fist, {marker: offset})"""
        tracks = {a[0]: {"translate": [deepcopy(self.carry[a[0]]["translate"][0])]} for a in ARMS}
        keys = {m: [] for m in markers}
        times = sorted({0, duration, *(e[0] for e in events), *(i / fps for i in range(1, int(duration * fps) + 1))})
        for t in times:
            front, back, mags = frame(t)
            solve(tracks, self.setup, self.carry, ARMS[0], t, *front)
            solve(tracks, self.setup, self.carry, ARMS[1], t, *back)
            for m in markers:
                v = mags.get(m, 0j)
                keys[m].append({"time": round(t, 5), "x": round(v.real, 3), "y": round(v.imag, 3)})
        for m in markers:
            tracks[m] = {"translate": keys[m]}
            tracks[m + "-alignment"] = {"translate": [{}]}
        pose = {"bones": tracks, "slots": {"special": {"attachment": [{"name": None}]}}}
        if events:
            pose["events"] = [{"time": round(t, 5), "name": "instrument-action", "string": s} for t, s in events]
        if slots:
            pose["slots"].update(slots)
        self.clips[name] = pose


def add_hand_magazine(actor, setup, gpx):
    if "colt1911-mag-hold" not in setup:
        actor["bones"].append({"name": "colt1911-mag-hold", "parent": "holder-secondary"})
        setup["colt1911-mag-hold"] = actor["bones"][-1]
    names = [s["name"] for s in actor["slots"]]
    if "colt1911-mag-hand" not in names:
        actor["slots"].insert(names.index("gpalm2") + 1, {"name": "colt1911-mag-hand", "bone": "colt1911-mag-hold"})
    k = gpx / world_scale(setup, ("hand2", "palm2", "holder-secondary"))
    default = next(s for s in actor["skins"] if s["name"] == "default")
    default["attachments"]["colt1911-mag-hand"] = {"mag": {
        "name": "colt1911-mag", "path": "colt1911-mag", "x": round((MAG_IMG[1] / 2 - .5) * k, 3), "y": 0,
        "rotation": -90, "scaleX": round(k, 4), "scaleY": round(k, 4),
        "width": MAG_IMG[0], "height": MAG_IMG[1]}}
    for side in ("left", "right"):
        marker = default["attachments"].setdefault("pair-magazine-" + side, {})
        marker.setdefault("magazine", {"name": "colt1911-mag", "path": "colt1911-mag", "width": 1, "height": 1})


# Sound cues (colt-reload.mp3 / colt-fetch.mp3, both start with the action):
#   reload: magazine release click ~0.31 s, magazine seated ~0.93 s
#   fetch:  slide pulled back 0.04-0.11 s, slide slams forward ~0.21 s
MAG_RELEASE, MAG_SEATED = .31, .94
RACK_EVENT, RACK_BACK, RACK_RELEASE = .03, .11, .19
GROUND = -27.0           # hands space (x up the chest): about the feet
GRAVITY = 420.0          # hands units / s^2 for the dropped magazine
RACK_PITCH = -60.0       # akimbo: muzzle down-forward while racking on the belt
# hands space height of the eyes (goggles band at world y ~24.4; the hands bone sits at world
# y 18.29 with scale 1.6, x up the chest)
EYE = 3.82


def eye_line(au, at, sight):
    """High stance: the barrel level and the sights (a gun point) at eye height, `at` gives the reach."""
    return complex(EYE - sight.imag * au.gpx, at.imag), -90.0


def solo_clips(au):
    g = au.gun
    hold_at, hold_pitch = complex(-1.4, -7.4), -89.5          # low stance: compact, at the chest
    aim_at, aim_pitch = eye_line(au, complex(.5, -10.8), g.px(4.0, 0))   # high stance (RMB): arms out
    work_at, work_pitch = complex(-1.42, -7.6), -61.5         # reloading: closer, muzzle up
    grip_front = g.px(10.0, 17)      # support fist on the front of the grip, under the trigger guard
    base = g.px(7.0, 24)             # base plate centre when seated
    rear = g.px(7.0, 2)              # slide serrations
    over = g.px(10.0, -3)
    out = direction(MAG_AXIS + 180)
    W = "solo-%s-" % WEAPON

    def two_hands(a, p):
        return (a, p), (au.on_gun(a, p, grip_front), p + 70)

    def still(a, p):
        return lambda t: (*two_hands(a, p), {})

    au.clip(W + "hold-weapon-1hand", .08, still(hold_at, hold_pitch))
    au.clip(W + "aim-weapon-1hand", .08, still(aim_at, aim_pitch))

    def shot(a0, p0):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
            return (*two_hands(a0 + complex(.35, .45) * k, p0 + 7 * k), {})
        return frame

    au.clip(W + "shoot-hold-weapon-1hand", .1, shot(hold_at, hold_pitch), [(0, "colt-cycle")])
    au.clip(W + "shoot-aim-weapon-1hand", .1, shot(aim_at, aim_pitch), [(0, "colt-cycle")])

    pouch, pouch_angle = complex(-8.6, -3.4), 175.0

    def reload(t):
        # the pistol stays in the working position to the end: after an empty magazine the rack
        # (fetch) follows right away from here; otherwise the game blends back to the hold
        f = ease(t, 0, .2)
        a, p = lerp(hold_at, work_at, f), lerp(hold_pitch, work_pitch, f)
        on = lambda q: au.on_gun(a, p, q)
        seat = p + MAG_AXIS
        mag = 0j
        if t < .2:                                    # support hand under the grip
            f = ease(t, .02, .2)
            s, ang = lerp(on(grip_front), on(base + out * 2), f), lerp(p + 70, seat, f)
        elif t < .32:                                 # release: the magazine drops into the hand
            mag = out * MAG_OUT * ease(t, .2, MAG_RELEASE)
            s, ang = on(base + mag), seat
        elif t < .52:                                 # into the pouch
            f = ease(t, .32, .52)
            s = lerp(on(base + out * MAG_OUT), pouch, f) + complex(.8, 0) * sin(pi * f)
            ang, mag = lerp(seat, pouch_angle, f), out * MAG_OUT
        elif t < .6:                                  # a fresh one
            s, ang, mag = pouch + complex(-.7, 0) * bump(t, .52, .6), pouch_angle, out * MAG_OUT
        elif t < .82:                                 # lined up under the grip
            f = ease(t, .6, .82)
            s = lerp(pouch, on(base + out * MAG_OUT), f) + complex(.8, 0) * sin(pi * f)
            ang, mag = lerp(pouch_angle, seat, f), out * MAG_OUT
        elif t < MAG_SEATED:                          # pushed home
            mag = out * MAG_OUT * (1 - ease(t, .82, MAG_SEATED))
            s, ang = on(base + mag), seat
        else:                                         # over the top onto the slide serrations
            f = ease(t, MAG_SEATED, RELOAD_TIME)
            s = lerp(lerp(on(base), on(over), f), lerp(on(over), on(rear), f), f)
            ang = lerp(seat, p - 25, f)
        return (a, p), (s, ang), {"pair-magazine-left": mag}

    # the slide is racked only by the fetch below: the game plays it right after a reload only
    # when the chamber is empty (WeaponSlotComponent: chambered == 0 && rounds > 0 -> doFetch)
    au.clip(W + "reload-1hand", RELOAD_TIME, reload, [(MAG_RELEASE, "unloaded"), (MAG_SEATED, "loaded")], {
        "pair-magazine-left": {"attachment": [
            {"name": "magazine"}, {"time": .32, "name": None}, {"time": .82, "name": "magazine"}]},
        "colt1911-mag-hand": {"attachment": [
            {"name": None}, {"time": .32, "name": "mag"}, {"time": .52, "name": None},
            {"time": .58, "name": "mag"}, {"time": .82, "name": None}]},
    })

    def fetch(t):
        # starts where the reload ends (support hand on the serrations, pistol up)
        f = ease(t, .3, FETCH_TIME)
        a, p = lerp(work_at, hold_at, f), lerp(work_pitch, hold_pitch, f)
        on = lambda q: au.on_gun(a, p, q)
        if t < RACK_RELEASE:                          # pull back with the sound, hold it there
            s, ang = on(rear + complex(-SLIDE_TRAVEL, 0) * ease(t, RACK_EVENT, RACK_BACK)), p - 25
        elif t < .3:                                  # let go: the hand slides off backwards
            k = ease(t, RACK_RELEASE, .3)
            s, ang = on(rear + complex(-SLIDE_TRAVEL - 3 * k, 2 * k)), p - 25 + 10 * k
        else:                                         # back to the two-hand hold
            s = lerp(on(rear + complex(-SLIDE_TRAVEL - 3, 2)), on(grip_front), f)
            ang = lerp(p - 15, p + 70, f)
        return (a, p), (s, ang), {}

    au.clip(W + "reload-1hand-fetch", FETCH_TIME, fetch, [(RACK_EVENT, "colt-rack")])


def straight(au, arm, up):
    """A fist position with the arm almost straight, `up` along the chest (hands space)."""
    upper, palm, holder = [au.setup[n] for n in arm]
    shoulder = complex(upper.get("x", 0), upper.get("y", 0))
    reach = (abs(complex(palm.get("x", 0), palm.get("y", 0))) +
             abs(complex(holder.get("x", 0), holder.get("y", 0)))) * upper.get("scaleX", 1) * .97
    dx = up - shoulder.real
    forward = (max(0.0, reach * reach - dx * dx)) ** .5
    return complex(up, shoulder.imag - forward)


def akimbo_clips(au):
    g = au.gun
    base = g.px(7.0, 24)
    out = direction(MAG_AXIS + 180)
    # front arm (hand1) holds the left / main pistol, back arm (hand2) the right / off-hand one;
    # the barrels are always parallel (same pitch) and the fists at about the same height
    # no low stance for akimbo: hold and aim are the same arms-out pose
    aim = (straight(au, ARMS[0], -.2), -89.0), (straight(au, ARMS[1], -.8), -89.0)
    low = aim
    # magazine pouches on the front of the belt: the far arm is drawn behind the torso, so its
    # pouch sits forward of it, where the arm and the pistol stay visible
    pouches = complex(-9.6, -3.6), complex(-9.4, -7.4)

    def still(pose):
        return lambda t: (pose[0], pose[1], {})

    au.clip("colt1911-akimbo", .08, still(low))
    au.clip("colt1911-akimbo-aim", .08, still(aim))

    def hit(pose):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
            return tuple((a + complex(.3, .4) * k, p + 6 * k) for a, p in pose) + ({},)
        return frame

    au.clip("colt1911-akimbo-hit", .1, hit(low))
    au.clip("colt1911-akimbo-aim-hit", .1, hit(aim))

    D = PAIRED_RELOAD_TIME
    # seated on the pouch magazine: the magazine-out direction (pitch + MAG_AXIS + 180) points
    # straight down (180 in hands space, where x goes up the chest)
    seat_pitch = 180 - (MAG_AXIS + 180)

    def one_hand_reload(arm):
        own, other = low[arm], low[1 - arm]
        pouch_base = pouches[arm]
        marker = "pair-magazine-" + ("left" if arm == 0 else "right")
        above = pouch_base - direction(seat_pitch) * (base + out * MAG_OUT) * au.gpx
        rack_at = pouch_base + complex(3.2, -1.0)        # rear sight hooked on the belt edge

        def gun(t):
            tilt = ease(t, 0, .12) * (1 - ease(t, .4, .55))
            start = own[0] + complex(.4, .6) * tilt, own[1] + 35 * tilt
            if t < .45:                                       # tilt the muzzle up, drop the magazine
                return start
            if t < .82:                                       # down to the pouch, well over the magazine
                f = ease(t, .45, .82)
                return lerp(start[0], above, f), lerp(start[1], seat_pitch, f)
            if t < MAG_SEATED:                                # seat the pistol onto it
                f = ease(t, .82, MAG_SEATED)
                return pouch_base - direction(seat_pitch) * (base + out * MAG_OUT * (1 - f)) * au.gpx, seat_pitch
            # up out of the pouch to the belt edge: an empty pistol is racked there right away
            # (the fetch below); otherwise the game blends back to the hold
            f = ease(t, MAG_SEATED, D)
            rest = pouch_base - direction(seat_pitch) * base * au.gpx
            return lerp(rest, rack_at, f), lerp(seat_pitch, RACK_PITCH, f)

        # the magazine slides out of the grip, then falls freely to the ground (world down)
        a0, p0 = gun(MAG_RELEASE)
        drop_at = au.on_gun(a0, p0, base + out * MAG_OUT)
        landed = MAG_RELEASE + ((drop_at.real - GROUND) * 2 / GRAVITY) ** .5

        def frame(t):
            a, p = gun(t)
            if t < MAG_RELEASE:
                mag = out * MAG_OUT * ease(t, .2, MAG_RELEASE)
            elif t < landed:
                dt = t - MAG_RELEASE
                world = drop_at - .5 * GRAVITY * dt * dt
                mag = (world - a) / (direction(p) * au.gpx) - base
            elif t < .82:
                mag = out * MAG_OUT
            elif t < MAG_SEATED:
                mag = out * MAG_OUT * (1 - ease(t, .82, MAG_SEATED))
            else:
                mag = 0j
            # the other pistol is lifted out of the way and kept pointing forward
            lift = ease(t, 0, .2)
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {marker: mag}

        prefix = "" if arm == 0 else "offhand/"
        side = "left" if arm == 0 else "right"
        events = [(MAG_RELEASE, prefix + "unloaded"), (MAG_SEATED, prefix + "loaded")]
        slots = {marker: {"attachment": [{"name": "magazine"}, {"time": round(landed, 4), "name": None},
                                         {"time": .82, "name": "magazine"}]}}
        for name in ("pair-%s-load-weapon-colt-weapon-colt" % side, "pair-%s-load-weapon-colt" % side):
            au.clip(name, D, frame, events, slots, markers=("pair-magazine-left", "pair-magazine-right"))

        def rack(t):
            # from the belt edge: pressed down with the sound (slide back), released, back to the hold
            press = complex(-.7, 0) * ease(t, RACK_EVENT, RACK_BACK) * (1 - ease(t, RACK_RELEASE, .25))
            f = ease(t, .25, FETCH_TIME)
            a, p = lerp(rack_at, own[0], f) + press, lerp(RACK_PITCH, own[1], f)
            lift = 1 - f
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {}

        au.clip("pair-%s-colt1911-rack" % side, FETCH_TIME, rack, [(RACK_EVENT, prefix + "colt-rack")],
                markers=("pair-magazine-left", "pair-magazine-right"))

    one_hand_reload(0)
    one_hand_reload(1)


def content_changes(content):
    def actions(item):
        comps = item["components"]
        acts = next((c for c in comps if c.get("class", "").endswith("InstrumentActionsComponent")), None)
        if acts is None:
            acts = {"class": "content.components.InstrumentActionsComponent", "tag": "client", "actions": []}
            comps.append(acts)
        acts["actions"] = [a for a in acts.get("actions", []) if a.get("for") not in ("colt-rack", "colt-cycle")] + [
            {"for": "colt-rack", "type": "animate", "animation": "rack"},
            {"for": "colt-cycle", "type": "animate", "animation": "cycle"}]

    content[WEAPON]["primary"]["reloadTime"] = RELOAD_TIME
    content[WEAPON]["primary"]["fetchTime"] = FETCH_TIME
    actions(content[WEAPON])
    if PAIRED in content:
        p = content[PAIRED]
        p["primary"]["reloadTime"] = PAIRED_RELOAD_TIME
        # akimbo: the chamber is there only for the rack after an empty magazine; the server fills
        # the magazine so that magazine + chamber = clip size (ServerWeaponComponentData), no "+1".
        # The second (off-hand) pistol has its own properties in SecondaryWeaponSlotComponent.
        p["primary"]["fetchTime"] = FETCH_TIME
        for comp in p["components"]:
            if comp.get("class", "").endswith("SecondaryWeaponSlotComponent"):
                comp["properties"]["fetchTime"] = FETCH_TIME
                comp["properties"]["reloadTime"] = PAIRED_RELOAD_TIME
        actions(p)
        states = next(c for c in p["components"] if "states" in c and "animation" in c)["states"]
        states.update(hold="colt1911-akimbo", aim="colt1911-akimbo-aim",
                      hit="colt1911-akimbo-hit", aimHit="colt1911-akimbo-aim-hit", fetch="colt1911-rack")


def build(source, destination):
    with ZipFile(source) as src:
        changes = {}
        content = json.loads(src.read("content.json"))
        content_changes(content["content"])
        changes["content.json"] = encode(content)
        names = src.namelist()
        if ACTOR in names and MODELS[0] in names:
            actor = json.loads(src.read(ACTOR))
            guns = {}
            for path in MODELS:
                if path in names:
                    model = json.loads(src.read(path))
                    guns[path] = model_changes(model)
                    changes[path] = encode(model)
            model = json.loads(changes[MODELS[0]])
            setup = {b["name"]: b for b in actor["bones"]}
            gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
            add_hand_magazine(actor, setup, gpx)
            au = Author(actor, guns[MODELS[0]], gpx)
            solo_clips(au)
            akimbo_clips(au)
            changes[ACTOR] = encode(actor)
        if "__H" in names:
            hashes = json.loads(src.read("__H"))
            hashes.update({name: zlib.crc32(data) for name, data in changes.items()})
            changes["__H"] = encode(hashes)
        with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=3) as out:
            for entry in src.infolist():
                out.writestr(entry, changes[entry.filename] if entry.filename in changes else src.read(entry))


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
