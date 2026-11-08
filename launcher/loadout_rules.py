"""Loadout rules shared by package generation and upgrades of existing installations."""
import json
import re
import sys
import zlib
from zipfile import ZipFile, ZIP_DEFLATED

LAUNCHERS = {"weapon-gm94", "weapon-hk69", "weapon-m79", "weapon-rg6", "weapon-rpg7", "weapon-m72law"}

def apply(content):
    content["weapon-ash12"]["primary"]["fire-rate"] = 600
    for key,item in list(content.items()):
        if item.get("slot") == "slot-special-extra" and item.get("instrument",{}).get("id") in LAUNCHERS:
            del content[key]
    for key in ("skin-player-relay","sl-skin-relay"):
        content.pop(key,None)

def encode(value):
    return json.dumps(value,ensure_ascii=False,separators=(",",":")).encode("utf8")

def build(source,target):
    with ZipFile(source) as origin, ZipFile(target,"w",ZIP_DEFLATED,compresslevel=3) as result:
        hashes={}
        for entry in origin.infolist():
            name=entry.filename
            if name in ("content/textures/relay-outfit.png","__H"):
                continue
            raw=origin.read(entry)
            if name=="content.json":
                obj=json.loads(raw);apply(obj["content"]);raw=encode(obj)
            elif name=="content/animations/actor.json":
                obj=json.loads(raw);obj["skins"]=[s for s in obj["skins"] if s["name"]!="relay"];raw=encode(obj)
            elif name=="content/textures/GAME.atlas":
                # The old page contains CR-CR-LF lines; page names themselves are never indented.
                raw=re.sub(rb"(?ms)^relay-outfit\.png\r*\n.*?(?=^[^ \r\n][^\r\n]*\.png\r*$|\Z)",b"",raw)
            elif name=="data/texts.json":
                obj=json.loads(raw);obj["data"].pop("ITEM_PLAYER_SKIN_RELAY",None);raw=encode(obj)
            hashes[name]=zlib.crc32(raw)
            result.writestr(entry,raw)
        if "__H" in origin.namelist():result.writestr("__H",encode(hashes))

if __name__=="__main__":build(*sys.argv[1:])
