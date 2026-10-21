"""Stage the Docker build context for the unattended capture image.

The image is built on the server from this context, never from the checkout, so
everything it contains is checked here first: the release wheel against the
published release's SHA256SUMS, the baked queue against its pinned SHA-256, and
the hashed requirements against the release lock. The context's own
`manifest.json` lists the SHA-256 of every staged file except the wheel, whose
hash is the release line in the staged SHA256SUMS; the image build checks both
again.

    gh release download vX.Y.Z -p 'necropsy-X.Y.Z-py3-none-any.whl' -p SHA256SUMS -D REL
    uv run python scripts/stage_capture_image.py --release REL --out CONTEXT

For a separate reviewed queue, supply both --queue QUEUE and --queue-pin PIN.
The pin file contains the queue's SHA-256 alone, as capture/queue.sha256 does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
CAPTURE = REPOSITORY / "capture"
QUEUE = REPOSITORY / "tasks" / "raid-completion" / "capture-queue.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lock_requirements() -> bytes:
    """The release lock's runtime dependencies, hashed, for every platform marker."""
    command = [
        "uv",
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
        "--no-header",
    ]
    exported = subprocess.run(command, cwd=REPOSITORY, check=True, capture_output=True)
    return exported.stdout.replace(b"\r\n", b"\n")


def release_wheel(release: Path, version: str) -> tuple[Path, str]:
    name = f"necropsy-{version}-py3-none-any.whl"
    sums: dict[str, str] = {}
    for line in (release / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, _, file = line.partition(" ")
        sums[file.removeprefix(" ").removeprefix("*")] = digest
    wheel = release / name
    if name not in sums or not wheel.is_file():
        raise ValueError(f"{release} has no {name} listed in SHA256SUMS")
    if sha256(wheel) != sums[name]:
        raise ValueError(f"{name} does not match the release SHA256SUMS")
    return wheel, f"{sums[name]}  {name}\n"


def stage(
    release: Path,
    out: Path,
    version: str,
    *,
    queue: Path | None = None,
    queue_pin: Path | None = None,
) -> dict[str, str]:
    if (queue is None) != (queue_pin is None):
        raise ValueError("supply both --queue and --queue-pin")
    queue = QUEUE if queue is None else queue
    queue_pin = CAPTURE / "queue.sha256" if queue_pin is None else queue_pin
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} is not empty; stage into a fresh directory")
    requirements = (CAPTURE / "requirements.txt").read_bytes()
    if requirements != lock_requirements():
        raise ValueError("capture/requirements.txt does not match uv.lock; re-export it")
    pin = queue_pin.read_text(encoding="ascii").strip()
    if sha256(queue) != pin:
        raise ValueError(f"the capture queue does not match {queue_pin.as_posix()}")
    wheel, sums_line = release_wheel(release, version)
    files = {
        "Dockerfile": CAPTURE / "Dockerfile",
        "entrypoint.sh": CAPTURE / "entrypoint.sh",
        "requirements.txt": CAPTURE / "requirements.txt",
        "capture_runner.py": REPOSITORY / "scripts" / "capture_runner.py",
        "queue/capture-queue.json": queue,
        "www/index.html": CAPTURE / "www" / "index.html",
        "www/status.mjs": CAPTURE / "www" / "status.mjs",
        f"wheel/{wheel.name}": wheel,
    }
    out.mkdir(parents=True, exist_ok=True)
    for target, source in files.items():
        (out / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, out / target)
    (out / "queue" / "capture-queue.sha256").write_bytes(pin.encode() + b"\n")
    (out / "SHA256SUMS").write_bytes(sums_line.encode())
    staged = {
        target: sha256(out / target)
        for target in sorted([*files, "queue/capture-queue.sha256", "SHA256SUMS"])
        if not target.startswith("wheel/")
    }
    manifest = {"version": version, "queue_sha256": pin, "files": staged}
    (out / "manifest.json").write_bytes(json.dumps(manifest, indent=2).encode() + b"\n")
    return staged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True, help="downloaded release assets")
    parser.add_argument("--out", type=Path, required=True, help="fresh build-context directory")
    parser.add_argument("--queue", type=Path, help="reviewed queue (requires --queue-pin)")
    parser.add_argument("--queue-pin", type=Path, help="queue SHA-256 file (requires --queue)")
    args = parser.parse_args(argv)
    from necropsy import __version__

    try:
        staged = stage(
            args.release, args.out, __version__, queue=args.queue, queue_pin=args.queue_pin
        )
    except ValueError as error:
        print(f"stage refused: {error}", file=sys.stderr)
        return 2
    print(f"Staged necropsy {__version__} capture image context in {args.out}")
    for target, digest in staged.items():
        print(f"  {digest[:12]}  {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
