"""
Minimal answers for services that are not implemented yet, so the game does not log errors.

event: GET /event/events            -> {"events": []}      (time-limited events / battle pass: TODO)
store: POST /store/orders           -> {"orders": []}      (pending store orders: TODO)
"""

from .common import HttpError


def event(ctx, rest):
    if rest and rest[0] == "events":
        return {"events": []}
    raise HttpError(404, {"error": "event call not implemented: " + "/".join(rest)})


def blog(ctx, rest):
    # GET /blog/blog/<name> -> {"entries": []}   (news in the main menu; TODO: own news feed)
    if rest and rest[0] == "blog":
        return {"entries": []}
    raise HttpError(404, {"error": "blog call not implemented: " + "/".join(rest)})


def store(ctx, rest):
    if rest and rest[0] == "orders":
        return {"orders": []}
    raise HttpError(404, {"error": "store call not implemented: " + "/".join(rest)})
