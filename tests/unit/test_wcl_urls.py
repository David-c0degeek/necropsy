"""Character URL parsing refuses anything it cannot trust."""

from __future__ import annotations

import pytest

from necropsy.wcl.sites import UnsupportedSite, require_supported
from necropsy.wcl.urls import BadCharacterUrl, parse_character_url


def test_character_id_url() -> None:
    ref = parse_character_url("https://vanilla.warcraftlogs.com/character/id/86583560")
    assert (ref.site.family, ref.character_id, ref.by_id) == ("vanilla", 86583560, True)


def test_named_url_with_encoded_realm() -> None:
    ref = parse_character_url(
        "https://vanilla.warcraftlogs.com/character/eu/pyrewood-village/H%C3%A4plina"
    )
    assert (ref.region, ref.realm, ref.name) == ("eu", "pyrewood-village", "Häplina")
    assert ref.character_id is None


@pytest.mark.parametrize(
    "url",
    [
        "http://vanilla.warcraftlogs.com/character/id/1",
        "https://vanilla.warcraftlogs.com.evil.example/character/id/1",
        "https://user@vanilla.warcraftlogs.com/character/id/1",
        "https://vanilla.warcraftlogs.com:8443/character/id/1",
        "https://evil.example/character/id/1",
        "https://vanilla.warcraftlogs.com/character/id/0",
        "https://vanilla.warcraftlogs.com/character/id/-5",
        "https://vanilla.warcraftlogs.com/character/id/12abc",
        "https://vanilla.warcraftlogs.com/character/eu/realm",
        "https://vanilla.warcraftlogs.com/character/xx/realm/name",
        "https://vanilla.warcraftlogs.com/character/eu/a%2Fb/name",
        "https://vanilla.warcraftlogs.com/character/eu/realm/..",
        "https://vanilla.warcraftlogs.com/character/eu/realm/na%00me",
        "https://vanilla.warcraftlogs.com/reports/abc",
        "not a url",
        "https://vanilla.warcraftlogs.com:abc/character/id/1",
        "https://vanilla.warcraftlogs.com/character/eu/realm/%FF",
        "https://vanilla.warcraftlogs.com/character//id/1",
        "https://vanilla.warcraftlogs.com/character/id//1",
        "https://vanilla.warcraftlogs.com/character/id/\x011",
        "https://vanilla.warcraftlogs.com/char\tacter/id/1",
        "https://vanilla.warcraftlogs.com/character/id/1 2",
    ],
)
def test_untrusted_urls_are_refused(url: str) -> None:
    with pytest.raises(BadCharacterUrl):
        parse_character_url(url)


def test_other_site_families_parse_but_are_not_supported() -> None:
    ref = parse_character_url("https://fresh.warcraftlogs.com/character/id/1")
    assert ref.site.family == "fresh"
    with pytest.raises(UnsupportedSite, match="not supported yet"):
        require_supported(ref.site)


def test_a_trailing_slash_is_allowed() -> None:
    assert parse_character_url("https://vanilla.warcraftlogs.com/character/id/7/").character_id == 7


def test_malformed_urls_fail_cleanly_in_the_cli() -> None:
    from typer.testing import CliRunner

    from necropsy.cli import app

    for url in (
        "https://vanilla.warcraftlogs.com:abc/character/id/1",
        "https://vanilla.warcraftlogs.com/character/eu/realm/%FF",
    ):
        result = CliRunner().invoke(app, ["resolve", url])
        assert result.exit_code == 1 and result.output.startswith("resolve failed:")
