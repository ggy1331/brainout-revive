"""Assemble a playable Windows game folder with BrainOut.exe from a local build.

    build\\pyenv\\Scripts\\python.exe launcher\\make_game_folder.py [папка] [--jdk ПУТЬ_К_JDK17]

Default folder: ..\\BrainOut-dev (next to the repo). Needs a finished build:
bin/client and bin/server with jars (gradlew server:dist desktop:dist) and
packages (scripts/make_data.py + launcher/build_packages.py).

Layout is the same as in the release archive:
  BrainOut.exe   compiled from launcher/Launcher.cs (csc from .NET Framework)
  python/        embeddable Python 3.10 (downloaded once, cached in build/)
  jre/           slim JRE made by jlink from JDK 17 (made once)
  support/       launcher/home.py, release_update.py, local_changes.py
  backend/       tools/mock-backend (backend.py + services/*.py)
  client/        jar, version.txt, packages/*.zip
  server/        jar, *.json/*.xml/*.shuffle, maps/*.map, packages/*.zip
Running it again refreshes only these distribution files: saves (solo-data),
client/settings.json and logs are left untouched.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PY_VERSION = "3.10.11"
PY_URL = "https://www.python.org/ftp/python/%s/python-%s-embed-amd64.zip" % (PY_VERSION, PY_VERSION)
CSC = Path(os.environ.get("WINDIR", r"C:\Windows")) / r"Microsoft.NET\Framework64\v4.0.30319\csc.exe"
# same module list as make-client-zip.ps1, plus what the server needs
JRE_MODULES = ("java.base,java.desktop,java.naming,java.prefs,java.security.jgss,java.sql,"
               "jdk.unsupported,jdk.crypto.ec,jdk.zipfs,java.net.http,jdk.charsets,jdk.localedata,"
               "jdk.httpserver,java.management,java.logging,java.xml,java.scripting")


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sync_dir(src, dst, pattern):
    """Copy files matching pattern; drop stale ones with the same pattern."""
    dst.mkdir(parents=True, exist_ok=True)
    names = {p.name for p in src.glob(pattern) if p.is_file()}
    for old in dst.glob(pattern):
        if old.is_file() and old.name not in names:
            old.unlink()
    for name in names:
        copy(src / name, dst / name)


def need(path, hint):
    if not path.exists():
        sys.exit("Нет %s — %s" % (path, hint))


def python_embed(dest):
    if (dest / "python" / "python.exe").exists():
        return
    cache = ROOT / "build" / ("python-%s-embed-amd64.zip" % PY_VERSION)
    if not cache.exists():
        print("Скачиваю", PY_URL)
        cache.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(PY_URL, cache)
    with zipfile.ZipFile(cache) as z:
        z.extractall(dest / "python")


def find_jdk(arg):
    for c in [arg, os.environ.get("JAVA_HOME"), r"C:\Program Files\Java\jdk-17",
              *sorted((ROOT.parent / "tools").glob("jdk-17*"))]:
        if c and (Path(c) / "bin" / "jlink.exe").exists():
            return Path(c)
    sys.exit("Не найден JDK 17 с jlink: укажите --jdk ПУТЬ")


def jre(dest, jdk_arg):
    if (dest / "jre" / "bin" / "java.exe").exists():
        return
    jdk = find_jdk(jdk_arg)
    print("jlink из", jdk)
    subprocess.check_call([str(jdk / "bin" / "jlink.exe"), "--add-modules", JRE_MODULES,
                           "--strip-debug", "--no-header-files", "--no-man-pages",
                           "--compress=2", "--output", str(dest / "jre")])


def launcher_exe(dest):
    need(CSC, "компилятор C# из .NET Framework 4")
    icon = ROOT / "data" / "assets" / "main" / "icons" / "icon.ico"
    subprocess.check_call([str(CSC), "/nologo", "/target:winexe", "/optimize+",
                           "/r:System.Windows.Forms.dll", "/win32icon:" + str(icon),
                           "/out:" + str(dest / "BrainOut.exe"), str(ROOT / "launcher" / "Launcher.cs")])


def release_tag():
    try:
        return subprocess.check_output(["git", "describe", "--tags", "--abbrev=0"], cwd=ROOT,
                                       text=True).strip()
    except Exception:
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    jdk_arg = None
    if "--jdk" in args:
        i = args.index("--jdk")
        jdk_arg = args[i + 1]
        del args[i:i + 2]
    dest = Path(args[0]).resolve() if args else ROOT.parent / "BrainOut-dev"

    client, server = ROOT / "bin" / "client", ROOT / "bin" / "server"
    for jar in (client / "brainout-desktop.jar", server / "brainout-server.jar"):
        need(jar, "сначала gradlew.bat server:dist desktop:dist")
    need(client / "packages" / "base.zip", "сначала make_data.py и launcher/build_packages.py")
    dest.mkdir(parents=True, exist_ok=True)
    print("Папка игры:", dest)

    python_embed(dest)
    jre(dest, jdk_arg)
    launcher_exe(dest)

    sl = ROOT / "launcher"
    for name in ("home.py", "release_update.py", "local_changes.py"):
        copy(sl / name, dest / "support" / name)
    mb = ROOT / "tools" / "mock-backend"
    copy(mb / "backend.py", dest / "backend" / "backend.py")
    if (mb / "radio-tools").exists():
        for name in ("ffmpeg.exe", "node.exe", "yt-dlp.exe"):
            copy(mb / "radio-tools" / name, dest / "python" / "radio-tools" / name)
        for notice in (sl / "radio-licenses").glob("*"):
            if notice.is_file():
                copy(notice, dest / "python" / "radio-tools" / notice.name)
    services = dest / "backend" / "services"
    sync_dir(mb / "services", services, "*.py")

    copy(client / "brainout-desktop.jar", dest / "client" / "brainout-desktop.jar")
    (dest / "client" / "brainout-desktop.jar.radio-update").unlink(missing_ok=True)
    copy(client / "version.txt", dest / "client" / "version.txt")
    sync_dir(client / "packages", dest / "client" / "packages", "*.zip")

    copy(server / "brainout-server.jar", dest / "server" / "brainout-server.jar")
    for pattern in ("*.json", "*.xml", "*.shuffle"):
        for f in server.glob(pattern):
            copy(f, dest / "server" / f.name)
    sync_dir(server / "maps", dest / "server" / "maps", "*.map")
    sync_dir(server / "packages", dest / "server" / "packages", "*.zip")

    copy(sl / "README.txt", dest / "README.txt")
    copy(ROOT / "LICENSE", dest / "LICENSE.txt")
    tag = release_tag()
    if tag:
        # updater only offers releases newer than this mark
        (dest / ".brainout-release").write_text(tag)
    print("Готово:", dest / "BrainOut.exe", "(версия %s)" % tag if tag else "")


if __name__ == "__main__":
    main()
