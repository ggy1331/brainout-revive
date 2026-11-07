"""
anthill-leaderboard imitation.

GET  /leaderboard/leaderboard/<order>/<name>?limit=&offset=&arbitrary_account=
     -> {"data": [{"display_name", "score", "account", "rank", "profile"}]}
POST /leaderboard/leaderboard/<order>/<name>   score, display_name, expire_in, profile, arbitrary_account
     (one entry per account; arbitrary_account is used for clans: "clans100" is posted with the clan id)

Leaderboards the game uses: "top100" (players by K/D, stat "kpd", posted by PostLeaderboardPlugin at the
end of a match when kpd >= 1.5), "clans100" (clans by efficiency), event leaderboards.
To keep "top100" alive in a small group it also includes every player whose profile has a "kpd" stat
(e.g. imported from the LAN games) and who has not posted a score yet.

Storage: leaderboards/<name>.json -> {"entries": {key: {display_name, score, account, profile, expires}}}
"""

import time

from .common import HttpError
from .login import token_from


def _entries(app, name):
    doc = app.storage.get("leaderboards", name, {"entries": {}})
    now = time.time()
    alive = {k: e for k, e in doc["entries"].items() if not e.get("expires") or e["expires"] > now}
    if len(alive) != len(doc["entries"]):
        doc["entries"] = alive
        app.storage.put("leaderboards", name, doc)
    return alive


def _profile_kpd_entries(app, posted):
    out = {}
    for acc, prof in app.storage.all("profiles").items():
        if acc in posted:
            continue
        kpd = (prof.get("stats") or {}).get("kpd")
        if isinstance(kpd, (int, float)) and kpd > 0:
            out[acc] = {"display_name": prof.get("name") or ("#" + acc), "score": float(kpd),
                        "account": acc, "profile": {}}
    return out


def handle(ctx, rest):
    app = ctx.app
    info = token_from(ctx)
    if len(rest) < 3 or rest[0] != "leaderboard":
        raise HttpError(404, {"error": "unknown leaderboard call"})
    order, name = rest[1], rest[2]
    desc = order != "asc"

    if ctx.method == "POST":
        key = str(ctx.arg("arbitrary_account") or info["account"])
        try:
            score = float(ctx.arg("score", 0))
        except ValueError:
            raise HttpError(400, {"error": "bad score"})
        expire_in = int(float(ctx.arg("expire_in", 0) or 0))
        with app.lock:
            doc = app.storage.get("leaderboards", name, {"entries": {}})
            doc["entries"][key] = {
                "display_name": ctx.arg("display_name") or ("#" + key), "score": score, "account": key,
                "profile": ctx.json_arg("profile", {}) or {},
                "expires": time.time() + expire_in if expire_in > 0 else None,
            }
            app.storage.put("leaderboards", name, doc)
        return {}

    entries = dict(_entries(app, name))
    if name == "top100":
        entries.update(_profile_kpd_entries(app, entries))
    ranked = sorted(entries.values(), key=lambda e: e["score"], reverse=desc)
    for i, e in enumerate(ranked, 1):
        e["rank"] = i
    arbitrary = ctx.arg("arbitrary_account")
    if arbitrary:
        ranked = [e for e in ranked if str(e["account"]) == str(arbitrary)]
    offset = int(ctx.arg("offset", 0) or 0)
    limit = int(ctx.arg("limit", 100) or 100)
    return {"data": [{k: e[k] for k in ("display_name", "score", "account", "rank", "profile")}
                     for e in ranked[offset:offset + limit]]}
