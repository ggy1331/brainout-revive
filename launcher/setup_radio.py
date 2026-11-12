"""Prepare portable radio tools, without installing system software.

Uses existing ffmpeg/node from PATH, downloads yt-dlp from its official release
and verifies the release SHA256 manifest. Run before make_game_folder.py.
"""
from pathlib import Path
import hashlib
import shutil
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'tools' / 'mock-backend' / 'radio-tools'
    target.mkdir(exist_ok=True)
    for name in ('ffmpeg', 'node'):
        found = shutil.which(name)
        if not found:
            raise SystemExit('Missing ' + name + ' in PATH; supply its portable executable in ' + str(target))
        shutil.copy2(found, target / (name + '.exe'))
    base = 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/'
    with urllib.request.urlopen(base + 'SHA2-256SUMS', timeout=60) as r:
        manifest = r.read().decode()
    expected = next(line.split()[0] for line in manifest.splitlines() if line.split()[-1].lstrip('*') == 'yt-dlp.exe')
    temp = target / 'yt-dlp.download'
    with urllib.request.urlopen(base + 'yt-dlp.exe', timeout=60) as r, temp.open('wb') as out:
        shutil.copyfileobj(r, out)
    if hashlib.sha256(temp.read_bytes()).hexdigest() != expected:
        raise SystemExit('yt-dlp checksum mismatch')
    temp.replace(target / 'yt-dlp.exe')
    print('Portable radio tools ready:', target)


if __name__ == '__main__':
    main()
