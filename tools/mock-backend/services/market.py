"""
anthill-market imitation (routes as in anthill-market/server.py). The game uses one market: "freeplay".

GET  /market/markets/<m>                         -> {"settings": {...}}
GET  /market/markets/<m>/items                   -> {"items": [{name, payload, amount}]}   (stash, rubles = "ru")
POST /market/markets/<m>/items          items=[{name, payload, amount(+/-)}]           (all or nothing)
GET  /market/markets/<m>/items/<name>   payload  -> {"amount": n}
POST /market/markets/<m>/items/<name>   payload, amount(+/-)
POST /market/markets/<m>/orders         give_item/give_amount/give_payload, take_*, orders_amount, payload, deadline
                                                 -> {"order_id", "fulfilled_immediately": false}
GET  /market/markets/<m>/orders         filters: owner_id, give_item, give_payload, take_item, take_payload,
                                        give_amount + give_amount_comparison (<,>,=), take_amount + ..., sort_by,
                                        sort_desc, offset, limit -> {"orders": [...]}
GET  /market/markets/<m>/orders/my
GET  /market/markets/<m>/orders/<id>
POST /market/markets/<m>/orders/<id>/fulfill   amount -> {"order_id", "fulfilled_completely"}
POST /market/markets/<m>/orders/<id>/delete    (rest of the escrow goes back to the owner)

Semantics follow anthill-market: an item is (name, payload); amounts can't go below zero (409);
posting an order moves give_amount * orders_amount of the item from the owner into escrow;
fulfilling takes take_amount * n from the buyer, gives it to the owner, gives give_amount * n to the buyer.
Expired orders (deadline passed) are refunded and removed lazily.

Storage: market_items/<market>-<account>.json, market_orders/<id>.json, market_settings/<market>.json
"""

import datetime
import json

from .common import HttpError
from .login import token_from

DEFAULT_SETTINGS = {
    # read by the client (NewSellOrderMenu): fee in percent, minimal fee, price limits
    "fee": 0,
    "fee-minimum": 0,
    "max-price": 50000,
    "max-apt-price": 1000000,
}

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _key(name, payload):
    return name + "|" + json.dumps(payload or {}, sort_keys=True, ensure_ascii=False)


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- items


def _items_doc(app, market, account):
    return app.storage.get("market_items", "%s-%s" % (market, account), {"items": []})


def list_items(app, market, account):
    return _items_doc(app, market, account)["items"]


def update_items(app, market, account, changes):
    """changes: list of {name, payload, amount}; all-or-nothing. Raises 409 if not enough."""
    with app.lock:
        doc = _items_doc(app, market, account)
        index = {_key(i["name"], i.get("payload")): i for i in doc["items"]}
        # check negative balances first (as the original does)
        need = {}
        for ch in changes:
            amount = _int(ch.get("amount"))
            if amount < 0:
                k = _key(ch["name"], ch.get("payload"))
                need[k] = need.get(k, 0) - amount
        for k, n in need.items():
            if k not in index or index[k]["amount"] < n:
                raise HttpError(409, {"error": "Not enough items '%s'" % k.split("|")[0]})
        for ch in changes:
            amount = _int(ch.get("amount"))
            if amount == 0:
                continue
            k = _key(ch["name"], ch.get("payload"))
            if k in index:
                index[k]["amount"] += amount
                if index[k]["amount"] <= 0:
                    del index[k]
            elif amount > 0:
                index[k] = {"name": ch["name"], "payload": ch.get("payload") or {}, "amount": amount}
        doc["items"] = list(index.values())
        app.storage.put("market_items", "%s-%s" % (market, account), doc)


def find_amount(app, market, account, name, payload):
    k = _key(name, payload)
    for i in list_items(app, market, account):
        if _key(i["name"], i.get("payload")) == k:
            return i["amount"]
    return 0


# ---------------------------------------------------------------- orders


def _next_order_id(app):
    meta = app.storage.get("meta", "orders", {"last": 0})
    meta["last"] += 1
    app.storage.put("meta", "orders", meta)
    return str(meta["last"])


def _order_out(o):
    return {k: o[k] for k in ("order_id", "owner_id", "give_item", "give_payload", "give_amount", "take_item",
                              "take_payload", "take_amount", "time", "available", "payload", "deadline")}


def _parse_time(v):
    if not v:
        return None
    for fmt in (TIME_FMT, "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(str(v), fmt)
        except ValueError:
            pass
    return None


def _expire_orders(app):
    now = datetime.datetime.now()
    with app.lock:
        for oid, o in app.storage.all("market_orders").items():
            dl = _parse_time(o.get("deadline"))
            if dl is not None and dl < now:
                _refund_and_delete(app, o)


def _notify(app, o, message_type, extra):
    """Message to the order owner, as anthill-market does (flags remove_delivered)."""
    from .message import deliver
    payload = {
        "order_id": o["order_id"], "give_item": o["give_item"], "give_amount": o["give_amount"],
        "give_payload": o["give_payload"], "take_item": o["take_item"], "take_amount": o["take_amount"],
        "take_payload": o["take_payload"], "payload": o.get("payload") or {},
    }
    payload.update(extra)
    try:
        deliver(app, "user", o["owner_id"], o["owner_id"], message_type, payload, ["remove_delivered"])
    except Exception:
        app.log.exception("market: failed to notify owner %s", o["owner_id"])


def _refund_and_delete(app, o):
    left = o["give_amount"] * o["available"]
    if left > 0:
        update_items(app, o["market"], o["owner_id"],
                     [{"name": o["give_item"], "payload": o["give_payload"], "amount": left}])
    app.storage.delete("market_orders", o["order_id"])
    _notify(app, o, "order_cancelled", {"were_available": o["available"]})


def _json(ctx, name, default):
    v = ctx.json_arg(name, default)
    return v if v is not None else default


def handle(ctx, rest):
    app = ctx.app
    if len(rest) < 2 or rest[0] != "markets":
        raise HttpError(404, {"error": "unknown market call"})
    info = token_from(ctx)
    account = str(info["account"])
    market = rest[1]
    sub = rest[2:]

    if not sub:
        settings = dict(DEFAULT_SETTINGS)
        settings.update(app.storage.get("market_settings", market, {}))
        return {"settings": settings}

    if sub[0] == "items":
        if len(sub) == 1:
            if ctx.method == "GET":
                return {"items": list_items(app, market, account)}
            items = _json(ctx, "items", [])
            if not isinstance(items, list):
                raise HttpError(400, {"error": "Corrupted items"})
            for it in items:
                if not isinstance(it, dict) or "name" not in it or "amount" not in it:
                    raise HttpError(400, {"error": "Item's field 'amount' or 'name' is missing or malformed"})
            update_items(app, market, account, items)
            return {}
        name = sub[1]
        payload = _json(ctx, "payload", {})
        if ctx.method == "GET":
            amount = find_amount(app, market, account, name, payload)
            if amount <= 0:
                raise HttpError(404, {"error": "No such item"})
            return {"amount": amount}
        update_items(app, market, account, [{"name": name, "payload": payload, "amount": _int(ctx.arg("amount"))}])
        return {}

    if sub[0] == "orders":
        _expire_orders(app)

        if len(sub) == 1 and ctx.method == "POST":
            give_amount = max(1, _int(ctx.arg("give_amount", 1), 1))
            take_amount = max(1, _int(ctx.arg("take_amount", 1), 1))
            orders_amount = max(1, _int(ctx.arg("orders_amount", 1), 1))
            o = {
                "market": market,
                "owner_id": account,
                "give_item": ctx.arg("give_item", required=True),
                "give_payload": _json(ctx, "give_payload", {}),
                "give_amount": give_amount,
                "take_item": ctx.arg("take_item", required=True),
                "take_payload": _json(ctx, "take_payload", {}),
                "take_amount": take_amount,
                "available": orders_amount,
                "payload": _json(ctx, "payload", {}),
                "time": datetime.datetime.now().strftime(TIME_FMT),
                "deadline": ctx.arg("deadline") or (datetime.datetime.now()
                                                     + datetime.timedelta(days=30)).strftime(TIME_FMT),
            }
            with app.lock:
                # escrow: take the items from the owner
                update_items(app, market, account, [{"name": o["give_item"], "payload": o["give_payload"],
                                                     "amount": -give_amount * orders_amount}])
                o["order_id"] = _next_order_id(app)
                app.storage.put("market_orders", o["order_id"], o)
            return {"order_id": o["order_id"], "fulfilled_immediately": False}

        if len(sub) == 1 or (len(sub) == 2 and sub[1] == "my"):
            orders = [o for o in app.storage.all("market_orders").values() if o.get("market") == market]
            if len(sub) == 2:
                orders = [o for o in orders if o["owner_id"] == account]
            else:
                a = ctx.args
                if a.get("owner_id"):
                    orders = [o for o in orders if o["owner_id"] == str(a["owner_id"])]
                for side in ("give", "take"):
                    if a.get(side + "_item"):
                        orders = [o for o in orders if o[side + "_item"] == a[side + "_item"]]
                    if a.get(side + "_payload"):
                        want = _json(ctx, side + "_payload", {})
                        orders = [o for o in orders
                                  if all(o[side + "_payload"].get(k) == v for k, v in want.items())]
                    amt, cmp = a.get(side + "_amount"), a.get(side + "_amount_comparison")
                    if amt is not None and cmp:
                        n = _int(amt)
                        ops = {">": lambda x: x > n, "<": lambda x: x < n, "=": lambda x: x == n,
                               ">=": lambda x: x >= n, "<=": lambda x: x <= n}
                        f = ops.get(cmp)
                        if f:
                            orders = [o for o in orders if f(o[side + "_amount"])]
                sort_by = a.get("sort_by")
                if sort_by in ("give_amount", "take_amount", "time", "available"):
                    orders.sort(key=lambda o: o[sort_by], reverse=str(a.get("sort_desc", "true")) == "true")
                else:
                    orders.sort(key=lambda o: _int(o["order_id"]), reverse=True)
                offset = _int(a.get("offset", 0))
                limit = min(_int(a.get("limit", 1000), 1000), 1000)
                orders = orders[offset:offset + limit]
            return {"orders": [_order_out(o) for o in orders]}

        oid = sub[1]
        o = app.storage.get("market_orders", oid)
        if o is None or o.get("market") != market:
            raise HttpError(404, {"error": "No such order"})

        if len(sub) == 2:
            return _order_out(o)

        if sub[2] == "fulfill":
            n = max(1, _int(ctx.arg("amount", 1), 1))
            with app.lock:
                o = app.storage.get("market_orders", oid)
                if o is None or o["available"] < n or o["owner_id"] == account:
                    raise HttpError(409, {"error": "Cannot fulfill the order"})
                need = o["take_amount"] * n
                update_items(app, market, account,
                             [{"name": o["take_item"], "payload": o["take_payload"], "amount": -need}])
                update_items(app, market, o["owner_id"],
                             [{"name": o["take_item"], "payload": o["take_payload"], "amount": need}])
                update_items(app, market, account,
                             [{"name": o["give_item"], "payload": o["give_payload"],
                               "amount": o["give_amount"] * n}])
                o["available"] -= n
                if o["available"] <= 0:
                    app.storage.delete("market_orders", oid)
                    complete = True
                else:
                    app.storage.put("market_orders", oid, o)
                    complete = False
            _notify(app, o, "order_completed", {"give_amount": o["give_amount"] * n,
                                                "amount_completed": n, "amount_left": max(0, o["available"])})
            return {"order_id": oid, "fulfilled_completely": complete}

        if sub[2] == "delete":
            if o["owner_id"] != account and "market_delete_order" not in info["scopes"]:
                raise HttpError(409, {"error": "The order has not been created by you."})
            with app.lock:
                _refund_and_delete(app, o)
            return {}

    raise HttpError(404, {"error": "unknown market call " + "/".join(sub)})
