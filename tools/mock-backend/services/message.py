"""
anthill-message imitation.

WebSocket  /message/listen?access_token=..&message_types=[..]   JSON-RPC 2.0
   client -> us: send_message(recipient_class, recipient_key, message_type, message, flags),
                 mark_as_read(message_id), delete_message(message_id), update_message(message_id, payload)
   us -> client: message(...), message_deleted(...), message_updated(...)
GET /message/messages                      -> {"messages": [...], "last_read_messages": [...]}
GET /message/group/<class>/<key>           -> {"messages": [...]}

Recipients: "user"/<account> or a group, e.g. "social-group"/<clan id> (members come from the social
service). The game server opens one session per player and forwards messages to the game client
(clan chat "clan_chat", clan requests, market notifications "order_completed"/"order_cancelled").
Other services call deliver() to post messages (the market does it on fulfil/cancel).

Storage: msgbox/<class>-<key>.json (last 200 messages per box)
"""

import datetime
import json
import threading
import uuid as uuidlib

from .common import HttpError
from .login import token_from, resolve_token

BOX_LIMIT = 200
TIME_FMT = "%Y-%m-%d %H:%M:%S"


class Sessions:
    def __init__(self):
        self.lock = threading.Lock()
        self.by_account = {}
        self.rpc_id = 0

    def add(self, account, s):
        with self.lock:
            self.by_account.setdefault(account, set()).add(s)

    def remove(self, account, s):
        with self.lock:
            self.by_account.get(account, set()).discard(s)

    def of(self, account):
        with self.lock:
            return list(self.by_account.get(str(account), set()))

    def next_id(self):
        with self.lock:
            self.rpc_id += 1
            return self.rpc_id


def _sessions(app):
    if not hasattr(app, "message_sessions"):
        app.message_sessions = Sessions()
    return app.message_sessions


def _box_key(cls, key):
    return "%s-%s" % (cls, key)


def _members(app, cls, key):
    if cls == "user":
        return [str(key)]
    if cls == "social-group":
        from . import social
        return social.group_member_accounts(app, key)
    return []


def _message_for_client(m):
    return {
        "gamespace_id": 1, "message_id": m["uuid"], "sender": m["sender"],
        "recipient_class": m["recipient_class"], "recipient_key": m["recipient"],
        "message_type": m["type"], "payload": m["payload"], "time": m["time"], "flags": m.get("flags", []),
    }


def _push(app, accounts, method, params):
    sessions = _sessions(app)
    for account in accounts:
        for s in sessions.of(account):
            if s.types and method == "message" and params.get("message_type") not in s.types:
                continue
            s.ws.send(json.dumps({"jsonrpc": "2.0", "method": method, "params": params,
                                  "id": sessions.next_id()}, ensure_ascii=False))


def deliver(app, recipient_class, recipient_key, sender, message_type, payload, flags=None):
    """Store a message and push it to everyone who should see it."""
    m = {
        "uuid": uuidlib.uuid4().hex, "recipient_class": recipient_class, "recipient": str(recipient_key),
        "sender": str(sender), "type": message_type, "payload": payload or {}, "gamespace": 1,
        "time": datetime.datetime.now().strftime(TIME_FMT), "flags": list(flags or []),
    }
    with app.lock:
        box = app.storage.get("msgbox", _box_key(recipient_class, recipient_key), {"messages": []})
        box["messages"].append(m)
        box["messages"] = box["messages"][-BOX_LIMIT:]
        app.storage.put("msgbox", _box_key(recipient_class, recipient_key), box)
    _push(app, _members(app, recipient_class, recipient_key), "message", _message_for_client(m))
    return m


def _find(app, message_id):
    for name, box in app.storage.all("msgbox").items():
        for m in box["messages"]:
            if m["uuid"] == message_id:
                return name, box, m
    return None, None, None


class Session:
    def __init__(self, ws, account, types):
        self.ws = ws
        self.account = account
        self.types = types


def serve_listen(app, handler, query):
    """Called by backend.py for a WebSocket upgrade on /message/listen."""
    from .websocket import WebSocket
    info = resolve_token(app, query.get("access_token"), required=False)
    if info is None:
        handler.send_error(403, "invalid access token")
        return
    ws = WebSocket.handshake(handler)
    if ws is None:
        handler.send_error(400, "websocket expected")
        return
    try:
        types = json.loads(query.get("message_types") or "[]")
    except ValueError:
        types = []
    account = str(info["account"])
    session = Session(ws, account, set(types or []))
    _sessions(app).add(account, session)
    app.log.info("message: account %s listening (%s)", account, ",".join(sorted(session.types)) or "all")
    try:
        while True:
            text = ws.recv()
            if text is None:
                break
            try:
                req = json.loads(text)
            except ValueError:
                continue
            if "method" not in req:
                continue  # a response to our push
            rid = req.get("id")
            try:
                result = _rpc(app, account, req["method"], req.get("params") or {})
                reply = {"jsonrpc": "2.0", "result": result, "id": rid}
            except HttpError as e:
                reply = {"jsonrpc": "2.0", "error": {"code": e.status, "message": str(e.body)}, "id": rid}
            if rid:
                ws.send(json.dumps(reply, ensure_ascii=False))
    finally:
        _sessions(app).remove(account, session)
        app.log.info("message: account %s disconnected", account)


def _rpc(app, account, method, p):
    if method == "send_message":
        payload = p.get("message")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError:
                payload = {"text": payload}
        m = deliver(app, p.get("recipient_class"), p.get("recipient_key"), account, p.get("message_type"),
                    payload, p.get("flags"))
        return {"message_id": m["uuid"]}
    if method == "mark_as_read":
        app.storage.put("msgread", account, {"last": p.get("message_id")})
        return "OK"
    if method in ("delete_message", "update_message"):
        with app.lock:
            name, box, m = _find(app, p.get("message_id"))
            if m is None:
                raise HttpError(404, "no such message")
            if method == "delete_message":
                box["messages"].remove(m)
            else:
                m["payload"] = p.get("payload") or {}
            app.storage.put("msgbox", name, box)
        params = {"gamespace_id": 1, "message_id": m["uuid"], "sender": account}
        if method == "update_message":
            params["payload"] = m["payload"]
        _push(app, _members(app, m["recipient_class"], m["recipient"]),
              "message_deleted" if method == "delete_message" else "message_updated", params)
        return "OK"
    raise HttpError(404, "unknown method " + method)


def handle(ctx, rest):
    app = ctx.app
    info = token_from(ctx)
    account = str(info["account"])
    if rest and rest[0] == "messages":
        from . import social
        msgs = list(app.storage.get("msgbox", _box_key("user", account), {"messages": []})["messages"])
        for gid in social.groups_of(app, account):
            msgs += app.storage.get("msgbox", _box_key("social-group", gid), {"messages": []})["messages"]
        msgs.sort(key=lambda m: m["time"])
        last = app.storage.get("msgread", account)
        return {"messages": msgs[-int(ctx.arg("limit", 100)):], "last_read_messages": []
                if not last else [{"uuid": last["last"], "recipient_class": "user", "recipient": account,
                                   "time": datetime.datetime.now().strftime(TIME_FMT)}]}
    if rest and rest[0] == "group" and len(rest) >= 3:
        box = app.storage.get("msgbox", _box_key(rest[1], rest[2]), {"messages": []})
        return {"messages": box["messages"][-int(ctx.arg("limit", 100)):]}
    raise HttpError(404, {"error": "unknown message call"})
