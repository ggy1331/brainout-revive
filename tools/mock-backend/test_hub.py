"""Hub transitions: the owner leaves a running match alone, comes back, ends it for everybody.

Run:  build/pyenv/Scripts/python.exe tools/mock-backend/test_hub.py
Rooms are fakes: no game servers are started, no UDP port is opened.
"""
import secrets
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from services import hub as hubmod  # noqa: E402
from services.common import HttpError  # noqa: E402

OWNER, GUEST = "1", "2"


class Room:
    def __init__(self, rid, game):
        self.id, self.game, self.capacity, self.live = rid, game, 16, True

    def alive(self):
        return self.live


class Master:
    def __init__(self):
        self.lock = threading.RLock()
        self.lobby = Room("lobby-1", "lobby")
        self.rooms = {self.lobby.id: self.lobby}
        self.n = 0

    def find_or_create(self, kind, settings):
        return self.lobby

    def _spawn(self, kind, settings, capacity=16):
        self.n += 1
        room = Room("match-%d" % self.n, kind)
        self.rooms[room.id] = room
        return room

    def _wait_ready(self, room):
        pass


class App:
    def __init__(self):
        self.player_rooms = {}


class Ctx:
    def __init__(self, account, method, owner, args=None):
        self.account, self.method = account, method
        self.headers = {"X-Hub-Key": KEY} if owner else {}
        self.args = args or {}

    def arg(self, name, default=None, required=False):
        return self.args.get(name, default)


KEY = secrets.token_hex(8)
master = Master()
hubmod.game._master = lambda app: master
hubmod.token_from = lambda ctx: {"account": ctx.account}

hub = hubmod.Hub.__new__(hubmod.Hub)
hub.app = App()
hub.secret = KEY
hub.name, hub.uid = "test", "x"
hub.lock, hub.transition = threading.RLock(), threading.Lock()
hub.visits, hub.seen, hub.pending, hub.zones = {}, {}, {}, {}
hub.owner, hub.match, hub.members, hub.away = None, None, set(), set()
hub.maps = {"factory": ["deathmatch"]}
retired = []
hub.retire = retired.append


def call(account, action, method="POST", args=None):
    return hub.dispatch(Ctx(account, method, account == OWNER, args), action)


def state(account):
    return call(account, "state", "GET")


def move(account, room):
    hub.app.player_rooms[account] = room.id


def check(cond, text):
    print(("ok   " if cond else "FAIL ") + text)
    if not cond:
        sys.exit(1)


# both in the hub, the owner starts a match
move(OWNER, master.lobby); move(GUEST, master.lobby)
state(OWNER); state(GUEST)
call(OWNER, "match", args={"map": "factory", "mode": "deathmatch"})
match = hub.match
check(state(OWNER)["target"] == match.id and state(GUEST)["target"] == match.id, "both are sent into the match")
move(OWNER, match); move(GUEST, match)
check(state(OWNER)["target"] == "" and state(OWNER)["running"], "in the match, nothing pending")

# the owner leaves alone
call(OWNER, "home")
check(state(OWNER)["target"] == master.lobby.id, "owner: sent to the hub")
check(hub.match is match and match.alive() and not retired, "the match keeps running")
check(GUEST in hub.members and state(GUEST)["target"] == "", "the guest stays in the match")
move(OWNER, master.lobby)
s = state(OWNER); s2 = state(OWNER)
check(s["target"] == "" and s2["target"] == "", "owner in the hub is NOT pulled back into the match")
check(s["running"] and s["away"], "hub state: match running, owner away")

# the owner comes back
call(OWNER, "rejoin")
check(state(OWNER)["target"] == match.id, "rejoin: owner is sent into the running match")
move(OWNER, match)
check(not state(OWNER)["away"], "back in the match, not away any more")

# end for everybody
call(OWNER, "return")
check(state(OWNER)["target"] == master.lobby.id and state(GUEST)["target"] == master.lobby.id, "end match: everybody to the hub")
check(retired == [match] and hub.match is None, "the match room is retired")
move(OWNER, master.lobby); move(GUEST, master.lobby)
check(not state(OWNER)["running"], "hub state: no match running")

# rejoin without a match is refused
try:
    call(OWNER, "rejoin")
    check(False, "rejoin without a match is refused")
except HttpError:
    check(True, "rejoin without a match is refused")
print("all hub checks passed")
