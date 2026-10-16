"""Explicit stable-release discovery from Necropsy's public GitHub repository."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import httpx

REPOSITORY = "https://github.com/David-c0degeek/necropsy"
LATEST_RELEASE = "https://api.github.com/repos/David-c0degeek/necropsy/releases/latest"
MAX_ASSET_SIZE = 1024 * 1024 * 1024
_VERSION = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
_SHA256 = re.compile(r"^sha256:([a-fA-F0-9]{64})$")


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    identifier: int
    sha256: str | None


@dataclass(frozen=True)
class Release:
    version: str
    notes: str
    assets: dict[str, Asset]

    @property
    def url(self) -> str:
        return f"{REPOSITORY}/releases/tag/v{self.version}"


def version_key(value: str) -> tuple[int, int, int, bool]:
    match = _VERSION.fullmatch(value)
    if match is None:
        raise ValueError("The app or release version could not be understood. Update manually.")
    return int(match[1]), int(match[2]), int(match[3]), match[4] is None


def client() -> httpx.Client:
    return httpx.Client(
        timeout=30,
        follow_redirects=False,
        trust_env=False,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "Necropsy-desktop-updates",
        },
    )


def check_response(response: httpx.Response) -> None:
    if response.status_code in (403, 429):
        raise ValueError("GitHub is limiting update checks. Try again later.")
    response.raise_for_status()
    # GitHub release downloads redirect to its public asset storage.
    _trusted_url(response.url)


def _trusted_url(url: httpx.URL) -> None:
    if (
        url.scheme != "https"
        or url.username
        or url.password
        or url.port not in (None, 443)
        or url.host
        not in {
            "api.github.com",
            "github.com",
            "release-assets.githubusercontent.com",
            "objects.githubusercontent.com",
            "github-releases.githubusercontent.com",
        }
    ):
        raise ValueError("The update download redirected outside GitHub. Nothing was installed.")


@contextmanager
def stream_response(connection: httpx.Client, url: str) -> Iterator[httpx.Response]:
    address = httpx.URL(url)
    for _ in range(6):
        _trusted_url(address)
        with connection.stream("GET", address, follow_redirects=False) as response:
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("The update download has no destination. Try again later.")
                address = address.join(location)
                continue
            yield response
            return
    raise ValueError("The update download redirected too many times. Nothing was installed.")


def latest_release(connection: httpx.Client) -> Release | None:
    with stream_response(connection, LATEST_RELEASE) as response:
        if response.status_code == 404:
            return None
        check_response(response)
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError("The release response was too large. Try again later.")
    try:
        raw = json.loads(data)
        return parse_release(raw)
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError(
            "The release information is incomplete. Try checking again later."
        ) from error


def parse_release(raw: Any) -> Release:
    tag = raw["tag_name"]
    if not isinstance(tag, str) or not tag.startswith("v"):
        raise ValueError("The release tag is not a supported Necropsy version.")
    version = tag[1:]
    if (
        not version_key(version)[3]
        or raw.get("draft") is not False
        or raw.get("prerelease") is not False
    ):
        raise ValueError("Only published stable releases can update this app.")
    if raw.get("html_url") != f"{REPOSITORY}/releases/tag/{tag}":
        raise ValueError("The release does not belong to Necropsy's official repository.")
    assets = {}
    for item in raw["assets"]:
        name, size, identifier = item["name"], item["size"], item["id"]
        if (
            not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9._-]+", name)
            or name in assets
            or item.get("state") != "uploaded"
            or type(size) is not int
            or not 0 < size <= MAX_ASSET_SIZE
            or type(identifier) is not int
            or identifier <= 0
        ):
            raise ValueError("The release assets are incomplete or ambiguous. Try again later.")
        url = f"{REPOSITORY}/releases/download/{tag}/{name}"
        if item["browser_download_url"] != url:
            raise ValueError("A release asset is outside Necropsy's official downloads.")
        digest = item.get("digest")
        match = _SHA256.fullmatch(digest) if isinstance(digest, str) else None
        if digest is not None and match is None:
            raise ValueError("A release asset has an unsupported checksum.")
        assets[name] = Asset(name, url, size, identifier, match[1].lower() if match else None)
    notes = raw.get("body") or "No release notes were provided."
    if not isinstance(notes, str):
        raise ValueError("The release notes could not be understood.")
    return Release(version, notes[:16000], assets)


def platform_archive(system: str, machine: str) -> str | None:
    arch = machine.lower()
    if system == "win32" and arch in ("amd64", "x86_64"):
        return "windows-x86_64.zip"
    if system == "darwin" and arch in ("arm64", "aarch64", "x86_64", "amd64"):
        return f"macos-{'arm64' if arch in ('arm64', 'aarch64') else 'x86_64'}.tar.gz"
    if system == "linux" and arch in ("x86_64", "amd64"):
        return "linux-x86_64.tar.gz"
    return None
