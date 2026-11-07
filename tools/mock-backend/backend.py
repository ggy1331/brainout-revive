"""
BRAIN / OUT revive: local imitation of the Anthill Platform back-end.

One HTTP server, every Anthill service lives under its own path prefix:
    http://HOST:PORT/environment, /discovery, /login, /profile, /market, ...
Data is stored as JSON files in the data directory (default: <repo>/backend-data).

Reference for the protocol: the open source Anthill services
(https://github.com/anthill-platform) and the Java runtime used by the game.

Run:  python backend.py [--host 0.0.0.0] [--port 9511] [--data DIR] [--public-host IP]
"""

import argparse
import json
import logging
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import registry  # noqa: E402
from services.common import Ctx, HttpError, Storage  # noqa: E402

log = logging.getLogger("backend")


class Handler(BaseHTTPRequestHandler):
    server_version = "AnthillMock/0.1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # silence default stderr logging
        pass

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def _dispatch(self, method):
        parsed = urlparse(self.path)
        parts = [p for p in parsed.path.split("/") if p]
        query = {k: v[-1] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
        raw = self._read_body()
        form = {}
        ctype = self.headers.get("Content-Type", "")
        if raw and "application/x-www-form-urlencoded" in ctype:
            form = {k: v[-1] for k, v in parse_qs(raw.decode("utf-8"), keep_blank_values=True).items()}
        elif raw and "json" in ctype:
            try:
                form = json.loads(raw.decode("utf-8"))
            except ValueError:
                form = {}
        args = dict(query)
        if isinstance(form, dict):
            args.update(form)

        ctx = Ctx(self.server.app, method, parts, args, self.headers, raw)
        self.server.app.interface.host = self.connection.getsockname()[0]
        status, payload, headers = 404, {"error": "not found"}, {}
        try:
            if not parts:
                raise HttpError(404, "no service")
            service = registry.get(parts[0])
            if service is None:
                raise HttpError(404, "unknown service " + parts[0])
            result = service(ctx, parts[1:])
            if isinstance(result, tuple):
                status, payload = result[0], result[1]
                if len(result) > 2:
                    headers = result[2]
            else:
                status, payload = 200, result
        except HttpError as e:
            status, payload = e.status, e.body
        except Exception:
            traceback.print_exc()
            status, payload = 500, {"error": "internal error"}

        short_args = {k: (v if len(str(v)) < 200 else str(v)[:200] + "...") for k, v in args.items()}
        level = logging.INFO if status < 400 else logging.WARNING
        if parts == ["hub", "state"] and status == 200:
            level = logging.DEBUG
        log.log(level, "%s %s %s -> %s", method, parsed.path, json.dumps(short_args, ensure_ascii=False), status)

        if isinstance(payload, (dict, list)):
            # the Java runtime parses JSON only when Content-Type is exactly "application/json"
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            ctype = "application/json"
        elif isinstance(payload, bytes):
            body = payload
            ctype = "application/octet-stream"
        else:
            body = str(payload if payload is not None else "").encode("utf-8")
            ctype = "text/plain; charset=utf-8"

        ctype = headers.pop("Content-Type", ctype)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if (self.headers.get("Upgrade") or "").lower() == "websocket":
            parsed = urlparse(self.path)
            query = {k: v[-1] for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
            log.info("WEBSOCKET %s", parsed.path)
            self.close_connection = True
            if parsed.path.rstrip("/") == "/message/listen":
                from services import message
                message.serve_listen(self.server.app, self, query)
            elif parsed.path.startswith("/game/party/"):
                from services import party
                party.serve_session(self.server.app, self, parsed.path, query)
            else:
                self.send_error(404, "no websocket here")
            return
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")


class App:
    def __init__(self, base_url, storage, public_host="127.0.0.1", repo=".", java="java",
                 server_dir=None, logs_dir=None):
        self.interface = threading.local()
        self.base_url = base_url
        self.storage = storage
        self.lock = threading.RLock()
        self.public_host = public_host
        self.repo = repo
        self.java = java
        self.server_dir = server_dir or os.path.join(repo, "bin", "server")
        self.logs_dir = logs_dir or os.path.join(repo, "build", "rooms")
        self.log = log
        self.solo_name = None  # solo PvE backend of one player (progress synced with sync_host)
        self.sync_host = None

    def service_url(self, name):
        if hasattr(self, "hub"):
            return "http://%s:%s/%s" % (getattr(self.interface, "host", "127.0.0.1"), self.hub_port, name)
        return self.base_url + "/" + name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9511)
    ap.add_argument("--public-host", default="127.0.0.1",
                    help="address clients use to reach this backend (Radmin/LAN IP for friends)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--data", default=os.path.join(repo, "backend-data"))
    default_java = r"C:\Program Files\Java\jdk-17\bin\java.exe"
    ap.add_argument("--java", default=default_java if os.path.exists(default_java) else "java",
                    help="java used to start game servers on demand")
    ap.add_argument("--server-dir", default=None, help="folder with brainout-server.jar (default bin/server)")
    ap.add_argument("--logs-dir", default=None)
    ap.add_argument("--solo", metavar="NICK", default=None,
                    help="single player PvE: the hub is replaced with the Conflict Zone for one player")
    ap.add_argument("--sync-host", default=None,
                    help="host backend url (http://IP:9511) to sync the solo progress with")
    ap.add_argument("--sync-only", action="store_true", help="sync the solo progress with --sync-host and exit")
    a = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout)])
    base_url = "http://%s:%d" % (a.public_host, a.port)
    app = App(base_url, Storage(a.data), public_host=a.public_host, repo=repo, java=a.java,
              server_dir=a.server_dir, logs_dir=a.logs_dir)
    from services import revive, game
    app.storage.on_put = lambda collection, key: revive.on_put(app, collection, key)
    if a.solo:
        app.solo_name = a.solo
        app.sync_host = (a.sync_host or "").rstrip("/") or None
        solo = dict(game.GAMES["freeplay"], max=1, env={"game_max_players": "1"})
        game.GAMES["freeplay"] = solo
        game.GAMES["lobby"] = solo
        if app.sync_host:
            log.info("Sync with %s: %s", app.sync_host, revive.sync_with_host(app, a.solo, app.sync_host))
        if a.sync_only:
            return
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    if os.environ.get("BRAINOUT_HUB_KEY"):
        from services.hub import Hub
        app.hub_port = srv.server_port
        app.hub = Hub(app, os.environ["BRAINOUT_HUB_NAME"], os.environ["BRAINOUT_HUB_KEY"])
    srv.app = app
    log.info("Anthill mock backend on %s:%d, public url %s, data %s", a.host, a.port, base_url, a.data)
    log.info("Services: %s", ", ".join(sorted(registry.names())))
    srv.serve_forever()


if __name__ == "__main__":
    main()
