"""Host the home room for the lifetime of BrainOut.exe."""
import ipaddress
import logging
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from backend import App, Handler, Storage, ThreadingHTTPServer
from services import revive
from services.hub import Hub


class HomeHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def run():
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    logging.basicConfig(filename=logs / "hub.log", filemode="w", level=logging.INFO)
    saved = ROOT / "connect-online-last.txt"
    parts = saved.read_text(encoding="utf-8-sig").split() if saved.exists() else []
    name = parts[1] if len(parts)>1 else os.environ.get("USERNAME", "Player")
    if not re.fullmatch(r"[\w-]{1,32}", name):
        name = "Player"
    key = secrets.token_hex(32)
    java = str(ROOT / "jre/bin/java.exe")
    try:
        http = HomeHTTPServer(("",9511), Handler)
    except OSError:
        http = HomeHTTPServer(("",0), Handler)
    home = "127.0.0.1:%d" % http.server_port
    app = App("http://"+home, Storage(ROOT/"solo-data"/name), java=java,
              server_dir=str(ROOT/"server"), logs_dir=str(logs/"rooms"))
    app.storage.on_put = lambda collection, item: revive.on_put(app,collection,item)
    app.hub_port = http.server_port
    app.hub = Hub(app, name, key)
    http.app = app
    threading.Thread(target=http.serve_forever, daemon=True).start()
    endpoint = home
    try:
        with tempfile.TemporaryDirectory() as temp:
            request = Path(temp) / "next"
            while True:
                env = dict(os.environ, DESKTOP_PROFILE_NAME=name, BRAINOUT_HUB_ENDPOINT=endpoint,
                           BRAINOUT_HUB_ID=app.hub.uid, BRAINOUT_HUB_HOME=home, BRAINOUT_HUB_NEXT=str(request))
                if endpoint == home:
                    env["BRAINOUT_OWNER_KEY"] = key
                with (ROOT/"client-last.log").open("w") as log:
                    code = subprocess.call([java, "-jar", "brainout-desktop.jar", "--unsafe",
                        "--auto-continue", "--name", name, "--env", "http://"+endpoint+"/environment"],
                        cwd=ROOT/"client", env=env, stdout=log, stderr=log,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                if not request.exists():
                    return code
                value = request.read_text(encoding="utf8").strip()
                request.unlink()
                if value == "install-update":
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("release_update", ROOT/"support/release_update.py")
                    updater = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(updater)
                    updater.schedule(ROOT)
                    return 0
                if value == "home":
                    endpoint = home
                else:
                    addr, number = value.split(":")
                    if not 1 <= int(number) <= 65535:
                        raise ValueError("Недопустимый порт")
                    endpoint = "%s:%d" % (ipaddress.IPv4Address(addr),int(number))
    finally:
        time.sleep(4)
        if hasattr(app,"game_master"):
            app.game_master.shutdown()
        http.shutdown()
        http.server_close()
        app.hub.listener.close()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception:
        logging.exception("Ошибка запуска хаба")
        sys.exit(1)
