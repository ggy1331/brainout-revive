"""
End-to-end test of the mock back-end over HTTP (no game needed).
Starts backend.py on a free port with a temporary data dir, runs scenarios, stops it.

Run: build\\pyenv\\Scripts\\python.exe tools\\mock-backend\\test_backend.py
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Client:
    def __init__(self, base):
        self.base = base
        self.token = None

    def call(self, method, path, **fields):
        if self.token and "access_token" not in fields:
            fields["access_token"] = self.token
        data = None
        url = self.base + path
        enc = {k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v)) for k, v in fields.items()}
        if method == "GET":
            url += "?" + urllib.parse.urlencode(enc)
        else:
            data = urllib.parse.urlencode(enc).encode()
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with urllib.request.urlopen(req) as r:
                assert r.headers.get("Content-Type") == "application/json", r.headers.get("Content-Type")
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def login(self, name):
        st, r = self.call("POST", "/login/auth", credential="anonymous", username=name, key="k-" + name,
                          scopes="profile,profile_write,market", gamespace="brainout:desktop")
        assert st == 200, (st, r)
        self.token = r["token"]
        return r["account"]


class WsClient:
    """Tiny WebSocket client for /message/listen (masked frames, text only)."""

    def __init__(self, port, token):
        import base64
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(("GET /message/listen?access_token=%s HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\n"
                           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
                           % (token, key)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            head += self.sock.recv(1)
        assert b" 101 " in head.split(b"\r\n")[0], head
        self.next_id = 0

    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError
            data += chunk
        return data

    def recv(self):
        """Next call from the server (responses to our own calls are skipped)."""
        while True:
            b1, b2 = self._read(2)
            n = b2 & 0x7F
            if n == 126:
                n = int.from_bytes(self._read(2), "big")
            elif n == 127:
                n = int.from_bytes(self._read(8), "big")
            msg = json.loads(self._read(n).decode())
            if "method" in msg:
                return msg

    def recv_type(self, message_type):
        """Next "message" of the given type (earlier notifications are skipped)."""
        while True:
            msg = self.recv()
            if msg.get("params", {}).get("message_type") == message_type:
                return msg

    def send(self, obj):
        data = json.dumps(obj).encode()
        mask = os.urandom(4)
        n = len(data)
        head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0x80 | 126]) + n.to_bytes(2, "big"))
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def call(self, method, **params):
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "method": method, "params": params, "id": self.next_id})


def balance(c, name="ru", payload=None):
    st, r = c.call("GET", "/market/markets/freeplay/items")
    assert st == 200, r
    for i in r["items"]:
        if i["name"] == name and (payload is None or i["payload"] == payload):
            return i["amount"]
    return 0


def main():
    port = free_port()
    data = tempfile.mkdtemp(prefix="mockbackend-")
    proc = subprocess.Popen([sys.executable, os.path.join(HERE, "backend.py"), "--port", str(port),
                             "--host", "127.0.0.1", "--data", data],
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        base = "http://127.0.0.1:%d" % port
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/discovery/services/login")
                break
            except Exception:
                time.sleep(0.1)

        a, b = Client(base), Client(base)
        acc_a, acc_b = a.login("alice"), b.login("bob")
        assert acc_a != acc_b
        assert a.login("alice") == acc_a, "same credential -> same account"

        # profile with @func
        st, r = a.call("POST", "/profile/profile/me", data={"stats": {"kills": 1}})
        assert st == 200, r
        st, r = a.call("POST", "/profile/profile/me", data={"stats": {"kills": {"@func": "++", "@value": 2}}})
        st, r = a.call("GET", "/profile/profile/me")
        assert r["stats"]["kills"] == 3, r
        st, r = a.call("POST", "/profile/profile/me", data={"stats": {"kills": {"@func": "--/0", "@value": 9}}})
        assert st == 400, (st, r)

        # stash
        gun = {"c": "weapon-ak47", "s": "skin-default"}
        st, r = a.call("POST", "/market/markets/freeplay/items",
                       items=[{"name": "instrument", "payload": gun, "amount": 2}, {"name": "ru", "payload": {}, "amount": 50}])
        assert st == 200, r
        assert balance(a, "instrument", gun) == 2 and balance(a) == 50
        st, r = a.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": -51}])
        assert st == 409 and balance(a) == 50, "can't go below zero"
        st, r = a.call("GET", "/market/markets/freeplay/items/ru", payload={})
        assert st == 200 and r["amount"] == 50, r

        # sell order: 2 guns, 300 ru each
        st, r = a.call("POST", "/market/markets/freeplay/orders", give_item="instrument", give_payload=gun,
                       give_amount=1, take_item="ru", take_payload={}, take_amount=300, orders_amount=2,
                       deadline="2099-01-01 00:00:00")
        assert st == 200, r
        oid = r["order_id"]
        assert balance(a, "instrument", gun) == 0, "escrow"
        st, r = b.call("GET", "/market/markets/freeplay/orders", give_item="instrument", sort_by="take_amount")
        assert len(r["orders"]) == 1 and r["orders"][0]["available"] == 2, r

        # buyer without money
        st, r = b.call("POST", "/market/markets/freeplay/orders/%s/fulfill" % oid, amount=1)
        assert st == 409, r
        b.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": 400}])
        ws_a = WsClient(port, a.token)
        ws_b = WsClient(port, b.token)
        time.sleep(0.2)
        st, r = b.call("POST", "/market/markets/freeplay/orders/%s/fulfill" % oid, amount=1)
        assert st == 200 and r["fulfilled_completely"] is False, r
        note = ws_a.recv()
        assert note["method"] == "message" and note["params"]["message_type"] == "order_completed", note
        assert note["params"]["payload"]["amount_left"] == 1, note
        # live message alice -> bob
        ws_a.call("send_message", recipient_class="user", recipient_key=acc_b, message_type="chat",
                  message={"text": "privet"}, flags=[])
        got = ws_b.recv()
        assert got["params"]["payload"]["text"] == "privet" and got["params"]["sender"] == str(acc_a), got
        st, r = a.call("GET", "/message/messages")
        assert any(m["type"] == "order_completed" for m in r["messages"]), r
        assert balance(b) == 100 and balance(b, "instrument", gun) == 1
        assert balance(a) == 350
        st, r = a.call("POST", "/market/markets/freeplay/orders/%s/fulfill" % oid, amount=1)
        assert st == 409, "can't buy own order"

        # delete: the remaining gun returns to the owner
        st, r = b.call("POST", "/market/markets/freeplay/orders/%s/delete" % oid)
        assert st == 409, "only the owner can delete"
        st, r = a.call("POST", "/market/markets/freeplay/orders/%s/delete" % oid)
        assert st == 200, r
        assert balance(a, "instrument", gun) == 1
        st, r = a.call("GET", "/market/markets/freeplay/orders/my")
        assert r["orders"] == [], r

        # expired order refunds
        st, r = a.call("POST", "/market/markets/freeplay/orders", give_item="instrument", give_payload=gun,
                       give_amount=1, take_item="ru", take_payload={}, take_amount=1, orders_amount=1,
                       deadline="2000-01-01 00:00:00")
        st, r = a.call("GET", "/market/markets/freeplay/orders")
        assert r["orders"] == [] and balance(a, "instrument", gun) == 1, "expired -> refunded"

        st, r = a.call("GET", "/market/markets/freeplay")
        assert "max-price" in r["settings"], r

        # clans (social groups)
        st, r = a.call("POST", "/social/groups/create", name="Dvor", join_method="approve", max_members=10,
                       group_profile={"tag": "DVR"}, participation_profile={"name": "alice"})
        assert st == 200, r
        gid = r["id"]
        st, r = b.call("POST", "/social/groups/create", name="dvor")
        assert st == 409, "name is busy (case-insensitive)"
        st, r = b.call("GET", "/social/groups/search", query="dv")
        assert r["groups"][0]["group"]["group_id"] == gid and r["groups"][0]["group"]["free_members"] == 9, r
        st, r = b.call("POST", "/social/group/%s/join" % gid)
        assert st == 409, "approve-only group"
        st, r = b.call("POST", "/social/group/%s/request" % gid, participation_profile={"name": "bob"},
                       notify={"name": "bob"})
        key = r["key"]
        note = ws_a.recv_type("group_request")
        assert note["params"]["message_type"] == "group_request" and note["params"]["recipient_key"] == gid, note
        st, r = b.call("POST", "/social/group/%s/approve/%s" % (gid, acc_b), key=key, role=0, permissions=[])
        assert st == 406, "only members can approve"
        st, r = a.call("POST", "/social/group/%s/approve/%s" % (gid, acc_b), key=key, role=5, permissions=["x"],
                       notify={"ok": True})
        assert st == 200, r
        ws_b.recv_type("group_request_approved")
        st, r = b.call("GET", "/social/group/%s" % gid)
        assert set(r["participants"]) == {acc_a, acc_b} and r["me"]["role"] == 5, r
        assert r["group"]["owner"] == acc_a and r["group"]["profile"]["tag"] == "DVR", r
        # clan chat through the message service
        ws_b.call("send_message", recipient_class="social-group", recipient_key=gid, message_type="clan_chat",
                  message={"text": "ku"}, flags=[])
        got = ws_a.recv_type("clan_chat")
        assert got["params"]["message_type"] == "clan_chat" and got["params"]["payload"]["text"] == "ku", got
        st, r = b.call("GET", "/message/group/social-group/%s" % gid)
        assert any(m["type"] == "clan_chat" for m in r["messages"]), r
        # group profile @func, participation, ownership rules
        st, r = b.call("POST", "/social/group/%s/profile" % gid, profile={"score": {"@func": "++", "@value": 7}})
        assert r["group"]["profile"]["score"] == 7, r
        st, r = a.call("GET", "/social/group/%s/participation/%s" % (gid, acc_b))
        assert r["participation"]["profile"]["name"] == "bob" and r["owner"] is False, r
        st, r = a.call("POST", "/social/group/%s/leave" % gid)
        assert st == 409, "owner can't leave a non-empty clan"
        st, r = b.call("DELETE", "/social/group/%s/participation/%s" % (gid, acc_a))
        assert st == 406, "can't kick a higher role"
        st, r = a.call("DELETE", "/social/group/%s/participation/%s" % (gid, acc_b), notify={"bye": 1})
        assert st == 200, r
        ws_b.recv_type("kicked")
        st, r = a.call("POST", "/social/group/%s/leave" % gid)
        st, r = a.call("GET", "/social/group/%s" % gid)
        assert st == 404, "last member left -> clan removed"

        # friends (our addition)
        a.call("POST", "/profile/profile/me", data={"name": "Alice"})
        b.call("POST", "/profile/profile/me", data={"name": "Bob"})
        st, r = a.call("POST", "/social/friends/add", name="nobody")
        assert st == 404, r
        st, r = a.call("POST", "/social/friends/add", name="bob")
        assert st == 200 and r["status"] == "outgoing", r
        req = ws_b.recv_type("friend_request")
        assert req["params"]["payload"]["name"] == "Alice", req
        st, r = b.call("GET", "/social/friends")
        assert r["friends"][0]["status"] == "incoming" and r["friends"][0]["name"] == "Alice", r
        st, r = b.call("POST", "/social/friends/add", account=acc_a)
        assert r["status"] == "friend", r
        st, r = a.call("GET", "/social/friends")
        f = r["friends"][0]
        assert f["status"] == "friend" and f["online"] is True and f["credential"] == "anonymous:bob", r
        st, r = a.call("POST", "/social/friends/invite", account=acc_b, room="7")
        inv = ws_b.recv_type("friend_invite")
        assert inv["params"]["payload"]["room"] == "7", inv
        st, r = b.call("POST", "/social/friends/remove", account=acc_a)
        st, r = a.call("GET", "/social/friends")
        assert r["friends"] == [], r
        st, r = a.call("POST", "/social/friends/invite", account=acc_b, room="7")
        assert st == 406, "can invite only friends"
        print("OK: login, profile @func, stash, orders (escrow, fulfill, delete, expiry), "
              "messages (websocket push, market notifications, history), "
              "clans (create, search, request/approve, chat, profile @func, kick, leave), "
              "friends (add by name, accept, online, invite, remove)")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
