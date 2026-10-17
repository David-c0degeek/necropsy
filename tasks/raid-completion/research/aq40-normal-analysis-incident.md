# AQ40 installed analysis failure investigation

2026-10-17. The normal installed `analyze --resume --wait-for-reset` acquisition
finished all54 selected actor/fights and108 whole-fight scopes with stopped=null.
It wrote native94217209-2005-20261017T210540.zip and its sidecars; SHA256
deb3e55b5af2a7e6defe168329e3da67936f8808bc00898d1a363d5cb4f1bde7.
The process then exited with Windows native status-1073741819 during analysis,
after its `Analyzing snapshot and writing report, playbook and package` message.
This is not a normal partial-evidence exit4 and is not accepted as successful
live product verification.

No other database ingest/replay/test was running. Independent raw extraction
and enumeration did overlap the analysis; their memory/CPU impact is a possible
confound, not an established cause. The native archive is complete and its
468,825,813 extracted bytes pass unlimited gitleaks with no findings. The earlier
29-source registered archive and previous output evidence remain intact.

Investigation uses the same unchanged installed checkpoint runtime, DuckDB1.5.6
and Python3.14.6, outside the checkout, with a fresh explicit database and Python
fault diagnostics. The first30-second diagnostic shows ordinary report loading
and canonical JSON encoding in normalization. No fault location or root cause
is established yet. Further database work stays serialized. Offline acceptance,
an installed rerun and the actual CLI recovery remain required before treating
this new archive as product-verified evidence.

The first isolated unchanged-installed offline reproduction completed all9 bosses
with exit0 and generated normal outputs. It used a fresh explicit database; no
crash was reproduced. The30-second diagnostic is a periodic progress trace,
not a timeout failure. Root cause remains unestablished. An actual installed
CLI resume with fault diagnostics is running next; no workaround or dependency
change has been adopted.

Primary upstream research:
[DuckDB issue22436](https://github.com/duckdb/duckdb/issues/22436) reports a
Windows/CPython3.14 multi-thread native crash on older tested DuckDB builds.
Its0xC0000409 signature differs from this run's0xC0000005; it is not a verified
match or justification for a dependency workaround. The
[1.5.6 release](https://www.duckdb.org/2026/09/28/announcing-duckdb-156) is already
installed. Current available physical memory is over43 GiB, so an exhausted
machine is not demonstrated. No Application Error1000 event was found in the
queried20-minute window; absence of an event does not explain the failure.

Actual installed CLI recovery completed with the expected partial-evidence
exit4, reused205 saved requests and spent0 new account-wide points. All nine
bosses have personal evidence and five comparisons. Four pet owner listings
remain missing. The recovered native archive211013 and original210540 are
byte-identical (same SHA256 above), including all532 members. The isolated
offline and actual normal CLI now both succeed on exactly the failed run's
immutable bytes. The failure remains recorded as an unreproduced native
incident, not claimed fixed or attributed to upstream without proof. No
dependency, threading or quota workaround has been introduced. Continue new
source/installed aura verification with database workloads serialized.
