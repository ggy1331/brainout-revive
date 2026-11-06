"""Service registry: maps the first URL path segment to a handler(ctx, rest_of_path)."""

from . import environment, discovery, login, profile, stubs, market, game

registry_map = {
    "environment": environment.handle,
    "discovery": discovery.handle,
    "login": login.handle,
    "profile": profile.handle,
    "event": stubs.event,
    "store": stubs.store,
    "market": market.handle,
    "game": game.handle,
    "blog": stubs.blog,
}


class _Registry:
    def get(self, name):
        return registry_map.get(name)

    def names(self):
        return list(registry_map.keys())


registry = _Registry()

# every Anthill service id the game may ask the discovery service about;
# ones without an implementation still get a URL so the request reaches us and is logged
KNOWN_SERVICES = [
    "login", "profile", "market", "game", "event", "social", "store", "leaderboard",
    "message", "blog", "promo", "static", "report", "dlc", "environment", "discovery",
    "exec", "config",
]
