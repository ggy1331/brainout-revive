"""Author lower-body transition clips on the original BrainOut actor rig."""
from copy import deepcopy

def add_stance_clips(actor):
    animations = actor["animations"]
    stand = animations["stay"]["bones"]
    sit = animations["sit"]["bones"]
    prone = animations["crouch"]["bones"]

    def pose(base, angles, positions):
        bones = deepcopy(base)
        for name, angle in angles.items():
            bones.setdefault(name, {})["rotate"] = [{"value": angle}]
        for name, (x, y) in positions.items():
            bones.setdefault(name, {})["translate"] = [{"x": x, "y": y}]
        return bones

    # Raise the chest first. The back leg stays extended while the near knee comes underneath.
    brace = pose(prone, {"root":-71, "root-hands":55, "head-root":66,
        "leg1":45, "knee1":-57, "leg2":-6, "knee2":-12,
        "foot1":-18, "foot2":-8}, {"root":(5.4,-6.4),"root-hands":(-0.6,1.3)})
    # Plant the leading foot, bring the hips over it, then extend the knees.
    kneel = pose(sit, {"root":-40,"root-hands":26,"head-root":34,
        "leg1":77,"knee1":-122,"leg2":6,"knee2":-68,"foot1":22,"foot2":28},
        {"root":(3.5,-5.7),"head-root":(0.4,0.8)})
    lift = pose(sit, {"root":-15,"root-hands":11,"head-root":13,
        "leg1":36,"knee1":-77,"leg2":40,"knee2":-50,"foot1":12,"foot2":3},
        {"root":(1.1,-2.8)})
    routes = [
        ("prone","stand",[(0,prone),(.13,brace),(.32,kneel),(.49,lift),(.66,stand)]),
        ("prone","sit",[(0,prone),(.12,brace),(.31,kneel),(.47,sit)]),
        ("sit","stand",[(0,sit),(.11,lift),(.26,stand)])]
    clips = {}
    for start,end,frames in routes:
        duration = frames[-1][0]
        clips["stance-"+start+"-"+end] = frames
        clips["stance-"+end+"-"+start] = [(round(duration-t,3),p) for t,p in reversed(frames)]

    push = pose(stand, {"root":-23,"root-hands":16,"head-root":17,
        "leg1":42,"knee1":-71,"leg2":-14,"knee2":5}, {"root":(0.6,-1.4)})
    flight = pose(prone, {"root":-76,"root-hands":68,"head-root":74,
        "leg1":8,"knee1":-18,"leg2":-11,"knee2":-29,"foot1":-14,"foot2":14},
        {"root":(4.7,-3.6)})
    clips["dolphin-dive"] = [(0,stand),(.06,push),(.19,flight),(.32,prone)]

    # slide (Ctrl while running): leaning back on the hip, the near leg stretched forward, the far
    # one folded under; root-hands / head-root turn back by the lean, so the gun stays level
    slide = pose(stand, {"root":30,"root-hands":-30,"head-root":-22,
        "leg1":40,"knee1":35,"foot1":-15,"leg2":70,"knee2":-120}, {"root":(0,-15.5)})
    drop = pose(stand, {"root":12,"root-hands":-12,"head-root":-8,
        "leg1":30,"knee1":10,"foot1":-10,"leg2":55,"knee2":-105}, {"root":(0,-9)})
    clips["slide-enter"] = [(0,stand),(.06,drop),(.14,slide)]
    clips["slide"] = [(0,slide),(.5,slide)]
    for name,poses in clips.items():
        tracks = {}
        for bone in sorted(set().union(*(p for _,p in poses))):
            timelines = {}
            for channel in sorted(set().union(*(p.get(bone,{}) for _,p in poses))):
                keys = []
                for t,p in poses:
                    frame = dict(p.get(bone,{}).get(channel,[{}])[0], time=t)
                    if channel == "rotate":
                        angle = frame.get("value",0)
                        frame["value"] = round((angle+180)%360-180,3)
                    keys.append(frame)
                timelines[channel] = keys
            tracks[bone] = timelines
        animations[name] = {"bones":tracks}
