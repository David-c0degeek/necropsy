"""Verify and run bounded, source-backed guidance drafts through LocalPilot ask.

Model output is untrusted. A machine pass is never content approval. The native
text-only ask path has no agent tools; its one provider is explicitly loopback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from necropsy.analysis.roles import ranking_policy  # noqa: E402
from scripts import guidance_lint as gl  # noqa: E402

UNKNOWN = "No supported advice in the provided excerpts."


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class InputPin(Strict):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class Order(Strict):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    kind: Literal["guidance-draft-v1"]
    input: InputPin
    encounter_id: int
    boss: str
    class_id: int
    faction: Literal["Alliance", "Horde"]
    metric: Literal["dps", "hps"]
    category: str
    allowed_keys: list[str] = Field(min_length=1)
    wall_seconds: int = Field(gt=0, le=600)
    max_output_tokens: int = Field(gt=0, le=4096)
    max_prompt_bytes: int = Field(gt=0, le=20000)


class Item(Strict):
    rule: str = Field(pattern=r"^[a-z0-9-]+-v1$")
    section: Literal["strategy"]
    classes: list[int]
    metrics: list[str]
    source: str
    retrieved: str
    text: str = Field(min_length=1, max_length=3000)
    support: list[str] = Field(min_length=1)
    quotes: dict[str, str]


class Category(Strict):
    status: Literal["draft", "unknown"]
    rules: list[str]
    reason: str


class Draft(Strict):
    order_id: str
    encounter_id: int
    boss: str
    items: list[Item] = Field(min_length=2, max_length=8)
    categories: dict[str, Category]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def source_for(order: Order, root: Path = ROOT) -> tuple[dict[str, Any], str]:
    ranking_policy(order.class_id, order.category, order.metric)
    path = (root / order.input.path).resolve()
    if not path.is_relative_to(root.resolve()) or sha(path) != order.input.sha256:
        raise ValueError("input path escapes the repository or differs from its pin")
    review = json.loads(path.read_text(encoding="utf-8"))
    sources = [s for s in review["sources"] if s.get("encounter_id") == order.encounter_id]
    if len(sources) != 1 or sources[0]["boss"] != order.boss:
        raise ValueError("input does not identify exactly the expected encounter")
    source = sources[0]
    if (
        order.class_id not in gl.CLASS_TAGS
        or (order.class_id == 6 and order.faction != "Alliance")
        or (order.class_id == 9 and order.faction != "Horde")
        or len(set(order.allowed_keys)) != len(order.allowed_keys)
        or not set(order.allowed_keys) <= gl._keys(source)
        or not set(order.allowed_keys) <= set(source["excerpts"])
    ):
        raise ValueError("illegal class/faction or unknown/conflicting excerpt scope")
    return source, review["retrieval"]["date"]


def verify(order: Order, data: bytes, root: Path = ROOT) -> list[str]:
    source, date = source_for(order, root)
    draft = Draft.model_validate_json(data)
    findings = []
    if (draft.order_id, draft.encounter_id, draft.boss) != (
        order.id,
        order.encounter_id,
        order.boss,
    ):
        findings.append("draft identity differs from its order")
    if set(draft.categories) != set(gl.CATEGORIES):
        findings.append("draft must account for all eight categories")
    rules = [i.rule for i in draft.items]
    if len(set(rules)) != len(rules):
        findings.append("duplicate rule id")
    referenced = []
    for category in draft.categories.values():
        if category.status == "unknown":
            if category.rules or category.reason != UNKNOWN:
                findings.append(
                    "unknown category must use the exact no-evidence reason and no rules"
                )
        elif not category.rules or category.reason:
            findings.append("draft category needs rules and an empty reason")
        referenced.extend(category.rules)
    if sorted(referenced) != sorted(rules):
        findings.append("each item must belong to exactly one category")
    slug = re.sub(r"[^a-z0-9]+", "-", order.boss.lower()).strip("-")
    for item in draft.items:
        if not item.rule.startswith(f"{slug}-{gl.CLASS_TAGS[order.class_id]}-"):
            findings.append("rule does not identify the boss and class")
        if item.classes != [order.class_id] or item.metrics != [order.metric]:
            findings.append("item class or metric differs from its order")
        if item.source != source["url"] or item.retrieved != date:
            findings.append("citation differs from the frozen source")
        if (
            len(set(item.support)) != len(item.support)
            or not set(item.support) <= set(order.allowed_keys)
            or set(item.quotes) != set(item.support)
            or any(
                not quote or quote != source["excerpts"].get(key)
                for key, quote in item.quotes.items()
            )
        ):
            findings.append("support must name permitted excerpts and quote each exactly")
        numbers = set(re.findall(r"\d+(?:\.\d+)?", item.text))
        quoted_numbers = set(re.findall(r"\d+(?:\.\d+)?", " ".join(item.quotes.values())))
        if not numbers <= quoted_numbers:
            findings.append("item introduces a number absent from its quoted support")
        if re.search(r"\b(?:dispel|decurse|cleanse|remove|cure|abolish)\w*\b", item.text, re.I):
            findings.append("this order has no certified removal capabilities")
    reviews = {
        order.encounter_id: {
            "url": source["url"],
            "retrieved": date,
            "keys": set(order.allowed_keys),
        }
    }
    findings.extend(
        gl.lint(
            {order.encounter_id: draft.model_dump()},
            order.class_id,
            order.faction,
            reviews,
            require_healer_loadout=False,
        )
    )
    return findings


def prompt_for(order: Order, root: Path = ROOT) -> str:
    source, date = source_for(order, root)
    bundle = {
        "order": order.model_dump(),
        "class_tag": gl.CLASS_TAGS[order.class_id],
        "rule_prefix": re.sub(r"[^a-z0-9]+", "-", order.boss.lower()).strip("-")
        + "-"
        + gl.CLASS_TAGS[order.class_id]
        + "-",
        "source_url": source["url"],
        "retrieved": date,
        "excerpts": {k: source["excerpts"][k] for k in order.allowed_keys},
        "output_schema": Draft.model_json_schema(),
        "categories": gl.CATEGORIES,
    }
    prompt = (
        "Return one JSON object only, without markdown fences. Draft at least two short, "
        "source-backed strategy items for this exact class, faction, category and metric. "
        "Use only the supplied excerpts; do not invent mechanics, timers or capabilities. "
        "Each material claim needs nonempty support keys and the exact verbatim quote for "
        "each key. Copy source URL and retrieval date exactly. Rule ids start with the "
        "lowercase hyphenated boss name, then the class tag, and end in -v1. "
        "Account for all eight categories. Each item belongs to exactly one category. "
        "For a category with no supported item use status unknown, rules [], and reason "
        f"{json.dumps(UNKNOWN)}. For a draft category use its rule ids and an empty reason. "
        "Do not infer talents or an individual loadout. There are no certified removal "
        "capabilities in this order, so do not draft dispel/decurse/cleanse/remove advice. "
        "Any positioning advice must say that the logs do not record positions. "
        "This is an unreviewed draft, never an evaluation of a player.\n"
        + json.dumps(bundle, ensure_ascii=False)
    )
    if len(prompt.encode("utf-8")) > order.max_prompt_bytes:
        raise ValueError("prompt exceeds its byte cap")
    return prompt


def tree_digest(root: Path = ROOT) -> str:
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).split(b"\0")
    digest = hashlib.sha256()
    for raw in sorted(n for n in names if n):
        name = raw.decode("utf-8")
        digest.update(raw + b"\0" + sha(root / name).encode() + b"\n")
    return digest.hexdigest()


def run(
    order: Order, workspace: Path, model: str, base_url: str, root: Path = ROOT
) -> dict[str, Any]:
    address = urlsplit(base_url)
    if (
        address.scheme != "http"
        or address.hostname not in {"localhost", "127.0.0.1", "::1"}
        or address.username
        or address.password
        or address.query
        or address.fragment
    ):
        raise ValueError("provider must be an explicit, credential-free loopback HTTP URL")
    workspace = workspace.resolve()
    out = (workspace / order.id).resolve()
    if not workspace.is_relative_to(root.resolve()) or not out.is_relative_to(workspace):
        raise ValueError("work-order output escapes its declared workspace")
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "--", out.relative_to(root).as_posix()],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if ignored.returncode != 0:
        raise ValueError("work-order output must be in a Git-ignored draft directory")
    prompt = prompt_for(order, root)
    executable = shutil.which("localpilot")
    if executable is None:
        raise ValueError("LocalPilot is not installed")
    out.mkdir(parents=True, exist_ok=False)
    (out / "order.json").write_text(
        order.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out / "prompt.txt").write_bytes(prompt.encode("utf-8"))
    packet = {
        "order": order.model_dump(),
        "output_schema": Draft.model_json_schema(),
        "allowed_driver_write_paths": [out.relative_to(root).as_posix() + "/"],
        "model_filesystem_tools": False,
        "verifier_command": [
            "uv",
            "run",
            "python",
            "scripts/guidance_work_order.py",
            "verify",
            (out / "order.json").relative_to(root).as_posix(),
            "--draft",
            (out / "draft.json").relative_to(root).as_posix(),
        ],
    }
    (out / "packet.json").write_text(
        json.dumps(packet, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    # JSON string quoting is also valid TOML basic-string quoting for these values.
    config = (
        '[provider]\ndefault = "bounded-local"\n\n[providers.bounded-local]\nkind = "anthropic"\n'
        f"base_url = {json.dumps(base_url)}\nmodel = {json.dumps(model)}\n"
        'api_key_env = "NECROPSY_LOOPBACK_TRIAL_KEY"\nsuppress_thinking = true\ntemperature = 0.2\n'
        f"max_tokens = {order.max_output_tokens}\n\n[research.web]\nenabled = false\n"
    )
    (out / ".localpilot.toml").write_text(config, encoding="utf-8", newline="\n")
    before = tree_digest(root)
    started = time.monotonic()
    receipt: dict[str, Any] = {
        "order_id": order.id,
        "packet_sha256": sha(out / "packet.json"),
        "order_sha256": sha(out / "order.json"),
        "prompt_sha256": sha(out / "prompt.txt"),
        "config_sha256": sha(out / ".localpilot.toml"),
        "model": model,
        "started_at": datetime.now(UTC).isoformat(),
        "localpilot_binary_sha256": sha(Path(executable)),
        "temperature": 0.2,
        "exit_code": None,
        "runner_sha256": sha(Path(__file__)),
        "max_output_tokens": order.max_output_tokens,
        "wall_seconds_cap": order.wall_seconds,
        "input_tokens": None,
        "output_tokens": None,
        "tree_before": before,
        "content_review": "pending",
        "mechanical_pass": False,
    }
    env = os.environ | {"NECROPSY_LOOPBACK_TRIAL_KEY": "local-loopback-only"}
    try:
        result = subprocess.run(
            [executable, "ask", "--provider", "bounded-local", "--model", model, prompt],
            cwd=out,
            env=env,
            timeout=order.wall_seconds,
            capture_output=True,
            check=False,
        )
        (out / "draft.json").write_bytes(result.stdout)
        (out / "stderr.log").write_bytes(result.stderr)
        receipt["exit_code"] = result.returncode
        receipt["draft_sha256"] = sha(out / "draft.json")
        if result.returncode == 0:
            receipt["findings"] = verify(order, result.stdout, root)
            receipt["mechanical_pass"] = not receipt["findings"]
    except subprocess.TimeoutExpired as error:
        (out / "draft.json").write_bytes(error.stdout or b"")
        (out / "stderr.log").write_bytes(error.stderr or b"")
        receipt["error"] = "wall clock cap reached; partial output retained, not accepted"
    except (ValueError, OSError) as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    finally:
        receipt["tree_after"] = tree_digest(root)
        receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        if receipt["elapsed_seconds"] > order.wall_seconds:
            receipt["mechanical_pass"] = False
            receipt["wall_cap_exceeded"] = True
        if receipt["tree_after"] != before:
            receipt["mechanical_pass"] = False
            receipt["tree_mutation"] = True
        (out / "run.json").write_text(
            json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "run"))
    parser.add_argument("order", type=Path)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--base-url", default="http://127.0.0.1:11435/v1")
    args = parser.parse_args(argv)
    try:
        order = Order.model_validate_json(args.order.read_bytes())
        if args.command == "verify":
            if args.draft is None:
                parser.error("verify requires --draft")
            findings = verify(order, args.draft.read_bytes())
            print(json.dumps({"findings": findings, "content_review": "pending"}))
            return int(bool(findings))
        if args.workspace is None or args.model is None:
            parser.error("run requires --workspace and --model")
        receipt = run(order, args.workspace, args.model, args.base_url)
        print(json.dumps(receipt))
        return int(not receipt["mechanical_pass"])
    except (ValueError, OSError) as error:
        print(f"work order refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
