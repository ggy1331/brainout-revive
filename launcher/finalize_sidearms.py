"""Apply current movement and sidearm tracks after all weapon grafts are present."""
import json
import zlib
from zipfile import ZIP_DEFLATED, ZipFile

from arm_animations import apply
from gameplay_package import encode
from pair_refinement import ACTOR
from solo_sidearms import perk_text
from stance_animations import add_stance_clips


def finalize(source, destination):
    with ZipFile(source) as src:
        content = json.loads(src.read("content.json"))
        actor = json.loads(src.read(ACTOR))
        changes = {}
        add_stance_clips(actor)
        apply(content["content"], actor, src.read, changes)
        changes["content.json"] = encode(content)
        changes[ACTOR] = encode(actor)
        texts = json.loads(src.read("data/texts.json"))
        perk_text(texts["data"])
        changes["data/texts.json"] = encode(texts)
        if "__H" in src.namelist():
            hashes = json.loads(src.read("__H"))
            hashes.update({name: zlib.crc32(data) for name, data in changes.items()})
            changes["__H"] = encode(hashes)
        with ZipFile(destination, "w", ZIP_DEFLATED, compresslevel=3) as out:
            for entry in src.infolist():
                out.writestr(entry, changes[entry.filename] if entry.filename in changes else src.read(entry))
