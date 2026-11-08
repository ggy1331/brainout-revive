"""Visit another LAN room while keeping the local account and launcher alive."""
from http.client import HTTPConnection
from ipaddress import IPv4Address
import json
import secrets
import threading
import time

from .common import HttpError

FIELDS = ("name", "layout", "slots", "favorites", "items", "level", "stats",
          "badges", "cont", "limits", "trophies", "last-daily-claim")
MISSING = object()


def reconcile(start, home, guest):
    if guest == start or home == guest:
        return home
    if home == start:
        return guest
    if all(isinstance(v, dict) for v in (start, home, guest)):
        result = {}
        for key in home.keys() | guest.keys() | start.keys():
            value = reconcile(start.get(key, MISSING), home.get(key, MISSING), guest.get(key, MISSING))
            if value is not MISSING:
                result[key] = value
        return result
    return home


class Visit:
    def __init__(self, app, account, endpoint):
        host, port = endpoint.rsplit(":", 1)
        self.host, self.port = str(IPv4Address(host)), int(port)
        if not 1 <= self.port <= 65535:
            raise ValueError("port")
        self.app, self.account = app, account
        self.token = None
        self.last_read = 0
        self.lock = threading.RLock()

    def request(self, path, data=None, timeout=4):
        conn = HTTPConnection(self.host, self.port, timeout=timeout)
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["X-Token"] = self.token
        try:
            conn.request("POST" if data is not None else "GET", path,
                         json.dumps(data).encode() if data is not None else None, headers)
            response = conn.getresponse()
            if response.status != 200:
                raise HttpError(response.status)
            return json.loads(response.read())
        finally:
            conn.close()

    def enter(self):
        info = self.request("/hub/info")
        if info.get("protocol") != "brainout-hub-10" or info.get("id") == self.app.hub.uid:
            raise HttpError(409)
        store = self.app.storage
        identity = "%s-%s-%s" % (self.account, self.host, self.port)
        with self.app.lock:
            auth = store.get("lan-guests", identity)
            if not auth:
                auth = {"username": "guest-" + secrets.token_hex(16), "key": secrets.token_hex(32)}
                store.put("lan-guests", identity, auth)
            profile = store.get("profiles", self.account)
            if not profile:
                raise HttpError(409, {"error": "Домашний профиль ещё загружается."})
            self.previous = {k: profile[k] for k in FIELDS if k in profile}
        self.token = self.request("/login/auth", dict(auth, credential="anonymous",
                                  scopes="game,profile,profile_write"))["token"]
        self.request("/profile/profile/me", {"data": self.previous, "merge": False})
        room = self.request("/game/join/brainout/lobby", {}, 90)
        next_room = self.request("/hub/state").get("target")
        return {"target": next_room or room["id"], "roomToken": self.token}

    def sync(self):
        with self.lock:
            incoming = self.request("/profile/profile/me")
            if not isinstance(incoming, dict) or "slots" not in incoming:
                return
            remote = {k: incoming[k] for k in FIELDS if k in incoming}
            if remote != self.previous:
                with self.app.lock:
                    profile = self.app.storage.get("profiles", self.account)
                    if not profile:
                        return
                    for k, value in remote.items():
                        merged = reconcile(self.previous.get(k, MISSING), profile.get(k, MISSING), value)
                        if merged is not MISSING:
                            profile[k] = merged
                    self.app.storage.put("profiles", self.account, profile)
                self.previous = remote
            self.last_read = time.monotonic()
