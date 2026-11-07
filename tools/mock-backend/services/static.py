"""
anthill-static imitation: player uploads (clan and profile avatars).

PUT /static/upload?filename=<name>&access_token=..   body = file  -> {"url": "<base>/static/files/<id>"}
GET /static/files/<id>                                           -> the file

Storage: <data>/static/<id> (max 2 MB per file).
"""

import mimetypes
import os
import secrets

from .common import HttpError
from .login import token_from

MAX_SIZE = 2 * 1024 * 1024


def _dir(app):
    d = os.path.join(app.storage.root, "static")
    os.makedirs(d, exist_ok=True)
    return d


def handle(ctx, rest):
    app = ctx.app
    if rest and rest[0] == "upload" and ctx.method in ("PUT", "POST"):
        token_from(ctx)
        data = ctx.raw or b""
        if not data:
            raise HttpError(400, {"error": "empty file"})
        if len(data) > MAX_SIZE:
            raise HttpError(413, {"error": "file is too big"})
        name = os.path.basename(ctx.arg("filename") or "file.png")
        safe = "".join(c for c in name if c.isalnum() or c in "-_.")[-60:] or "file.png"
        file_id = secrets.token_hex(8) + "_" + safe
        with open(os.path.join(_dir(app), file_id), "wb") as f:
            f.write(data)
        return {"url": app.service_url("static") + "/files/" + file_id}

    if len(rest) >= 2 and rest[0] == "files" and ctx.method == "GET":
        file_id = os.path.basename(rest[1])
        path = os.path.join(_dir(app), file_id)
        if not os.path.isfile(path):
            raise HttpError(404, {"error": "no such file"})
        with open(path, "rb") as f:
            data = f.read()
        ctype = mimetypes.guess_type(file_id)[0] or "application/octet-stream"
        return 200, data, {"Content-Type": ctype}

    raise HttpError(404, {"error": "unknown static call"})
