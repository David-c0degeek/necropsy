# Architecture decisions

[Documentation](../README.md) · [Current architecture](../architecture.md)

These accepted decisions describe implemented contracts and their consequences.
They describe design boundaries; actual authenticated Windows validation is
recorded separately in [observed live validation](../live-validation.md). The confidential-client design is for personal use.

| Decision | Contract |
|---|---|
| [Personal authentication](0001-personal-authentication.md) | One approved OS credential store; public-client PKCE required before distribution |
| [Bounded acquisition and fair cohorts](0002-bounded-acquisition.md) | Fixed endpoint, explicit context, graded faction and bounded comparison samples |
| [Immutable revision generations](0003-immutable-generations.md) | No-clobber cache, verified completion and whole-entry restarts |
| [Snapshots and derived outputs](0004-snapshots-and-derived-outputs.md) | Strict live archive, shared offline pipeline, rebuildable database and explicit output replacement |
