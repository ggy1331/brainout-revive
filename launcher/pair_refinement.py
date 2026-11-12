"""Apply paired reloads to the installed content, including locally added sidearms."""
from copy import deepcopy
from pathlib import Path
from math import acos, atan2, cos, sin, radians, degrees
import json
import sys
import zlib
from zipfile import ZipFile, ZIP_DEFLATED
from gameplay_package import add_pair, encode
from cylinder_animations import rotation_at

ARMS = (("hand1","palm1","holder-primary"),("hand2","palm2","holder-secondary"))
ACTOR = "content/animations/actor.json"
ATLAS = "content/textures/GAME.atlas"

def direction(angle):
    return complex(cos(radians(angle)),sin(radians(angle)))

def angle(v):
    return degrees(atan2(v.imag,v.real))

def offset(b):
    return complex(b.get("x",0),b.get("y",0))

def bend(upper,palm,holder,goal):
    delta=(goal-offset(upper))/upper.get("scaleX",1)
    a,b=abs(offset(palm)),abs(offset(holder))
    # Leave room at the elbow even when the requested contact is out of reach.
    elbow=degrees(acos(max(cos(radians(147)),min(cos(radians(48)),(abs(delta)**2-a*a-b*b)/(2*a*b)))))
    shoulder=angle(delta)-angle(a+b*direction(elbow))
    u=shoulder-angle(offset(palm))
    v=shoulder+elbow-angle(offset(holder))
    return u-upper["rotation"],v-u-palm["rotation"],v

def reload_pose(actor,native,side,well,welrod=False):
    """Retain the source clip's timing and motion, solving each wrist in its own arm."""
    bones={b["name"]:b for b in actor["bones"]}
    carry=actor["animations"]["paired-extend"]["bones"]
    near,far=ARMS if side=="left" else ARMS[::-1]
    events={e.get("string"):e["time"] for e in native.get("events",[])}
    out=events["welrod-take" if welrod else "unloaded"]
    seat=events["welrod-seat" if welrod else "loaded"]
    end=max(seat,max(k.get("time",0) for t in native["bones"].values() for keys in t.values() for k in keys))
    start=max(0,out-.14)
    away=out+(seat-out)*.23
    incoming=out+(seat-out)*.55
    steps=sorted({0,start,out,away,incoming,seat,end}|{i/40 for i in range(1,int(end*40)+1)})
    slot="pair-magazine-"+side
    pose={"bones":{},"events":deepcopy(native.get("events",[])),"slots":{slot:{"attachment":[
        {"name":None},{"time":start,"name":"magazine"},{"time":away,"name":None},
        {"time":incoming,"name":"magazine"},{"time":seat,"name":None}]}}}
    if side=="right":
        for e in pose["events"]:
            if e["name"]=="instrument-action":e["string"]="offhand/"+e["string"]
    for arm in (near,far):
        for name in arm:
            pose["bones"][name]={"rotate":[]}
        pose["bones"][arm[0]]["translate"]=[]
    travel=[]
    def ramp(t,a,b):
        x=max(0,min(1,(t-a)/max(.001,b-a)))
        return x*x*(3-2*x)
    def key(name,t,value):
        keys=pose["bones"][name]["rotate"]
        last=keys[-1]["value"] if keys else carry[name]["rotate"][0]["value"]
        keys.append({"time":round(t,5),"value":round(last+(value-last+180)%360-180,4)})
    for t in steps:
        lift=ramp(t,0,max(.08,start))*(1-ramp(t,seat,end))
        extended=ramp(t,start,away)*(1-ramp(t,incoming,seat))
        motion=complex(-3,-11)*extended
        travel.append({"time":round(t,5),"x":round(motion.real,4),"y":round(motion.imag,4)})
        # Sample the gun hand from the actual model's assigned clip.
        ref=[rotation_at(native["bones"][b]["rotate"],t) for b in ARMS[0]]
        u,p,h=[bones[n] for n in near]
        rest=[carry[n]["rotate"][0]["value"] for n in near]
        shoulder=u["rotation"]+rest[0]
        forearm=shoulder+p["rotation"]+rest[1]
        gun=forearm+h["rotation"]+rest[2]
        idle=offset(u)+u.get("scaleX",1)*(direction(shoulder)*offset(p)+direction(forearm)*offset(h))
        pitch=max(-24,min(24,sum(ref)-sum(rotation_at(native["bones"][b]["rotate"],0) for b in ARMS[0])))
        axis=gun+lift*(12+pitch*.55)
        # Draw the pistol in before reaching for a forward-mounted magazine.
        socket=idle*(1-.36*lift)+complex(0,1.4)*lift
        upper,lower,world=bend(u,p,h,socket)
        active=(upper,lower,axis-world-h["rotation"])
        for n,r,v in zip(near,rest,active):key(n,t,r+lift*((v-r+180)%360-180))
        u,p,h=[bones[n] for n in far]
        goal=socket+direction(axis)*(well+motion)*.24
        upper,lower,world=bend(u,p,h,goal)
        stable=sum(bones[n]["rotation"]+carry[n]["rotate"][0]["value"] for n in far)
        for n,v in zip(far,(upper,lower,stable-world-h["rotation"])):
            r=carry[n]["rotate"][0]["value"]
            key(n,t,r+lift*((v-r+180)%360-180))
        for name in (near[0],far[0]):
            rest=carry[name]["translate"][0]
            pose["bones"][name]["translate"].append({"time":round(t,5),"x":rest.get("x",0)*(1-lift),"y":rest.get("y",0)*(1-lift)})
    pose["bones"][slot]={"translate":travel}
    return pose

def refine(z,c,actor,changes):
    def read(path):
        return changes[path] if path in changes else z.read(path)
    if ATLAS in z.namelist():
        atlas=read(ATLAS)
        if b"restored-pair-icons.png" not in atlas:
            atlas+=b"\n\nrestored-pair-icons.png\nformat: RGBA8888\nfilter: Nearest,Nearest\nrepeat: none\n"
            for i,name in enumerate(("obrez","akimbo")):
                atlas+=f"restored-{name}\n  rotate: false\n  xy: 0, {i*32}\n  size: 64, 32\n  orig: 64, 32\n  offset: 0, 0\n  index: -1\n".encode()
            changes[ATLAS]=atlas
        changes["content/textures/restored-pair-icons.png"]=Path(__file__).with_name("pair-icons.png").read_bytes()
    for item,name in (("conversion-obrez","obrez"),("sl-pl-akimbo","akimbo")):
        for part in c[item]["components"]:
            if part.get("class","").endswith(".IconComponent"):
                part.update(icon="restored-"+name,**{"big-icon":"restored-"+name})
    # the Akimbo perk gets an icon in the style of the other perks
    # (textures/ICONS/icon-shop-special-akimbo.png, tools/weapon-art/akimbo_perk_icon.py)
    for part in c["sl-pl-akimbo"]["components"]:
        if part.get("class","").endswith(".IconComponent"):
            part.pop("big-icon",None)
            part["icon"]="icon-shop-special-akimbo"
    clips=actor["animations"]
    for key,item in list(c.items()):
        if item.get("slot")!="slot-secondary" or not key.startswith("sl-sec-"):continue
        wid=item["instrument"]["id"]
        if "paired-"+wid not in c:add_pair(key,item,c,z,changes)
        w=c.get("paired-"+wid)
        if not w:continue
        anim=next(p for p in w["components"] if "states" in p)
        original=next(p for p in c[wid]["components"] if "states" in p)
        source=original["states"]["reload"]
        native=clips[source]
        events={e.get("string") for e in native.get("events",[])}
        welrod="welrod-take" in events
        if not welrod and not {"unloaded","loaded"}<=events:continue
        path="content/"+c[anim["animation"]]["animation"].split(":")[1]
        model=json.loads(read(path))
        mount=next((s for s in model["slots"] if s["name"] in ("clip","magazine","grip")),None)
        well=complex(12,0) if wid=="weapon-mauser" else 0j
        if mount:
            shapes=next((s["attachments"][mount["name"]] for s in model["skins"] if mount["name"] in s["attachments"]),{})
            shape=shapes.get(mount.get("attachment"),next(iter(shapes.values()),{}))
            if not welrod:well=offset(shape)
            if mount["bone"]!="pair-mag-travel":
                model["bones"].append({"name":"pair-mag-travel","parent":mount["bone"]})
                mount["bone"]="pair-mag-travel"
            for part in w["components"]:
                actions=part.get("actions")
                if isinstance(actions,list):
                    part["actions"]=[a for a in actions if not (a.get("slot")==mount["name"] and a.get("for") in ("unloaded","loaded")) and not (welrod and a.get("for") in ("welrod-take","welrod-seat"))]
            if welrod:
                model["animations"]["pair-fire"]["bones"].update(deepcopy(model["animations"]["cycle"]["bones"]))
            changes[path]=encode(model)
        name="load-"+wid
        anim["states"]["reload"]=name
        for side in ("left","right"):
            pose=reload_pose(actor,native,side,well,welrod)
            clips["pair-"+side+"-"+name]=pose
            if welrod:
                clips["pair-"+side+"-welrod-reload-matte"]=deepcopy(pose)
    from arm_animations import apply as animate_arms
    animate_arms(c,actor,read,changes)
    changes[ACTOR]=encode(actor)

def build(source,dest):
    with ZipFile(source) as z:
        data=json.loads(z.read("content.json")); changes={}
        refine(z,data["content"],json.loads(z.read(ACTOR)),changes)
        changes["content.json"]=encode(data)
        if "data/texts.json" in z.namelist():
            from solo_sidearms import perk_text
            texts=json.loads(z.read("data/texts.json"))
            perk_text(texts["data"])
            changes["data/texts.json"]=encode(texts)
        if "__H" in z.namelist():
            hashes=json.loads(z.read("__H"));hashes.update({k:zlib.crc32(v) for k,v in changes.items()})
            changes["__H"]=encode(hashes)
        with ZipFile(dest,"w",ZIP_DEFLATED,compresslevel=3) as out:
            for entry in z.infolist():
                out.writestr(entry,changes.pop(entry.filename) if entry.filename in changes else z.read(entry))
            for name,value in changes.items():out.writestr(name,value)
if __name__=="__main__":build(*sys.argv[1:])
