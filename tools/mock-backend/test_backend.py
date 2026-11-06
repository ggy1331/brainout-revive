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
        st, r = b.call("POST", "/market/markets/freeplay/orders/%s/fulfill" % oid, amount=1)
        assert st == 200 and r["fulfilled_completely"] is False, r
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
        print("OK: login, profile @func, stash, orders (escrow, fulfill, delete, expiry)")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
