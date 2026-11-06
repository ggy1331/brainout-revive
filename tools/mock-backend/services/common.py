import json
import os
import threading


class HttpError(Exception):
    def __init__(self, status, body=None):
        super().__init__("%s %s" % (status, body))
        self.status = status
        self.body = body if body is not None else {"error": str(status)}


class Ctx:
    """One HTTP request."""

    def __init__(self, app, method, parts, args, headers, raw):
        self.app = app
        self.method = method
        self.parts = parts
        self.args = args
        self.headers = headers
        self.raw = raw

    def arg(self, name, default=None, required=False):
        if name in self.args:
            return self.args[name]
        if required:
            raise HttpError(400, {"error": "missing argument " + name})
        return default

    def json_arg(self, name, default=None):
        v = self.args.get(name)
        if v is None:
            return default
        if isinstance(v, (dict, list)):
            return v
        try:
            return json.loads(v)
        except ValueError:
            raise HttpError(400, {"error": "bad json in " + name})


class Storage:
    """Tiny JSON document store: <data>/<collection>/<key>.json"""

    def __init__(self, root):
        self.root = root
        self.lock = threading.RLock()
        os.makedirs(root, exist_ok=True)

    def _path(self, collection, key):
        safe = "".join(c if c.isalnum() or c in "-_.@" else "_" for c in str(key))
        d = os.path.join(self.root, collection)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, safe + ".json")

    def get(self, collection, key, default=None):
        p = self._path(collection, key)
        with self.lock:
            if not os.path.exists(p):
                return default
            with open(p, encoding="utf-8") as f:
                return json.load(f)

    def put(self, collection, key, value):
        p = self._path(collection, key)
        with self.lock:
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)

    def delete(self, collection, key):
        p = self._path(collection, key)
        with self.lock:
            if os.path.exists(p):
                os.remove(p)

    def all(self, collection):
        d = os.path.join(self.root, collection)
        if not os.path.isdir(d):
            return {}
        out = {}
        with self.lock:
            for fn in os.listdir(d):
                if fn.endswith(".json"):
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        out[fn[:-5]] = json.load(f)
        return out
