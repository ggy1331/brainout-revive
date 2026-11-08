"""Build hand animation tracks in the actor rig's coordinates."""
from pair_refinement import ARMS, bend, direction, offset
from cylinder_animations import rotation_at
import json


def component(item):
    return next(p for p in item["components"] if "states" in p and "animation" in p)


def scalar(track, axis, t):
    if not track:
        return 0
    # Translation curves have separate handles per axis.
    keys = [{"time":k.get("time",0),"value":k.get(axis,0),
             **({"curve":"stepped"} if k.get("curve")=="stepped" else {})} for k in track]
    return rotation_at(keys,t)


def wrist(setup, clip, arm, t):
    pos, rot, scale = 0j, 0, 1
    for name in arm:
        bone = setup[name]
        track = clip.get(name,{})
        trans = track.get("translate",[])
        pos += direction(rot)*scale*(offset(bone)+complex(scalar(trans,"x",t),scalar(trans,"y",t)))
        rot += bone.get("rotation",0)+rotation_at(track.get("rotate",[{}]),t)
        scale *= bone.get("scaleX",1)
    return pos,rot


def put_arm(tracks, setup, arm, t, point, pitch):
    u,p,h = [setup[n] for n in arm]
    upper, fore, axis = bend(u,p,h,point)
    for n,value in zip(arm,(upper,fore,pitch-axis-h["rotation"])):
        keys = tracks.setdefault(n,{}).setdefault("rotate",[])
        last = keys[-1]["value"] if keys else 0
        keys.append({"time":round(t,5),"value":round(last+(value-last+180)%360-180,3)})


def arm_tracks():
    # Reset shoulder translations left by the previous pose while this track is active.
    return {arm[0]:{"translate":[{}]} for arm in ARMS}


def sprint(clips,setup,hold,sidearm):
    native = clips[hold]["bones"]
    original = [wrist(setup,native,arm,0) for arm in ARMS]
    paired = hold=="paired-extend"
    tracks = arm_tracks()
    # Each contact, recoil of the arms, and passing step has its own wrist targets.
    # Local X goes up the chest; negative Y goes forward.
    frames = [(0,0,0),(.08,-.7,.65),(.19,.65,-.30),(.28,.12,.12),
              (.37,-.5,.42),(.48,.55,-.45),(.56,0,0)]
    for t,bob,swing in frames:
        pitch = (-89+32 if sidearm else -89-27) + swing*5
        near = complex(-2.0 if sidearm else -5.5,-6.6 if sidearm else -6.8) + complex(bob,swing)
        if paired:
            far = complex(-2.8-bob*.55,-7.2-swing)
        elif sidearm:
            # Free elbow counter-swings beside the torso.
            far = complex(-7.6-bob,-8.8-3.2*swing)
        else:
            far = near+(original[1][0]-original[0][0])*direction(pitch-original[0][1])
        put_arm(tracks,setup,ARMS[0],t,near,pitch)
        put_arm(tracks,setup,ARMS[1],t,far,pitch+(0 if paired else original[1][1]-original[0][1]))
    return {"bones":tracks}


def profile(model, wid):
    bones={b["name"]:b for b in model["bones"]}
    chamber=offset(bones.get("shell-bone",bones["root"]))
    mount=next((s for s in model["slots"] if s["name"] in ("clip","magazine","grip")),None)
    shapes={} if mount is None else next((skin["attachments"][mount["name"]] for skin in model["skins"]
                    if mount["name"] in skin.get("attachments",{})),{})
    shape=shapes.get((mount or {}).get("attachment"),next(iter(shapes.values()),{}))
    well=offset(shape) if shape else 0j
    if wid=="weapon-qsz92":well=complex(-1.8,-4.5)
    if wid=="weapon-mauser":well=complex(12,1)
    if wid=="weapon-welrod":well=complex(0,-2)
    travel=complex(-1,-max(7,min(16,shape.get("height",14)*.75)))
    if wid=="weapon-p50":travel=complex(-4,12)
    return well, chamber, travel, abs(offset(bones.get("center-bone",bones["root"])))


def apply(content,actor,read,changes=None):
    from paired_reload_art import align_markers, authored_reload
    align_markers(actor)
    clips=actor["animations"]
    setup={b["name"]:b for b in actor["bones"]}
    carry=clips["paired-extend"]["bones"]
    # The far shoulder used to add three units along the vertical axis of the rig.
    for name in ("paired-extend","paired-extend-hit"):
        pose=clips[name]["bones"]
        for far,near in zip(pose["hand2"]["translate"],pose["hand1"]["translate"]):
            far["x"]=near.get("x",0)+0.5
    for key,item in content.items():
        if item.get("class")!="content.instrument.Weapon":continue
        slot=item.get("slot")
        if slot not in ("slot-secondary","slot-primary","slot-special"):continue
        comp=next((p for p in item.get("components",[]) if p.get("states",{}).get("hold")),None)
        if not comp:continue
        hold=comp["states"]["hold"]
        name=("sprint-short-" if slot=="slot-secondary" else "sprint-long-")+hold
        if hold in clips:clips[name]=sprint(clips,setup,hold,slot=="slot-secondary")
        if not key.startswith("paired-weapon-"):continue
        wid=key[len("paired-"):]
        original=component(content[wid])["states"]
        model=json.loads(read("content/"+content[comp["animation"]]["animation"].split(":")[1]))
        # Composite the moving native magazine behind the receiver throughout its stroke.
        slot=next((s for s in model["slots"] if s["bone"]=="pair-mag-travel"),None)
        if changes is not None:
            if slot:
                model["slots"].remove(slot)
                model["slots"].insert(0,slot)
            # Wrist tracks own presentation. Keep weapon event-driven parts independent.
            model["animations"]["pair-reload"]={"bones":{"pair-motion-root":{
                "translate":[{},{"time":1}]}}} if any(b["name"]=="pair-motion-root" for b in model["bones"]) else {"bones":{model["bones"][0]["name"]:{"translate":[{},{"time":1}]}}}
            path="content/"+content[comp["animation"]]["animation"].split(":")[1]
            changes[path]=json.dumps(model,ensure_ascii=False,separators=(",",":")).encode()
        rest={arm:wrist(setup,carry,arm,0) for arm in ARMS}
        variants={comp["states"]["reload"]:original["reload"]}
        if item.get("looseCylinder"):
            cap=item["primary"]["clipSize"]
            prefix="rsh-cylinder-" if item.get("groupEjection") else "cylinder-"
            for i in range(1,min(12,cap)+1):variants[prefix+str(i)]=prefix+str(i)
        for k,v in content.items():
            if not k.startswith(("upgrade-"+wid[7:]+"-","skin-"+wid+"-")):continue
            for part in v.get("components",[]):
                rep=part.get("replace",{})
                if isinstance(rep,dict) and rep.get("reload") in clips:variants[rep["reload"]]=rep["reload"]
        if wid=="weapon-welrod":variants["welrod-reload-matte"]="welrod-reload-matte"
        for action,source in variants.items():
            for side in ("left","right"):
                base="pair-"+side+"-"+action
                if base not in clips:
                    # Some official packages contain the pair but omit its actor clip.
                    from pair_refinement import reload_pose
                    clips[base]=reload_pose(actor,clips[source],side,profile(model,wid)[0],
                                            wid=="weapon-welrod")
                clips[base+"-"+wid]=authored_reload(clips[source],setup,carry,side,model,wid,rest)

    if changes is not None:
        from solo_sidearms import build_solos
        build_solos(content,actor,read,changes)
