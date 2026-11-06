"""
anthill-social imitation: groups (clans in BRAIN / OUT). Routes as in anthill-social/server.py:

POST /social/groups/create                       name, join_method (free|approve|invite), max_members,
                                                 group_profile, participation_profile, group_messages -> {"id"}
GET  /social/groups/search?query=                -> {"groups": [{"group": {...}}]}
GET  /social/groups/profiles?group_ids=[..]      -> {"groups": {id: {"profile"}}}
POST /social/groups/profiles  profiles={id: p}, merge
GET  /social/group/<id>                          -> {"group", "participants", "me", "message"}
POST /social/group/<id>                          name, join_method, notify          (summary)
GET  /social/group/<id>/profile                  -> {"participant", "group": {"profile"}}
POST /social/group/<id>/profile                  profile, merge, notify
POST /social/group/<id>/join                     participation_profile, notify      (free groups)
POST /social/group/<id>/leave                    notify
POST /social/group/<id>/request                  participation_profile, notify -> {"key"}   (approve groups)
POST /social/group/<id>/approve/<account>        role, key, permissions, notify
POST /social/group/<id>/reject/<account>         key, notify
POST /social/group/<id>/invite/<account>         role, permissions, notify -> {"key"}
POST /social/group/<id>/invitation/accept        key, participation_profile, notify
POST /social/group/<id>/invitation/reject        key, notify
GET  /social/group/<id>/participation/<acc|me>   -> {"participation": {profile, role, permissions}, "owner"}
POST /social/group/<id>/participation/<acc|me>   profile, merge, notify
DELETE /social/group/<id>/participation/<acc>    notify                              (kick)
POST /social/group/<id>/participation/<acc>/permissions   permissions, role, notify
POST /social/group/<id>/ownership                account_transfer_to, my_role, notify

Notifications (only when the game passes "notify", like the original): to the group channel
("social-group"/<id>): group_request, group_profile_updated, group_renamed, participation_profile_updated,
permissions_updated, ownership_transferred, group_invite_rejected; to a user: group_invite,
group_request_approved, group_request_rejected, kicked.
Profiles support "@func" (same merge code as player profiles). Owner role = 1000, new member = 0.

Storage: groups/<id>.json
"""

import copy
import secrets

from .common import HttpError
from .login import token_from
from .anthill_profile import Profile, ProfileError

MAXIMUM_ROLE = 1000
MINIMUM_ROLE = 0
DEFAULT_MAX_MEMBERS = 50
GROUP_CLASS = "social-group"


# ------------------------------------------------------------------ helpers used by other services


def groups_of(app, account):
    account = str(account)
    return [gid for gid, g in app.storage.all("groups").items()
            if account in (g.get("participants") or {})]


def group_member_accounts(app, group_id):
    g = app.storage.get("groups", str(group_id))
    return list((g or {}).get("participants", {}).keys())


# ------------------------------------------------------------------ internals


def _next_group_id(app):
    meta = app.storage.get("meta", "groups", {"last": 0})
    meta["last"] += 1
    app.storage.put("meta", "groups", meta)
    return str(meta["last"])


def _load(app, gid):
    g = app.storage.get("groups", str(gid))
    if g is None:
        raise HttpError(404, {"error": "No such group"})
    return g


def _save(app, g):
    app.storage.put("groups", g["group_id"], g)


def _merge(old, new, merge):
    try:
        return Profile.merge_data(copy.deepcopy(old or {}), new, None, merge)
    except ProfileError as e:
        raise HttpError(400, {"error": str(getattr(e, "message", e))})


def _notify(app, ctx, cls, key, sender, message_type, g=None):
    notify = ctx.json_arg("notify", None)
    if not notify:
        return
    if g is not None and "messages" not in g.get("flags", []) and cls == GROUP_CLASS:
        return
    from .message import deliver
    deliver(app, cls, key, sender, message_type, notify)


def _free(g):
    return g["max_members"] - len(g["participants"])


def _group_out(g):
    return {"group_id": g["group_id"], "profile": g["profile"], "join_method": g["join_method"],
            "free_members": _free(g), "owner": g["owner"], "name": g["name"]}


def _participant(g, account):
    p = g["participants"].get(str(account))
    if p is None:
        raise HttpError(406, {"error": "This account does not participate this group."})
    return p


def _add_member(g, account, role, permissions, profile):
    if str(account) in g["participants"]:
        raise HttpError(409, {"error": "Already a member"})
    if _free(g) <= 0:
        raise HttpError(409, {"error": "The group is full"})
    g["participants"][str(account)] = {"role": int(role), "permissions": list(permissions or []),
                                       "profile": profile or {}}
    g.get("requests", {}).pop(str(account), None)
    g.get("invitations", {}).pop(str(account), None)


def _list_arg(ctx, name):
    v = ctx.json_arg(name, [])
    return v if isinstance(v, list) else []


# ------------------------------------------------------------------ friends (our addition)
#
# BRAIN / OUT had no friends of its own: the Steam build took them from Steam. This is a small
# replacement used by the revive client (GameUser) when it is not running through Steam:
#   GET  /social/friends                       -> {"friends": [{account, credential, name, status, online, room}]}
#        status: "friend" | "incoming" (wants to be your friend) | "outgoing" (you asked)
#   POST /social/friends/add     name|account  -> mutual add = friends; notifies with "friend_request"
#   POST /social/friends/remove  account
#   POST /social/friends/invite  account, room -> message "friend_invite" {room, name, account}
# Online = the player's game server keeps a message session for him; room = last room he joined.
# Storage: friends/<account>.json -> {"friends": [], "incoming": [], "outgoing": []}


def _friends_doc(app, account):
    return app.storage.get("friends", str(account), {"friends": [], "incoming": [], "outgoing": []})


def _account_name(app, account):
    prof = app.storage.get("profiles", str(account)) or {}
    return prof.get("name") or ("#" + str(account))


def _account_credential(app, account):
    for cred, rec in app.storage.all("credentials").items():
        if str(rec.get("account")) == str(account):
            # old records have no "credential": the file name has ':' replaced with '_'
            return rec.get("credential") or cred.replace("_", ":", 1)
    return ""


def _find_account_by_name(app, name):
    name = (name or "").strip().lower()
    if not name:
        return None
    if name.startswith("#") and name[1:].isdigit():
        return name[1:]
    matches = [acc for acc, prof in app.storage.all("profiles").items()
               if (prof.get("name") or "").strip().lower() == name]
    if not matches:
        return None
    # the same nickname can belong to several accounts: prefer the one online, then the newest
    matches.sort(key=lambda acc: (_is_online(app, acc), int(acc) if acc.isdigit() else 0), reverse=True)
    return matches[0]


def _is_online(app, account):
    sessions = getattr(app, "message_sessions", None)
    return bool(sessions and sessions.of(str(account)))


def _friends(ctx, rest, me):
    app = ctx.app
    call = rest[1] if len(rest) > 1 else ""
    if call == "" and ctx.method == "GET":
        doc = _friends_doc(app, me)
        rooms = getattr(app, "player_rooms", {})
        out = []
        for status, accounts in (("friend", doc["friends"]), ("incoming", doc["incoming"]),
                                 ("outgoing", doc["outgoing"])):
            for acc in accounts:
                online = _is_online(app, acc)
                out.append({"account": acc, "credential": _account_credential(app, acc),
                            "name": _account_name(app, acc), "status": status, "online": online,
                            "room": rooms.get(str(acc)) if (online and status == "friend") else None})
        return {"friends": out}

    if call == "add":
        target = str(ctx.arg("account") or "") or _find_account_by_name(app, ctx.arg("name"))
        if not target or app.storage.get("profiles", target) is None:
            raise HttpError(404, {"error": "No such player"})
        if target == me:
            raise HttpError(409, {"error": "That's you"})
        with app.lock:
            mine, theirs = _friends_doc(app, me), _friends_doc(app, target)
            if target in mine["friends"]:
                return {"status": "friend"}
            if target in mine["incoming"]:
                mine["incoming"].remove(target)
                theirs["outgoing"] = [a for a in theirs["outgoing"] if a != me]
                mine["friends"].append(target)
                theirs["friends"].append(me)
                status = "friend"
            else:
                if target not in mine["outgoing"]:
                    mine["outgoing"].append(target)
                if me not in theirs["incoming"]:
                    theirs["incoming"].append(me)
                status = "outgoing"
            app.storage.put("friends", me, mine)
            app.storage.put("friends", target, theirs)
        from .message import deliver
        deliver(app, "user", target, me, "friend_request" if status == "outgoing" else "friend_added",
                {"name": _account_name(app, me), "account": me})
        return {"status": status, "account": target, "name": _account_name(app, target)}

    if call == "remove":
        target = str(ctx.arg("account", required=True))
        with app.lock:
            mine, theirs = _friends_doc(app, me), _friends_doc(app, target)
            for d, other in ((mine, target), (theirs, me)):
                for k in ("friends", "incoming", "outgoing"):
                    d[k] = [a for a in d[k] if a != other]
            app.storage.put("friends", me, mine)
            app.storage.put("friends", target, theirs)
        return {}

    if call == "invite":
        target = str(ctx.arg("account", required=True))
        if target not in _friends_doc(app, me)["friends"]:
            raise HttpError(406, {"error": "Not your friend"})
        from .message import deliver
        deliver(app, "user", target, me, "friend_invite",
                {"room": ctx.arg("room") or "", "name": _account_name(app, me), "account": me})
        return {}

    raise HttpError(404, {"error": "unknown friends call"})


# ------------------------------------------------------------------ handler


def handle(ctx, rest):
    app = ctx.app
    info = token_from(ctx)
    me = str(info["account"])
    if not rest:
        raise HttpError(404, {"error": "no social call"})

    if rest[0] == "friends":
        return _friends(ctx, rest, me)

    if rest[0] == "groups":
        sub = rest[1] if len(rest) > 1 else ""
        if sub == "create":
            join_method = ctx.arg("join_method", "free")
            if join_method not in ("free", "approve", "invite"):
                raise HttpError(400, {"error": "Invalid join method"})
            max_members = int(ctx.arg("max_members", DEFAULT_MAX_MEMBERS))
            if max_members < 2 or max_members > 1000:
                raise HttpError(400, {"error": "Bad max_members"})
            name = ctx.arg("name")
            with app.lock:
                if name and any((g.get("name") or "").lower() == name.lower()
                                for g in app.storage.all("groups").values()):
                    raise HttpError(409, {"error": "Name is busy"})
                g = {
                    "group_id": _next_group_id(app), "name": name, "profile": ctx.json_arg("group_profile", {}) or {},
                    "join_method": join_method, "max_members": max_members, "owner": me,
                    "flags": ["messages"] if str(ctx.arg("group_messages", "true")) == "true" else [],
                    "participants": {}, "requests": {}, "invitations": {},
                }
                _add_member(g, me, MAXIMUM_ROLE, [], ctx.json_arg("participation_profile", {}))
                _save(app, g)
            return {"id": g["group_id"]}

        if sub == "search":
            q = (ctx.arg("query") or "").lower()
            found = [g for g in app.storage.all("groups").values() if q in (g.get("name") or "").lower()]
            found.sort(key=lambda g: int(g["group_id"]))
            return {"groups": [{"group": _group_out(g)} for g in found[:100]]}

        if sub == "profiles":
            if ctx.method == "GET":
                out = {}
                for gid in _list_arg(ctx, "group_ids"):
                    g = app.storage.get("groups", str(gid))
                    if g is None:
                        raise HttpError(404, {"error": "No such group"})
                    out[str(gid)] = {"profile": g["profile"]}
                return {"groups": out}
            profiles = ctx.json_arg("profiles", {}) or {}
            merge = str(ctx.arg("merge", "true")) == "true"
            out = {}
            with app.lock:
                for gid, p in profiles.items():
                    g = _load(app, gid)
                    g["profile"] = _merge(g["profile"], p, merge)
                    _save(app, g)
                    out[str(gid)] = {"profile": g["profile"]}
            return {"groups": out}
        raise HttpError(404, {"error": "unknown groups call"})

    if rest[0] != "group" or len(rest) < 2:
        raise HttpError(404, {"error": "unknown social call"})

    gid = rest[1]
    sub = rest[2:]

    with app.lock:
        g = _load(app, gid)

        if not sub:
            if ctx.method == "GET":
                out = {"group": _group_out(g),
                       "participants": {acc: dict(p) for acc, p in g["participants"].items()},
                       "message": {"recipient_class": GROUP_CLASS, "recipient_key": g["group_id"]}}
                if me in g["participants"]:
                    p = g["participants"][me]
                    out["me"] = {"role": p["role"], "permissions": p["permissions"], "profile": p["profile"]}
                return out
            _participant(g, me)
            if ctx.arg("name"):
                g["name"] = ctx.arg("name")
            if ctx.arg("join_method") in ("free", "approve", "invite"):
                g["join_method"] = ctx.arg("join_method")
            _save(app, g)
            _notify(app, ctx, GROUP_CLASS, gid, me, "group_renamed", g)
            return {}

        call = sub[0]

        if call == "profile":
            if ctx.method == "GET":
                return {"participant": me in g["participants"], "group": {"profile": g["profile"]}}
            _participant(g, me)
            g["profile"] = _merge(g["profile"], ctx.json_arg("profile", {}) or {},
                                  str(ctx.arg("merge", "true")) == "true")
            _save(app, g)
            _notify(app, ctx, GROUP_CLASS, gid, me, "group_profile_updated", g)
            return {"group": {"profile": g["profile"]}}

        if call == "join":
            if g["join_method"] != "free":
                raise HttpError(409, {"error": "The group is not free to join"})
            _add_member(g, me, MINIMUM_ROLE, [], ctx.json_arg("participation_profile", {}))
            _save(app, g)
            return {}

        if call == "leave":
            _participant(g, me)
            if g["owner"] == me and len(g["participants"]) > 1:
                raise HttpError(409, {"error": "The owner should transfer the ownership first"})
            del g["participants"][me]
            if not g["participants"]:
                app.storage.delete("groups", gid)
            else:
                _save(app, g)
            return {}

        if call == "request":
            if g["join_method"] != "approve":
                raise HttpError(409, {"error": "The group does not accept requests"})
            if me in g["participants"]:
                raise HttpError(409, {"error": "Already a member"})
            key = secrets.token_hex(8)
            g.setdefault("requests", {})[me] = {"key": key, "profile": ctx.json_arg("participation_profile", {})}
            _save(app, g)
            _notify(app, ctx, GROUP_CLASS, gid, me, "group_request", g)
            return {"key": key}

        if call in ("approve", "reject") and len(sub) >= 2:
            _participant(g, me)
            target = sub[1]
            req = g.get("requests", {}).get(target)
            if req is None or (ctx.arg("key") and ctx.arg("key") != req["key"]):
                raise HttpError(404, {"error": "No such request"})
            if call == "approve":
                _add_member(g, target, int(ctx.arg("role", MINIMUM_ROLE)), _list_arg(ctx, "permissions"),
                            req.get("profile"))
            else:
                g["requests"].pop(target, None)
            _save(app, g)
            _notify(app, ctx, "user", target, me,
                    "group_request_approved" if call == "approve" else "group_request_rejected")
            return {}

        if call == "invite" and len(sub) >= 2:
            _participant(g, me)
            target = sub[1]
            key = secrets.token_hex(8)
            g.setdefault("invitations", {})[target] = {"key": key, "role": int(ctx.arg("role", MINIMUM_ROLE)),
                                                       "permissions": _list_arg(ctx, "permissions")}
            _save(app, g)
            _notify(app, ctx, "user", target, me, "group_invite")
            return {"key": key}

        if call == "invitation" and len(sub) >= 2:
            inv = g.get("invitations", {}).get(me)
            if inv is None or inv["key"] != ctx.arg("key"):
                raise HttpError(404, {"error": "No such invitation"})
            if sub[1] == "accept":
                _add_member(g, me, inv["role"], inv["permissions"], ctx.json_arg("participation_profile", {}))
                _save(app, g)
            else:
                g["invitations"].pop(me, None)
                _save(app, g)
                _notify(app, ctx, GROUP_CLASS, gid, me, "group_invite_rejected", g)
            return {}

        if call == "participation" and len(sub) >= 2:
            target = me if sub[1] == "me" else sub[1]
            if len(sub) >= 3 and sub[2] == "permissions":
                mine = _participant(g, me)
                p = _participant(g, target)
                role = int(ctx.arg("role", p["role"]))
                if target != me and (role >= mine["role"] or p["role"] >= mine["role"]):
                    raise HttpError(406, {"error": "You cannot set a role >= than yours"})
                if target == me and role > p["role"]:
                    raise HttpError(406, {"error": "You can only downgrade your own role"})
                p["role"] = role
                p["permissions"] = _list_arg(ctx, "permissions")
                _save(app, g)
                _notify(app, ctx, GROUP_CLASS, gid, me, "permissions_updated", g)
                return {}
            if ctx.method == "GET":
                if target not in g["participants"]:
                    raise HttpError(404, {"error": "Player is not participating this group"})
                p = g["participants"][target]
                return {"participation": {"profile": p["profile"], "role": p["role"],
                                          "permissions": p["permissions"]},
                        "owner": g["owner"] == target}
            if ctx.method == "DELETE":
                mine = _participant(g, me)
                if target not in g["participants"]:
                    raise HttpError(404, {"error": "Player is not participating this group"})
                if target != me and g["participants"][target]["role"] >= mine["role"]:
                    raise HttpError(406, {"error": "Your role should be higher"})
                del g["participants"][target]
                _save(app, g)
                _notify(app, ctx, "user", target, me, "kicked")
                return {}
            if target not in g["participants"]:
                raise HttpError(404, {"error": "Player is not participating this group"})
            p = g["participants"][target]
            p["profile"] = _merge(p["profile"], ctx.json_arg("profile", {}) or {},
                                  str(ctx.arg("merge", "true")) == "true")
            _save(app, g)
            _notify(app, ctx, GROUP_CLASS, gid, me, "participation_profile_updated", g)
            return {"profile": p["profile"]}

        if call == "ownership":
            if g["owner"] != me:
                raise HttpError(406, {"error": "You are not the owner"})
            to = str(ctx.arg("account_transfer_to", required=True))
            _participant(g, to)
            g["owner"] = to
            g["participants"][to]["role"] = MAXIMUM_ROLE
            g["participants"][me]["role"] = int(ctx.arg("my_role", 0))
            _save(app, g)
            _notify(app, ctx, GROUP_CLASS, gid, me, "ownership_transferred", g)
            return {}

    raise HttpError(404, {"error": "unknown group call " + "/".join(sub)})
