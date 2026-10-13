"""Parse Warcraft Logs character URLs strictly.

Only HTTPS URLs on the known Warcraft Logs hosts are accepted, with exactly
`/character/id/<positive id>` or `/character/<region>/<realm>/<name>` paths.
Anything else (other hosts, user info, ports, look-alike hosts, query-encoded
path separators) is refused rather than guessed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from necropsy.wcl.sites import SITES, Site


class BadCharacterUrl(ValueError):
    """Not a Warcraft Logs character URL Necropsy can use."""


@dataclass(frozen=True, slots=True)
class CharacterRef:
    site: Site
    character_id: int | None
    region: str | None
    realm: str | None
    name: str | None

    @property
    def by_id(self) -> bool:
        return self.character_id is not None


_REGIONS = frozenset({"us", "eu", "kr", "tw", "cn"})
_ID = re.compile(r"[1-9][0-9]{0,11}")


def _segment(raw: str, what: str) -> str:
    try:
        text = unquote(raw, errors="strict")
    except UnicodeDecodeError:
        raise BadCharacterUrl(f"the {what} is not valid UTF-8") from None
    if not text or any(c in text for c in "/\\?#") or text in (".", ".."):
        raise BadCharacterUrl(f"invalid {what} in the URL: {raw!r}")
    if any(unicodedata.category(c).startswith("C") for c in text):
        raise BadCharacterUrl(f"invalid characters in the {what}")
    return text


def parse_character_url(url: str) -> CharacterRef:
    url = url.strip()
    if any(c.isspace() or unicodedata.category(c).startswith("C") for c in url):
        raise BadCharacterUrl("the URL contains spaces or control characters")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise BadCharacterUrl("not a valid URL") from None
    if parts.scheme != "https":
        raise BadCharacterUrl("use the https:// Warcraft Logs URL")
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        raise BadCharacterUrl("URLs with user information are not accepted")
    if port is not None or ":" in parts.netloc:
        raise BadCharacterUrl("URLs with a port are not accepted")
    host = parts.netloc.lower()
    site = SITES.get(host)
    if site is None:
        raise BadCharacterUrl(f"{parts.netloc} is not a Warcraft Logs site")
    path = parts.path[:-1] if parts.path.endswith("/") else parts.path
    segments = path.split("/")[1:] if path.startswith("/") else []
    if not segments or any(s == "" for s in segments):
        raise BadCharacterUrl("expected /character/id/<id> or /character/<region>/<realm>/<name>")
    if len(segments) == 3 and segments[0] == "character" and segments[1] == "id":
        if not _ID.fullmatch(segments[2]):
            raise BadCharacterUrl("the character id must be a positive number")
        return CharacterRef(site, int(segments[2]), None, None, None)
    if len(segments) == 4 and segments[0] == "character":
        region = _segment(segments[1], "region").lower()
        if region not in _REGIONS:
            raise BadCharacterUrl(f"unknown region {region!r}")
        realm = _segment(segments[2], "realm")
        name = _segment(segments[3], "character name")
        return CharacterRef(site, None, region, realm, name)
    raise BadCharacterUrl("expected /character/id/<id> or /character/<region>/<realm>/<name>")


__all__ = ["BadCharacterUrl", "CharacterRef", "parse_character_url"]
