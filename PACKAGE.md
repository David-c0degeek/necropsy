# Necropsy

A Warcraft performance coach backed by combat-log forensics for all nine Classic Era classes in Naxxramas.
Requires Python 3.14 or newer. Includes class rules, offline report templates
and assets. Windows is the first verified installation/credential-store target;
macOS and Linux remain unverified.

Version 0.1.0 is distributed as a reviewed wheel and source archive through the
[repository releases](https://github.com/David-c0degeek/necropsy/releases/tag/v0.1.0).
Repository access is required. Download the wheel and SHA256SUMS; no PyPI
availability is claimed. With uv installed:

```powershell
uv tool install --python 3.14 .\necropsy-0.1.0-py3-none-any.whl
necropsy --version
necropsy auth login
necropsy analyze "YOUR_CHARACTER_URL" --endpoint user --cache .\cache --out .\analysis
```

The registered public application ID is included in the package. Each person grants their
own browser authorization. Public login uses S256 PKCE and requests no shared
client secret. Tokens are stored only in an approved OS credential backend.
Owners of confidential personal clients can use `auth login --mode personal`.
Public-mode acquisition and resolution require explicit `--endpoint user`;
permission failures never switch endpoints. Archived/private access depends on
your account. Expired tokens refresh when a refresh token is issued; otherwise
sign in again. Use `COMMAND --help` for options.

Replay your saved supported snapshot without credentials or network:

```powershell
necropsy offline .\snapshot.zip --out .\offline-analysis
```

Open playbook.html for priorities and your next-pull plan; use report.html to investigate comparisons and evidence. Both are self-contained offline pages. Unknown evidence
stays unknown; exit 4 from acquisition means partial coverage. Read the coverage
notes. Keep your snapshots and reports private unless sharing is authorized.

For an upgrade, install the newly reviewed wheel using `uv tool install --force`.
Before uninstalling, run `necropsy auth logout --forget-secret`, then
`uv tool uninstall necropsy`. Logout removes the active client/mode only;
other saved clients require separate sign-out. Local removal does not revoke
authorization on WCL. Caches, snapshots and reports remain yours to retain/remove.

This package is a local CLI. Desktop UI, hosted services, bundled executables
and automatic updates are outside its current scope.
