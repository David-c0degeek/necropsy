"""Warcraft Logs site families and which of them Necropsy may talk to."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Site:
    family: str
    host: str
    supported: bool
    """Only supported sites ever receive credentials or API requests."""

    @property
    def base(self) -> str:
        return f"https://{self.host}"

    @property
    def authorize_url(self) -> str:
        return f"{self.base}/oauth/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.base}/oauth/token"

    @property
    def client_api(self) -> str:
        return f"{self.base}/api/v2/client"

    @property
    def user_api(self) -> str:
        return f"{self.base}/api/v2/user"


SITES: dict[str, Site] = {
    s.host: s
    for s in (
        Site("vanilla", "vanilla.warcraftlogs.com", supported=True),
        Site("fresh", "fresh.warcraftlogs.com", supported=False),
        Site("sod", "sod.warcraftlogs.com", supported=False),
        Site("classic", "classic.warcraftlogs.com", supported=False),
        Site("retail", "www.warcraftlogs.com", supported=False),
    )
}
VANILLA = SITES["vanilla.warcraftlogs.com"]


class UnsupportedSite(Exception):
    """The URL belongs to a Warcraft Logs site Necropsy does not analyse yet."""


def require_supported(site: Site) -> Site:
    """Refuse an unsupported site before any credential lookup or request."""
    if not site.supported:
        raise UnsupportedSite(
            f"{site.host} ({site.family}) is not supported yet; Necropsy currently "
            f"analyses {VANILLA.host} only"
        )
    return site


__all__ = ["SITES", "VANILLA", "Site", "UnsupportedSite", "require_supported"]
