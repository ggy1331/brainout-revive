"""
anthill-login imitation.

POST /login/auth      credential, username, key, scopes, gamespace -> {token, account, credential, scopes}
POST /login/extend    access_token, extend, scopes                 -> same, for the access_token's account
GET  /login/validate  access_token                                  -> {account, credential, scopes}
GET  /login/server-token?name=...                                   -> token for a game server (our addition)

Tokens are opaque random strings stored in <data>/tokens. Every requested scope is granted:
this is a private back-end for friends, not a security boundary.
Accounts: <data>/credentials/<credential>.json -> {"account": "1", "key": "..."}
"""

import secrets
import time

from .common import HttpError

ADMIN_SCOPES = ["game", "game_root", "game_mod", "profile", "profile_write", "profile_private",
                "market", "store", "party", "party_create", "message_listen", "blog", "static_upload",
                "report_upload", "game_editor", "group", "game_ban", "event", "social", "leaderboard",
                "promo", "exec", "admin"]


def _scopes(value):
    if isinstance(value, list):
        return [s for s in value if s]
    return [s for s in (value or "").split(",") if s]


def _next_account(st):
    meta = st.get("meta", "accounts", {"last": 0})
    meta["last"] += 1
    st.put("meta", "accounts", meta)
    return str(meta["last"])


def issue_token(app, account, credential, scopes, gamespace="brainout:desktop"):
    token = secrets.token_hex(24)
    app.storage.put("tokens", token, {
        "account": account, "credential": credential, "scopes": scopes,
        "gamespace": gamespace, "issued": int(time.time()),
    })
    return token


def resolve_token(app, token, required=True):
    """Return token info dict or raise 403."""
    info = app.storage.get("tokens", token) if token else None
    if info is None and required:
        raise HttpError(403, {"error": "invalid access token"})
    return info


def token_from(ctx, required=True):
    token = ctx.arg("access_token") or ctx.headers.get("X-Token") or ctx.headers.get("Access-Token")
    return resolve_token(ctx.app, token, required)


def _response(token, info):
    return {"token": token, "account": info["account"], "credential": info["credential"],
            "scopes": info["scopes"]}


def handle(ctx, rest):
    app = ctx.app
    st = app.storage
    call = rest[0] if rest else ""

    if call == "auth" and ctx.method == "POST":
        credential_type = ctx.arg("credential", required=True)
        username = ctx.arg("username") or secrets.token_hex(8)
        key = ctx.arg("key", "")
        gamespace = ctx.arg("gamespace", "brainout:desktop")
        scopes = sorted(set(_scopes(ctx.arg("scopes")) + _scopes(ctx.arg("should_have"))))

        credential = "%s:%s" % (credential_type, username)
        with app.lock:
            rec = st.get("credentials", credential)
            if rec is None:
                rec = {"account": _next_account(st), "key": key, "created": int(time.time()),
                       "credential": credential}
                st.put("credentials", credential, rec)
            elif rec.get("key") and key and rec["key"] != key:
                raise HttpError(403, {"error": "wrong key"})
        token = issue_token(app, rec["account"], credential, scopes, gamespace)
        return _response(token, st.get("tokens", token))

    if call == "extend" and ctx.method == "POST":
        target = resolve_token(app, ctx.arg("access_token", required=True))
        resolve_token(app, ctx.arg("extend", required=True))  # extender must be valid
        scopes = sorted(set(target["scopes"]) | set(_scopes(ctx.arg("scopes"))))
        token = issue_token(app, target["account"], target["credential"], scopes, target.get("gamespace"))
        return _response(token, st.get("tokens", token))

    if call == "validate":
        info = resolve_token(app, ctx.arg("access_token", required=True))
        return {"account": info["account"], "credential": info["credential"], "scopes": info["scopes"]}

    if call == "server-token":
        name = ctx.arg("name", "game-server")
        credential = "server:" + name
        with app.lock:
            rec = st.get("credentials", credential)
            if rec is None:
                rec = {"account": _next_account(st), "key": "", "created": int(time.time())}
                st.put("credentials", credential, rec)
        token = issue_token(app, rec["account"], credential, ADMIN_SCOPES)
        return _response(token, st.get("tokens", token))

    raise HttpError(404, {"error": "unknown login call " + call})
