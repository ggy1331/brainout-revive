"""Build v0.8 equipment and localization data for the local client and server."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from zipfile import ZipFile

RETIRED = {"skillpts", "gears", "nuclear-material"}
STAT_SLOTS = {"extra-mag", "accuracy", "wear-resistance", "reload-time", "recoil", "shoot-time", "shot-time"}

def transform(data):
    content = data["content"]
    animation = content["anim-actor"]
    animation["skip-mix"] = [name for name in animation["skip-mix"] if not name.startswith("crouch")]
    for transition in animation["states"]:
        if transition["duration"] == 0 and any(transition[key].startswith(("sit", "crouch")) for key in ("from", "to")):
            transition["duration"] = 0.36
    shop = content["shop"]
    shop["items"] = {k: price for k, price in shop["items"].items() if price.get("currency") not in RETIRED}
    cases = {key for key,value in content.items() if value.get("class") == "content.gamecase.Case"}
    removed = {key for key in content if key.startswith("sl-store-case-")} | {"sl-store-skillpts", "sl-store-gears"}
    for key in removed:
        shop["items"].pop(key, None)
    for category in content["slot-store"]["categories"]:
        category["items"] = [key for key in category.get("items", []) if key not in removed]
    for value in content.values():
        if value.get("class") == "content.quest.Quest":
            value["rewards"] = [reward for reward in value.get("rewards", []) if reward.get("id") not in cases | RETIRED]
        components = value.get("components", [])
        if any(c.get("class") == "content.components.UnlockStoreItemComponent" and c.get("content") in cases for c in components):
            value["components"] = [c for c in components if c.get("class") not in ("content.components.UnlockStoreItemComponent", "content.components.ServerUnlockStoreItemComponent")]
    content["slot-primary"]["categories"].insert(-1, {"id":"machineguns","title":"MENU_MACHINEGUNS"})
    for model in "aek999 bar fnminimi hk21 kac-chainsaw l86 m134 m60 mg34 mg36 mg42 pecheneg pkm rpd rpk16 rpk74 tul1".split():
        content["sl-pri-" + model]["category"] = "machineguns"
    for model in "gm94 hk69 m79 rg6 rpg7 shield".split():
        item = content["sl-pri-" + model]
        item.update(slot="slot-special", category="special")
        content[item["instrument"]["id"]]["slot"] = "slot-special"
    content["instrument-binoculars"]["throwable"] = False
    del content["sl-spc-binoculars"]
    shop["items"].pop("sl-spc-binoculars", None)
    second = deepcopy(content["slot-special"])
    second.update(name="CONTROL_SPECIAL_TWO", default="sl-inst-none-slot2")
    content["slot-special-extra"] = second
    if not any(isinstance(v, dict) and v.get("@then") == "slot-special-extra" for v in shop["slots"]):
        index = next(i for i,v in enumerate(shop["slots"]) if isinstance(v,dict) and v.get("@then")=="slot-special")
        shop["slots"].insert(index+1,dict(shop["slots"][index], **{"@then":"slot-special-extra"}))
    for key,value in list(content.items()):
        instrument = value.get("instrument")
        if isinstance(instrument,dict) and "upgrades" in instrument:
            instrument["upgrades"] = {k:v for k,v in instrument["upgrades"].items() if k not in STAT_SLOTS}
        if value.get("slot") == "slot-special" and value["class"].startswith("content.shop."):
            extra = deepcopy(value)
            extra.update(slot="slot-special-extra", original=key)
            content[key+"-slot2"] = extra
        if value.get("class") == "content.upgrades.UpgradeChain" and all(any(u.startswith("upgrade-"+s+"-") for s in STAT_SLOTS) for u in value["upgrades"]):
            value["enabled"] = False
            for u in value["upgrades"]:
                content[u]["properties"] = {}

def build(source, target):
    with ZipFile(source) as origin, ZipFile(target,"w") as result:
        for entry in origin.infolist():
            raw = origin.read(entry)
            if entry.filename in ("content.json","data/texts.json"):
                obj=json.loads(raw)
                if entry.filename=="content.json":
                    transform(obj)
                else:
                    for key, ru, en in [("MAP_DUEL","Дуэль","Duel"), ("MAP_HALLOWEEN","Хэллоуин","Halloween"), ("MAP_BUNKER_CTF","Бункер (флаги)","Bunker (CTF)"), ("MODE_DUEL","Дуэль","Duel"), ("MODE_ZOMBIE","Зомби","Zombies")]:
                        obj["data"].setdefault(key, {"RU": ru, "EN": en})
                    obj["data"]["MENU_MACHINEGUNS"]={"RU":"Пулемёты","EN":"Machine guns"}
                    obj["data"]["CONTROL_PRONE"]={"RU":"Лечь / встать","EN":"Toggle prone"}
                    obj["data"]["CONTROL_KNIFE"]={"RU":"Нож","EN":"Knife"}
                    obj["data"]["CONTROL_SPECIAL_ONE"]={"RU":"Спецоружие 1","EN":"Special equipment 1"}
                    obj["data"]["CONTROL_SPECIAL_TWO"]={"RU":"Спецоружие 2","EN":"Special equipment 2"}
                    obj["data"]["CONTROL_KNIFE_ALT"]={"RU":"Быстрый удар","EN":"Quick melee"}
                raw=json.dumps(obj,ensure_ascii=True,separators=(",",":")).encode("utf8")
            result.writestr(entry,raw)

if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))

