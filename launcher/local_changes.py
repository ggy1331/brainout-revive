"""Three-way merge for the locally modified files of a BrainOut installation."""
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile
import zlib

ABSENT = object()
BASE = ".brainout-local-base"


def fingerprint(path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.digest()


def conflict(key):
    raise ValueError("Конфликт обновления в " + key + ". Локальная версия сохранена.")


def merge_json(base, local, new, key):
    if local == base or local == new:
        return new
    if new == base:
        return local
    if all(isinstance(x, dict) for x in (base, local, new)):
        result = {}
        for k in dict.fromkeys([*new, *local, *base]):
            v = merge_json(base.get(k, ABSENT), local.get(k, ABSENT), new.get(k, ABSENT), key+"/"+k)
            if v is not ABSENT:
                result[k] = v
        return result
    if all(isinstance(x, list) for x in (base, local, new)):
        # Stable class order means the two edits touched the same component objects.
        if all(all(isinstance(v, dict) and "class" in v for v in seq) for seq in (base, local, new)):
            ids = [[v["class"] for v in seq] for seq in (base, local, new)]
            if ids[0] == ids[1] == ids[2] and len(set(ids[0])) == len(ids[0]):
                return [merge_json(a,b,c,key+"/"+a["class"]) for a,b,c in zip(base,local,new)]
    conflict(key)


def compact(obj):
    return json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf8")


def merge_archive(base, local, new, dest):
    with ZipFile(base) as b, ZipFile(local) as l, ZipFile(new) as n, ZipFile(dest,"w",ZIP_DEFLATED,compresslevel=3) as out:
        hashes = {} if "__H" in n.namelist() else None
        for k in dict.fromkeys(n.namelist()+l.namelist()+b.namelist()):
            if hashes is not None and k == "__H":
                continue
            infos = [z.NameToInfo.get(k) for z in (b,l,n)]
            a,v,w = [(i.CRC,i.file_size) if i else None for i in infos]
            if v == a or v == w:
                chosen = n
            elif w == a:
                chosen = l
            else:
                chosen = None
            if chosen is not None:
                if k not in chosen.NameToInfo:
                    continue
                data = chosen.read(k)
            elif all(infos) and k.endswith(".json"):
                data = compact(merge_json(*(json.loads(z.read(k)) for z in (b,l,n)),key=k))
            elif all(infos) and k.endswith(".atlas"):
                prev,ours,theirs=(z.read(k).rstrip() for z in (b,l,n))
                if not ours.startswith(prev+b"\n"):
                    conflict(k)
                suffix=ours[len(prev):]
                if any(page.strip() in theirs.splitlines() for page in suffix.splitlines() if page.strip().endswith(b".png")):
                    conflict(k)
                data = theirs + suffix + b"\n"
            else:
                conflict(k)
            out.writestr(k,data)
            if hashes is not None and not k.endswith("/"):
                hashes[k] = zlib.crc32(data)
        if hashes is not None:
            out.writestr("__H",compact(hashes))


def merge_file(base,local,new,dest):
    a,v,w=map(fingerprint,(base,local,new))
    dest.parent.mkdir(parents=True,exist_ok=True)
    if v == a or v == w:
        shutil.copy2(new,dest)
    elif w == a and local.is_file():
        shutil.copy2(local,dest)
    elif all((a,v,w)) and new.suffix in (".zip",".jar"):
        merge_archive(base,local,new,dest)
    else:
        conflict(str(local))


def stage(root,ready,work):
    """Prepare every merge before changing any live file or the saved baseline."""
    baseline=root/BASE
    if not baseline.is_dir():
        return []
    replacements=[]
    for prev in baseline.rglob("*"):
        if not prev.is_file():
            continue
        rel=prev.relative_to(baseline)
        incoming=ready/rel
        if not incoming.is_file():
            continue
        merged=work/"merged"/rel
        merge_file(prev,root/rel,incoming,merged)
        replacements.append((merged,root/rel))
        replacements.append((incoming,prev))
    return replacements
