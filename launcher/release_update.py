"""Download verified Windows releases and replace distribution files after a clean exit."""
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from http.client import IncompleteRead
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
REPO = "ggy1331/brainout-revive"
BASELINE = "v0.10.2"
MARKER = ".brainout-release"
CACHE = ".brainout-update"

def version(tag):
    if not re.fullmatch(r"v?[0-9]+(?:\.[0-9]+){1,3}", tag):
        raise ValueError("Неизвестный формат версии")
    numbers = tuple(map(int, tag.lstrip("v").split(".")))
    return numbers + (0,) * (4-len(numbers))

def distributable(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name or str(p) != name:
        raise ValueError("Недопустимый путь в архиве")
    if any(part.endswith((".", " ")) or Path(part).is_reserved() for part in p.parts):
        raise ValueError("Недопустимое имя файла")
    # Player profiles, custom settings, logs and room state live outside these distribution paths.
    if name in ("BrainOut.exe","LICENSE.txt","README.txt","client/version.txt","client/brainout-desktop.jar","server/brainout-server.jar"):
        return True
    if p.parts[0] in ("jre","python"):return len(p.parts)>1
    if p.parts[0] in ("support","backend"):return p.suffix==".py"
    if p.parts[:2] in (("client","packages"),("server","packages")):return len(p.parts)==3 and p.suffix==".zip"
    if p.parts[:2]==("server","maps"):return len(p.parts)==3 and p.suffix==".map"
    return len(p.parts)==2 and p.parts[0]=="server" and p.suffix in (".json",".xml",".shuffle")

def unpack(archive, dest, digest):
    sha = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):sha.update(block)
    if sha.hexdigest()!=digest:raise ValueError("Контрольная сумма загрузки не совпала")
    seen=set()
    with ZipFile(archive) as z:
        for entry in z.infolist():
            if entry.is_dir() or not distributable(entry.filename):continue
            name=entry.filename.casefold()
            if name in seen:raise ValueError("Повторяющийся путь в архиве")
            seen.add(name)
            path=dest/entry.filename
            path.parent.mkdir(parents=True,exist_ok=True)
            with z.open(entry) as src,path.open("xb") as out:shutil.copyfileobj(src,out)
    if not {"brainout.exe","client/brainout-desktop.jar","server/brainout-server.jar","support/home.py"} <= seen:
        raise ValueError("Релиз не содержит полной Windows-сборки")

def open_url(url,timeout=90,accept="application/vnd.github+json"):
    return urlopen(Request(url,headers={"User-Agent":"BrainOut-Windows-Updater","Accept":accept,
                                       "Accept-Language":"en"}),timeout=timeout)

def transient(error):
    return not isinstance(error, HTTPError) or error.code in (403,408,429,500,502,503,504)

class ReleaseAssetPage(HTMLParser):
    def __init__(self, tag):
        super().__init__()
        self.name = f"BrainOut-{tag}-Windows.zip"
        self.path = f"/{REPO}/releases/download/{tag}/{self.name}"
        self.link_found = False
        self.digest = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href") == self.path:
            self.link_found = True
        if tag == "clipboard-copy" and attrs.get("aria-label") == "Copy to clipboard digest for "+self.name:
            self.digest = attrs.get("value")

class ReleaseRedirect(HTTPRedirectHandler):
    # GitHub identifies its latest release in the redirect itself.
    def http_error_302(self, request, response, code, message, headers):
        return response

def web_release(page, current):
    request = Request(page+"latest", headers={"User-Agent":"BrainOut-Windows-Updater"})
    with build_opener(ReleaseRedirect()).open(request,timeout=60) as response:
        target = urljoin(page,response.headers.get("Location",""))
    if not target.startswith(page+"tag/"):
        raise ValueError("GitHub не вернул страницу релиза")
    tag = target[len(page+"tag/"):]
    if version(tag) <= version(current):
        return {"tag_name":tag}
    parser = ReleaseAssetPage(tag)
    with open_url(page+"expanded_assets/"+tag,60,"text/html") as response:
        parser.feed(response.read().decode("utf-8"))
    parser.close()
    if not parser.link_found or not re.fullmatch(r"sha256:[0-9a-f]{64}",parser.digest or ""):
        raise ValueError("В релизе не найден Windows-архив с контрольной суммой")
    return {"tag_name":tag, "assets":[{"name":parser.name, "digest":parser.digest,
                                       "browser_download_url":"https://github.com"+parser.path}]}

def release_info(current):
    api = "https://api.github.com/repos/"+REPO+"/releases/"
    page = "https://github.com/"+REPO+"/releases/"
    for attempt in range(3):
        try:
            endpoint = api+"latest"
            if attempt == 2:
                endpoint += "?check=" + str(int(time.time()))
            if attempt == 1:
                return web_release(page,current)
            with open_url(endpoint,12 if attempt == 0 else 60) as response:
                return json.load(response)
        except (URLError, TimeoutError, ConnectionError, IncompleteRead, ValueError) as exc:
            if not transient(exc) or attempt == 2:
                raise
            time.sleep(attempt + 1)

def download_asset(asset, archive):
    direct = asset["browser_download_url"]
    urls = (direct, asset.get("url",direct), direct)
    for attempt, url in enumerate(urls):
        try:
            with open_url(url,accept="application/octet-stream") as src, archive.open("wb") as out:
                shutil.copyfileobj(src,out)
            if "size" not in asset or archive.stat().st_size == asset["size"]:
                return
            if attempt == 2:
                raise ValueError("Загрузка прервана")
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
            if not transient(exc) or attempt == 2:
                raise
        time.sleep(attempt + 1)

def prepare(root):
    current=(root/MARKER).read_text().strip() if (root/MARKER).exists() else BASELINE
    release=release_info(current)
    tag=release["tag_name"]
    if version(tag)<=version(current):
        print("Установлена актуальная версия "+current+".");return 0
    asset=next(a for a in release["assets"] if a["name"]==f"BrainOut-{tag}-Windows.zip")
    digest=asset.get("digest","")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}",digest):raise ValueError("GitHub не предоставил SHA-256 релиза")
    cache=root/CACHE;cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache) as tmp:
        archive=Path(tmp)/"release.zip"
        download_asset(asset,archive)
        dest=Path(tmp)/"files";unpack(archive,dest,digest[7:])
        if (cache/"ready").exists():shutil.rmtree(cache/"ready")
        os.replace(dest,cache/"ready")
        (cache/"tag").write_text(tag)
    print("Скачана "+tag+". Перезапустить игру и установить обновление?");return 2

def apply(root):
    cache=root/CACHE;ready=cache/"ready";tag=(cache/"tag").read_text().strip();version(tag)
    backup=cache/"rollback"
    if backup.exists():raise RuntimeError("Обнаружена резервная копия незавершённого обновления: "+str(backup))
    backup.mkdir()
    changed=[]
    try:
        checked=[]
        for stage in sorted(ready.rglob("*")):
            if not stage.is_file():continue
            rel=stage.relative_to(ready)
            if not distributable(rel.as_posix()):raise ValueError(str(rel))
            target=root/rel
            if not target.resolve().is_relative_to(root.resolve()):raise ValueError(str(target))
            checked.append((stage,target))
        if (root/".brainout-local-base").is_dir():
            import importlib.util
            spec=importlib.util.spec_from_file_location("local_changes",root/"support/local_changes.py")
            helper=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)
            merged=helper.stage(root,ready,cache/"work")
            protected={target for _,target in merged}
            checked=[pair for pair in checked if pair[1] not in protected]+merged
        for stage,target in checked:
            rel=target.relative_to(root)
            target.parent.mkdir(parents=True,exist_ok=True)
            old=None
            if target.exists():
                old=backup/rel;old.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(target,old)
            # Retain the verified input so a failed commit can be rolled back and retried.
            pending=cache/"pending-file"
            shutil.copy2(stage,pending)
            os.replace(pending,target)
            changed.append((target,old))
        marker=cache/"version";marker.write_text(tag);os.replace(marker,root/MARKER)
    except BaseException:
        for target,old in reversed(changed):
            if old:os.replace(old,target)
            else:target.unlink(missing_ok=True)
        shutil.rmtree(backup)
        raise
    shutil.rmtree(cache)

def schedule(root):
    # The updater needs a private interpreter so the shipped runtime and EXE can also be updated.
    # Reuse a separate runtime per installation instead of leaving a new interpreter on disk each time.
    identity=hashlib.sha256(str(root.resolve()).casefold().encode()).hexdigest()[:16]
    helper=Path(os.environ.get("LOCALAPPDATA",tempfile.gettempdir()))/"BrainOut"/"Updater"/identity
    helper.mkdir(parents=True,exist_ok=True)
    shutil.copytree(root/"python",helper/"python",dirs_exist_ok=True)
    shutil.copy2(root/"support/release_update.py",helper/"apply.py")
    subprocess.Popen([str(helper/"python/python.exe"),str(helper/"apply.py"),"apply",str(root),str(os.getppid())],
                     creationflags=subprocess.CREATE_NO_WINDOW,cwd=helper)

def main():
    if sys.argv[1]=="prepare":
        sys.stdout.reconfigure(encoding="utf-8")
        try:return prepare(ROOT)
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
            detail = f" (HTTP {exc.code})" if isinstance(exc, HTTPError) else ""
            print("Не удалось получить обновление с GitHub"+detail+". Повторите проверку позже.")
            return 1
        except Exception as exc:print("Не удалось скачать обновление: "+str(exc));return 1
    root=Path(sys.argv[2])
    kernel=ctypes.windll.kernel32
    handle=kernel.OpenProcess(0x100000,False,int(sys.argv[3]))
    if handle:
        kernel.WaitForSingleObject(handle,0xffffffff);kernel.CloseHandle(handle)
    try:apply(root)
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None,str(exc),"Не удалось установить обновление",16)
    subprocess.Popen([str(root/"BrainOut.exe")],cwd=root)

if __name__=="__main__":sys.exit(main())
