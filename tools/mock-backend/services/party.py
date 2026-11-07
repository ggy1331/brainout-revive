"""Parties of the game service (play the Conflict Zone together with a partner).

WebSocket JSON-RPC 2.0, as anthill-runtime-java GameService.PartySession expects:
  /game/party/create/<app>/<version>/<game>/session?max_members=&auto_start=&room_settings=&access_token=
  /game/party/<id>/session?access_token=
Server -> client calls (always with an id, the runtime ignores calls without one):
  party   {party_info: {party: {id, num_members, max_members, settings}, members: [...]}}
  message {message_type: player_joined | player_left | game_starting | game_start_failed | game_started
                         | party_closed, payload: {...}}
Client -> server: leave_party, start_game, close_party, send_message, join_party.
When the party is full (auto_start) the game master finds/starts the room and every member gets
game_started {id, slot, key, location{host, ports}, settings}.
"""

import json
import threading
import uuid

from .common import HttpError
from .login import resolve_token


class Member:
    def __init__(self, ws, account, name, profile):
        self.ws = ws
        self.account = account
        self.name = name
        self.profile = profile or {}
        self.role = 0

    def out(self):
        return {"account": self.account, "role": self.role, "profile": self.profile}


class Party:
    def __init__(self, party_id, game, max_members, settings, room_settings, auto_start, auto_close):
        self.id = party_id
        self.game = game
        self.max_members = max_members
        self.settings = settings
        self.room_settings = room_settings
        self.auto_start = auto_start
        self.auto_close = auto_close
        self.members = []
        self.started = False
        self.lock = threading.RLock()

    def info(self):
        return {"party": {"id": self.id, "num_members": len(self.members), "max_members": self.max_members,
                          "settings": self.settings},
                "members": [m.out() for m in self.members]}


class Parties:
    def __init__(self, app):
        self.app = app
        self.parties = {}
        self.lock = threading.Lock()
        self.rpc_id = 0

    def next_id(self):
        with self.lock:
            self.rpc_id += 1
            return self.rpc_id

    def call(self, member, method, params):
        try:
            member.ws.send(json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                                       "id": self.next_id()}, ensure_ascii=False))
        except OSError:
            pass

    def message(self, members, message_type, payload):
        for m in members:
            self.call(m, "message", {"message_type": message_type, "payload": payload})


def _parties(app):
    if not hasattr(app, "parties"):
        app.parties = Parties(app)
    return app.parties


def _json(query, key, default):
    try:
        v = json.loads(query.get(key) or "null")
    except ValueError:
        v = None
    return v if v is not None else default


def _start(app, party):
    """Find (or start) the room and send it to every member."""
    from .game import _master, _remember_room
    ps = _parties(app)
    with party.lock:
        if party.started:
            return
        party.started = True
        members = list(party.members)
    ps.message(members, "game_starting", {})
    try:
        gm = _master(app)
        room = gm.find_or_create(party.game, party.room_settings, True)
    except HttpError as e:
        party.started = False
        ps.message(members, "game_start_failed", {"code": e.status, "reason": str(e.body)})
        return
    for m in members:
        out = gm.room_out(room)
        out["slot"] = m.account
        _remember_room(app, {"account": m.account}, room)
        ps.message([m], "game_started", out)
    app.log.info("party %s: started room %s for %s", party.id, room.id, ",".join(m.name for m in members))
    if party.auto_close:
        ps.message(members, "party_closed", {"reason": "started"})
        with ps.lock:
            ps.parties.pop(party.id, None)


def serve_session(app, handler, path, query):
    """backend.py calls this for a WebSocket upgrade on /game/party/..."""
    from .websocket import WebSocket
    ps = _parties(app)
    info = resolve_token(app, query.get("access_token"), required=False)
    if info is None:
        handler.send_error(403, "invalid access token")
        return
    parts = [p for p in path.split("/") if p]  # game party ...
    account = str(info["account"])
    party = None
    if len(parts) >= 7 and parts[2] == "create":
        party = Party(uuid.uuid4().hex[:12], parts[5], int(query.get("max_members") or 8),
                      _json(query, "party_settings", {}), _json(query, "room_settings", {}),
                      (query.get("auto_start") or "true") == "true", (query.get("auto_close") or "true") == "true")
        with ps.lock:
            ps.parties[party.id] = party
        app.log.info("party %s: created by %s for %s", party.id, account, party.game)
    elif len(parts) >= 4 and parts[3] == "session":
        with ps.lock:
            party = ps.parties.get(parts[2])
        if party is None:
            handler.send_error(404, "no such party")
            return
    else:
        handler.send_error(404, "unknown party call")
        return

    ws = WebSocket.handshake(handler)
    if ws is None:
        handler.send_error(400, "websocket expected")
        return

    from .social import _account_name
    me = Member(ws, account, _account_name(app, account), _json(query, "member_profile", {}))
    joined = False

    def join():
        nonlocal joined
        with party.lock:
            if joined:
                return
            if len(party.members) >= party.max_members or party.started:
                raise HttpError(409, {"error": "party is full"})
            others = list(party.members)
            if not party.members:
                me.role = 1000  # leader
            party.members.append(me)
            joined = True
        ps.message(others, "player_joined", me.out())
        app.log.info("party %s: %s joined (%d/%d)", party.id, me.name, len(party.members), party.max_members)

    def leave():
        nonlocal joined
        with party.lock:
            if not joined:
                return
            party.members.remove(me)
            joined = False
            others = list(party.members)
        ps.message(others, "player_left", me.out())
        if not others and not party.started:
            with ps.lock:
                ps.parties.pop(party.id, None)
            app.log.info("party %s: released", party.id)

    try:
        if (query.get("auto_join") or "true") == "true":
            join()
        ps.call(me, "party", {"party_info": party.info()})
        if party.auto_start and len(party.members) >= party.max_members:
            threading.Thread(target=_start, args=(app, party), daemon=True).start()
        while True:
            text = ws.recv()
            if text is None:
                break
            try:
                req = json.loads(text)
            except ValueError:
                continue
            if "method" not in req:
                continue  # a reply to our call
            method, p, rid = req["method"], req.get("params") or {}, req.get("id")
            result = "ok"
            try:
                if method == "leave_party":
                    leave()
                elif method == "join_party":
                    join()
                    if party.auto_start and len(party.members) >= party.max_members:
                        threading.Thread(target=_start, args=(app, party), daemon=True).start()
                elif method == "start_game":
                    threading.Thread(target=_start, args=(app, party), daemon=True).start()
                elif method == "close_party":
                    ps.message([m for m in party.members if m is not me], "party_closed", p.get("message") or {})
                    with ps.lock:
                        ps.parties.pop(party.id, None)
                elif method == "send_message":
                    ps.message([m for m in party.members if m is not me], "custom", p.get("payload") or {})
                reply = {"jsonrpc": "2.0", "result": result, "id": rid}
            except HttpError as e:
                reply = {"jsonrpc": "2.0", "error": {"code": e.status, "message": str(e.body)}, "id": rid}
            if rid is not None:
                ws.send(json.dumps(reply, ensure_ascii=False))
    finally:
        leave()
