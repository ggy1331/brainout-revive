"""LAN discovery and group transitions for one locally hosted BrainOut hub."""
import json
import secrets
import socket
import threading
import time
from pathlib import Path

from . import game
from .common import HttpError
from .login import token_from

PORT = 39518
QUERY = b"BrainOut hub discovery/10"


class Hub:
    def __init__(self, app, name, key):
        self.app = app
        self.secret = key
        self.name = name
        self.uid = secrets.token_hex(12)
        self.lock = threading.RLock()
        self.transition = threading.Lock()
        self.seen = {}
        self.pending = {}
        self.owner = None
        self.match = None
        self.members = set()
        self.zones = {}
        with open(Path(app.server_dir) / "maps-set.json", encoding="utf-8-sig") as f:
            data = json.load(f)
        self.maps = {s["map"]: s["mode"].split(",") for s in data["sets"]
                     if s["map"] in data["maps"]}
        with open(Path(app.server_dir) / "zombie-set.json", encoding="utf-8-sig") as f:
            for entry in json.load(f)["sets"]:
                self.maps.setdefault(entry["map"], []).append("zombie")
        self.maps["duel"] = ["duel"]
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("", PORT))
        threading.Thread(target=self.announce, daemon=True).start()

    def room(self, account):
        rid = getattr(self.app, "player_rooms", {}).get(account)
        return game._master(self.app).rooms.get(rid)

    def in_lobby(self, account):
        room = self.room(account)
        return room and room.game == "lobby" and self.seen.get(account, 0) > time.monotonic() - 12

    def announce(self):
        while True:
            try:
                data, addr = self.listener.recvfrom(65535)
                if data != QUERY:
                    continue
                info = self.info()
                if not info:
                    continue
                self.listener.sendto(json.dumps(info).encode(), addr)
            except (ConnectionResetError, ConnectionRefusedError):
                continue
            except OSError:
                self.app.log.exception("Hub discovery stopped")
                return

    def info(self):
        with self.lock:
            in_match = self.match and self.match.alive()
            if not in_match and not self.in_lobby(self.owner):
                return None
            return {"protocol": "brainout-hub-10", "id": self.uid, "name": self.name,
                    "match": bool(in_match),
                    "players": (sum(1 for a in self.members if self.seen.get(a, 0) > time.monotonic() - 12) if in_match else sum(1 for a in self.seen if self.in_lobby(a))), "port": self.app.hub_port}

    def dispatch(self, ctx, action):
        if action == "info" and ctx.method == "GET":
            info = self.info()
            if info is None:
                raise HttpError(404)
            return info
        account = str(token_from(ctx)["account"])
        master = game._master(self.app)
        owner = secrets.compare_digest(ctx.headers.get("X-Hub-Key", ""), self.secret)
        with self.lock:
            if owner:
                self.owner = account
            if action == "leave" and ctx.method == "POST" and not owner:
                self.members.discard(account)
                self.pending.pop(account, None)
                self.seen.pop(account, None)
                return {"ok": True}
            if action == "maps":
                return {"maps": self.maps}
            if action == "state":
                self.seen[account] = time.monotonic()
                room = self.room(account)
                if self.match and not self.match.alive():
                    self.members.clear()
                    self.pending = {a: t for a, t in self.pending.items() if t != self.match.id}
                    self.match = None
                if self.match and room and room.game == "lobby" and account not in self.zones:
                    active = sum(a == self.owner or self.seen.get(a, 0) > time.monotonic() - 12 for a in self.members)
                    if account in self.members or active < self.match.capacity:
                        self.members.add(account)
                        self.pending[account] = self.match.id
                target = self.pending.get(account)
                if room and room.id == target:
                    self.pending.pop(account, None)
                    target = None
                return {"target": target or "", "room": room.game if room else "",
                        "match": bool(self.match and account in self.members)}
        if action not in ("match", "return", "zone") or ctx.method != "POST":
            raise HttpError(404)
        with self.transition:
            with self.lock:
                current = self.room(account)
                if not current:
                    raise HttpError(409)
                if action == "match":
                    map_id, mode = ctx.arg("map"), ctx.arg("mode")
                    if not owner or current.game != "lobby" or self.match:
                        raise HttpError(403)
                    participants = {a for a in self.seen if self.in_lobby(a)} | {account}
                    choices = [(m, g) for m, modes in self.maps.items() for g in modes
                               if (not map_id or m == map_id) and (not mode or mode == g)
                               and (g != "duel" or len(participants) <= 2)]
                    if not choices:
                        raise HttpError(409, {"error": "Для дуэли в хабе должно быть не больше двух игроков."} if mode == "duel" else {"error":"Нет подходящей карты."})
                    map_id, mode = secrets.choice(choices)
                if action == "zone" and (current.game != "lobby" or account in self.members):
                    raise HttpError(409)
            if action == "match":
                with master.lock:
                    kind = mode if mode in ("duel", "zombie") else "main"
                    room = master._spawn(kind, {"map": map_id, "mode": mode, "keep-mode": True},
                                         capacity=2 if mode == "duel" else max(16, len(participants)))
                try:
                    master._wait_ready(room)
                except Exception:
                    if room.alive():
                        room.proc.terminate()
                    raise
                with self.lock:
                    self.match = room
                    self.members = participants
                    for a in participants:
                        self.pending[a] = room.id
            elif action == "zone":
                with master.lock:
                    room = self.zones.get(account)
                    if not room or not room.alive():
                        room = master._spawn("freeplay", {})
                        self.zones[account] = room
                master._wait_ready(room)
                with self.lock:
                    self.pending[account] = room.id
            else:
                lobby = master.find_or_create("lobby", {})
                with self.lock:
                    if owner and self.match:
                        old = self.match
                        for a in self.members:
                            self.pending[a] = lobby.id
                        self.members.clear()
                        self.match = None
                        self.retire(old)
                    else:
                        self.members.discard(account)
                    self.pending[account] = lobby.id
                    zone = self.zones.pop(account, None)
                    if zone:
                        self.retire(zone)
        return {"ok": True}

    def retire(self, room):
        def stop():
            if room.alive():
                room.proc.terminate()
        timer = threading.Timer(15, stop)
        timer.daemon = True
        timer.start()


def handle(ctx, rest):
    if not hasattr(ctx.app, "hub") or len(rest) != 1:
        raise HttpError(404)
    return ctx.app.hub.dispatch(ctx, rest[0])
