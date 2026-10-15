"""Check local Markdown links and heading anchors on maintained product surfaces."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def anchors(text: str) -> set[str]:
    found: set[str] = set()
    counts: dict[str, int] = {}
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE):
        slug = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        found.add(f"{slug}-{count}" if count else slug)
    return found


def main() -> None:
    files = [ROOT / name for name in ("README.md", "PACKAGE.md", "CHANGELOG.md", "CONTRIBUTING.md")]
    files.extend(sorted((ROOT / "docs").glob("*.md")))
    errors: list[str] = []
    checked = 0
    for file in files:
        text = re.sub(r"```.*?```", "", file.read_text(encoding="utf-8"), flags=re.DOTALL)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            url = urlsplit(target.strip("<>"))
            if url.scheme or url.netloc:
                continue
            path = (file.parent / unquote(url.path)).resolve() if url.path else file
            checked += 1
            if not path.exists():
                errors.append(f"{file.relative_to(ROOT)}: missing {target}")
            elif (
                url.fragment
                and path.suffix == ".md"
                and unquote(url.fragment) not in anchors(path.read_text(encoding="utf-8"))
            ):
                errors.append(f"{file.relative_to(ROOT)}: missing anchor {target}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Checked {checked} local links across {len(files)} maintained Markdown files.")


if __name__ == "__main__":
    main()
