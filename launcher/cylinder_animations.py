from copy import deepcopy

ARMS = {"hand1":"hand2", "palm1":"palm2", "holder-primary":"holder-secondary"}
SWAP = dict(ARMS, **{v:k for k,v in ARMS.items()})

def prepare_cylinders(content):
    for weapon in list(content.values()):
        parts = weapon.get("components", [])
        if not any(p.get("states", {}).get("reload","").startswith("reload-weapon-revolver") for p in parts):
            continue
        weapon["looseCylinder"] = True
        for part in parts:
            actions = part.get("actions", [])
            if not isinstance(actions,list) or any(a.get("for") == "drop-bullet" for a in actions if isinstance(a,dict)):
                continue
            grouped = next((a for a in actions if isinstance(a,dict) and a.get("for","").startswith("drop-bullets")), None)
            if grouped:
                single = deepcopy(grouped)
                single["for"] = "drop-bullet"
                for variant in single["effects"]:
                    if isinstance(variant,list):
                        physical = [x for x in variant if isinstance(x,dict)]
                        variant[:] = [x for x in variant if not isinstance(x,dict)] + physical[:1]
                actions.append(single)
    rsh = content["weapon-rsh12"]
    rsh["groupEjection"] = True
    actions = next(p["actions"] for p in rsh["components"] if "actions" in p)
    single = next(a for a in actions if a["for"] == "drop-bullet")
    for spent in range(1,13):
        group = deepcopy(single)
        group["for"] = "empty-cylinder-"+str(spent)
        for variant in group["effects"]:
            case = next(effect for effect in variant if isinstance(effect,dict))
            variant.extend(deepcopy(case) for _ in range(spent-1))
        actions.append(group)
    for part in content["upgrade-rsh12-fastloader"]["components"]:
        if "replace" in part:
            part["replace"]["reload"] = "reload-rsh12-fast"

def cylinder_clip(source,count,group=False):
    # Retain the authored opening, one complete movement per case, and the closing motion.
    sections = [(0,.1667)] + [(.1667,.3333)]*(1 if group else count) + [(1.1667,1.275)] + [(1.275,1.525)]*count + [(2.775,3.0833)]
    def splice(keys):
        result = []
        offset = 0
        for start,end in sections:
            for key in keys:
                t = key.get("time",0)
                if start <= t < end or t == end == sections[-1][1]:
                    k = deepcopy(key)
                    k["time"] = round(offset + t - start,5)
                    curve = k.get("curve")
                    if isinstance(curve,list):
                        for i in range(0,len(curve),2):
                            curve[i] += offset-start
                    result.append(k)
            offset += end-start
        return result
    clip = deepcopy(source)
    for tracks in clip["bones"].values():
        for channel,keys in tracks.items():
            tracks[channel] = splice(keys)
    for tracks in clip.get("slots", {}).values():
        for channel,keys in tracks.items():
            tracks[channel] = splice(keys)
    clip["events"] = splice(source["events"])
    if group:
        for event in clip["events"]:
            if event["string"] == "drop-bullet": event["string"] = "empty-cylinder-"+str(count)
    return clip

def rotation_at(keys, t):
    """Sample the authored Spine rotate timeline, including cubic handles."""
    for start, end in zip(keys, keys[1:]):
        b = end.get("time", 0)
        if t >= b:
            continue
        a = start.get("time", 0)
        y = start.get("value", 0)
        z = end.get("value", 0)
        curve = start.get("curve")
        if t <= a or curve == "stepped":
            return y
        if not isinstance(curve, list):
            return y + (z-y)*(t-a)/(b-a)
        def cubic(a,b,c,d,u):
            v = 1-u
            return v*v*v*a + 3*v*v*u*b + 3*v*u*u*c + u*u*u*d
        low, high = 0, 1
        for _ in range(14):
            mid = (low+high)/2
            if cubic(a,curve[0],curve[2],b,mid) < t:
                low = mid
            else:
                high = mid
        return cubic(y,curve[1],curve[3],z,(low+high)/2)
    return keys[-1].get("value",0)

def steady_barrel(pose, carry, arm):
    # Follow the authored hand path. Counter-rotate just the weapon mount so
    # the second pistol stays level as its wrist reaches down and back up.
    upper,palm,holder = arm
    tracks = pose["bones"]
    rest = sum(carry[b]["rotate"][0]["value"] for b in arm)
    keys = [tracks.get(b,{}).get("rotate",[{}]) for b in (upper,palm)]
    times = {k.get("time",0) for track in keys for k in track}
    end = max(times)
    times.update(i/60 for i in range(1, int(end*60)+1))
    tracks.setdefault(holder,{})["rotate"] = [
        {"time":round(t,5),"value":round(rest-sum(rotation_at(track,t) for track in keys),4)}
        for t in sorted(times)]

def add_magazine_mount(actor,side,holder):
    slot = "pair-magazine-"+side
    actor["bones"].append({"name":slot,"parent":holder})
    pos = next(i for i,s in enumerate(actor["slots"]) if s["name"]=="slot-"+holder.split("-")[1])
    actor["slots"].insert(pos,{"name":slot,"bone":slot})
    for skin in actor["skins"]:
        skin.setdefault("attachments",{})[slot] = {"magazine":{
            "name":"pistol-clip-extended","width":12,"height":22,"scaleX":0.44,"scaleY":0.44}}
    return slot

def animate_magazine(pose,slot,events):
    if "unloaded" not in events or "loaded" not in events:
        return
    out, seated = events["unloaded"], events["loaded"]
    gap = seated-out
    if gap <= 0:
        return
    start, away, incoming = max(0,out-0.14), out+gap*0.23, out+gap*0.55
    pose.setdefault("slots",{})[slot] = {"attachment":[{"name":None},
        {"time":start,"name":"magazine"},{"time":away,"name":None},
        {"time":incoming,"name":"magazine"},{"time":seated,"name":None}]}
    pose["bones"][slot] = {"translate":[{"time":start,"x":0,"y":0},
        {"time":out,"x":-1,"y":-6},{"time":away,"x":-3,"y":-11},
        {"time":incoming,"x":-3,"y":-11},{"time":seated,"x":0,"y":0}]}

def hand_clips(actor,content):
    clips = actor["animations"]
    fast = deepcopy(clips["reload-weapon-revolver-fast"])
    drops = (3,2)
    for event,count in zip((e for e in fast["events"] if e["string"]=="drop-bullets"),drops):
        event["string"] += "-"+str(count)
    clips["reload-rsh12-fast"] = fast
    for n in range(1,13):
        clips["cylinder-"+str(n)] = cylinder_clip(clips["reload-weapon-revolver-2"],n)
        clips["rsh-cylinder-"+str(n)] = cylinder_clip(clips["reload-weapon-revolver-2"],n,group=True)
    setup = {b["name"]:b for b in actor["bones"]}
    sources = {p["states"][s] for key,w in content.items() if key.startswith("paired-weapon-")
               for p in w.get("components",[]) for s in ("reload","cock","fetch") if s in p.get("states",{})}
    sources.update(p["replace"]["reload"] for w in content.values() for p in w.get("components",[]) if "reload" in p.get("replace",{}))
    sources.update("cylinder-"+str(i) for i in range(1,13))
    sources.update("rsh-cylinder-"+str(i) for i in range(1,13))
    mag_slots = {side:add_magazine_mount(actor,side,holder) for side,holder in
                 (("left","holder-primary"),("right","holder-secondary"))}
    for name in sorted(sources.intersection(clips)):
        for side in ("left","right"):
            pose = deepcopy(clips[name])
            # Keep both mounted weapons visible. Native special prop slots may be animated.
            if side == "right":
                for event in pose.get("events",[]):
                    if event["name"] == "instrument-action":
                        event["string"] = "offhand/" + event["string"]
                mapped = {}
                for src,track in pose.get("bones",{}).items():
                    dst = SWAP.get(src,src)
                    delta = setup[src].get("rotation",0)-setup[dst].get("rotation",0)
                    for k in track.get("rotate",[]):
                        k["value"] = k.get("value",0)+delta
                        if isinstance(k.get("curve"),list):
                            for i in (1,3): k["curve"][i] += delta
                    mapped[dst] = track
                pose["bones"] = mapped
            if name == "cock-weapon-revolver":
                active = ARMS.keys() if side == "left" else ARMS.values()
                pose["bones"] = {bone:track for bone,track in pose["bones"].items() if bone in active}
                pose.pop("slots",None)
                # Show the cocking stroke on the acting arm even when both
                # revolvers are cocked independently on separate tracks.
                upper = "hand1" if side == "left" else "hand2"
                rot = pose["bones"][upper]["rotate"]
                base = rot[0]["value"]
                pose["bones"][upper]["rotate"] = [
                    {"time":t,"value":base+angle} for t,angle in
                    ((0,0),(.09,9),(.17,13),(.26,4),(.3333,0))]
            else:
                if side == "right":
                    # Keep the original shoulder anchors. Retarget the elbow and wrist
                    # excursion relative to this arm's grip, with no wrap at +/-180.
                    carry = clips["paired-extend"]["bones"]
                    for bone in SWAP:
                        track = pose["bones"].setdefault(bone,{})
                        keys = track.get("rotate")
                        if keys:
                            start = keys[0].get("value",0)
                            rest = carry[bone]["rotate"][0]["value"]
                            limit = 18 if bone.startswith("holder") else 40
                            def retarget(value):
                                diff = (value-start+180)%360-180
                                return rest + max(-limit,min(limit,diff*0.72))
                            for key in keys:
                                key["value"] = retarget(key.get("value",0))
                                if isinstance(key.get("curve"),list):
                                    for i in (1,3): key["curve"][i] = retarget(key["curve"][i])
                        if bone.startswith("hand"):
                            track["translate"] = deepcopy(carry[bone]["translate"])
                passive = list(ARMS.values() if side == "left" else ARMS.keys())
                steady_barrel(pose,clips["paired-extend"]["bones"],passive)
                events = {e.get("string"):e.get("time",0) for e in clips[name].get("events",[])}
                animate_magazine(pose,mag_slots[side],events)
            clips["pair-"+side+"-"+name] = pose
