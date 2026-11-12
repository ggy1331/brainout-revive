"""The odd secondaries: Super Shorty (pump shotgun), Welrod (the grip is the magazine, bolt
action) and the M98k sawn-off (now a conversion of the rifle). Called from sidearms.build after
sidearms_front; reuses its clip authoring.

Super Shorty
  pistol grip + the support fist under the pump; the pump is its own bone (holder slot) with a
  "pump" animation. Reload is per shell (the game replays the reload state for every round):
  a shell from the belt, pushed up into the loading port under the receiver, timed to the
  spas12-reload click. Fetch = the pump back and forward with the m1897-pull sound; the
  unfolded foregrip upgrade swaps in "pull-shotgun-underbarrel-2-fast".
  Akimbo: the loading port is pressed down onto a shell standing in the belt carrier, the pump
  is worked against the belt edge.
Welrod
  the Colt approach: grip-magazine pulled down, pouch, fresh one, pushed in, the hand ends on the
  bolt knob at the rear; fetch (after every shot) = the knob pulled back. The fetch sound is fired
  by a clip event so it matches the hand (it used to start with the fetch state). The matte skin
  has its own reload clip (the grip in the hand is matte).
M98k sawn-off
  like the Mosin obrez: no separate secondary any more, a "conversion" upgrade of the M98k
  (primary slot, the rifle's arm animations).
"""
from copy import deepcopy
import json

from math import acos, degrees

from pair_refinement import ARMS, direction, angle, offset
from colt1911 import Author, world_scale, lerp, ease, straight, eye_line, RACK_PITCH, GRAVITY
import sidearms_front as front

PISTOL = dict(hold=(complex(-1.4, -7.4), -89.5), aim=(complex(.5, -10.8), -88.0), work=(complex(-1.42, -7.6), -61.5))

# points in root units of each weapon skeleton (before the grip shift)
SHORTY = dict(grip=(-2, -3), sight=17.5, support=((43, 8.0), -38), foregrip=((58, -1), 112),
              port=(31, 9), pump=7, shell="sa-shell-12", forend=(47, 9.5))
PAIR_GRIP = (3.5, 3.8)      # akimbo: the fist at the top of the grip, under the receiver, by the trigger
FLIP_T = .9              # akimbo pump (one-handed flip): its own fetch time
FLIP_SND = .33           # the pump sound is fired by the clip: back at +.13, forward at +.31
SHELL_TURN = -116.0      # akimbo: the loading fist relative to the loaded gun: its own gun hangs straight down
SHELL_IN = .49           # spas12-reload-1/2: the shell clicks in
PUMP_EVENT = .05         # m1897-pull: pump back ~.13, forward ~.31
WELROD = dict(grip=(.5, -1), axis=75, sight=14, support=((10, 5), 70), rack=((-11, 10), 7), grab=(-1.8, -7),
              **PISTOL)
WELROD_T = (.31, .95, .2, .36)  # colt-reload: release, seated; bolt back / forward (sound fired at .12)
WELROD_SND = .12


def spline(keys, t):
    """Catmull-Rom through (time, value) keys (values complex or float): no stop at every key."""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    i = max(j for j, k in enumerate(keys[:-1]) if k[0] <= t)
    t0, p1 = keys[i]
    t1, p2 = keys[i + 1]
    p0 = keys[i - 1][1] if i > 0 else p1
    p3 = keys[i + 2][1] if i + 2 < len(keys) else p2
    u = (t - t0) / max(1e-6, t1 - t0)
    u2, u3 = u * u, u * u * u
    return .5 * (2 * p1 + (p2 - p0) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (3 * p1 - p0 - 3 * p2 + p3) * u3)


def near(angle, ref):
    """The same direction as `angle`, the short way round from `ref` (no full spins of the fist)."""
    return ref + (angle - ref + 180) % 360 - 180


def forearm(au, arm, point):
    """The world angle of the hand bone's parent when the fist is at `point` (the arm IK of
    paired_reload_art.solve, without the wrist)."""
    upper, palm, holder = [au.setup[n] for n in arm]
    origin = offset(upper) + offset(au.carry[arm[0]]["translate"][0])
    delta = (point - origin) / upper.get("scaleX", 1)
    a, b = abs(offset(palm)), abs(offset(holder))
    elbow = degrees(acos(max(-.94, min(.995, (abs(delta) ** 2 - a * a - b * b) / (2 * a * b)))))
    first = angle(delta) - angle(a + b * direction(elbow)) - angle(offset(palm))
    return first + angle(offset(palm)) + elbow - angle(offset(holder)) + holder.get("rotation", 0)


def wrist(au, arm, point, pitch):
    """How far the hand (and the gun in it) is bent from the forearm in a pose."""
    return pitch - forearm(au, arm, point)


def natural(au, arm, point, bend):
    """The gun angle for a fist at `point` with the wrist kept as in a normal hold: the gun turns
    only with the arm, never on its own in the hand."""
    return bend + forearm(au, arm, point)


class RootGun:
    sx = sy = 1

    def __init__(self, grip):
        self.grip = complex(*grip)

    def at(self, xy):
        return complex(*xy) - self.grip


def regrip(model, grip):
    """The fist holds `grip`: everything on the root moves under a shifted "grip" bone
    (an existing one - the Welrod has it for its magazine - is reused)."""
    bones = model["bones"]
    root = bones[0]["name"]
    g = next((b for b in bones if b["name"] == "grip"), None)
    if g is None:
        g = {"name": "grip", "parent": root}
    else:
        bones.remove(g)
    bones.insert(1, g)                                   # parents come before children
    g["parent"], g["x"], g["y"] = root, -grip[0], -grip[1]
    for b in bones[2:]:
        if b.get("parent") == root:
            b["parent"] = "grip"
    for s in model["slots"]:
        if s["bone"] == root:
            s["bone"] = "grip"


def animation_of(content, item):
    comp = next(c for c in item["components"] if "states" in c and "animation" in c)
    return comp, "content/" + content[comp["animation"]]["animation"].split(":")[1]


def add_action(item, action):
    comps = item["components"]
    acts = next((c for c in comps if c.get("class", "").endswith("InstrumentActionsComponent")), None)
    if acts is None:
        acts = {"class": "content.components.InstrumentActionsComponent", "tag": "client", "actions": []}
        comps.append(acts)
    acts["actions"] = [a for a in acts.get("actions", []) if a.get("for") != action["for"]] + [action]


def add_events(au, name, events):
    clip = au.clips[name]
    clip["events"] = sorted(clip.get("events", []) + [
        {"time": round(t, 5), "name": "instrument-action", "string": s} for t, s in events], key=lambda e: e["time"])


def akimbo_poses(au):
    return (straight(au, ARMS[0], -.2), -89.0), (straight(au, ARMS[1], -.8), -89.0)


def other_lift(other, k):
    return other[0] + complex(.8, .6) * k, other[1] + 6 * k


# --- M98k sawn-off ---------------------------------------------------------------------------
def m98k_conversion(c, clips):
    old, base = "sl-sec-m98kobrez", "sl-pri-m98k"
    if old not in c or base not in c or "weapon-m98kobrez" not in c:
        return
    c["conversion-m98kobrez"] = {
        "class": "content.upgrades.Upgrade", "access": "byDefault", "name": c[old]["name"], "properties": {},
        "conversion": "weapon-m98kobrez", "components": [
            {"class": "content.components.IconComponent", "tag": "client",
             "icon": "m98kobrez-skin", "big-icon": "m98kobrez-skin"}]}
    for key in (old, old + "-slot2", "sl-pair-m98kobrez"):
        if key in c:
            c[key]["enabled"] = False
    for suffix in ("", "-slot2"):
        if base + suffix in c:
            c[base + suffix]["instrument"].setdefault("upgrades", {})["conversion"] = "conversion-m98kobrez"
    obrez, rifle = c["weapon-m98kobrez"], c["weapon-m98k"]
    obrez["slot"], obrez["instrumentTags"] = "slot-primary", "primary"
    have = {x.get("class") for x in obrez["components"]}
    for comp in rifle["components"]:
        if comp.get("class", "").endswith(("WeaponDurabilityComponent", "InstrumentBeltComponent")) \
                and comp["class"] not in have:
            obrez["components"].append(deepcopy(comp))
    animation_of(c, obrez)[0]["states"] = deepcopy(animation_of(c, rifle)[0]["states"])
    for name in [k for k in clips if "m98kobrez" in k]:
        del clips[name]                      # the pistol-style poses: the rifle's arms take over


# --- Super Shorty -----------------------------------------------------------------------------
def shorty_model(model, grip=None):
    regrip(model, grip or SHORTY["grip"])
    if not any(b["name"] == "sa-pump" for b in model["bones"]):
        model["bones"].append({"name": "sa-pump", "parent": "grip"})
    slots = model["slots"]
    holder = next(s for s in slots if s["name"] == "holder")
    holder["bone"] = "sa-pump"
    if not any(s["name"] == "sa-barrel" for s in slots):
        slots.insert(slots.index(holder), {"name": "sa-barrel", "bone": "grip", "attachment": "barrel"})
    for skin in model["skins"]:
        atts = skin.get("attachments", {})
        h = atts.get("holder", {})
        if "off" in h:
            atts["sa-barrel"] = {"barrel": dict(h["off"], name="sa-shorty-barrel", path="sa-shorty-barrel")}
        for state in ("off", "on"):
            if state in h and not h[state].get("path", "").startswith("sa-"):
                h[state] = dict(h[state], name="sa-shorty-pump-" + state, path="sa-shorty-pump-" + state)
    travel = SHORTY["pump"]
    anims = model.setdefault("animations", {})
    anims["pump"] = {"bones": {"sa-pump": {"translate": [
        {"time": 0}, {"time": .08, "x": -travel}, {"time": .2, "x": -travel}, {"time": .26}]}}}


def flip_pump(t):
    """The pump back at FLIP_SND + .13 and home at + .31, like the m1897-pull sound (0..1)."""
    return ease(t, FLIP_SND + .07, FLIP_SND + .13) * (1 - ease(t, FLIP_SND + .25, FLIP_SND + .31))


def pump_offset(t):
    u = t - PUMP_EVENT
    return ease(u, 0, .08) * (1 - ease(u, .2, .26))


def shorty_shell(actor, setup, gpx):
    default = next(s for s in actor["skins"] if s["name"] == "default")
    atts = default["attachments"]
    k = gpx / world_scale(setup, ("hand2", "palm2", "holder-secondary"))
    pos = direction(-20) * 2.0 * k                     # held by the brass, lying along the gun
    atts.setdefault("sa-mag-hand", {})[SHORTY["shell"]] = {
        "name": SHORTY["shell"], "path": SHORTY["shell"], "x": round(pos.real, 3), "y": round(pos.imag, 3),
        "rotation": -20, "scaleX": round(k, 4), "scaleY": round(k, 4), "width": 7, "height": 3}
    # akimbo: the free fist (its own gun hanging down) pushes a shell into the other gun's port;
    # the shell lies along the loaded gun, a bit forward of and above the fist
    if "sa-shell-hold1" not in setup:
        actor["bones"].append({"name": "sa-shell-hold1", "parent": "holder-primary"})
        setup["sa-shell-hold1"] = actor["bones"][-1]
    names = [s["name"] for s in actor["slots"]]
    if "sa-shell-hand1" not in names:
        actor["slots"].insert(names.index("gpalm1") + 1, {"name": "sa-shell-hand1", "bone": "sa-shell-hold1"})
    for slot, arm in (("sa-mag-hand", ("hand2", "palm2", "holder-secondary")),
                      ("sa-shell-hand1", ("hand1", "palm1", "holder-primary"))):
        ws = world_scale(setup, arm)
        local = complex(1.6, .5) * direction(-SHELL_TURN) / ws
        atts.setdefault(slot, {})[SHORTY["shell"] + "-turned"] = {
            "name": SHORTY["shell"], "path": SHORTY["shell"], "x": round(local.real, 3), "y": round(local.imag, 3),
            "rotation": -SHELL_TURN, "scaleX": round(gpx / ws, 4), "scaleY": round(gpx / ws, 4),
            "width": 7, "height": 3}


def shorty_solo(au, states, D, F, F_fast):
    g = au.gun
    sp, sa = SHORTY["support"]
    support = g.at(sp)
    fp, fa = SHORTY["foregrip"]
    foregrip = g.at(fp)
    port = g.at(SHORTY["port"])
    hold = front.fit(au, front.HOLD, [support])
    aim = front.fit(au, eye_line(au, front.HOLD[0], g.at((0, SHORTY["sight"]))), [support])
    work = front.fit(au, front.WORK, [port, port + complex(-1, -4)])
    W = "solo-weapon-supershorty-"

    def two(a, p):
        return (a, p), (au.on_gun(a, p, support), p + sa)

    def shot(a0, p0):
        def frame(t):
            k = ease(t, 0, .03) * (1 - ease(t, .03, .12))
            return (*two(a0 + complex(.5, .6) * k, p0 + 10 * k), {})
        return frame

    for state, fn, d in (("hold", lambda t: (*two(*hold), {}), .08), ("aim", lambda t: (*two(*aim), {}), .08),
                         ("hit", shot(*hold), .12), ("aimHit", shot(*aim), .12)):
        if states.get(state):
            au.clip(W + states[state], d, fn)

    a_w, p_w = work
    on = lambda q: au.on_gun(a_w, p_w, q)
    up = p_w + 20                                      # fist under the port, shell along the gun
    belt = near(front.POUCH_ANGLE, up)
    ready = port + complex(-1, -4)
    hand_keys = [(0, on(ready)), (.16, front.POUCH), (.24, front.POUCH + complex(-.6, 0)),
                 (SHELL_IN - .08, on(port + complex(0, -4))), (SHELL_IN, on(port)),
                 (SHELL_IN + .07, on(port + complex(3, 0))), (D, on(ready))]
    ang_keys = [(0, up), (.16, belt), (.24, belt), (SHELL_IN - .08, up), (D, up)]

    def reload(t):
        return (a_w, p_w), (spline(hand_keys, t), spline(ang_keys, t)), {}

    if states.get("reload"):
        au.clip(W + states["reload"], D, reload, [(SHELL_IN, "add-bullet")], {
            "sa-mag-hand": {"attachment": [{"name": None}, {"time": .2, "name": SHORTY["shell"]},
                                           {"time": round(SHELL_IN + .02, 4), "name": None}]}})

    def pump(point, angle, d, pose=None):
        pose = pose or front.fit(au, front.HOLD, [point, point - SHORTY["pump"]])

        def frame(t):
            a, p = pose
            s = au.on_gun(a, p, point - SHORTY["pump"] * pump_offset(t))
            return (a, p), (s, p + angle), {}
        return frame

    if states.get("fetch"):
        au.clip(W + states["fetch"], F, pump(support, sa, F, hold), [(PUMP_EVENT, "sa-pump")])
        # unfolded foregrip (upgrade): a faster pump on the vertical grip
        au.clip(W + states["fetch"] + "-fast", F_fast, pump(foregrip, fa, F_fast), [(PUMP_EVENT, "sa-pump")])


FLIP_COM = (25, 8)       # the shotgun's centre of mass (root units): what flies on a parabola


def flip_motion(au, arm, own):
    """One-handed pump, akimbo: (frame(t) -> fist pose, weapon animation).

    Held, the gun moves rigidly with the fist. A flick of the wrist throws it up; in the air its
    centre of mass flies on a parabola (gravity) and it turns at a constant rate while the fist
    goes for the pump and catches it, muzzle up, the receiver hanging under it. A jerk down and
    up of the fist: the heavy receiver lags and works the pump. Another flick, flight, and the
    fist catches the grip again, back to the aim. The fist is the attachment point of the gun, so
    the weapon animation moves and turns the gun in the fist (grip bone) by the difference."""
    a0, p0 = own
    gp = au.gpx
    hand = ARMS[arm]
    grip_v = au.gun.grip                            # the akimbo grip (PAIR_GRIP)
    fs = complex(*SHORTY["forend"]) - grip_v
    ms = complex(*FLIP_COM) - grip_v
    travel = SHORTY["pump"]
    t_r1, t_c1, t_r2, t_c2 = .14, .3, .7, .82
    bend = wrist(au, hand, a0, p0)

    def nat(point, extra=0.0):
        return near(natural(au, hand, point, bend) + extra, p0)

    # 1. on the grip: a small dip, then the flick (up and turning the muzzle up)
    held_a = [(0, a0, p0), (.07, a0 + complex(-.4, .2), p0 - 8), (t_r1, a0 + complex(1.0, .5), p0 + 40)]
    # caught by the pump, muzzle up a little forward
    h_c1 = a0 + complex(.5, 1.5)
    pg_c1 = -22.0
    turn_c = near(nat(h_c1, 25), pg_c1) - pg_c1          # how the gun sits in the fist on the pump
    # 3. on the pump: settle under the weight, jerk down, hold, jerk up, the flick back
    snd = FLIP_SND
    held_c = [(t_c1, h_c1), (.36, h_c1 + complex(-.25, .05)), (snd + .07, h_c1 + complex(.15, 0)),
              (snd + .13, h_c1 + complex(-1.4, .15)), (snd + .25, h_c1 + complex(-1.3, .15)),
              (snd + .31, h_c1 + complex(.1, 0)), (t_r2, h_c1 + complex(.9, -.3))]
    flick_c = [(t_c1, 0.0), (snd + .31, 0.0), (t_r2, -18.0)]
    # 5. caught by the grip, back to the aim
    h_c2, pg_c2 = a0 + complex(.5, .4), p0 + 14
    held_e = [(t_c2, h_c2, pg_c2), (FLIP_T, a0, p0)]

    def rigid_a(t):
        h = spline([(k[0], k[1]) for k in held_a], t)
        pg = spline([(k[0], k[2]) for k in held_a], t)
        return h, pg, h, pg                               # fist on the grip: gun = fist

    def rigid_c(t):
        h = spline(held_c, t)
        hp = nat(h, 25) + spline(flick_c, t)
        pg = hp - turn_c
        g = h - direction(pg) * fs * gp + direction(pg) * travel * flip_pump(t) * gp
        return h, hp, g, pg

    def rigid_e(t):
        h = spline([(k[0], k[1]) for k in held_e], t)
        pg = spline([(k[0], k[2]) for k in held_e], t)
        return h, pg, h, pg

    def flight(t, t0, t1, start, end):
        """The gun between release and catch: centre of mass on a parabola, constant spin."""
        _, _, g0, pg0 = start(t0)
        hc, hpc, g1, pg1 = end(t1)
        pg1 = near(pg1, pg0)
        c0 = g0 + direction(pg0) * ms * gp
        c1 = g1 + direction(pg1) * ms * gp
        T = t1 - t0
        fall = complex(-GRAVITY, 0)                       # hands space: x is up
        v = (c1 - c0 - .5 * fall * T * T) / T
        u = t - t0
        f = u / T
        pg = pg0 + (pg1 - pg0) * f
        com = c0 + v * u + .5 * fall * u * u
        g = com - direction(pg) * ms * gp
        # the fist goes from where it let go to where it catches
        hs, hps, _, _ = start(t0)
        k = ease(t, t0, t1)
        h = lerp(hs, hc, k)
        hp = lerp(hps, near(hpc, hps), k)
        return h, hp, g, pg

    def state(t):
        if t <= t_r1:
            return rigid_a(t)
        if t < t_c1:
            return flight(t, t_r1, t_c1, rigid_a, rigid_c)
        if t <= t_r2:
            return rigid_c(t)
        if t < t_c2:
            return flight(t, t_r2, t_c2, rigid_c, rigid_e)
        return rigid_e(t)

    grip_keys, rot_keys, pump_keys = [], [], []
    prev = 0.0
    for i in range(int(FLIP_T * 30) + 1):
        t = min(FLIP_T, i / 30)
        h, hp, g, pg = state(t)
        r = near(pg - hp, prev)
        prev = r
        rel = (g - h) / (direction(hp) * gp)              # the grip point in the fist's root space
        delta = rel + grip_v - direction(r) * grip_v
        grip_keys.append({"time": round(t, 4), "x": round(delta.real, 3), "y": round(delta.imag, 3)})
        rot_keys.append({"time": round(t, 4), "value": round(r, 2)})
        pump_keys.append({"time": round(t, 4), "x": round(-travel * flip_pump(t), 3)})
    anim = {"bones": {"grip": {"translate": grip_keys, "rotate": rot_keys}, "sa-pump": {"translate": pump_keys}}}
    return (lambda t: state(t)[:2]), anim


def shorty_akimbo(au, D, F, fast_name):
    g = au.gun
    port = g.at(SHORTY["port"])
    aim = akimbo_poses(au)
    P = "sa-supershorty-"
    au.clip(P + "akimbo", .08, lambda t: (aim[0], aim[1], {}))

    def hit(t):
        k = ease(t, 0, .03) * (1 - ease(t, .03, .12))
        return tuple((a + complex(.4, .5) * k, p + 9 * k) for a, p in aim) + ({},)

    au.clip(P + "akimbo-hit", .1, hit)
    markers = ("pair-magazine-left", "pair-magazine-right")
    pouches = complex(-8.8, -3.0), complex(-8.6, -3.6)
    anims = {}
    for arm in (0, 1):
        own, other = aim[arm], aim[1 - arm]
        prefix = "" if arm == 0 else "offhand/"
        side = "left" if arm == 0 else "right"
        # the loaded gun held at the chest, muzzle up, its port turned to the other hand
        load_a, load_p = (complex(-2.6, -8.6) if arm == 0 else complex(-2.8, -9.4)), -64.0
        port_w = au.on_gun(load_a, load_p, port)
        below, forward = direction(load_p - 90), direction(load_p)
        turned = load_p + SHELL_TURN
        ready = port_w + below * 1.6 - forward * .6
        pouch = pouches[1 - arm]
        t_turn = lambda p, v=turned: v
        t_pouch = lambda p: front.POUCH_ANGLE
        path = front.Path([
            (0, ("world", ready), t_turn, 0),
            (.16, ("world", pouch), t_pouch, 0),
            (.24, ("world", pouch + complex(-.6, 0)), t_pouch, 0),
            (SHELL_IN - .08, ("world", port_w + below * 1.0), t_turn, 0),
            (SHELL_IN, ("world", port_w + below * .25), t_turn, 0),
            (SHELL_IN + .07, ("world", port_w + below * .25 + forward * .8), t_turn, 0),
            (D, ("world", ready), t_turn, 0)])

        hand_keys = [(0, ready), (.16, pouch), (.24, pouch + complex(-.6, 0)), (SHELL_IN - .08, port_w + below * 1.0),
                     (SHELL_IN, port_w + below * .25), (SHELL_IN + .07, port_w + below * .25 + forward * .8), (D, ready)]
        loader = ARMS[1 - arm]
        bend = wrist(au, loader, *aim[1 - arm])      # the wrist as in the akimbo hold

        def frame(t, arm=arm, hand_keys=hand_keys, load_a=load_a, load_p=load_p, loader=loader, bend=bend):
            s = spline(hand_keys, t)
            ang = natural(au, loader, s, bend)
            poses = [(load_a, load_p), (s, ang)]
            if arm == 1:
                poses.reverse()
            return poses[0], poses[1], {}

        shell_slot = "sa-mag-hand" if arm == 0 else "sa-shell-hand1"
        # the shell in that fist: along the loaded gun, half into the port, when it is pushed in
        hand_in = port_w + below * .25
        pitch_in = natural(au, loader, hand_in, bend)
        ws = world_scale(au.setup, loader)
        local = (port_w + forward * .7 - hand_in) * direction(-pitch_in) / ws
        default = next(sk for sk in au.actor["skins"] if sk["name"] == "default")
        default["attachments"].setdefault(shell_slot, {})[SHORTY["shell"] + "-turned"] = {
            "name": SHORTY["shell"], "path": SHORTY["shell"], "x": round(local.real, 3), "y": round(local.imag, 3),
            "rotation": round(load_p - pitch_in, 2), "scaleX": round(au.gpx / ws, 4), "scaleY": round(au.gpx / ws, 4),
            "width": 7, "height": 3}
        au.clip("pair-%s-%sreload" % (side, P), D, frame, [(SHELL_IN, prefix + "add-bullet")], {
            shell_slot: {"attachment": [{"name": None}, {"time": .2, "name": SHORTY["shell"] + "-turned"},
                                        {"time": round(SHELL_IN + .02, 4), "name": None}]}}, markers=markers)

        motion, anims["flip-" + side] = flip_motion(au, arm, own)

        def rack(t, other=other, arm=arm, motion=motion):
            a, p = motion(t)
            oa, op = other_lift(other, ease(t, 0, .2) * (1 - ease(t, F - .15, F)))
            poses = [(a, p), (oa, op)] if arm == 0 else [(oa, op), (a, p)]
            return poses[0], poses[1], {}

        au.clip("pair-%s-%srack" % (side, P), F, rack, [(0, prefix + "sa-flip-" + side), (FLIP_SND, prefix + "sa-pump-snd")],
                markers=markers)
        au.clips["pair-%s-%s" % (side, fast_name)] = deepcopy(au.clips["pair-%s-%srack" % (side, P)])
    return anims


def shorty(c, names, read, changes, encode, actor, setup):
    item = c.get("weapon-supershorty")
    if item is None:
        return
    comp, path = animation_of(c, item)
    if path not in names:
        return
    model = json.loads(read(path))
    shorty_model(model)
    changes[path] = encode(model)
    states = dict(comp["states"])
    for weapon in (item, c.get("paired-weapon-supershorty")):
        if weapon:
            weapon["primary"]["clipSize"] = 3              # was 2
            for comp in weapon["components"]:
                if comp.get("class", "").endswith("SecondaryWeaponSlotComponent"):
                    comp["properties"]["clipSize"] = 3
    D = item["primary"].get("reloadTime", .75)
    F = item["primary"].get("fetchTime", .6)
    gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
    au = Author(actor, RootGun(SHORTY["grip"]), gpx)
    shorty_shell(actor, setup, gpx)
    shorty_solo(au, states, D, F, .32)
    add_action(item, {"for": "sa-pump", "type": "animate", "animation": "pump"})
    pair = c.get("paired-weapon-supershorty")
    if pair:
        pcomp, ppath = animation_of(c, pair)
        # akimbo: one hand only, so it holds high on the grip, the finger on the trigger
        pau = Author(actor, RootGun(PAIR_GRIP), gpx)
        flips = shorty_akimbo(pau, D, FLIP_T, states.get("fetch", "pull-shotgun-underbarrel-2") + "-fast")
        if ppath in names:
            pmodel = json.loads(read(ppath))
            shorty_model(pmodel, PAIR_GRIP)
            pmodel["animations"].update(flips)
            changes[ppath] = encode(pmodel)
        add_action(pair, {"for": "sa-pump", "type": "animate", "animation": "pump"})
        for side in ("left", "right"):
            add_action(pair, {"for": "sa-flip-" + side, "type": "animate", "animation": "flip-" + side})
        for comp in pair["components"]:
            if comp.get("class", "").endswith("InstrumentEffectsComponent"):
                sound = comp.get("fetch")
                if sound:
                    add_action(pair, {"for": "sa-pump-snd", "type": "effect", "effects": deepcopy(sound)})
                comp["fetch"], comp["fetchSecondary"] = [], []
            if comp.get("class", "").endswith("SecondaryWeaponSlotComponent"):
                comp["properties"]["fetchTime"] = FLIP_T
        pair["primary"]["fetchTime"] = FLIP_T
        P = "sa-supershorty-"
        pcomp["states"].update(hold=P + "akimbo", aim=P + "akimbo", hit=P + "akimbo-hit", aimHit=P + "akimbo-hit",
                               reload=P + "reload", fetch=P + "rack")


# --- Welrod -----------------------------------------------------------------------------------
def welrod_model(model):
    regrip(model, WELROD["grip"])
    model.setdefault("animations", {})["cycle"] = {"bones": {"bolt": {"translate": [
        {"time": 0}, {"time": .08, "x": -WELROD["rack"][1]}, {"time": .2, "x": -WELROD["rack"][1]},
        {"time": .25}]}}}


def welrod_sound(item):
    for comp in item["components"]:
        if comp.get("class", "").endswith("InstrumentEffectsComponent"):
            for key in ("fetch", "fetchSecondary"):
                if key in comp:
                    comp[key] = []
    add_action(item, {"for": "welrod-fetch-snd", "type": "effect", "effects": "colt-fetch"})


def welrod(c, names, read, changes, encode, actor, setup):
    item = c.get("weapon-welrod")
    if item is None:
        return
    comp, path = animation_of(c, item)
    if path not in names:
        return
    model = json.loads(read(path))
    grips = {s["name"]: s["attachments"].get("grip", {}).get("default") for s in model["skins"]}
    welrod_model(model)
    changes[path] = encode(model)
    gun = RootGun(WELROD["grip"])
    gpx = world_scale(setup, ("hand1", "palm1", "holder-primary")) * model["bones"][0].get("scaleX", 1)
    grab = gun.at(WELROD["grab"])
    top = gun.at((1, 4))
    f = dict(WELROD, mag_out=abs(top - grab) + 1, hand="fm-welrod")
    for skin, name in (("weapon-blued", "fm-welrod"), ("weapon-matte", "fm-welrod-matte")):
        att = grips.get(skin)
        if att:
            centre = complex(att["x"], att["y"]) - gun.grip
            front.add_hand_magazine(actor, setup, "welrod", f, att, centre, grab, gpx, name=name)
    D = round(max(item["primary"].get("reloadTime", 1.65), WELROD_T[1] + .3), 3)
    F = round(max(item["primary"].get("fetchTime", .67), WELROD_T[3] + .35), 3)
    T = (*WELROD_T, D, F)
    au = Author(actor, gun, gpx)
    states = dict(comp["states"])
    front.solo_clips(au, "welrod", states, f, T, grab, None)
    W = "solo-weapon-welrod-"
    if states.get("fetch"):
        add_events(au, W + states["fetch"], [(WELROD_SND, "welrod-fetch-snd"), (WELROD_SND, "welrod-cycle")])
    if states.get("reload"):
        matte = deepcopy(au.clips[W + states["reload"]])
        for key in matte.get("slots", {}).get("sa-mag-hand", {}).get("attachment", []):
            if key.get("name") == "fm-welrod":
                key["name"] = "fm-welrod-matte"
        au.clips[W + "welrod-reload-matte"] = matte
    front.content_changes(item, T)
    welrod_sound(item)
    pair = c.get("paired-weapon-welrod")
    if pair:
        pcomp, ppath = animation_of(c, pair)
        if ppath in names and ppath != path:
            pmodel = json.loads(read(ppath))
            welrod_model(pmodel)
            changes[ppath] = encode(pmodel)
        front.akimbo_clips(au, "welrod", f, T, grab)
        front.pair_changes(pair, "welrod", T)
        welrod_sound(pair)
        for side, prefix in (("left", ""), ("right", "offhand/")):
            add_events(au, "pair-%s-sa-welrod-rack" % side,
                       [(WELROD_SND, prefix + "welrod-fetch-snd"), (WELROD_SND, prefix + "welrod-cycle")])
            au.clips["pair-%s-welrod-reload-matte" % side] = deepcopy(au.clips["pair-%s-sa-welrod-reload" % side])


BUCKSHOT_PELLETS = 9      # was 6; the weapon's damage is now for all pellets together (BulletData.getDamage)


def buckshot(c):
    shell = c.get("bullet-12-76")
    if shell:
        shell["bulletAtLaunch"] = BUCKSHOT_PELLETS


def build(names, read, content, actor, setup, changes, encode):
    buckshot(content)
    m98k_conversion(content, actor["animations"])
    shorty(content, names, read, changes, encode, actor, setup)
    welrod(content, names, read, changes, encode, actor, setup)
