"""
anthill-game-master imitation: regions, rooms and on-demand game servers.

GET  /game/regions                                   -> {"regions": {...}, "my_region": "local"}
GET  /game/status                                    -> {"players": n}
POST /game/join/<app>/<game>/<version>   settings, auto_create  -> {id, key, location{host, ports}, settings}
POST /game/create/<app>/<game>/<version> settings    -> {id, key, location{host, ports, init}}
POST /game/room/<app>/<room_id>/join                 -> {id, key, location, settings}
GET  /game/rooms/<app>/<game>/<version>              -> {"rooms": [...]}   (server browser)

Game servers are started here (like game-master + game-controller did): java -jar brainout-server.jar
in bin/server with online env (login_access_token, discovery_services, room_id, room_settings,
server_settings). One room per (game, settings) is reused while its process is alive.
The room key is not checked by the game server (no game-controller); the client also sends its
access token and the server authenticates the player with it.
"""

import atexit
import json
import os
import secrets
import socket
import subprocess
import threading
import time

from .common import HttpError
from .login import token_from, issue_token, ADMIN_SCOPES

# game name (as the client asks for it) -> server command line and env
GAMES = {
    "lobby":    {"args": ["--mode", "lobby", "--settings", "server-lobby.json"], "bots": 0, "max": 100},
    "main":     {"args": ["--settings", "server-settings.json", "--maps", "maps-set.json"], "bots": 8, "max": 16},
    "freeplay": {"args": ["--mode", "free", "--settings", "server-free.json", "--map", "freeplay-maps.shuffle"],
                 "bots": 0, "max": 4, "env": {"game_max_players": "4"}},
    "duel":     {"args": ["--mode", "duel", "--settings", "server-duel.json"], "bots": 0, "max": 2},
    "zombie":   {"args": ["--settings", "server-settings.json", "--maps", "zombie-set.json"], "bots": 0, "max": 8},
    "custom":   {"args": ["--settings", "server-settings.json", "--maps", "maps-set.json"], "bots": 8, "max": 16},
}

FIRST_PORT = 36600
READY_TIMEOUT = 90


class Room:
    def __init__(self, room_id, game, settings, ports, proc, log_path):
        self.id = room_id
        self.game = game
        self.settings = settings
        self.ports = ports
        self.proc = proc
        self.log_path = log_path
        self.started = time.time()
        self.ready = False

    def alive(self):
        return self.proc.poll() is None

    def check_ready(self):
        if self.ready:
            return True
        try:
            with open(self.log_path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError:
            return False
        if "Initialized!" in text:
            self.ready = True
        return self.ready


class GameMaster:
    def __init__(self, app):
        self.app = app
        self.rooms = {}
        self.lock = threading.RLock()
        self.next_room = 1
        atexit.register(self.shutdown)

    # ------------------------------------------------------------ servers

    def _free_ports(self):
        used = {p for r in self.rooms.values() for p in r.ports}
        port = FIRST_PORT
        while True:
            ports = [port, port + 1, port + 2]
            if not (set(ports) & used) and all(self._port_free(p) for p in ports):
                return ports
            port += 3

    @staticmethod
    def _port_free(port):
        s = socket.socket()
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False
        finally:
            s.close()

    def _spawn(self, game, settings, capacity=None):
        cfg = GAMES[game]
        app = self.app
        room_id = str(self.next_room)
        self.next_room += 1
        ports = self._free_ports()

        server_token = issue_token(app, "0", "server:room-" + room_id, ADMIN_SCOPES)
        services = {sid: app.service_url(sid) for sid in
                    ("login", "profile", "promo", "event", "game", "leaderboard", "message", "store", "social",
                     "static", "report", "blog", "market", "discovery", "environment")}
        env = dict(os.environ)
        env.update({
            "login_access_token": server_token,
            "discovery_services": json.dumps(services),
            "room_id": room_id,
            "server_settings": json.dumps({"bots": cfg.get("bots", 0)}),
            "game_max_players": str(capacity or cfg.get("max", 16)),
        })
        env.update(cfg.get("env", {}))
        room_settings = {k: v for k, v in (settings or {}).items() if k in ("mode", "map", "preset", "keep-mode")}
        if room_settings:
            env["room_settings"] = json.dumps(room_settings)
        else:
            env.pop("room_settings", None)

        os.makedirs(app.logs_dir, exist_ok=True)
        log_path = os.path.join(app.logs_dir, "room-%s-%s.log" % (room_id, game))
        logf = open(log_path, "w", encoding="utf-8")
        cmd = [app.java, "-jar", "brainout-server.jar", "no", ",".join(map(str, ports))] + cfg["args"]
        proc = subprocess.Popen(cmd, cwd=app.server_dir, env=env, stdout=logf, stderr=subprocess.STDOUT,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        room = Room(room_id, game, settings or {}, ports, proc, log_path)
        room.capacity = capacity or cfg.get("max", 16)
        self.rooms[room_id] = room
        app.log.info("Room %s: started %s server on ports %s (pid %s), log %s",
                     room_id, game, ports, proc.pid, log_path)
        return room

    def _wait_ready(self, room):
        deadline = time.time() + READY_TIMEOUT
        while time.time() < deadline:
            if not room.alive():
                raise HttpError(500, {"error": "game server exited, see " + room.log_path})
            if room.check_ready():
                return
            time.sleep(0.5)
        raise HttpError(503, {"error": "game server is not ready"})

    def cleanup(self):
        with self.lock:
            for rid in [rid for rid, r in self.rooms.items() if not r.alive()]:
                self.app.log.info("Room %s (%s) has exited", rid, self.rooms[rid].game)
                del self.rooms[rid]

    def shutdown(self):
        for r in list(self.rooms.values()):
            if r.alive():
                r.proc.terminate()

    # ------------------------------------------------------------ rooms

    def find_or_create(self, game, settings, auto_create=True):
        if game not in GAMES:
            raise HttpError(404, {"error": "unknown game " + game})
        self.cleanup()
        wanted = {k: v for k, v in (settings or {}).items() if k in ("mode", "map", "preset")}
        with self.lock:
            room = None
            for r in self.rooms.values():
                if r.game == game and {k: v for k, v in r.settings.items() if k in wanted} == wanted:
                    room = r
                    break
            if room is None:
                if not auto_create:
                    raise HttpError(404, {"error": "no rooms"})
                room = self._spawn(game, settings)
        self._wait_ready(room)
        return room

    def room_out(self, room, with_key=True):
        out = {
            "id": room.id,
            "location": {"host": getattr(self.app.interface, "host", self.app.public_host) if hasattr(self.app, "hub") else self.app.public_host, "ports": room.ports},
            "settings": room.settings,
            "players": 0,
            "max_players": room.capacity,
            "game_name": room.game,
            "game_version": "valpha2",
            "game_server": room.game,
        }
        if with_key:
            out["key"] = secrets.token_hex(16)
        return out


def _remember_room(app, player, room):
    """Last room of every player (friends see "in game" and can be invited there)."""
    if not hasattr(app, "player_rooms"):
        app.player_rooms = {}
    app.player_rooms[str(player["account"])] = room.id


def _master(app):
    if not hasattr(app, "game_master"):
        app.game_master = GameMaster(app)
    return app.game_master


def handle(ctx, rest):
    app = ctx.app
    gm = _master(app)
    call = rest[0] if rest else ""

    if call == "status":
        return {"players": 0}

    if call == "regions":
        token_from(ctx)
        return {"regions": {"local": {"settings": {}, "location": {"x": 0, "y": 0}}}, "my_region": "local"}

    if call in ("join", "create") and len(rest) >= 3:
        player = token_from(ctx)
        game = rest[2]
        visit = getattr(getattr(app, "hub", None), "visits", {}).get(str(player["account"]))
        if visit:
            if call != "join" or game != "lobby":
                raise HttpError(403)
            return visit.request("/game/join/brainout/lobby", {}, 90)
        settings = ctx.json_arg("create_settings", None) or ctx.json_arg("settings", {}) or {}
        if not isinstance(settings, dict):
            settings = {}
        auto_create = call == "create" or str(ctx.arg("auto_create", "true")).lower() == "true"
        room = gm.find_or_create(game, settings, auto_create)
        _remember_room(app, player, room)
        out = gm.room_out(room)
        if call == "create":
            out["location"]["init"] = room.settings
        return out

    if call == "room" and len(rest) >= 4 and rest[3] == "join":
        player = token_from(ctx)
        visit = getattr(getattr(app, "hub", None), "visits", {}).get(str(player["account"]))
        if visit:
            if not rest[2].isdigit():
                raise HttpError(400)
            return visit.request("/game/room/brainout/" + rest[2] + "/join", {}, 90)
        gm.cleanup()
        room = gm.rooms.get(rest[2])
        if room is None:
            raise HttpError(404, {"error": "no such room"})
        gm._wait_ready(room)
        _remember_room(app, player, room)
        return gm.room_out(room)

    if call == "rooms" and len(rest) >= 3:
        gm.cleanup()
        game = rest[2]
        return {"rooms": [gm.room_out(r, with_key=False) for r in gm.rooms.values()
                          if r.game == game and r.ready]}

    raise HttpError(404, {"error": "unknown game call " + "/".join(rest)})
