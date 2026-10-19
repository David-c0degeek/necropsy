# Unattended credential file

Status: accepted · 2026-10-19

ADR 0001 keeps Warcraft Logs credentials in exactly one approved OS credential
store, with no file fallback. An unattended Linux server, such as a capture
container that runs for days, has no Windows Credential Locker, Keychain,
Secret Service or KWallet. The owner chose an explicit token file for that
case. This record narrows ADR 0001; it does not replace it.

`NECROPSY_CREDENTIAL_FILE` names one JSON file, and only that selects it. It
is never a fallback: without the variable, store selection and its errors are
unchanged. Setting it together with `NECROPSY_KEYRING_BACKEND` is refused
before either store is opened. It is POSIX-only and refused on Windows.

The file must be a regular file (a link is refused), mode exactly `0600`, owned
by the process user. Its directory must be a plain directory with mode `0700`,
owned by the same user. Any other state is refused with a fixed message that
never includes file content. The directory, not the single file, is mounted
into a container, so rotation can replace the file.

Every write rewrites the whole file through a `0600` temporary file in the same
directory: write, fsync, rename, then fsync the directory. A failure before the
rename removes the temporary file, keeps the previous file and raises. A
failure while syncing the directory after the rename also raises, but then
either the previous or the new complete file may be on disk; durability is
uncertain, never partial. In both cases a caller that has just received a
rotated refresh token must stop, not continue with the old one. The file is
opened without following links and without blocking, so a FIFO or device is
refused by its type check instead of hanging. The file holds the same values
the OS store would hold for the selected sign-in: the client selection and that
client's record.

`necropsy auth export` writes the sign-in in effect as credential-file JSON to
standard output, and refuses when standard output is a terminal. It rebuilds
the selection from the effective client, so a client ID override on the
exporting machine is not needed on the server. `necropsy auth import`, run on
the server with the variable set, reads the whole input, refuses anything but
one complete sign-in with a token, and only then replaces the file through the
same atomic write. Empty, truncated or failed input leaves the previous file.
Export is piped straight into import over SSH, so the token never lands in a
shared temporary file, the clipboard or chat. Secrets are never accepted
through arguments or environment variables; the variable holds only a path.

An export copies a refresh token that the provider may rotate on use. The
exporting machine and the server must not refresh the same sign-in at the same
time: the server is its only user while a run is active. If either copy is
invalidated, sign in again and export again.

Threat model: anyone with root on the server, or a process running as the same
user, can read the token. That matches any other secret a container holds. The
file mode limits other local users. Revoke access by signing out, or by
revoking the application on Warcraft Logs, and deleting the file. Rolling back
means unsetting the variable: saved captures stay, and OS-stored credentials
are never migrated or deleted.

Verification: POSIX tests cover the exact modes, another owner, linked files
and directories, a FIFO (bounded subprocess), unreadable content, a failed save
(ENOSPC on fsync), an interrupted rename, a failed directory sync after the
rename, the selector conflict and the unchanged OS-store path. Export and import
tests cover personal, public and client-override round trips, incomplete or
mismatched values, terminal refusal, a missing sign-in, and empty, truncated,
garbage and incomplete import input that keeps the previous file. The POSIX
tests run on Linux; on Windows they are skipped, and a refusal test runs
instead.
