# Public PKCE alongside personal authentication

Status: Implemented; registered public sign-in/refresh and API probes observed.
Independent account/machine acceptance and publication approval confirmed by owner
on 2026-10-15.
Date: 2026-10-15

Necropsy now defaults new sign-ins to public S256 PKCE. The application client
ID is public identity; each person authorizes their own account. No distributed
secret is used. `auth login --mode personal` retains the confidential flow for
the owner's own client. Do not convert an existing confidential client implicitly.

Reuse the existing approved OS backend, browser listener and token HTTP client.
Each attempt creates fresh state and an 86-character verifier in memory. Hash
the verifier with SHA256 and send the unpadded base64url challenge. Bind the
listener before opening the external browser; reject incorrect/ambiguous state,
denial, missing code, attempts older than five minutes and consumed attempts.
Consume before exchange, including failed exchanges. Provider invalid_grant
requires a new sign-in, never retrying the authorization code automatically.

Public exchanges and refresh requests carry client_id in form data and no Basic
authorization. Store mode-tagged public records separately under public-client
keys; preserve legacy personal keys and untagged personal JSON readability.
Write the record first, active selection last using the existing generation
store. Failed switching leaves the previous selection usable. A successful
provider refresh followed by a local write failure can invalidate the old refresh
token; sign in again if needed. The OS store is not a distributed transaction.

Acquisition keeps one explicit endpoint per run and its existing endpoint cache
identity. Public mode requires `--endpoint user` on analyze and resolve. Reject
client_credentials before HTTP in public mode. No automatic fallback or endpoint
inference from cached content. Offline replay and analysis JSON are unchanged.

The exact callback remains `http://localhost:8765/callback`, served on IPv4
loopback. Its registered-app approval and WCL permissions must be observed.
Do not promise arbitrary ports, scopes, archive access or refresh issuance from
the general OAuth standard. No extra scopes are requested by default.

Windows/Python 3.14 is the first verification target. Real OS-store probes and
clean installs establish engineering evidence, not independent user acceptance.
macOS/Linux stores remain unverified. No public release until registration,
another account/machine acceptance and explicit publication approval.

Rollback: sign in with `--mode personal --client-id YOUR_PERSONAL_CLIENT_ID`
before downgrading. Public records remain separate. Logout affects the active
mode/client only; `--forget-secret` also removes that record and selection.
Other saved clients/modes must be logged out separately.

Primary contracts: [WCL OAuth](https://www.warcraftlogs.com/api/docs),
[RFC7636](https://www.rfc-editor.org/rfc/rfc7636),
[RFC8252](https://www.rfc-editor.org/rfc/rfc8252).

On 2026-10-15 the owner registered the public client and supplied its public ID.
The packaged default completed S256 browser/loopback sign-in and public refresh
rotation on Windows. User API character lookup, leaderboard, current/archived
report bundles and an event page passed without extra requested scopes. See
[live validation](../live-validation.md) for scope and remaining acceptance.
