"""Bring player skins added to the source actor.json back into the package.

welrod_graft.apply replaces content/animations/actor.json with the v0.11.0 copy from
welrod_bundle, so a skin added later to data/packages/base/.../actor.json would be lost.
This stage appends every skin of the source actor that the package actor lacks; it runs
right after Welrod, so the later stages (finalize, colt1911, sidearms) see the new skins
like any other one.
"""
import json
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gameplay_package import encode
from pair_refinement import ACTOR

SOURCE = Path(__file__).resolve().parent.parent / "data" / "packages" / "base" / "contents" / ACTOR


def build(source, destination):
    own = json.loads(SOURCE.read_text(encoding="utf-8"))
    with ZipFile(source) as src:
        actor = json.loads(src.read(ACTOR))
        have = {skin["name"] for skin in actor["skins"]}
        slots = {slot["name"] for slot in actor["slots"]}
        added = []
        for skin in own["skins"]:
            if skin["name"] in have:
                continue
            missing = set(skin.get("attachments", {})) - slots
            if missing:
                raise ValueError("skin %s uses unknown slots %s" % (skin["name"], sorted(missing)))
            # slots every packaged skin carries (e.g. pair-magazine-* from the Welrod set)
            shared = {}
            for other in actor["skins"]:
                if other["name"] != "default":
                    for slot, value in other.get("attachments", {}).items():
                        shared.setdefault(slot, value)
            counts = {slot: sum(slot in o.get("attachments", {}) for o in actor["skins"] if o["name"] != "default")
                      for slot in shared}
            total = sum(1 for o in actor["skins"] if o["name"] != "default")
            attachments = skin.setdefault("attachments", {})
            for slot, value in shared.items():
                if counts[slot] == total and slot not in attachments:
                    attachments[slot] = value
            actor["skins"].append(skin)
            added.append(skin["name"])
        changes = {ACTOR: encode(actor)}
        if "__H" in src.namelist():
            hashes = json.loads(src.read("__H"))
            hashes.update({name: zlib.crc32(data) for name, data in changes.items()})
            changes["__H"] = encode(hashes)
        with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=3) as out:
            for entry in src.infolist():
                out.writestr(entry, changes[entry.filename] if entry.filename in changes else src.read(entry))
    print("player skins added:", ", ".join(added) or "none")
