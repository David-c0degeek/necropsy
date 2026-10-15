# Readiness evidence — 2026-10-15

Baseline: `b5b0915`, clean main, origin configured. Milestone A review packet
records explicit final approval; all nine classes must remain supported.
No AGENTS.md/CLAUDE.md in checkout or its parent roots. Read README,
CONTRIBUTING, architecture, roadmap, ADR0001–0006, permanent lessons, prior review
packet, original specification's product goals and this plan. Origin is design
history. Preserve graded evidence, immutable raw archives and no-network replay.

Python >=3.14, uv/uv_build, httpx, Typer, keyring, DuckDB, Pydantic, Jinja and
YAML already locked. Extend auth/CLI/client; retain existing callback and approved
credential store, fixed endpoint cache identity, acquisition and offline pipeline.
Wheel already includes rules/templates/assets. Existing installed-rule test is
the starting point for installed command/replay coverage. Extend the existing
live acceptance documentation rather than introduce another acquisition harness.

## Baseline commands

`uv build`: wheel/sdist succeed. `uv run ruff check .`: pass;
`uv run ruff format --check .`: 185 files; `uv run mypy`: 148 files pass.
`uv run pytest tests/unit/test_wcl_auth.py tests/unit/test_wcl_credentials.py -q`:
47 pass. Broad fast suite running; final complete suite remains mandatory.
Golden/acceptance/browser are separate final gates; never substitute skip for pass.

## Primary research and resulting constraints

- https://www.warcraftlogs.com/api/docs (indexed primary text retrieved
  2026-10-15; direct page fetch returns 403): public PKCE exchanges client_id,
  code_verifier, code, grant_type=authorization_code and matching redirect_uri;
  no Basic secret. Authorization adds S256 challenge and state. PKCE accesses
  /api/v2/user. Preserve site-specific vanilla routing already exercised personally.
- https://www.rfc-editor.org/rfc/rfc7636: SHA256 raw digest, unpadded base64url;
  fresh high-entropy verifier (43–128 permitted characters) per attempt.
- https://www.rfc-editor.org/rfc/rfc8252: external browser and loopback listener.
  Retain fixed localhost:8765/callback to match existing callback contract;
  registration-specific support must be observed, not inferred from the RFC.
- WCL's overview does not establish this app's public registration, scope grant,
  refresh issuance/rotation or every archived ranking permission. Gate those on
  a real-account receipt. Request no undocumented scope by default; support
  explicit documented scopes only after primary schema evidence.
- https://docs.astral.sh/uv/guides/package/: build wheel through sdist and
  exercise isolated installed artifact. No publishing during engineering checks.

## Capability discovery and trust

1. Loaded skills/tools: adopt tooling-readiness, pre-mortem and Captain Hindsight
   (local read-only guidance); existing shell/web/pytest sufficient.
2. Enumerated user/project and bundled SKILL.md paths. No dedicated WCL/OAuth
   skill; no project skill/instructions. Existing Python OAuth seam is prior art.
3. Inspected trusted installed plugin registry/cache roots (c0degeek-ai and
   openai bundles); no additional auth implementation needed.
4. Live callable tool inventory and resource/template listing: GitHub/browser/
   artifact tools available; no live WCL MCP. No auth credentials sent to tools.
5. Web searched concrete `Warcraft Logs MCP server skill` and WCL PKCE docs:
   third-party warcraftlogs-mcp and @hillerstorm/wcl candidates deferred. They
   add another credential/network surface and duplicate the current pipeline.
   Sources: https://www.npmjs.com/package/warcraftlogs-mcp and
   https://www.npmjs.com/package/@hillerstorm/wcl . Permission: API credentials
   and network; setup would require npm/MCP configuration; no install approved
   or performed. Official WCL docs adopted as contract, not third-party behavior.

No new dependencies, credentialed tools, network services or permission grants.
Use existing approved locked tools. Document surfaces: README, getting-started,
warcraft-logs, auth, architecture, roadmap, decisions index/new ADR, live acceptance,
CONTRIBUTING and CHANGELOG. JSON schema is unchanged (authentication is outside it).

## Readiness review

Keep: reuse one store/client/pipeline; preserve personal login and offline contracts.
Fix before closing: broad baseline must finish or receive explicit disposition.
Record: original PM-1–PM-3 in pre-mortem; subsequent registered-app validation
cannot be fabricated. Risk: no public client ID/registration evidence supplied.
Verdict: DO NOT CLOSE until baseline finishes; research and guardrails complete.

Subsequent disposition: full baseline completed with 948 passed, 251 deselected.
Updated implementation regression completed with 974 passed, 251 deselected;
11 subsequently added artifact-boundary tests also pass. Readiness is CLOSE;
the initial interim verdict above is retained as historical evidence.
