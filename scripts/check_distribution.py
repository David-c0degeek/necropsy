"""Audit built artifacts and exercise an isolated installed CLI outside the checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from necropsy.report.package import package_name
from necropsy.wcl.acceptance import check_package, secret_scan

PUBLIC_PROBE = """
import json
from urllib.parse import parse_qs
import httpx
from typer.testing import CliRunner
import necropsy
from necropsy.cli import app
from necropsy.wcl import cli
from necropsy.wcl.auth import Auth, AuthMode, PUBLIC_CLIENT_ID
from necropsy.wcl.credentials import CredentialStore
from necropsy.wcl.client import WclClient, RATE_FIELDS
from necropsy.wcl.sites import VANILLA
assert 'site-packages' in necropsy.__file__, necropsy.__file__
class Memory:
    def __init__(self): self.values = {}
    def get_password(self, service, name): return self.values.get((service, name))
    def set_password(self, service, name, value): self.values[service, name] = value
    def delete_password(self, service, name): self.values.pop((service, name), None)
requests = []
def respond(request):
    requests.append(request)
    if request.url.path == '/oauth/token':
        form = parse_qs(request.content.decode())
        assert 'authorization' not in request.headers
        assert 'client_secret' not in form
        assert PUBLIC_CLIENT_ID and form['client_id'] == [PUBLIC_CLIENT_ID]
        assert 43 <= len(form['code_verifier'][0]) <= 128
        return httpx.Response(200, json={
            'access_token': 'synthetic-user-token', 'expires_in': 3600})
    assert request.url.path == '/api/v2/user'
    assert request.headers['Authorization'] == 'Bearer synthetic-user-token'
    return httpx.Response(200, json={'data': {'rateLimitData': {
        'limitPerHour': 3600, 'pointsSpentThisHour': 1, 'pointsResetIn': 60}}})
transport = httpx.MockTransport(respond)
auth = Auth(VANILLA, CredentialStore(Memory()), transport=transport)
cli._auth = lambda: auth
class Listener:
    def __init__(self, state): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def wait(self): return 'synthetic-code'
cli.CallbackListener = Listener
result = CliRunner().invoke(app, [
    'auth', 'login', '--no-browser'])
assert result.exit_code == 0, result.output
assert 'secret' not in result.output.lower()
assert auth.mode() is AuthMode.PUBLIC
client = WclClient(VANILLA, auth.token_for, transport=transport)
try: client.query('query { ' + RATE_FIELDS + ' }', endpoint='user')
finally: client.close()
assert len(requests) == 2
print('installed public CLI + synthetic user API: passed')
"""

STORE_PROBE = """
import secrets
from necropsy.wcl import credentials
credentials.SERVICE = 'necropsy-install-probe-' + secrets.token_hex(12)
store = credentials.CredentialStore.open()
try:
    store.set('probe', 'synthetic-probe-value-' * 200)
    assert store.get('probe') == 'synthetic-probe-value-' * 200
    store.set('probe', 'replacement')
    assert store.get('probe') == 'replacement'
finally:
    store.delete('probe')
assert store.get('probe') is None
print(store.backend_name)
"""


def run(argv: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600
    )
    if result.returncode:
        raise RuntimeError(f"{Path(argv[0]).name} failed ({result.returncode}): {result.stderr}")
    return result.stdout.strip()


def members(artifact: Path) -> dict[str, bytes]:
    if artifact.suffix == ".whl":
        with zipfile.ZipFile(artifact) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("duplicate wheel member")
            return {name: archive.read(name) for name in names if not name.endswith("/")}
    with tarfile.open(artifact) as archive:
        result = {}
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile() or member.name in result:
                raise ValueError("unsupported or duplicate sdist member")
            stream = archive.extractfile(member)
            assert stream is not None
            result[member.name] = stream.read()
        return result


def audit(artifact: Path, destination: Path) -> dict[str, Any]:
    data = members(artifact)
    for name, payload in data.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("unsafe artifact member")
        parts = path.parts if artifact.suffix == ".whl" else path.parts[1:]
        if not parts:
            raise ValueError("artifact member has no package-relative path")
        # uv's minimal sdist contains only build metadata, README and package source.
        permitted = (
            parts[0] == "necropsy" or parts[0].endswith(".dist-info")
            if artifact.suffix == ".whl"
            else parts in [("README.md",), ("PACKAGE.md",), ("pyproject.toml",), ("PKG-INFO",)]
            or parts[:2] == ("src", "necropsy")
        )
        if not permitted or path.suffix in {".zip", ".duckdb", ".whl", ".pyc"}:
            raise ValueError(f"unexpected packaged member: {name}")
        if b"C:\\repos\\" in payload or b"C:/repos/" in payload or b"/Users/" in payload:
            raise ValueError(f"developer-local path in artifact: {name}")
        target = destination.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    scan = secret_scan(destination)
    if scan["status"] != "passed":
        raise RuntimeError(f"artifact secret scan: {scan['status']}")
    return {
        "file": artifact.name,
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "bytes": artifact.stat().st_size,
        "members": len(data),
        "extracted_bytes": sum(map(len, data.values())),
        "secret_scan": scan,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--probe-os-store", action="store_true")
    args = parser.parse_args()
    (wheel,) = args.dist.resolve().glob("necropsy-*.whl")
    (sdist,) = args.dist.resolve().glob("necropsy-*.tar.gz")
    snapshot = args.snapshot.resolve(strict=True)
    # Isolate from editable imports, client selection and developer credentials.
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"PYTHONPATH", "VIRTUAL_ENV"} and not k.startswith("NECROPSY_")
    }
    env["PYTHONUTF8"] = "1"
    with tempfile.TemporaryDirectory(prefix="necropsy-install-") as temporary:
        work = Path(temporary)
        artifacts = [audit(path, work / path.name) for path in (wheel, sdist)]
        run(["uv", "venv", str(work / "venv"), "--python", sys.executable], work, env)
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        command = python.with_name("necropsy.exe" if os.name == "nt" else "necropsy")
        run(["uv", "pip", "install", "--python", str(python), str(wheel)], work, env)
        version = run([str(command), "--version"], work, env)
        run([str(command), "--help"], work, env)
        public = run([str(python), "-c", PUBLIC_PROBE], work, env)
        output = work / "replay"
        replay = run([str(command), "offline", str(snapshot), "--out", str(output)], work, env)
        for name in ("analysis.json", "report.html", "playbook.html"):
            if not (output / name).is_file():
                raise RuntimeError(f"installed replay missing {name}")
        # A valid old report is still the wrong installation: verify the current
        # shell and the exact embedded assets from this source tree.
        assets = Path(__file__).resolve().parents[1] / "src/necropsy/report/render/assets"
        for name in ("report.html", "playbook.html"):
            html = (output / name).read_text(encoding="utf-8")
            for marker in ('data-theme="dark"', 'data-class="hunter"', "Next-pull clarity."):
                if marker not in html:
                    raise RuntimeError(f"installed {name} lacks current design: {marker}")
            for asset in ("report.css", "report.js"):
                if (assets / asset).read_text(encoding="utf-8") not in html:
                    raise RuntimeError(f"installed {name} has outdated {asset}")
        document = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
        snapshot_digest = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        if document["snapshot"]["archive_sha256"] != snapshot_digest:
            raise RuntimeError("installed replay source digest differs")
        package = output / package_name(document)
        if check_package(package):
            raise RuntimeError("installed replay package integrity failed")
        with zipfile.ZipFile(package) as archive:
            for name in ("analysis.json", "report.html", "playbook.html"):
                if archive.read(name) != (output / name).read_bytes():
                    raise RuntimeError("installed replay package differs from output")
        scan = secret_scan(output)
        if scan["status"] != "passed":
            raise RuntimeError(f"replay scan: {scan['status']}")
        backend = (
            run([str(python), "-c", STORE_PROBE], work, env)
            if args.probe_os_store
            else "not performed"
        )
        receipt = {
            "version": version,
            "platform": sys.platform,
            "python": sys.version.split()[0],
            "artifacts": artifacts,
            "installed_public_auth": public,
            "installed_offline_replay": "passed",
            "replay_secret_scan": scan,
            "snapshot_sha256": snapshot_digest,
            "installed_package_integrity": "passed",
            "credential_backend_probe": backend,
            "live_public_account": "not performed",
            "independent_user": "not performed",
            "replay_output_lines": len(replay.splitlines()),
        }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"Installation checks passed; receipt: {args.receipt}")


if __name__ == "__main__":
    main()
