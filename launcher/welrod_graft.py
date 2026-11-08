"""Welrod Mk II: the part of v0.11.0 that exists only in the release archive.

The pistol was added to the v0.11.0 installation directly; its sources are not in
git. This script keeps the build reproducible until they are:

  extract  release_base.zip built_base.zip [release_freeplay.zip]
      Compare the release base.zip with one built from git by the usual pipeline
      and store every Welrod piece in launcher/welrod_bundle/ (content entries,
      texts, files, atlas pages, actor.json, freeplay loot entry).
  apply    built_base.zip out_base.zip
  freeplay built_freeplay.zip out_freeplay.zip
      Add the stored Welrod pieces to freshly built packages.

Run from the launcher folder with the project's Python.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json
import sys
import zlib

BUNDLE = Path(__file__).resolve().parent / "welrod_bundle"
# entries that exist in git but get one Welrod line in the release
PATCHED = ("ammobox-active", "metal")


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf8")


def atlas_pages(text):
    """Split a libGDX atlas into {page name: block}; blocks are separated by a blank line."""
    pages, order = {}, []
    for block in text.replace("\r\n", "\n").strip("\n").split("\n\n"):
        name = block.strip("\n").split("\n", 1)[0].strip()
        if name:
            pages[name] = block.strip("\n")
            order.append(name)
    return pages, order


def extract(release, built, release_freeplay=None):
    BUNDLE.mkdir(exist_ok=True)
    (BUNDLE / "files").mkdir(exist_ok=True)
    with ZipFile(release) as r, ZipFile(built) as b:
        rc, bc = json.loads(r.read("content.json"))["content"], json.loads(b.read("content.json"))["content"]
        added = {k: v for k, v in rc.items() if k not in bc}
        patched = {k: rc[k] for k in PATCHED}
        other = [k for k in rc if k in bc and rc[k] != bc[k] and k not in PATCHED]
        assert not other, "unexpected differences: %s" % other
        rt, bt = json.loads(r.read("data/texts.json"))["data"], json.loads(b.read("data/texts.json"))["data"]
        texts = {k: v for k, v in rt.items() if k not in bt}
        files = sorted(n for n in r.namelist() if n not in b.namelist() and n != "__H")
        for n in files:
            out = BUNDLE / "files" / n
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(r.read(n))
        rpages, rorder = atlas_pages(r.read("content/textures/GAME.atlas").decode("utf8"))
        bpages, _ = atlas_pages(b.read("content/textures/GAME.atlas").decode("utf8"))
        pages = [p for p in rorder if p not in bpages]
        (BUNDLE / "atlas.txt").write_bytes(("\n\n".join(rpages[p] for p in pages) + "\n").encode("utf8"))
        (BUNDLE / "actor.json").write_bytes(r.read("content/animations/actor.json"))
        (BUNDLE / "content.json").write_bytes(json.dumps({"added": added, "patched": patched, "texts": texts, "files": files},
                                                         ensure_ascii=False, indent=1).encode("utf8"))
    if release_freeplay:
        with ZipFile(release_freeplay) as r:
            spawn = json.loads(r.read("content.json"))["content"]["freeplay-items-spawm"]["items"]
        loot = [[n, i] for n, i in enumerate(spawn) if i.get("item") == "bullet-32acp"]
        (BUNDLE / "freeplay-loot.json").write_bytes(json.dumps(loot, indent=1).encode("utf8"))
    print("bundle: %d entries, %d texts, %d files, %d atlas pages" % (len(added), len(texts), len(files), len(pages)))


def rewrite(src, dst, change):
    with ZipFile(src) as z, ZipFile(dst, "w", ZIP_DEFLATED, compresslevel=3) as out:
        files = change(z)
        hashes = {}
        old_hashes = json.loads(z.read('__H')) if '__H' in z.namelist() else {}
        for entry in z.infolist():  # keep the original order, replace in place
            if entry.filename == "__H":
                continue
            raw = files.pop(entry.filename, None)
            if raw is None:
                raw = z.read(entry)
            # folders are hashed only where the package already did that
            if not entry.filename.endswith('/') or entry.filename in old_hashes:
                hashes[entry.filename] = zlib.crc32(raw)
            out.writestr(entry, raw)
        for name, raw in files.items():  # new files go to the end
            hashes[name] = zlib.crc32(raw)
            out.writestr(name, raw)
        if "__H" in z.namelist():
            out.writestr("__H", encode(hashes))


def apply(built, out):
    meta = json.loads((BUNDLE / "content.json").read_text(encoding="utf8"))

    def change(z):
        data = json.loads(z.read("content.json"))
        data["content"].update(meta["added"])
        data["content"].update(meta["patched"])
        texts = json.loads(z.read("data/texts.json"))
        texts["data"].update(meta["texts"])
        client = "content/textures/GAME.atlas" in z.namelist()
        # the server package has no textures or sounds, only skeletons
        files = {n: (BUNDLE / "files" / n).read_bytes() for n in meta["files"]
                 if client or n.startswith("content/animations/")}
        files.update({"content.json": encode(data), "data/texts.json": encode(texts),
                      "content/animations/actor.json": (BUNDLE / "actor.json").read_bytes()})
        if client:
            # the release keeps the Welrod pages right before the pair-icons page
            atlas = z.read("content/textures/GAME.atlas")
            pages = (BUNDLE / "atlas.txt").read_bytes().replace(b"\r\n", b"\n").strip(b"\n")
            at = atlas.find(b"\nrestored-pair-icons.png")
            if at < 0:
                atlas = atlas.rstrip(b"\n") + b"\n\n" + pages + b"\n"
            else:
                atlas = atlas[:at].rstrip(b"\n") + b"\n\n" + pages + b"\n\n\n" + atlas[at:].lstrip(b"\n")
            files["content/textures/GAME.atlas"] = atlas
        return files
    rewrite(built, out, change)


def freeplay(built, out):
    loot = json.loads((BUNDLE / "freeplay-loot.json").read_text(encoding="utf8"))

    def change(z):
        data = json.loads(z.read("content.json"))
        items = data["content"]["freeplay-items-spawm"]["items"]
        for at, item in loot:  # same position as in the release
            if item not in items:
                items.insert(at, item)
        return {"content.json": encode(data)}
    rewrite(built, out, change)


if __name__ == "__main__":
    {"extract": extract, "apply": apply, "freeplay": freeplay}[sys.argv[1]](*sys.argv[2:])
