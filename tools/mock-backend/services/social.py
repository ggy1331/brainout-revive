"""
anthill-social imitation (groups = clans). For now only membership lookups used by the message
service; the group API (create/search/join/requests/invitations/permissions...) comes next.

Storage: groups/<group_id>.json -> {"group_id", "name", "owner", "participants": {account: {...}}, ...}
"""

from .common import HttpError


def groups_of(app, account):
    account = str(account)
    return [gid for gid, g in app.storage.all("groups").items()
            if account in (g.get("participants") or {})]


def group_member_accounts(app, group_id):
    g = app.storage.get("groups", group_id)
    return list((g or {}).get("participants", {}).keys())


def handle(ctx, rest):
    raise HttpError(404, {"error": "social call not implemented yet: " + "/".join(rest)})
