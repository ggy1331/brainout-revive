"""Sync of a player's progress between a local solo backend (single player PvE on his own PC)
and the host's online backend. Our addition, not an Anthill service.

What is synced: the profile (stats, items, levels...) and the market inventories (Conflict Zone
stash, rubles `ru`, real estate). Orders on the flea market stay on the host.

Every backend keeps per account (collection `sync`):
  dirty_profile / dirty_items - changed since the last sync with the peer
  synced                      - was ever linked with the peer
  base_items                  - inventories as of the last sync (for the three-way merge)
  mtime                       - last change (only to break a tie when both sides changed)

Rules (local side runs them, see sync_with_host):
  host has no account for the nick -> nothing (local progress waits until he logs in online once)
  local has no account yet         -> host snapshot is kept as "pending" and becomes the profile of the
                                      first account created on this local backend (solo mode)
  never linked                     -> the older account wins (it is the one with the real progress)
  profile                          -> the changed side wins; both changed -> the newer one
  inventories                      -> three-way merge: local + (host - base); so rubles from a lot sold
                                      on the host while you played solo are not lost

HTTP (both sides):  GET /revive/snapshot?name=NICK    POST /revive/apply {name, profile, items, base_items}
"""

import json
import threading
import time
import urllib.request

from .common import HttpError

_quiet = threading.local()


def is_quiet():
    return getattr(_quiet, "on", False)


def on_put(app, collection, key):
    """Storage hook: mark the account dirty on profile / inventory writes."""
    if is_quiet():
        return
    if collection == "profiles":
        account, field = str(key), "dirty_profile"
    elif collection == "market_items":
        account, field = str(key).rsplit("-", 1)[-1], "dirty_items"
    else:
        return
    st = app.storage
    with app.lock:
        s = st.get("sync", account, {})
        if s.get(field) and time.time() - s.get("mtime", 0) < 5:
            return  # avoid rewriting the sync file on every save
        s[field] = True
        s["mtime"] = time.time()
        _quiet.on = True
        try:
            st.put("sync", account, s)
        finally:
            _quiet.on = False


# ------------------------------------------------------------------ local data

def _human_accounts(app):
    out = []
    for cred, rec in app.storage.all("credentials").items():
        c = rec.get("credential") or cred
        if not c.startswith("server"):
            out.append((str(rec.get("account")), rec.get("created", 0)))
    return out


def account_of(app, name):
    if getattr(app, "solo_name", None):
        accs = _human_accounts(app)
        if not accs:
            return None
        accs.sort(key=lambda a: a[1])
        return accs[0][0]
    from .social import _find_account_by_name
    return _find_account_by_name(app, name)


def _created(app, account):
    for acc, created in _human_accounts(app):
        if acc == str(account):
            return created
    return 0


def _items(app, account):
    out = {}
    for key, doc in app.storage.all("market_items").items():
        market, _, acc = key.rpartition("-")
        if acc == str(account):
            out[market] = doc.get("items", [])
    return out


def snapshot(app, name):
    account = account_of(app, name)
    if account is None:
        return {"exists": False}
    s = app.storage.get("sync", account, {})
    return {"exists": True, "account": account, "created": _created(app, account),
            "synced": bool(s.get("synced")), "dirty_profile": bool(s.get("dirty_profile")),
            "dirty_items": bool(s.get("dirty_items")), "mtime": s.get("mtime", 0),
            "base_items": s.get("base_items", {}),
            "profile": app.storage.get("profiles", account) or {}, "items": _items(app, account)}


def apply(app, name, profile, items, base_items, account=None):
    """Overwrite (profile if not None, items if not None) and mark synced & clean."""
    account = account or account_of(app, name)
    if account is None:
        raise HttpError(404, {"error": "no account for " + str(name)})
    st = app.storage
    with app.lock:
        _quiet.on = True
        try:
            if profile is not None:
                profile = dict(profile)
                if name:
                    profile["name"] = profile.get("name") or name
                st.put("profiles", account, profile)
            if items is not None:
                markets = set(items) | set(_items(app, account))
                for market in markets:
                    st.put("market_items", "%s-%s" % (market, account), {"items": items.get(market, [])})
            st.put("sync", account, {"synced": True, "dirty_profile": False, "dirty_items": False,
                                     "mtime": time.time(), "base_items": base_items or {}})
        finally:
            _quiet.on = False
    app.log.info("revive: progress of %s (account %s) updated%s%s", name, account,
                 " [profile]" if profile is not None else "", " [items]" if items is not None else "")
    return {"ok": True, "account": account}


def adopt_pending(app, account):
    """Solo mode: the first account created gets the progress pulled from the host."""
    pending = app.storage.get("sync", "pending")
    if not pending:
        return
    app.storage.delete("sync", "pending")
    apply(app, getattr(app, "solo_name", None), pending.get("profile"), pending.get("items"),
          pending.get("items"), account=account)


# ------------------------------------------------------------------ merge

def _key(item):
    return item["name"] + "|" + json.dumps(item.get("payload") or {}, sort_keys=True)


def merge_items(local, host, base):
    """local + (host - base), per market and item."""
    out = {}
    for market in set(local) | set(host) | set(base):
        amounts, proto = {}, {}
        for src, sign in ((local.get(market, []), 1), (host.get(market, []), 1), (base.get(market, []), -1)):
            for i in src:
                k = _key(i)
                proto.setdefault(k, i)
                amounts[k] = amounts.get(k, 0) + sign * int(i.get("amount", 0))
        out[market] = [dict(proto[k], amount=a) for k, a in amounts.items() if a > 0]
    return out


def _http(url, data=None, timeout=4):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def sync_with_host(app, name, host_url):
    """Run on the local (solo) backend. Returns a short human-readable result."""
    from urllib.parse import quote
    try:
        host = _http("%s/revive/snapshot?name=%s" % (host_url, quote(name)))
    except Exception as e:
        return "хост недоступен (%s), прогресс останется локально до следующего раза" % e.__class__.__name__
    local = snapshot(app, name)

    def push(profile, items, base):
        _http(host_url + "/revive/apply", {"name": name, "profile": profile, "items": items, "base_items": base})

    if not host.get("exists"):
        return "на хосте ещё нет аккаунта %s — зайдите один раз в онлайн, потом прогресс подтянется" % name

    if not local.get("exists"):
        app.storage.put("sync", "pending", {"profile": host["profile"], "items": host["items"]})
        push(None, None, host["items"])  # host: linked, clean
        return "прогресс загружен с хоста"

    if not (local["synced"] and host["synced"]):
        # first link: the older account holds the real progress
        if host.get("created", 0) <= local.get("created", 0):
            apply(app, name, host["profile"], host["items"], host["items"])
            push(None, None, host["items"])
            return "первая привязка: взят прогресс с хоста"
        push(local["profile"], local["items"], local["items"])
        apply(app, name, None, None, local["items"])
        return "первая привязка: прогресс отправлен на хост"

    # profile
    profile_to_host = profile_to_local = None
    if local["dirty_profile"] and host["dirty_profile"]:
        if local["mtime"] >= host["mtime"]:
            profile_to_host = local["profile"]
        else:
            profile_to_local = host["profile"]
    elif local["dirty_profile"]:
        profile_to_host = local["profile"]
    elif host["dirty_profile"]:
        profile_to_local = host["profile"]

    # inventories
    items = None
    if local["dirty_items"] or host["dirty_items"]:
        items = merge_items(local["items"], host["items"], local["base_items"])

    if profile_to_host is None and profile_to_local is None and items is None:
        return "изменений нет"
    push(profile_to_host, items, items if items is not None else local["base_items"])
    apply(app, name, profile_to_local, items, items if items is not None else local["base_items"])
    parts = []
    if profile_to_host is not None:
        parts.append("профиль → хост")
    if profile_to_local is not None:
        parts.append("профиль ← хост")
    if items is not None:
        parts.append("тайник и рубли объединены")
    return ", ".join(parts)


# ------------------------------------------------------------------ HTTP

def handle(ctx, rest):
    app = ctx.app
    call = rest[0] if rest else ""
    if call == "snapshot":
        return snapshot(app, ctx.arg("name", required=True))
    if call == "apply" and ctx.method == "POST":
        return apply(app, ctx.arg("name", required=True), ctx.arg("profile"), ctx.arg("items"),
                     ctx.arg("base_items"))
    if call == "sync" and ctx.method == "POST":
        host = getattr(app, "sync_host", None)
        if not host:
            return {"result": "хост не задан"}
        return {"result": sync_with_host(app, app.solo_name, host)}
    raise HttpError(404, {"error": "unknown revive call " + call})
