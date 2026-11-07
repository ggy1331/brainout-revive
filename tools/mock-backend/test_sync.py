"""
Test of the solo <-> host progress sync (services/revive.py) and of parties (services/party.py).
Two back-ends with temporary data: a host and a local solo one.

Run: build\\pyenv\\Scripts\\python.exe tools\\mock-backend\\test_sync.py
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time

from test_backend import Client, free_port, WsClient, HERE

PY = sys.executable


def start(port, data, *extra):
    p = subprocess.Popen([PY, os.path.join(HERE, "backend.py"), "--port", str(port), "--data", data] + list(extra),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return p
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("backend did not start")


def sync_only(port, data, host_port, nick):
    out = subprocess.run([PY, os.path.join(HERE, "backend.py"), "--port", str(port), "--data", data, "--solo", nick,
                          "--sync-host", "http://127.0.0.1:%d" % host_port, "--sync-only"],
                         capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    line = [l for l in (out.stdout + out.stderr).splitlines() if "Sync with" in l]
    return line[-1].split(": ", 2)[-1] if line else out.stdout + out.stderr


def ru(c):
    st, r = c.call("GET", "/market/markets/freeplay/items")
    return sum(i["amount"] for i in r["items"] if i["name"] == "ru")


def main():
    tmp = tempfile.mkdtemp(prefix="bo-sync-")
    hp, lp = free_port(), free_port()
    host = start(hp, os.path.join(tmp, "host"))
    local = None
    ok = []
    try:
        # --- player has progress on the host
        h = Client("http://127.0.0.1:%d" % hp)
        h.login("tester-online")
        assert h.call("POST", "/profile/profile/me", data={"name": "Tester", "stats": {"kills": 10}})[0] == 200
        h.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": 100}])

        # --- first solo start: no local account yet -> pending, the new account gets the host progress
        r = sync_only(lp, os.path.join(tmp, "local"), hp, "Tester")
        assert "загружен" in r, r
        local = start(lp, os.path.join(tmp, "local"), "--solo", "Tester", "--sync-host", "http://127.0.0.1:%d" % hp)
        l = Client("http://127.0.0.1:%d" % lp)
        l.login("tester-solo")
        st, prof = l.call("GET", "/profile/profile/me")
        assert prof["stats"]["kills"] == 10, prof
        assert ru(l) == 100
        ok.append("first solo start takes the host progress")

        # --- solo play: +50 ru, kills 15; meanwhile a lot sold on the host: +30 ru
        l.call("POST", "/profile/profile/me", data={"stats": {"kills": 15}})
        l.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": 50}])
        h.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": 30}])
        local.terminate(); local.wait()
        r = sync_only(lp, os.path.join(tmp, "local"), hp, "Tester")
        assert "профиль → хост" in r and "объединены" in r, r
        assert h.call("GET", "/profile/profile/me")[1]["stats"]["kills"] == 15
        assert ru(h) == 180, ru(h)
        ok.append("solo progress goes to the host, rubles merged (100 + 50 solo + 30 sold = 180)")

        # --- online play on the host -> next solo start pulls it
        h.call("POST", "/profile/profile/me", data={"stats": {"kills": 20}})
        h.call("POST", "/market/markets/freeplay/items", items=[{"name": "ru", "payload": {}, "amount": -80}])
        r = sync_only(lp, os.path.join(tmp, "local"), hp, "Tester")
        assert "профиль ← хост" in r, r
        local = start(lp, os.path.join(tmp, "local"), "--solo", "Tester")
        l = Client("http://127.0.0.1:%d" % lp)
        l.login("tester-solo")
        assert l.call("GET", "/profile/profile/me")[1]["stats"]["kills"] == 20
        assert ru(l) == 100, ru(l)
        ok.append("online progress comes back to solo")

        assert "изменений нет" in sync_only(lp + 1, os.path.join(tmp, "local"), hp, "Tester")
        ok.append("nothing changed -> nothing synced")

        # --- host down -> local keeps its progress
        r = sync_only(lp + 1, os.path.join(tmp, "local"), free_port(), "Tester")
        assert "недоступен" in r, r
        ok.append("host down is not an error")

        # --- party: two players, the second joins -> both get the same room (game start fails without java
        #     servers in the test, game_start_failed is enough to see the flow)
        a = Client("http://127.0.0.1:%d" % hp); a.login("party-a")
        b = Client("http://127.0.0.1:%d" % hp); b.login("party-b")
        wa = WsClient(hp, a.token, "/game/party/create/brainout/valpha2/freeplay/session?max_members=2&auto_start=true")
        party = wa.recv_method("party")
        pid = party["party_info"]["party"]["id"]
        wb = WsClient(hp, b.token, "/game/party/%s/session?" % pid)
        assert len(wb.recv_method("party")["party_info"]["members"]) == 2
        assert wa.recv_method("message")["message_type"] == "player_joined"
        assert wa.recv_method("message")["message_type"] == "game_starting"
        ok.append("party: create, join, auto start")
    finally:
        for p in (host, local):
            if p and p.poll() is None:
                p.terminate()
    print("OK:\n  " + "\n  ".join(ok))


if __name__ == "__main__":
    main()
