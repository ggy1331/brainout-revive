"""Apply gameplay additions to the published v0.10.2 base package (client or server)."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import sys
from PIL import Image, ImageDraw, ImageFilter
from loadout_rules import apply as apply_loadout_rules

def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf8")

def make_icons(z):
    # Match the inventory atlas: two-pixel marks, ivory highlights, amber bloom and a dotted trail.
    glyphs = {
        "shield": [(12,2,22,2,25,6,24,15,18,20,12,16,10,6)],
        "guitar": [(6,13,9,10,13,11,15,9,18,10,17,13,13,14,12,18,8,19,5,17),
                   (14,11,25,3,28,3,27,6,16,13)],
        "electric": [(4,17,8,12,12,12,16,8,15,12,18,12,12,17,7,19),
                     (13,13,25,3,29,2,27,6,15,15)],
        "gm94": [(3,13,8,8,24,8,24,7,31,7,31,10,21,10,20,13,12,13,10,17,8,16,9,12,5,15)],
        "hk69": [(3,12,9,8,12,9,13,7,26,7,26,11,14,11,12,14,11,17,8,16,10,12,5,14)],
        "m79": [(2,14,9,10,14,9,15,7,31,7,31,9,16,10,13,12,12,15,10,14,10,12,4,16)],
        "m72law": [(3,10,7,9,8,8,20,8,20,6,21,6,21,8,30,8,31,7,32,7,32,12,30,12,29,11,7,12,3,13)],
        "rg6": [(2,13,8,9,11,9,12,7,18,6,22,8,30,8,30,11,22,11,20,15,14,15,11,12,9,16,7,15,8,12,3,15)],
        "rpg7": [(2,12,7,10,14,9,16,8,22,8,25,6,31,8,32,9,26,11,22,10,16,11,14,15,12,15,13,11,6,12,3,14)],
        "obrez": [(2,14,8,10,15,9,18,7,28,7,28,9,17,10,13,12,10,12,5,16)],
        "paired": [(4,11,17,11,17,14,10,14,8,19,5,19,6,14,4,14),
                   (13,4,27,4,27,7,19,7,18,12,15,12,16,7,13,7)]
    }
    details = {"shield":[(13,6,22,7),(16,11,21,11)],"guitar":[(10,14,11,15)],
        "electric":[(10,14,12,14)], "gm94":[(15,10,20,10)], "hk69":[(15,9,23,9)],
        "m79":[(17,8,24,8)],"m72law":[(8,10,17,10)],"rg6":[(15,9,15,12),(18,9,18,12)],
        "rpg7":[(8,11,13,10)],"obrez":[(14,10,18,9)],"paired":[(8,13,12,13),(17,6,21,6)]}
    sheet = Image.new("RGBA",(4*88,3*68))
    atlas = "\n\ngameplay-icons.png\nformat: RGBA8888\nfilter: Nearest,Nearest\nrepeat: none\n"
    def add(name,im,i):
        nonlocal atlas
        x,y=i%4*88,i//4*68
        sheet.alpha_composite(im,(x,y))
        atlas += f"{name}\n  rotate: false\n  xy: {x}, {y}\n  size: {im.width}, {im.height}\n  orig: {im.width}, {im.height}\n  offset: 0, 0\n  index: -1\n"
    for i,(name,shapes) in enumerate(glyphs.items()):
        mask=Image.new("L",(36,23));pen=ImageDraw.Draw(mask)
        for polygon in shapes:pen.polygon(polygon,fill=255)
        body=Image.new("RGBA",mask.size,(231,218,181));body.putalpha(mask)
        pen=ImageDraw.Draw(body)
        for x in range(mask.width):
            col=[y for y in range(mask.height) if mask.getpixel((x,y))]
            if col:
                pen.point((x,col[0]),fill=(255,250,228,255))
                pen.point((x,col[-1]),fill=(149,127,83,255))
        for line in details[name]:pen.line(line,fill=(113,98,65,255))
        # Echo the left edge as sparse, progressively fainter pixels.
        for y in range(3,20):
            edge=next((x for x in range(mask.width) if mask.getpixel((x,y))),None)
            if edge is None:continue
            for d in range(2,9):
                if edge>=d and (y*13+d*7)%11<3:
                    pen.point((edge-d,y),fill=(223,197,135,190-d*12))
        art=Image.new("RGBA",(88,68))
        art.alpha_composite(body.resize((72,46),Image.Resampling.NEAREST),(8,11))
        glow=Image.new("RGBA",art.size,(245,186,59));glow.putalpha(art.getchannel("A").filter(ImageFilter.GaussianBlur(5)))
        glow.alpha_composite(art)
        add("gear-icon-"+name,glow,i)
    tick=Image.new("RGBA",(10,10));ImageDraw.Draw(tick).line([(0,5),(3,8),(9,1)],fill="#dbe6c5",width=2)
    add("loadout-confirm",tick,11)
    out=BytesIO();sheet.save(out,"PNG")
    return atlas.encode(),out.getvalue()

def paired_model(model):
    model=deepcopy(model)
    parents={slot["bone"] for slot in model["slots"]}
    bones={name:"pair-motion-"+name for name in sorted(parents)}
    model["bones"].extend({"name":new,"parent":old} for old,new in bones.items())
    for slot in model["slots"]:slot["bone"]=bones[slot["bone"]]
    for action,frames in (("fire",[(0,-2,0,5),(.055,-3,1,8),(.14,0,0,0)]),
                          ("reload",[(0,0,0,0),(.24,0,-1,-3),(.70,-1,-1,-4),(1,0,0,0)])):
        model["animations"]["pair-"+action]={"bones":{bone:{
            "translate":[{"time":t,"x":x,"y":y} for t,x,y,angle in frames],
            "rotate":[{"time":t,"value":angle} for t,x,y,angle in frames]} for bone in bones.values()}}
    return model

from cylinder_animations import prepare_cylinders, hand_clips

def add_pair(key,item,c,z,changes):
    spec=item["instrument"];wid=spec["id"];w=deepcopy(c[wid])
    if "primary" not in w:return
    w["slot"]="slot-secondary"
    properties=w["primary"]
    # Both hands draw from one reserve through independent weapon slots.
    properties.update(magazineManagement=0,autoReload=False,canReloadBoth=False)
    components=w["components"]
    components[:]=[v for v in components if not v.get("class","").endswith(".SecondaryWeaponSlotComponent")]
    components.append({"class":"content.components.SecondaryWeaponSlotComponent","icon":"gear-icon-paired","properties":deepcopy(properties)})
    for part in components:
        if part.get("class","").endswith(".InstrumentEffectsComponent"):
            for action in ("shoot","reload","fetch"):
                if action in part: part[action+"Secondary"] = deepcopy(part[action])
        if part.get("class","").endswith("WeaponAnimationComponent"):
            part["states"].update(hold="paired-extend",aim="paired-extend",hit="paired-extend-hit",aimHit="paired-extend-hit")
            aid=part["animation"]; anim=deepcopy(c[aid]);ref=anim["animation"];prefix,fn=ref.split(":",1)
            pairedfile=fn.replace("animations/","animations/paired-")
            anim["animation"]=prefix+":"+pairedfile;part["animation"]="paired-"+aid;c["paired-"+aid]=anim
            if "content/"+fn in z.namelist():
                changes["content/"+pairedfile]=encode(paired_model(json.loads(z.read("content/"+fn))))
    c["paired-"+wid]=w
    row=deepcopy(item);row.update(enabled=False,original=key)
    row["instrument"]["id"]="paired-"+wid
    c["sl-pair-"+key[7:]]=row

def build(src,dst):
    with ZipFile(src) as z, ZipFile(dst,"w",ZIP_DEFLATED,compresslevel=3) as output:
        data=json.loads(z.read("content.json")); c=data["content"]
        texts=json.loads(z.read("data/texts.json")); t=texts["data"]
        changes={}
        def label(key,ru,en):t[key]={"RU":ru,"EN":en}
        def icon(name):return {"class":"content.components.IconComponent","tag":"client","icon":"gear-icon-"+name,"big-icon":"gear-icon-"+name}
        cat=c["slot-primary"]["categories"]
        cat.insert(-1,{"id":"dmr","title":"MENU_DMR"})

        label("MENU_DMR","Марксманские","DMR");label("MENU_AKIMBO","Акимбо","Akimbo")
        for model in "g3 hksl8 hk417 rsaas m14 m21 m110 kac qbu88 sks svd svds svu vsk94 vss vssm-2 gewehr43 svt40 garand".split():
            c["sl-pri-"+model]["category"]="dmr"
        c["sl-pl-sc-clip"]["enabled"]=False
        label("ITEM_SPECIAL_MAGAZINE_DESC","По одному дополнительному магазину для основного оружия и пистолета.","One extra magazine for both primary and secondary weapons.")
        for old,base,upgrade,model in [("sl-pri-mosinobrez","sl-pri-mosin","obrez","obrez"),("sl-spc-electro-guitar","sl-spc-guitar","electric","electric")]:
            c["conversion-"+upgrade]={"class":"content.upgrades.Upgrade","access":"byDefault","name":c[old]["name"],"properties":{},
                "conversion":c[old]["instrument"]["id"],"components":[icon(model)]}
            for suffix in ("","-slot2"):
                if base+suffix in c:
                    c[old+suffix]["enabled"]=False
                    c[base+suffix]["instrument"].setdefault("upgrades",{})["conversion"]="conversion-"+upgrade
        perk=deepcopy(c["sl-pl-clip"])
        for k in ("slotFrom","additionalClip","weaponExcept","clipExcept"):perk.pop(k,None)
        perk.update(name="MENU_AKIMBO",description="DESC_AKIMBO",components=[icon("paired")],index=7)
        label("DESC_AKIMBO","Вторичное оружие становится парным. ЛКМ и ПКМ — разные руки, R — поочерёдная перезарядка. Точность ×0,5, отдача ×2.","Dual wield your secondary. Left and right click fire independently. Reload one hand at a time. Half accuracy, double recoil.")
        prepare_cylinders(c)
        c["sl-pl-akimbo"]=perk
        for key,item in list(c.items()):
            if not key.startswith("sl-sec-") or "instrument" not in item:continue
            add_pair(key,item,c,z,changes)

        obrez_path="content/animations/weapon-mosinobrez.json"
        obrez=json.loads(z.read(obrez_path))
        mosin=json.loads(z.read("content/animations/weapon-mosin.json"))
        obrez["slots"].insert(0,deepcopy(next(v for v in mosin["slots"] if v["name"]=="scope")))
        scope=next(s for s in mosin["skins"] if s["name"]=="weapon-default")["attachments"]["scope"]
        for skin in obrez["skins"]:skin["attachments"]["scope"]=deepcopy(scope)
        changes[obrez_path]=encode(obrez)
        actor=json.loads(z.read("content/animations/actor.json"))
        setup={b["name"]:b for b in actor["bones"]}
        for target,source in (("paired-extend","aim-weapon-1hand"),("paired-extend-hit","shoot-hold-weapon-1hand")):
            pose=deepcopy(actor["animations"][source])
            for near,far in (("hand1","hand2"),("palm1","palm2"),("holder-primary","holder-secondary")):
                near_track=pose["bones"][near]
                far_track=deepcopy(near_track)
                for frame in far_track.get("rotate",[]):
                    frame["value"]=frame.get("value",0)+setup[near]["rotation"]-setup[far]["rotation"]
                if far=="hand2":
                    # Separate the parallel barrels in the side view without detaching the grip.
                    for frame in far_track["translate"]:
                        frame["x"]=frame.get("x",0)+3
                        frame["y"]=frame.get("y",0)+3
                pose["bones"][far]=far_track
            actor["animations"][target]=pose
        from stance_animations import add_stance_clips
        add_stance_clips(actor)
        hand_clips(actor,c)
        changes["content/animations/actor.json"]=encode(actor)
        apply_loadout_rules(c)
        if "content/textures/GAME.atlas" in z.namelist():
            atlas,png=make_icons(z);path="content/textures/GAME.atlas"
            changes[path]=z.read(path).rstrip()+atlas
            changes["content/textures/gameplay-icons.png"]=png
        from pair_refinement import refine
        refine(z,c,actor,changes)
        from solo_sidearms import perk_text
        perk_text(t)
        changes.update({"content.json":encode(data),"data/texts.json":encode(texts)})
        for entry in z.infolist():
            if entry.filename not in changes:output.writestr(entry,z.read(entry))
        for key,value in changes.items():output.writestr(key,value)

if __name__=="__main__":build(*sys.argv[1:])
