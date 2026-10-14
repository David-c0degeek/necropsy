# Immutable cache and whole-entry revision generations

Status: Accepted · Date: 2026-10-13

[Decision index](README.md) · [Architecture](../architecture.md)

## Context

Report data can change between requests. A cache path alone cannot prove that
pages belong to one actor, endpoint, filter or revision. Interrupted cleanup must
not replace completed evidence or follow a link outside the cache.

## Decision

Key API data by site family, report code, revision and fight; identify streams by
endpoint, actor role, ID and direction. Validate names, containment and link/reparse paths.
Store the full canonical query identity separately from fetch-time metadata.
Publish fsynced owned temporaries with no-clobber hard links under OS advisory
locks; identical content may be reused, conflicting content fails. Write the
completion marker last and verify identity, hashes, counts and pagination on read.
Completion requires an explicit null terminal cursor.

Cache format 2 stores report bundles and combined report sets as generations named
by endpoint and full content SHA-256. Rankings and archive-access metadata can
change without a report re-export; revision alone does not identify their bytes.
Each run fetches a fresh bundle and combined finalization answer, then records and
reads that exact generation. Completed event pages can be reused only when their
full canonical request identity matches. They are immutable local observations,
not an API guarantee that all response data remains unchanged.

Every events request also checks the report revision. If it changes, restart the
whole entry once, including bundle, actor, faction, pet ownership and streams.
Keep old immutable generations. Unknown pet ownership stays unknown. Recovery
cleans only owned incomplete stream files while holding its lock.

## Alternatives and consequences

Replacing completed files or resuming solely from page names was rejected.
Hard-link publication is required; unsupported filesystems fail explicitly rather
than using an overwrite fallback. OS locks release on process death. Durability
depends on fsync and link behavior; directory entries are not fsynced everywhere.
Cache reuse can replay an older immutable generation offline; network acquisition
checks the current revision. Fetch point metadata is account-wide accounting,
not an exact stream cost.

Format 1 caches are refused without modification. Use a new cache directory and
retain the previous one; there is no in-place migration. Existing historical and
live snapshot v1 archives remain readable. These guards address cache conflicts
observed during the first authenticated attempts.

API reference: [WCL report schema](https://vanilla.warcraftlogs.com/v2-api-docs/warcraft/report.doc.html)
describes changing rankings and report revision on re-export.

Implementation: [cache](../../src/necropsy/wcl/cache.py),
[fetch](../../src/necropsy/wcl/fetch.py),
[entry orchestration](../../src/necropsy/wcl/acquire.py).

