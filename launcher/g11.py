"""HK G11: own stances, magazine-from-the-top reload and the rotary cocking handle.

    python g11.py source-base.zip result-base.zip      (run from the launcher folder)

Runs last in build_packages. Needs weapon-g11.json and the g11-* sprites made by
tools/weapon-art/import_g11_concept.py, the sounds by tools/weapon-art/build_g11_audio.py.
Preview any clip with tools/weapon-art/spine_preview.py.

Weapon skeleton (weapon-g11.json): body on the root, the magazine (slot clip) on pair-mag-travel,
moved by the pair-magazine-left marker of the arm clips (WeaponAnimationComponentData), the
cocking handle on g11-crank with the animation "crank" (one turn, played by the g11-crank action).
Player rig (actor.json): g11-mag-hand slot on the support fist (the magazine carried in hand).

Clips (states in smart/Weapons/g11/Weapon.txt):
  g11-hold / g11-aim (+ -hit): the receiver is tall, so the gun sits lower than other rifles; in the
      high stance the scope eyepiece is at eye height; support hand under the front of the housing
  sprint-long-g11-hold: the rifle sprint clip with the same support hand
  g11-reload (2.4 s): the support hand pulls the old magazine forward out of the top and lets it
      fall, takes a fresh one from the chest pouch, slides it in from the front, presses it home;
      timed to g11/reload.wav: slides 0.25-0.75 and 1.15-2.1 s, lock 2.16 s
  g11-fetch (1.0 s, only after an empty magazine): the support hand turns the cocking handle one
      full turn (click at 0.71 s of g11/fetch.wav)
"""
from copy import deepcopy
from math import cos, sin, pi, radians
import json
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gameplay_package import encode
from pair_refinement import ACTOR, ARMS, direction, angle, offset
from paired_reload_art import solve, smooth
from colt1911 import EYE, GRAVITY, GROUND, world_scale

MODEL = "content/animations/weapon-g11.json"
WEAPON = "weapon-g11"
RELOAD_TIME = 2.4
FETCH_TIME = 1.0

# gun points from g11-hires.png (mirrored concept) pixels: origin at the middle of the grip
K = 120 / 1832


def hi(x, y):
    return complex((x - 812) * K, (590 - y) * K)


SIGHT = hi(600, 62)          # rear of the scope eyepiece
SUPPORT = hi(1200, 468)      # under the front of the housing
MAG_GRAB = hi(1450, 205)     # top of the magazine, its middle (the far arm reaches it)
CRANK = hi(502, 398)         # centre of the cocking handle
CRANK_R = 3.2                # gun px: where the fingers hold the handle, off its centre
CRANK_PUSH, CRANK_TILT = complex(-1.2, -1.8), 14.0   # hands space / degrees, see fetch()
MAG_FWD, MAG_UP = 12.0, 9.0  # gun px: out of the well = a bit forward, then up
POUCH, POUCH_ANGLE = complex(-8.6, -3.4), 175.0

# sound cues (g11/reload.wav, g11/fetch.wav)
PULL0, PULL1 = .22, .62      # old magazine pulled forward
POUCH0, POUCH1 = .62, .86    # hand to the pouch
TAKE = .94                   # fresh magazine out
LINE = 1.18                  # lined up in front of the well
SLID = 1.96                  # slid in
LOCK = 2.16                  # pressed home: click
CRANK_EVENT, CRANK_TURN = .22, .48   # the handle turns 0.22-0.70, click at 0.71


def lerp(a, b, f):
    return a + (b - a) * f


def ease(t, t0, t1):
    return smooth((t - t0) / max(1e-5, t1 - t0))


def near(a, ref):
    """the angle equivalent to a that is closest to ref (no turning the long way round)"""
    return ref + (a - ref + 180) % 360 - 180


def fk(setup, bones, arm, t=0):
    """position and absolute angle of the arm's holder in hands space for a clip"""
    def sample(keys, field, default):
        if not keys:
            return default
        if t <= keys[0].get("time", 0):
            return keys[0].get(field, default)
        for a, b in zip(keys, keys[1:]):
            if a.get("time", 0) <= t <= b.get("time", 0):
                f = (t - a.get("time", 0)) / max(1e-6, b.get("time", 0) - a.get("time", 0))
                return a.get(field, default) + (b.get(field, default) - a.get(field, default)) * f
        return keys[-1].get(field, default)
    pos, rot, scale = 0j, 0.0, 1.0
    for n in arm:
        b, tl = setup[n], bones.get(n, {})
        local = offset(b) + complex(sample(tl.get("translate"), "x", 0), sample(tl.get("translate"), "y", 0))
        pos = pos + direction(rot) * local * scale
        rot = rot + b.get("rotation", 0) + sample(tl.get("rotate"), "value", 0)
        scale *= b.get("scaleX", 1)
    return pos, rot


class Author:
    def __init__(self, actor, gpx):
        self.actor = actor
        self.setup = {b["name"]: b for b in actor["bones"]}
        self.clips = actor["animations"]
        self.gpx = gpx
        hold = self.clips["hold-weapon-2hands"]["bones"]
        # neutral key values for the unwrapping in solve()
        self.carry = {n: {"translate": [{}], "rotate": [{"value": hold.get(n, {}).get("rotate", [{}])[0].get("value", 0)}]}
                      for arm in ARMS for n in arm}

    def on_gun(self, anchor, pitch, p):
        return anchor + direction(pitch) * p * self.gpx

    def clip(self, name, duration, frame, events=(), slots=None, extra_times=(), fps=30):
        """frame(t) -> ((pos, angle) of the trigger fist, (pos, angle) of the support fist, magazine offset or None)"""
        tracks = {a[0]: {"translate": [{}]} for a in ARMS}
        keys = []
        times = sorted({0, duration, *(e[0] for e in events), *extra_times,
                        *(i / fps for i in range(1, int(duration * fps) + 1))})
        for t in times:
            front, back, mag = frame(t)
            solve(tracks, self.setup, self.carry, ARMS[0], t, *front)
            solve(tracks, self.setup, self.carry, ARMS[1], t, *back)
            if mag is not None:
                keys.append({"time": round(t, 5), "x": round(mag.real, 3), "y": round(mag.imag, 3)})
        tracks["pair-magazine-left"] = {"translate": keys or [{}]}
        tracks["pair-magazine-left-alignment"] = {"translate": [{}]}
        pose = {"bones": tracks, "slots": {"special": {"attachment": [{"name": None}]}}}
        if events:
            pose["events"] = [{"time": round(t, 5), "name": "instrument-action", "string": s} for t, s in events]
        if slots:
            pose["slots"].update(slots)
        self.clips[name] = pose


def add_hand_magazine(actor, setup, gpx, model, grab_angle):
    """the g11-mag sprite on the support fist, so that the grab point sits on the fist and the
    magazine is parallel to the gun when the fist angle is pitch + grab_angle"""
    if "g11-mag-hold" not in setup:
        actor["bones"].append({"name": "g11-mag-hold", "parent": "holder-secondary"})
        setup["g11-mag-hold"] = actor["bones"][-1]
    names = [s["name"] for s in actor["slots"]]
    if "g11-mag-hand" not in names:
        actor["slots"].insert(names.index("gpalm2") + 1, {"name": "g11-mag-hand", "bone": "g11-mag-hold"})
    att = next(s for s in model["skins"] if s["name"] == "weapon-default")["attachments"]["clip"]["default"]
    centre = complex(att["x"], att["y"])
    k = gpx / world_scale(setup, ("hand2", "palm2", "holder-secondary"))
    # gun px -> fist space: rotate by -grab_angle, scale k
    local = (centre - MAG_GRAB) * direction(-grab_angle) * k
    default = next(s for s in actor["skins"] if s["name"] == "default")
    default["attachments"]["g11-mag-hand"] = {"mag": {
        "name": "g11-mag", "path": "g11-mag", "x": round(local.real, 3), "y": round(local.imag, 3),
        "rotation": round(-grab_angle, 3), "scaleX": round(k, 4), "scaleY": round(k, 4),
        "width": att["width"], "height": att["height"]}}


def clips(au, model):
    s = au.setup
    hold_src = au.clips["hold-weapon-2hands"]["bones"]
    aug_front, aug_pitch = fk(s, hold_src, ARMS[0])
    aug_back, aug_back_angle = fk(s, hold_src, ARMS[1])
    support_rel = aug_back_angle - aug_pitch          # how a rifle support fist is turned

    # high stance: barrel level, the eyepiece at eye height, the reach of the AUG aim
    aim_front, _ = fk(s, au.clips["aim-weapon-2hands"]["bones"], ARMS[0])
    aim_at, aim_pitch = complex(EYE - SIGHT.imag * au.gpx, aim_front.imag), -90.0
    # low stance: lower and a bit closer, the muzzle slightly down
    hold_at, hold_pitch = aim_at + complex(-3.3, 1.0), -86.0
    work_at, work_pitch = hold_at + complex(.6, .9), -83.0   # reloading: closer to the chest

    def two(a, p):
        return (a, p), (au.on_gun(a, p, SUPPORT), p + support_rel)

    def still(a, p):
        return lambda t: (*two(a, p), None)

    au.clip("g11-hold", .08, still(hold_at, hold_pitch))
    au.clip("g11-aim", .08, still(aim_at, aim_pitch))

    def shot(a0, p0):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
            return (*two(a0 + complex(.15, .35) * k, p0 + 2.5 * k), None)
        return frame

    au.clip("g11-hit", .1, shot(hold_at, hold_pitch))
    au.clip("g11-aim-hit", .1, shot(aim_at, aim_pitch))

    # sprint: the rifle sprint clip moved by the same amount as the low stance, our support hand
    src = au.clips.get("sprint-long-hold-weapon-2hands")
    if src:
        shift = hold_at - aug_front
        dur = max([k.get("time", 0) for tr in src["bones"].values() for ks in tr.values() for k in ks] + [.1])

        def sprint(t):
            a, p = fk(s, src["bones"], ARMS[0], t)
            return (*two(a + shift, p), None)
        au.clip("sprint-long-g11-hold", dur, sprint)

    grab_angle = support_rel + 75                     # fingers down onto the magazine top
    out = complex(MAG_FWD, MAG_UP)

    def path(f):
        """magazine offset along the way out of the well: forward first, then up (f 0..1)"""
        return complex(MAG_FWD * smooth(f / .55), MAG_UP * smooth((f - .35) / .65))

    def gun(t):
        """the rifle: hold -> working position, back towards the hold at the end"""
        f = ease(t, 0, .22) * (1 - ease(t, LOCK, RELOAD_TIME) * .5)
        return lerp(hold_at, work_at, f), lerp(hold_pitch, work_pitch, f)

    a_drop, p_drop = gun(PULL1)
    drop_from = au.on_gun(a_drop, p_drop, out)        # the magazine's position when let go
    landed = PULL1 + ((drop_from.real - GROUND) * 2 / GRAVITY) ** .5

    def reload(t):
        a, p = gun(t)
        on = lambda q: au.on_gun(a, p, q)
        grab = p + grab_angle
        mag = 0j
        if t < PULL0:                                  # support hand up onto the magazine
            f = ease(t, .02, PULL0)
            hand = lerp(on(SUPPORT), on(MAG_GRAB), f) + complex(1.2, 0) * sin(pi * f)
            ang = lerp(p + support_rel, near(grab, p + support_rel), f)
        elif t < PULL1:                                # pulled forward and up out of the well
            mag = path((t - PULL0) / (PULL1 - PULL0))
            hand, ang = on(MAG_GRAB + mag), grab
        else:
            if t < landed:                             # let go: it falls (world down = hands -x)
                dt = t - PULL1
                world = drop_from - .5 * GRAVITY * dt * dt
                mag = (world - a) / (direction(p) * au.gpx)
            elif t < LINE:
                mag = out                              # hidden (marker without attachment)
            elif t < SLID:                             # lowered into the well, slid back
                mag = path(1 - (t - LINE) / (SLID - LINE))
            else:                                      # pressed home
                mag = complex(0, -.6) * sin(pi * ease(t, SLID, LOCK))
            if t < POUCH1:                             # to the pouch
                f = ease(t, PULL1, POUCH1)
                start = on(MAG_GRAB + out)
                hand = lerp(start, POUCH, f) + complex(1.5, 0) * sin(pi * f)
                ang = lerp(grab, near(POUCH_ANGLE, grab), f)
            elif t < TAKE:                             # a fresh one
                hand = POUCH + complex(-.6, 0) * sin(pi * ease(t, POUCH1, TAKE))
                ang = near(POUCH_ANGLE, grab)
            elif t < LINE:                             # up in front of the well
                f = ease(t, TAKE, LINE)
                hand = lerp(POUCH, on(MAG_GRAB + out), f) + complex(1.8, 0) * sin(pi * f)
                ang = lerp(near(POUCH_ANGLE, grab), grab, f)
            elif t < LOCK:                             # the hand rides on the magazine
                hand, ang = on(MAG_GRAB + mag), grab
            else:                                      # back under the front of the housing
                f = ease(t, LOCK, RELOAD_TIME)
                hand = lerp(on(MAG_GRAB), on(SUPPORT), f) + complex(1.0, 0) * sin(pi * f)
                ang = lerp(grab, near(p + support_rel, grab), f)
        return (a, p), (hand, ang), mag

    au.clip("g11-reload", RELOAD_TIME, reload, extra_times=(PULL0, PULL1, landed, POUCH1, TAKE, LINE, SLID, LOCK), slots={
        "pair-magazine-left": {"attachment": [
            {"name": "magazine"}, {"time": round(landed, 4), "name": None}, {"time": LINE, "name": "magazine"}]},
        "g11-mag-hand": {"attachment": [
            {"name": None}, {"time": TAKE - .04, "name": "mag"}, {"time": LINE, "name": None}]},
    })

    # turning the handle: the rifle pushed out and the muzzle up, so the handle (behind the grip)
    # comes away from the shoulder and the support arm is not folded up against the face
    crank_at, crank_pitch = work_at + CRANK_PUSH, work_pitch + CRANK_TILT

    def fetch(t):
        # starts where a reload leaves the rifle (half way back to the hold)
        a = lerp(lerp(hold_at, work_at, .5), crank_at, ease(t, 0, CRANK_EVENT))
        p = lerp(lerp(hold_pitch, work_pitch, .5), crank_pitch, ease(t, 0, CRANK_EVENT))
        back = ease(t, CRANK_EVENT + CRANK_TURN, FETCH_TIME)
        a, p = lerp(a, hold_at, back), lerp(p, hold_pitch, back)
        on = lambda q: au.on_gun(a, p, q)
        turn = ease(t, CRANK_EVENT, CRANK_EVENT + CRANK_TURN) * 360   # clockwise as seen
        handle = CRANK + CRANK_R * direction(90 - turn)
        twist = p + support_rel + 40 - 25 * sin(radians(turn))
        if t < CRANK_EVENT:                           # from under the housing (end of the reload) to the handle
            f = ease(t, 0, CRANK_EVENT)
            hand = lerp(on(SUPPORT), on(handle), f) + complex(.8, 0) * sin(pi * f)
            ang = lerp(p + support_rel, near(twist, p + support_rel), f)
        elif t < CRANK_EVENT + CRANK_TURN:            # one turn
            hand, ang = on(handle), twist
        else:                                         # back under the front of the housing
            f = ease(t, CRANK_EVENT + CRANK_TURN, FETCH_TIME)
            hand = lerp(on(handle), on(SUPPORT), f) + complex(1.0, 0) * sin(pi * f)
            ang = lerp(twist, near(p + support_rel, twist), f)
        return (a, p), (hand, ang), None

    au.clip("g11-fetch", FETCH_TIME, fetch, [(CRANK_EVENT, "g11-crank")])
    return grab_angle


def front_order(actor):
    """drawOrder offsets that put the support arm (normally behind the rifle) in front of it"""
    names = [sl["name"] for sl in actor["slots"]]
    moved = [n for n in ("ghand2", "gpalm2", "g11-mag-hand") if n in names]
    order = [n for n in names if n not in moved]
    anchor = max(order.index(n) for n in ("slot-primary", "slot-primary-upper") if n in order)
    order[anchor + 1:anchor + 1] = moved
    return [{"slot": n, "offset": order.index(n) - names.index(n)} for n in moved]


def content_changes(content):
    w = content[WEAPON]
    w["primary"]["reloadTime"] = RELOAD_TIME
    w["primary"]["fetchTime"] = FETCH_TIME
    for comp in w["components"]:
        if "states" in comp and "animation" in comp:
            comp["states"].update(hold="g11-hold", aim="g11-aim", hit="g11-hit", aimHit="g11-aim-hit",
                                  reload="g11-reload", fetch="g11-fetch")


def build(source, destination):
    with ZipFile(source) as src:
        changes = {}
        names = src.namelist()
        content = json.loads(src.read("content.json"))
        if WEAPON not in content["content"]:
            raise SystemExit("g11: no %s in %s" % (WEAPON, source))
        content_changes(content["content"])
        changes["content.json"] = encode(content)
        if ACTOR in names:      # the client package (the server has no actor.json)
            actor = json.loads(src.read(ACTOR))
            model = json.loads(src.read(MODEL))
            setup = {b["name"]: b for b in actor["bones"]}
            gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
            au = Author(actor, gpx)
            grab_angle = clips(au, model)
            add_hand_magazine(actor, setup, gpx, model, grab_angle)
            # the handle is on the visible side: the support hand turns it in front of the rifle,
            # back behind it before the clip ends (a mix-out restores the setup order anyway)
            actor["animations"]["g11-fetch"]["drawOrder"] = [
                {"time": 0, "offsets": front_order(actor)}, {"time": round(FETCH_TIME - .15, 3)}]
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
