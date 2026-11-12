"""Pistols with a magazine in the grip and a slide: the Colt 1911 approach for the whole family.

    python sidearms.py source-base.zip result-base.zip      (run from the launcher folder)

Runs in build_packages after colt1911. Needs the sprites and launcher/sidearms_geometry.json
made by `tools/weapon-art/sidearm_sprites.py --all` (sprites packed by make_data into GAME).

For every pistol of FAMILY (and its akimbo pair, paired-weapon-<id>):
  weapon skeleton: a "grip" bone shifts the pistol so the fist holds the middle of the grip;
    body -> sa-<id>-frame-<n>, a new slide slot sa-<id>-slide-<n> with "rack" / "cycle"
    animations, the "clip" slot shows sa-<id>-mag inside the grip on pair-mag-travel
  player rig: sa-mag-hand slot on the support fist (the magazine carried in hand)
  solo: low stance at the chest, high stance (RMB) arms out, shots cycle the slide,
    reload = magazine into the hand, into the pouch, a fresh one, pushed in, the hand ends on
    the slide; the rack (fetch) follows only after an empty magazine
  akimbo: both arms out, barrels parallel; one-handed reload: the magazine falls to the ground,
    the pistol is seated on a magazine in the belt pouch, racked on the belt edge (only empty);
    the chamber counts toward the clip (ServerWeaponComponentData / getLoadedRounds)
All timings follow the weapon's own reload / fetch sounds (SOUNDS).
"""
from copy import deepcopy
from math import sin, pi
import json
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gameplay_package import encode
import sidearms_front
import sidearms_special
from pair_refinement import ACTOR, ARMS, direction
from paired_reload_art import smooth
from colt1911 import Author, straight, world_scale, lerp, ease, bump, eye_line, GROUND, GRAVITY, RACK_PITCH

GEOMETRY = Path(__file__).with_name("sidearms_geometry.json")

# reload sound: magazine out, magazine seated; fetch sound: slide back, slide forward (seconds)
SOUNDS = {
    "glock": (.10, .65, .06, .13),
    "usp": (.32, 1.10, .09, .21),
    "pistol": (.12, .53, .06, .23),
    "usp-match": (.16, .60, .06, .18),
    "colt": (.31, .94, .09, .19),
    "luger": (.31, .94, .10, .19),     # magnum-reload.mp3 / luger-fetch.mp3
}
FAMILY = {
    "aps": "glock", "baltiets": "pistol", "beretta": "usp", "browning": "usp", "cz75": "glock",
    "desert": "pistol", "desert50ae": "pistol", "fiveseven": "usp", "fnx45": "glock",
    "fort12": "colt", "jericho": "pistol", "makarov": "colt", "mp443": "usp", "ots33": "colt",
    "p99": "usp", "pistol": "glock", "pistol-s": "pistol", "qsz92": "usp", "sigsauer": "glock",
    "taurus": "glock", "tt": "colt", "usp": "usp", "usp-match": "usp-match", "vp70": "glock",
    "m93r": "usp", "luger": "luger", "mauser": "luger",
}
TOGGLE_ANGLE = -35.0     # Luger: the toggle folds up (clockwise when facing right)
BOLT_TRAVEL = 6          # Mauser: sprite px the bolt goes back
CLIP_HOME = (14.5, 6.0)  # Mauser: the stripper clip inside the magazine box (sprite px), hidden


def animation_path(content, item):
    comp = next(c for c in item["components"] if "states" in c and "animation" in c)
    return comp, "content/" + content[comp["animation"]]["animation"].split(":")[1]


class Gun:
    """Points on a pistol in its root space (after the grip shift), from sprite pixels."""

    def __init__(self, geo, att, shifted):
        w, h = geo["size"]
        self.sx, self.sy = att.get("scaleX", 1), att.get("scaleY", 1)
        self.left = att["x"] - w * self.sx / 2
        self.top = att["y"] + h * self.sy / 2
        gx, gy = geo["grip"]
        self.grip = complex(self.left + (gx + .5) * self.sx, self.top - (gy + .5) * self.sy)
        self.shift = -self.grip if shifted else 0j

    def at(self, xy):
        return complex(self.left + xy[0] * self.sx, self.top - xy[1] * self.sy) + self.shift


def model_changes(model, wid, geo):
    body_slot = geo["body_slot"]
    skins = {s["name"]: s for s in model["skins"]}
    default = next((s for s in model["skins"] if body_slot in s.get("attachments", {})), model["skins"][0])
    battach = next(s["attachment"] for s in model["slots"] if s["name"] == body_slot)
    att = default["attachments"][body_slot][battach]
    plain = Gun(geo, att, False)
    root = model["bones"][0]["name"]
    if not any(b["name"] == "grip" for b in model["bones"]):
        for b in model["bones"][1:]:
            if b.get("parent") == root:
                b["parent"] = "grip"
        model["bones"].insert(1, {"name": "grip", "parent": root,
                                  "x": round(-plain.grip.real, 3), "y": round(-plain.grip.imag, 3)})
        for s in model["slots"]:
            if s["bone"] == root:
                s["bone"] = "grip"
    names = {b["name"] for b in model["bones"]}
    if "pair-mag-travel" not in names:
        model["bones"].append({"name": "pair-mag-travel", "parent": "grip"})
    pivot = plain.at(geo["pivot"]) if "pivot" in geo else 0j
    if "sa-slide" not in names:
        model["bones"].append({"name": "sa-slide", "parent": "grip",
                               "x": round(pivot.real, 3), "y": round(pivot.imag, 3)})
    slots = model["slots"]
    if not any(s["name"] == "sa-slide" for s in slots):
        i = next(i for i, s in enumerate(slots) if s["name"] == body_slot)
        slots.insert(i + 1, {"name": "sa-slide", "bone": "sa-slide", "attachment": "default"})
    clip = next((s for s in slots if s["name"] == "clip"), None)
    if clip is None:
        clip = {"name": "clip", "bone": "pair-mag-travel"}
    else:
        slots.remove(clip)
    clip["bone"] = "pair-mag-travel"
    clip["attachment"] = "sa-mag"
    slots.insert(0, clip)                        # the magazine sits behind the frame

    mw, mh = geo["mag_img"]
    axis = geo["axis"]
    base = plain.at(geo["base"])                 # bone space of pair-mag-travel = unshifted root space
    centre = base + direction(axis) * (mh / 2 - .5) * plain.sx
    mag_rotation = axis - 90
    if geo.get("fixed_mag"):
        centre, mag_rotation = plain.at(CLIP_HOME), 0
    for skin in model["skins"]:
        a = skin.setdefault("attachments", {})
        b = a.get(body_slot, {}).get(battach)
        n = geo["skins"].get(skin["name"])
        if b and n is not None:
            b["name"] = b["path"] = "sa-%s-frame-%d" % (wid, n)
            a["sa-slide"] = {"default": dict(b, name="sa-%s-slide-%d" % (wid, n), path="sa-%s-slide-%d" % (wid, n),
                                             x=round(b["x"] - pivot.real, 3), y=round(b["y"] - pivot.imag, 3))}
        a.setdefault("clip", {})["sa-mag"] = {
            "name": "sa-%s-mag" % wid, "path": "sa-%s-mag" % wid, "x": round(centre.real, 3),
            "y": round(centre.imag, 3), "rotation": round(mag_rotation, 2), "width": mw, "height": mh,
            "scaleX": plain.sx, "scaleY": plain.sy}

    w = geo["size"][0]
    travel = max(3, round(w * .11)) * plain.sx
    rel, seat, back, fwd = SOUNDS[FAMILY[wid]]
    event = max(0, back - .06)
    pull = back - event
    hold = max(pull + .02, fwd - event - .02)
    anims = model.setdefault("animations", {})
    anims["rack"] = {"bones": {"sa-slide": {"translate": [
        {"time": round(pull * i / 6, 4), "x": round(-travel * smooth(i / 6), 3)} for i in range(7)] + [
        {"time": round(hold, 4), "x": -travel}, {"time": round(hold + .02, 4), "x": round(-travel * .35, 3)},
        {"time": round(hold + .03, 4)}]}}}
    anims["cycle"] = {"bones": {"sa-slide": {"translate": [
        {"time": 0}, {"time": .03, "x": -travel}, {"time": .075}]}}}
    if "pivot" in geo:          # Luger: the toggle folds up instead of sliding
        anims["rack"] = {"bones": {"sa-slide": {"rotate": [
            {"time": round(pull * i / 6, 4), "value": round(TOGGLE_ANGLE * smooth(i / 6), 2)} for i in range(7)] + [
            {"time": round(hold, 4), "value": TOGGLE_ANGLE}, {"time": round(hold + .03, 4)}]}}}
        anims["cycle"] = {"bones": {"sa-slide": {"rotate": [
            {"time": 0}, {"time": .03, "value": TOGGLE_ANGLE}, {"time": .075}]}}}
    if geo.get("fixed_mag"):    # Mauser: the bolt is held open for the stripper clip, then released
        travel = BOLT_TRAVEL * plain.sx
        anims["open"] = {"bones": {"sa-slide": {"translate": [
            {"time": round(.12 * i / 6, 4), "x": round(-travel * smooth(i / 6), 3)} for i in range(7)]}}}
        anims["close"] = {"bones": {"sa-slide": {"translate": [
            {"time": 0, "x": -travel}, {"time": .04}]}}}
        anims["cycle"] = {"bones": {"sa-slide": {"translate": [
            {"time": 0}, {"time": .03, "x": -travel}, {"time": .075}]}}}
    return Gun(geo, att, True), travel


def add_hand_magazine(actor, setup, wid, geo, gun, gpx):
    if "sa-mag-hold" not in setup:
        actor["bones"].append({"name": "sa-mag-hold", "parent": "holder-secondary"})
        setup["sa-mag-hold"] = actor["bones"][-1]
    names = [s["name"] for s in actor["slots"]]
    if "sa-mag-hand" not in names:
        actor["slots"].insert(names.index("gpalm2") + 1, {"name": "sa-mag-hand", "bone": "sa-mag-hold"})
    mw, mh = geo["mag_img"]
    k = gpx * gun.sx / world_scale(setup, ("hand2", "palm2", "holder-secondary"))
    default = next(s for s in actor["skins"] if s["name"] == "default")
    default["attachments"].setdefault("sa-mag-hand", {})["sa-" + wid] = {
        "name": "sa-%s-mag" % wid, "path": "sa-%s-mag" % wid, "x": round((mh / 2 - .5) * k, 3), "y": 0,
        "rotation": -90, "scaleX": round(k, 4), "scaleY": round(k, 4), "width": mw, "height": mh}
    for side in ("left", "right"):
        default["attachments"].setdefault("pair-magazine-" + side, {}).setdefault(
            "magazine", {"name": "sa-%s-mag" % wid, "path": "sa-%s-mag" % wid, "width": 1, "height": 1})


def timings(wid, item, geo=None):
    rel, seat, back, fwd = SOUNDS[FAMILY[wid]]
    D = round(max(item["primary"].get("reloadTime", 1), seat + .28 + (.2 if (geo or {}).get("fixed_mag") else 0)), 3)
    F = round(max(item["primary"].get("fetchTime", .4), fwd + .35), 3)
    return rel, seat, back, fwd, D, F


def solo_clips(au, wid, states, geo, travel, T):
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    axis = geo["axis"]
    mag_out = (geo["mag"][1] + 2) * g.sx
    hold_at, hold_pitch = complex(-1.4, -7.4), -89.5
    aim_at, aim_pitch = eye_line(au, complex(.5, -10.8), g.at((geo["rear"][0], geo["slide_top"])))
    work_at, work_pitch = complex(-1.42, -7.6), -61.5
    grip_front = g.at(geo.get("support", geo["front"]))
    support_angle = geo.get("support_angle", 70)
    base = g.at(geo["base"])
    rear = g.at(geo["rear"])
    over = rear + complex(3 * g.sx, 5 * g.sy)
    out = direction(axis + 180)
    pouch, pouch_angle = complex(-8.6, -3.4), 175.0
    W = "solo-weapon-%s-" % wid

    def two(a, p):
        return (a, p), (au.on_gun(a, p, grip_front), p + support_angle)

    def still(a, p):
        return lambda t: (*two(a, p), {})

    def shot(a0, p0):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
            return (*two(a0 + complex(.35, .45) * k, p0 + 7 * k), {})
        return frame

    for state, fn, d, ev in (("hold", still(hold_at, hold_pitch), .08, ()),
                             ("aim", still(aim_at, aim_pitch), .08, ()),
                             ("hit", shot(hold_at, hold_pitch), .1, [(0, "sa-cycle")]),
                             ("aimHit", shot(aim_at, aim_pitch), .1, [(0, "sa-cycle")])):
        if states.get(state):
            au.clip(W + states[state], d, fn, ev)

    if geo.get("fixed_mag"):
        mauser_solo(au, wid, states, geo, T, hold_at, hold_pitch, work_at, work_pitch, grip_front, support_angle)
        return

    tilt_end = max(.06, rel - .11)
    trip = max(.3, seat_t - rel - .14)
    t_take = rel + .01
    t_pouch = t_take + trip * .38
    t_fresh = t_pouch + trip * .14
    t_line = seat_t - .12

    def reload(t):
        f = ease(t, 0, tilt_end + .08)
        a, p = lerp(hold_at, work_at, f), lerp(hold_pitch, work_pitch, f)
        on = lambda q: au.on_gun(a, p, q)
        seat = p + axis
        mag = 0j
        if t < tilt_end:
            f = ease(t, 0, tilt_end)
            s, ang = lerp(on(grip_front), on(base + out * 2 * g.sx), f), lerp(p + support_angle, seat, f)
        elif t < t_take:
            mag = out * mag_out * ease(t, tilt_end, rel)
            s, ang = on(base + mag), seat
        elif t < t_pouch:
            f = ease(t, t_take, t_pouch)
            s = lerp(on(base + out * mag_out), pouch, f) + complex(.8, 0) * sin(pi * f)
            ang, mag = lerp(seat, pouch_angle, f), out * mag_out
        elif t < t_fresh:
            s, ang, mag = pouch + complex(-.7, 0) * bump(t, t_pouch, t_fresh), pouch_angle, out * mag_out
        elif t < t_line:
            f = ease(t, t_fresh, t_line)
            s = lerp(pouch, on(base + out * mag_out), f) + complex(.8, 0) * sin(pi * f)
            ang, mag = lerp(pouch_angle, seat, f), out * mag_out
        elif t < seat_t:
            mag = out * mag_out * (1 - ease(t, t_line, seat_t))
            s, ang = on(base + mag), seat
        else:
            f = ease(t, seat_t, D)
            s = lerp(lerp(on(base), on(over), f), lerp(on(over), on(rear), f), f)
            ang = lerp(seat, p - 25, f)
        return (a, p), (s, ang), {"pair-magazine-left": mag}

    hand = "sa-" + wid
    if states.get("reload"):
        au.clip(W + states["reload"], D, reload, [(rel, "unloaded"), (seat_t, "loaded")], {
            "pair-magazine-left": {"attachment": [
                {"name": "magazine"}, {"time": round(t_take, 4), "name": None}, {"time": round(t_line, 4), "name": "magazine"}]},
            "sa-mag-hand": {"attachment": [
                {"name": None}, {"time": round(t_take, 4), "name": hand}, {"time": round(t_pouch, 4), "name": None},
                {"time": round(t_fresh - .02, 4), "name": hand}, {"time": round(t_line, 4), "name": None}]},
        })

    event = max(0, back - .06)

    def fetch(t):
        f = ease(t, fwd + .1, F)
        a, p = lerp(work_at, hold_at, f), lerp(work_pitch, hold_pitch, f)
        on = lambda q: au.on_gun(a, p, q)
        if t < fwd:
            s, ang = on(rear + complex(-travel, 0) * ease(t, event, back)), p - 25
        elif t < fwd + .1:
            k = ease(t, fwd, fwd + .1)
            s, ang = on(rear + complex(-travel - 3 * g.sx * k, 2 * g.sy * k)), p - 25 + 10 * k
        else:
            s = lerp(on(rear + complex(-travel - 3 * g.sx, 2 * g.sy)), on(grip_front), f)
            ang = lerp(p - 15, p + support_angle, f)
        return (a, p), (s, ang), {}

    if states.get("fetch"):
        au.clip(W + states["fetch"], F, fetch, [(event, "sa-rack")])


def mauser_solo(au, wid, states, geo, T, hold_at, hold_pitch, work_at, work_pitch, grip_front, support_angle):
    """Bolt back by its ears, a stripper clip from the pouch into the guides, thumbed down, bolt released."""
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    travel = BOLT_TRAVEL * g.sx
    ears = g.at((3.0, 0.5))                      # bolt ears at the rear top
    guide = g.at((CLIP_HOME[0], 0.0))            # top of the receiver over the magazine
    clip_len = geo["mag_img"][1] * g.sx
    up = 1j                                      # gun space up
    pouch, pouch_angle = complex(-8.6, -3.4), 175.0
    t_open, t_pouch, t_fresh, t_line = .12, .5, .58, .78
    t_close = seat_t + .12

    def reload(t):
        f = ease(t, 0, .14) * (1 - ease(t, t_close + .05, D))
        a, p = lerp(hold_at, work_at, f), lerp(hold_pitch, work_pitch, f)
        on = lambda q: au.on_gun(a, p, q)
        down = p - 90
        mag = up * clip_len
        if t < t_open:                                           # to the bolt ears
            k = ease(t, 0, t_open)
            s, ang = lerp(on(grip_front), on(ears), k), lerp(p + support_angle, p - 25, k)
        elif t < rel:                                            # pull the bolt back, it stays open
            s, ang = on(ears - travel * ease(t, t_open, t_open + .12)), p - 25
        elif t < t_pouch:                                        # to the pouch
            k = ease(t, rel, t_pouch)
            s = lerp(on(ears - travel), pouch, k) + complex(.8, 0) * sin(pi * k)
            ang = lerp(p - 25, pouch_angle, k)
        elif t < t_fresh:
            s, ang = pouch + complex(-.7, 0) * bump(t, t_pouch, t_fresh), pouch_angle
        elif t < t_line:                                         # the clip over the guides
            k = ease(t, t_fresh, t_line)
            s = lerp(pouch, on(guide + up * clip_len), k) + complex(.8, 0) * sin(pi * k)
            ang = lerp(pouch_angle, down, k)
        elif t < seat_t:                                         # thumbed down into the magazine
            mag = up * clip_len * (1 - ease(t, t_line, seat_t))
            s, ang = on(guide + mag), down
        elif t < t_close:                                        # back to the ears, release
            k = ease(t, seat_t, t_close)
            s, ang = lerp(on(guide), on(ears - travel), k), lerp(down, p - 25, k)
            mag = 0j
        else:
            k = ease(t, t_close, D)
            s = lerp(on(ears + complex(-2 * g.sx, 3 * g.sy)), on(grip_front), k)
            ang = lerp(p - 10, p + support_angle, k)
            mag = 0j
        return (a, p), (s, ang), {"pair-magazine-left": mag if t_line <= t < seat_t else 0j}

    hand = "sa-" + wid
    if states.get("reload"):
        au.clip("solo-weapon-%s-%s" % (wid, states["reload"]), D, reload,
                [(t_open, "sa-open"), (seat_t, "loaded"), (t_close, "sa-close")], {
                    "pair-magazine-left": {"attachment": [{"name": None}, {"time": t_line, "name": "magazine"},
                                                          {"time": round(seat_t, 4), "name": None}]},
                    "sa-mag-hand": {"attachment": [{"name": None}, {"time": round(t_fresh - .03, 4), "name": hand},
                                                   {"time": t_line, "name": None}]}})


def mauser_akimbo(au, wid, geo, T, aim):
    """One-handed: bolt opened on the belt edge, the pistol turned over onto a clip in the pouch,
    pressed down, the bolt bumped closed on the belt, back."""
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    clip_len = geo["mag_img"][1] * g.sx
    guide = g.at((CLIP_HOME[0], 0.0))
    up = 1j
    pouches = complex(-9.6, -3.6), complex(-9.4, -7.4)
    flip = 90.0                                   # the receiver top faces down, the muzzle back
    t_flip, t_line, t_close = .4, .74, seat_t + .12
    P = "sa-%s-" % wid
    for arm in (0, 1):
        own, other = aim[arm], aim[1 - arm]
        pouch = pouches[arm]
        belt = pouch + complex(3.2, -1.0)
        marker = "pair-magazine-" + ("left" if arm == 0 else "right")

        def frame(t, arm=arm, own=own, other=other, pouch=pouch, belt=belt, marker=marker):
            mag = 0j
            if t < rel:                                           # bolt ears onto the belt edge, push
                k = ease(t, 0, .2)
                a, p = lerp(own[0], belt, k) + complex(-.6, 0) * ease(t, .2, rel), lerp(own[1], RACK_PITCH, k)
            elif t < t_line:                                      # turn it over above the clip
                k = ease(t, rel, t_line)
                over = pouch + up * 0 - direction(flip) * (guide + up * clip_len) * au.gpx
                a, p = lerp(belt, over, k), lerp(RACK_PITCH, flip, k)
                mag = up * clip_len if t > t_flip else 0j
            elif t < seat_t:                                      # pressed down onto it
                k = ease(t, t_line, seat_t)
                mag = up * clip_len * (1 - k)
                a, p = pouch - direction(flip) * (guide + mag) * au.gpx, flip
            elif t < t_close:                                     # back up, bolt bumped closed on the belt
                k = ease(t, seat_t, t_close)
                rest = pouch - direction(flip) * guide * au.gpx
                a, p = lerp(rest, belt, k), lerp(flip, RACK_PITCH, k)
            else:
                k = ease(t, t_close, D)
                a, p = lerp(belt, own[0], k), lerp(RACK_PITCH, own[1], k)
            lift = ease(t, 0, .2) * (1 - ease(t, t_close, D))
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {marker: mag}

        prefix = "" if arm == 0 else "offhand/"
        side = "left" if arm == 0 else "right"
        slots = {marker: {"attachment": [{"name": None}, {"time": t_line, "name": "magazine"},
                                         {"time": round(seat_t, 4), "name": None}]}}
        au.clip("pair-%s-%sreload" % (side, P), D, frame,
                [(.2, prefix + "sa-open"), (seat_t, prefix + "loaded"), (t_close, prefix + "sa-close")],
                slots, markers=("pair-magazine-left", "pair-magazine-right"))


def akimbo_clips(au, wid, geo, T):
    g = au.gun
    rel, seat_t, back, fwd, D, F = T
    axis = geo["axis"]
    mag_out = (geo["mag"][1] + 2) * g.sx
    base = g.at(geo["base"])
    out = direction(axis + 180)
    aim = (straight(au, ARMS[0], -.2), -89.0), (straight(au, ARMS[1], -.8), -89.0)
    pouches = complex(-9.6, -3.6), complex(-9.4, -7.4)
    P = "sa-%s-" % wid

    au.clip(P + "akimbo", .08, lambda t: (aim[0], aim[1], {}))

    def hit(t):
        k = ease(t, 0, .03) * (1 - ease(t, .03, .1))
        return tuple((a + complex(.3, .4) * k, p + 6 * k) for a, p in aim) + ({},)

    au.clip(P + "akimbo-hit", .1, hit)
    if geo.get("fixed_mag"):
        mauser_akimbo(au, wid, geo, T, aim)
        return
    seat_pitch = -axis
    t_down = rel + .1
    t_line = max(t_down + .15, seat_t - .12)
    event = max(0, back - .06)

    for arm in (0, 1):
        own, other = aim[arm], aim[1 - arm]
        pouch_base = pouches[arm]
        marker = "pair-magazine-" + ("left" if arm == 0 else "right")
        above = pouch_base - direction(seat_pitch) * (base + out * mag_out) * au.gpx
        rack_at = pouch_base + complex(3.2, -1.0)

        def gun(t, own=own, above=above, pouch_base=pouch_base, rack_at=rack_at):
            tilt = ease(t, 0, max(.06, rel - .04)) * (1 - ease(t, t_down, t_line))
            start = own[0] + complex(.4, .6) * tilt, own[1] + 35 * tilt
            if t < t_down:
                return start
            if t < t_line:
                f = ease(t, t_down, t_line)
                return lerp(start[0], above, f), lerp(start[1], seat_pitch, f)
            if t < seat_t:
                f = ease(t, t_line, seat_t)
                return pouch_base - direction(seat_pitch) * (base + out * mag_out * (1 - f)) * au.gpx, seat_pitch
            f = ease(t, seat_t, D)
            rest = pouch_base - direction(seat_pitch) * base * au.gpx
            return lerp(rest, rack_at, f), lerp(seat_pitch, RACK_PITCH, f)

        a0, p0 = gun(rel)
        drop_at = au.on_gun(a0, p0, base + out * mag_out)
        landed = rel + ((drop_at.real - GROUND) * 2 / GRAVITY) ** .5

        def frame(t, arm=arm, gun=gun, other=other, marker=marker, drop_at=drop_at, landed=landed):
            a, p = gun(t)
            if t < rel:
                mag = out * mag_out * ease(t, max(0, rel - .1), rel)
            elif t < landed:
                dt = t - rel
                world = drop_at - .5 * GRAVITY * dt * dt
                mag = (world - a) / (direction(p) * au.gpx) - base
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
        slots = {marker: {"attachment": [{"name": "magazine"}, {"time": round(landed, 4), "name": None},
                                         {"time": round(t_line, 4), "name": "magazine"}]}}
        au.clip("pair-%s-%sreload" % (side, P), D, frame, [(rel, prefix + "unloaded"), (seat_t, prefix + "loaded")],
                slots, markers=("pair-magazine-left", "pair-magazine-right"))

        def rack(t, arm=arm, own=own, other=other, rack_at=rack_at):
            press = complex(-.7, 0) * ease(t, event, back) * (1 - ease(t, fwd, fwd + .06))
            f = ease(t, fwd + .06, F)
            a, p = lerp(rack_at, own[0], f) + press, lerp(RACK_PITCH, own[1], f)
            lift = 1 - f
            oa, op = other[0] + complex(.8, .6) * lift, other[1] + 6 * lift
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {}

        au.clip("pair-%s-%srack" % (side, P), F, rack, [(event, prefix + "sa-rack")],
                markers=("pair-magazine-left", "pair-magazine-right"))


def actions(item):
    comps = item["components"]
    acts = next((c for c in comps if c.get("class", "").endswith("InstrumentActionsComponent")), None)
    if acts is None:
        acts = {"class": "content.components.InstrumentActionsComponent", "tag": "client", "actions": []}
        comps.append(acts)
    acts["actions"] = [a for a in acts.get("actions", []) if a.get("for") not in
                       ("sa-rack", "sa-cycle", "sa-open", "sa-close")] + [
        {"for": "sa-rack", "type": "animate", "animation": "rack"},
        {"for": "sa-cycle", "type": "animate", "animation": "cycle"},
        {"for": "sa-open", "type": "animate", "animation": "open"},
        {"for": "sa-close", "type": "animate", "animation": "close"}]


def content_changes(content, wid, T, geo):
    rel, seat, back, fwd, D, F = T
    if geo.get("fixed_mag"):
        F = 0          # the bolt is worked during the reload itself: no separate chambering
    item = content["weapon-" + wid]
    item["primary"]["reloadTime"] = D
    item["primary"]["fetchTime"] = F
    actions(item)
    pair = content.get("paired-weapon-" + wid)
    if pair:
        pair["primary"]["reloadTime"] = D
        pair["primary"]["fetchTime"] = F
        for comp in pair["components"]:
            if comp.get("class", "").endswith("SecondaryWeaponSlotComponent"):
                comp["properties"]["reloadTime"] = D
                comp["properties"]["fetchTime"] = F
        actions(pair)
        states = next(c for c in pair["components"] if "states" in c and "animation" in c)["states"]
        P = "sa-%s-" % wid
        states.update(hold=P + "akimbo", aim=P + "akimbo", hit=P + "akimbo-hit", aimHit=P + "akimbo-hit",
                      reload=P + "reload", fetch=P + "rack")


def build(source, destination):
    geometry = json.loads(GEOMETRY.read_text())
    with ZipFile(source) as src:
        names = src.namelist()
        changes = {}
        content = json.loads(src.read("content.json"))
        c = content["content"]
        timing = {wid: timings(wid, c["weapon-" + wid], geometry.get(wid)) for wid in FAMILY if "weapon-" + wid in c}
        actor = json.loads(src.read(ACTOR)) if ACTOR in names else None
        setup = {b["name"]: b for b in actor["bones"]} if actor else None
        for wid, T in timing.items():
            geo = geometry[wid]
            item = c["weapon-" + wid]
            comp, path = animation_path(c, item)
            states = dict(comp["states"])
            if path in names and actor is not None:
                model = json.loads(src.read(path))
                gun, travel = model_changes(model, wid, geo)
                changes[path] = encode(model)
                pair = c.get("paired-weapon-" + wid)
                if pair:
                    _, ppath = animation_path(c, pair)
                    if ppath in names:
                        pmodel = json.loads(src.read(ppath))
                        model_changes(pmodel, wid, geo)
                        changes[ppath] = encode(pmodel)
                gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
                add_hand_magazine(actor, setup, wid, geo, gun, gpx)
                au = Author(actor, gun, gpx)
                solo_clips(au, wid, states, geo, travel, T)
                if pair:
                    akimbo_clips(au, wid, geo, T)
            content_changes(c, wid, T, geo)
        if actor is not None:
            sidearms_front.build(names, src.read, c, actor, setup, changes, encode, animation_path)
            sidearms_special.build(names, src.read, c, actor, setup, changes, encode)
        changes["content.json"] = encode(content)
        if actor is not None:
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
