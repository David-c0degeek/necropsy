"""Headless inspection of explicitly synthetic guidance layout specimens."""

import argparse
import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, help="freshly generated preview directory")
work = parser.parse_args().directory.resolve()
manifest = json.loads((work / "manifest.json").read_bytes())
for specimen in manifest["specimens"]:
    folder = (work / specimen["key"]).resolve()
    if not folder.is_relative_to(work):
        raise SystemExit("specimen escapes preview directory")
    assert (
        hashlib.sha256((folder / "synthetic-analysis.json").read_bytes()).hexdigest()
        == specimen["analysis_sha256"]
    )
    for page_name, digest in specimen["pages"].items():
        assert page_name in {"report", "playbook"}
        assert hashlib.sha256((folder / f"{page_name}.html").read_bytes()).hexdigest() == digest
shots = work / "screenshots"
shots.mkdir(exist_ok=False)
results = []
failures = []
sampled = set()
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    context = browser.new_context()
    context.route("http://**/*", lambda route: route.abort())
    context.route("https://**/*", lambda route: route.abort())
    page = context.new_page()
    errors = []
    remote = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on(
        "request", lambda r: remote.append(r.url) if r.url.startswith(("http:", "https:")) else None
    )
    for specimen in manifest["specimens"]:
        class_id = specimen["configuration"]["class_id"]
        sample = class_id not in sampled
        longest = max(
            specimen["selected_strategy"],
            key=lambda eid: sum(
                len(item["text"]) for item in specimen["selected_strategy"][eid]["items"]
            ),
        )
        for name in ["report", "playbook"]:
            for mode, width, height in [
                ("desktop", 1440, 1000),
                ("mobile", 390, 844),
                ("narrow", 320, 720),
                ("print", 794, 1123),
            ]:
                page.set_viewport_size({"width": width, "height": height})
                page.emulate_media(media="print" if mode == "print" else "screen")
                page.goto((work / specimen["key"] / f"{name}.html").as_uri())
                page.evaluate("document.fonts.ready")
                # Report sources are deliberately disclosed for inspection.
                page.locator("details.encounter-strategy").evaluate_all(
                    "(nodes) => nodes.forEach(n => n.open = true)"
                )
                metrics = page.evaluate("""() => ({
                    width: innerWidth, scroll: document.documentElement.scrollWidth,
                    bosses: document.querySelectorAll('section.boss').length,
                    clipping: [...document.querySelectorAll(
                        '.pull-step p, .encounter-strategy p, .pull-step li')]
                        .filter(n => n.getBoundingClientRect().width > 0
                            && n.scrollWidth > n.clientWidth + 2)
                        .map(n => ({tag: n.tagName, text: n.textContent.slice(0,100),
                            width:n.clientWidth, scroll:n.scrollWidth})),
                    draft: document.querySelector('h1').textContent.includes('DRAFT PREVIEW')})""")
                row = {"key": specimen["key"], "page": name, "mode": mode, **metrics}
                if (
                    metrics["scroll"] > width + 1
                    or metrics["clipping"]
                    or metrics["bosses"] != 15
                    or not metrics["draft"]
                ):
                    failures.append(row)
                for eid, selected in specimen["selected_strategy"].items():
                    target = page.locator(f"#boss-{eid}")
                    content = " ".join(target.inner_text().split())
                    for item in selected["items"]:
                        if " ".join(item["text"].split()) not in content:
                            failures.append(
                                {
                                    "key": specimen["key"],
                                    "page": name,
                                    "mode": mode,
                                    "missing_rule": item["rule"],
                                }
                            )
                        if (
                            target.locator("a").evaluate_all(
                                "(nodes, source) => nodes.some(n => n.href === source)",
                                item["source"],
                            )
                            is not True
                        ):
                            failures.append(
                                {
                                    "key": specimen["key"],
                                    "page": name,
                                    "mode": mode,
                                    "missing_source": item["source"],
                                }
                            )
                if sample and name == "playbook" and mode != "narrow":
                    path = shots / f"class-{class_id}-{mode}-boss-{longest}.png"
                    page.locator(f"#boss-{longest}").screenshot(path=str(path))
                    row["screenshot"] = str(path.relative_to(work))
                    row["screenshot_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                results.append(row)
        sampled.add(class_id)
        print(specimen["key"], "checked", flush=True)
    browser.close()
receipt = {
    "kind": (
        "Synthetic source-bound draft layout review; "
        "no production content or real-capture acceptance."
    ),
    "recipe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "manifest_sha256": hashlib.sha256((work / "manifest.json").read_bytes()).hexdigest(),
    "configurations": len(manifest["specimens"]),
    "views_checked": len(results),
    "classes_sampled": sorted(sampled),
    "screenshots": len(list(shots.glob("*.png"))),
    "browser_errors": errors,
    "remote_requests": remote,
    "failures": failures,
    "checks": results,
}
(work / "layout-checks.json").write_text(
    json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
)
print(
    json.dumps(
        {
            k: receipt[k]
            for k in [
                "configurations",
                "views_checked",
                "classes_sampled",
                "screenshots",
                "browser_errors",
                "remote_requests",
                "failures",
            ]
        }
    )
)
raise SystemExit(1 if failures or errors or remote else 0)
