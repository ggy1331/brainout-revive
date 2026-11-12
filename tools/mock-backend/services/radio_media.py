"""YouTube metadata in RAM and bounded PCM pipes. Never writes media/cache files."""
import json
import math
import time
import socket
from collections import OrderedDict
import re
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .common import HttpError

_lock = threading.Lock()
_metadata = OrderedDict()


def clear_legacy_cache(app):
    """One-time migration: only our old media filenames, never the saved playlist."""
    root = Path(app.storage.root).resolve()
    folder = root / 'radio-cache'
    if not folder.is_dir() or folder.resolve().parent != root:
        return
    for path in folder.iterdir():
        if (re.fullmatch(r'[A-Za-z0-9_-]{11}\.(?:ogg|webm|m4a|mp3|json)(?:\.part)?', path.name)
                and path.is_file() and path.resolve().parent == folder.resolve()):
            try:
                path.unlink()
            except OSError:
                pass  # A previous client can still hold a file open on Windows.
    try:
        folder.rmdir()  # Empty only; unrelated files are deliberately retained.
    except OSError:
        pass


def video_id(value):
    value = str(value).strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', value):
        return value
    p = urlparse(value)
    if p.scheme not in ('http', 'https') or p.username or p.password:
        raise HttpError(400, {'error': 'Вставьте ссылку YouTube.'})
    if p.hostname in ('youtu.be', 'www.youtu.be'):
        candidate = p.path.strip('/')
    elif p.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        candidate = parse_qs(p.query).get('v', [''])[0] if p.path == '/watch' else p.path.rsplit('/', 1)[-1] if p.path.startswith(('/shorts/', '/embed/')) else ''
    else:
        candidate = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
        raise HttpError(400, {'error': 'Не удалось распознать ролик YouTube.'})
    return candidate


def tool(name):
    backend = Path(__file__).resolve().parents[1]
    # v0.12.3's updater already allows every file under python/, but excludes
    # backend/*.exe. This location makes the first radio update self-contained.
    candidates = [backend.parent / 'python' / 'radio-tools' / (name + '.exe'),
                  backend / 'radio-tools' / (name + '.exe')]
    found = next((str(p) for p in candidates if p.exists()), None) or shutil.which(name)
    if not found:
        raise HttpError(503, {'error': 'Для радио не найден ' + name + '. Запустите launcher/setup_radio.py.'})
    return found


def run(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                timeout=90, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HttpError(503, {'error': 'YouTube не ответил вовремя.'}) from exc
    if result.returncode:
        raise HttpError(422, {'error': 'Трек недоступен на YouTube.'})
    return result.stdout


def source(app, value):
    video = video_id(value)
    key = (id(app), video)
    with _lock:
        cached = _metadata.get(key)
        if cached and cached[0] > time.monotonic():
            _metadata.move_to_end(key)
            return dict(cached[1])
    downloader = tool('yt-dlp')
    base = [downloader, '--ignore-config', '--no-cache-dir', '--no-playlist', '--no-warnings',
            '--socket-timeout', '15', '--retries', '1', '--no-progress',
            '--dump-single-json', '--skip-download', '-f', 'bestaudio[protocol=https]/bestaudio']
    node = shutil.which('node')
    bundled_node = Path(downloader).parent / 'node.exe'
    if bundled_node.exists():
        node = str(bundled_node)
    if node:
        base += ['--js-runtimes', 'node:' + node]
    info = json.loads(run(base + ['https://www.youtube.com/watch?v=' + video]))
    duration = info.get('duration') or 0
    if info.get('is_live') or not 1 <= duration <= 3600:
        raise HttpError(400, {'error': 'Радио поддерживает записи длительностью до часа.'})
    url = info.get('url', '')
    if urlparse(url).scheme != 'https':
        raise HttpError(422, {'error': 'YouTube не предоставил поток звука.'})
    result = {'video': video, 'title': str(info.get('title', video))[:180], 'duration': duration,
              'url': url, 'headers': info.get('http_headers', {})}
    with _lock:
        _metadata[key] = (time.monotonic() + 1200, result)
        while len(_metadata) > 128:
            _metadata.popitem(last=False)
    return dict(result)


def resolve(app, value):
    info = source(app, value)
    return {k: info[k] for k in ('video', 'title', 'duration')}


class AudioStream:
    """The handler owns this pipe and closes the exact decoder when HTTP closes."""
    def __init__(self, app, value, position):
        try:
            position = float(position)
        except (TypeError, ValueError):
            raise HttpError(400)
        if not math.isfinite(position) or not 0 <= position <= 3600:
            raise HttpError(400)
        self.app, self.video, self.position = app, video_id(value), position

    def serve(self, handler):
        info = source(self.app, self.video)
        headers = ''.join(str(k) + ': ' + str(v) + '\r\n' for k, v in info['headers'].items()
                          if not any(c in str(k) + str(v) for c in '\r\n'))
        args = [tool('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-nostdin',
                '-rw_timeout', '15000000', '-ss', str(self.position)]
        if headers:
            args += ['-headers', headers]
        args += ['-i', info['url'], '-vn', '-ac', '2', '-ar', '48000', '-f', 's16le', 'pipe:1']
        proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, bufsize=0,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        timer = threading.Timer(25, lambda: proc.kill() if proc.poll() is None else None)
        timer.daemon = True
        timer.start()
        try:
            first = proc.stdout.read(8192)
            timer.cancel()
            if not first:
                with _lock:
                    _metadata.pop((id(self.app), self.video), None)
                raise HttpError(422, {'error': 'Не удалось открыть аудиопоток.'})
            handler.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 32768)
            handler.connection.settimeout(15)
            handler.close_connection = True
            handler.send_response(200)
            handler.send_header('Content-Type', 'audio/pcm')
            handler.send_header('Cache-Control', 'no-store')
            handler.send_header('Connection', 'close')
            handler.end_headers()
            chunk = first
            while chunk:
                handler.wfile.write(chunk)
                chunk = proc.stdout.read(8192)
        except (BrokenPipeError, ConnectionError, OSError):
            pass
        finally:
            timer.cancel()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            proc.stdout.close()


def media(app, value, position=0):
    return AudioStream(app, value, position)
