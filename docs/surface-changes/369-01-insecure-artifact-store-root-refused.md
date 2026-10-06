# 369-01 — the file-backed artifact store is owner-only, and refuses an insecure root by name

SEC-014 under `D-IMPL-368` (ruling Q8: fixed modes, no knob), amended by
`D-IMPL-369` (Dave, 2026-10-05: *"SDK-created roots are owner-only. An insecure
pre-existing root is refused by name, without chmod. Verify that refusal leaves its
permissions unchanged."*). Measured before this entry: under umask `0o000` the store
created its root and parents `0o777` and its files `0o666`; the modes were whatever
the host umask left.

## ccf.artifacts.file_store.InsecureArtifactStoreRoot

- Surface: ccf.artifacts.file_store.InsecureArtifactStoreRoot
- Public surface: true
- Change type: added
- Before: absent — a pre-existing root was used whatever its mode and owner.
- After: a `PermissionError` subclass raised by `FileArtifactStore(...)` when its root already existed and either carries any mode bit outside `0o700` or is not owned by the process's effective uid. The message names the path, the observed mode and the observed owner. The root is never chmodded: its permissions are unchanged by the refusal.
- Why: `D-IMPL-369` — the store does not change permissions on a directory it did not create; the operator who made the root decides whether to tighten it or point the store elsewhere.
- Migration: a deployment that pre-creates its artifact-store root with the default umask (`0o755`/`0o775`) must create it `0o700`, or let the store create it.

## ccf.artifacts.file_store.FileArtifactStore

- Surface: ccf.artifacts.file_store.FileArtifactStore
- Public surface: true
- Change type: behavior
- Before: the root and any missing parents were created with `mkdir(parents=True, exist_ok=True)` and files written with `write_bytes`/`write_text`; every mode was the host umask's.
- After: every directory the store creates (the root and any missing parents) is `0o700` and every file it writes (artifact, naming index, and their `.partial` staging files) is `0o600`, set explicitly after creation regardless of the process umask; no store-local `umask` is used. A pre-existing root is refused with `InsecureArtifactStoreRoot` unless it is `0o700` or narrower and owned by the process.
- Why: SEC-014 — replay records and Control Plane artifacts are decision evidence (CLAUDE.md §7.4); the host's default umask is not a confidentiality posture for them. Fixed, not configurable (ruling Q8).
- Migration: see `InsecureArtifactStoreRoot` above. Files an earlier store version wrote are not re-moded.
