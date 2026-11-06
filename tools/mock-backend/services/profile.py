"""
anthill-profile imitation (routes as in anthill-profile/server.py):

GET  /profile/me[/path]            -> profile (404 if none)
POST /profile/me[/path]            data=<json object>, merge=true|false -> updated value
GET  /profile/<account>[/path]
POST /profile/<account>[/path]
GET  /profiles?accounts=[..]&profile_fields=[..] -> {account: profile}
POST /profiles  data={account: fields}, merge  -> {account: updated}

Merge rules and "@func" functions ("++", "--", "--/0", "==", "exists", "append", ...) come from the
original anthill-common code (anthill_profile.py), so behaviour matches the official back-end.
Storage: <data>/profiles/<account>.json
"""

import copy

from .common import HttpError
from .login import token_from
from .anthill_profile import Profile, ProfileError

COLLECTION = "profiles"


def _get_path(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def get_profile(app, account):
    return app.storage.get(COLLECTION, account)


def update_profile(app, account, fields, path=None, merge=True):
    """Apply fields (with @func support) to the account profile. Returns the updated value at path."""
    with app.lock:
        root = app.storage.get(COLLECTION, account) or {}
        work = copy.deepcopy(root)
        try:
            new_root = Profile.merge_data(work, fields, path or None, merge)
        except ProfileError as e:
            raise HttpError(400, {"error": str(e.message if hasattr(e, "message") else e)})
        app.storage.put(COLLECTION, account, new_root)
    return _get_path(new_root, path) if path else new_root


def _path(rest):
    return [p for p in rest if p]


def handle(ctx, rest):
    app = ctx.app

    if not rest:
        raise HttpError(404, {"error": "no profile call"})

    if rest[0] == "profiles":
        token_from(ctx)
        if ctx.method == "GET":
            accounts = [str(a) for a in (ctx.json_arg("accounts", []) or [])]
            fields = ctx.json_arg("profile_fields", []) or []
            out = {}
            for account in accounts:
                prof = get_profile(app, account)
                if prof is None:
                    continue
                if fields:
                    prof = {f: prof[f] for f in fields if f in prof}
                out[account] = prof
            return out
        data = ctx.json_arg("data", {})
        merge = str(ctx.arg("merge", "true")).lower() != "false"
        if not isinstance(data, dict):
            raise HttpError(400, {"error": "data must be an object"})
        return {str(account): update_profile(app, str(account), fields, None, merge)
                for account, fields in data.items()}

    if rest[0] == "profile" and len(rest) >= 2:
        info = token_from(ctx)
        account = info["account"] if rest[1] == "me" else rest[1]
        path = _path(rest[2:])

        if ctx.method == "GET":
            prof = get_profile(app, account)
            if prof is None:
                raise HttpError(404, {"error": "Profile was not found."})
            return _get_path(prof, path) if path else prof

        data = ctx.json_arg("data", None)
        if not isinstance(data, dict):
            raise HttpError(400, {"error": "Expected 'data' field to be an object (a set of fields)."})
        merge = str(ctx.arg("merge", "true")).lower() != "false"
        return update_profile(app, account, data, path, merge)

    raise HttpError(404, {"error": "unknown profile call"})
