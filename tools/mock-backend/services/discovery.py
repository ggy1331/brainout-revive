"""
anthill-discovery: GET /discovery/services/<id1>,<id2>,...
Returns {"id": "url", ...} for every requested service.
"""

from .common import HttpError


def handle(ctx, rest):
    if len(rest) >= 2 and rest[0] == "services":
        ids = [s for s in rest[1].split(",") if s]
        return {sid: ctx.app.service_url(sid) for sid in ids}
    if len(rest) >= 2 and rest[0] == "service":
        return ctx.app.service_url(rest[1])
    raise HttpError(404, {"error": "unknown discovery call"})
