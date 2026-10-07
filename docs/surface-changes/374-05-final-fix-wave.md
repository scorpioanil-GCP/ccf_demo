# 374-05 — the final fix wave on `deadline-rows`: the whole-branch review's rulings

`D-IMPL-374`, the final fix wave (FW-1 to FW-10) over the whole-branch review
of `deadline-rows` at `e61e04f0`. Each entry names the review finding it closes.
The red tests are named in each entry's `Why`.

**FW-2 (I-1, SEC-013 x SEC-023).** On the joined tree, replay of a
classification decision could not run outside the live writer's process on any
persistent store: the only reader that answers a classification read came from
`ccf.boot.boot`, which always minted a writer and took the cross-process writer
lease. The ruled repair is a read-only boot. It opens the reader and mints the
classification authority from the pinned resolution spec through the same
private mint path as the writer boot, mints no writer and takes no lease. The
SEC-013 premise that "a read-only store over a live graph is legitimate" is
true again with it: the read-only boot is that store, governed. The red tests
are `tests/replay/test_fw2_read_only_replay.py`.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: reshaped
- Before: every boot minted a boot token, so every boot built a writer and took the store's writer lease. Beside a live writer on a persistent store the boot was refused with `SingleWriterViolation`.
- After: a keyword `read_only: bool = False`. `True` resolves and type-checks the pinned resolution spec, builds L2 over it (validating and auditing the policy-bundle pin as before), mints the classification authority through the same private mint path as the writer boot, and returns a handle whose reader is governed exactly like a writer boot's. It mints no boot token, so no writer exists, no writer lease is taken, no graph is marked live, and no invalidation-register capability is minted. `False` is the writer boot, unchanged.
- Why: FW-2, whole-branch review I-1 (`D-IMPL-374`). Whitepaper §7.10 replay must be able to read a classification decision beside the live writer. Red tests: `tests/replay/test_fw2_read_only_replay.py`.
- Migration: none for a writer boot. A process that only reads a graph a live writer holds (a replay tool, an audit export) passes `read_only=True`.

## ccf.boot.ReadOnlyFabricRefused

- Surface: ccf.boot.ReadOnlyFabricRefused
- Public surface: true
- Change type: added
- Before: absent.
- After: a `RuntimeError` the worker of a read-only boot raises for every write (`ingest`, `ingest_admitted`, `admit_entity_claim`, `admit_relationship_claim`), before anything reaches the store. It names the verb and cites FW-2 and `D-IMPL-374`.
- Why: FW-2. A read-only fabric holds no writer; a write through it would be a second writer, which INV-CH7-10 forbids.
- Migration: none.

## ccf.boot.READ_ONLY_LEASE_SCOPE

- Surface: ccf.boot.READ_ONLY_LEASE_SCOPE
- Public surface: true
- Change type: added
- Before: absent.
- After: the constant `"read-only"`, which `FabricHandle.lease_scope` reports for a read-only boot.
- Why: FW-2. The handle reports the read-only state rather than a lease it does not hold.
- Migration: none.

## ccf.boot.READ_ONLY_LEASE_MECHANISM

- Surface: ccf.boot.READ_ONLY_LEASE_MECHANISM
- Public surface: true
- Change type: added
- Before: absent.
- After: the text `FabricHandle.lease_mechanism` reports for a read-only boot: no writer was minted and no writer lease was taken.
- Why: FW-2.
- Migration: none.

## ccf.boot.FabricHandle

- Surface: ccf.boot.FabricHandle
- Public surface: true
- Change type: reshaped
- Before: `lease_scope: WriterLeaseScope | None`.
- After: `lease_scope: WriterLeaseScope | Literal["read-only"] | None`. A read-only handle keeps the whole contract: its `worker` is L2 over a writer that refuses every write by name, and its `close` closes the store only.
- Why: FW-2. The handle has to say it is read-only, and `WriterLeaseScope` names the scopes of leases that are held.
- Migration: a reader of `lease_scope` that matched exhaustively on the two lease scopes adds `"read-only"`.

## ccf.deployment.load_and_boot

- Surface: ccf.deployment.load_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a manifest deployment without a writer.
- After: a keyword `read_only: bool = False`, handed to `ccf.boot.boot` unchanged. The registration loop runs either way, into the caller's registry.
- Why: FW-2. `ccf.replay.environment.RecordedEnvironment` takes a `BootedFabric`, which the deployment doors build. Without the keyword the replay road would boot a writer.
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a manifest deployment without a writer.
- After: a keyword `read_only: bool = False` (the same function `ccf.deployment.load_and_boot` re-exports).
- Why: FW-2.
- Migration: none.

## ccf.deployment.load_config_and_boot

- Surface: ccf.deployment.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a single-file deployment without a writer.
- After: a keyword `read_only: bool = False`, handed through the shared registration spine to `ccf.boot.boot`.
- Why: FW-2. This is the door the paved road's replay reopens a fabric through.
- Migration: none. To replay beside a live writer, pass `read_only=True`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a single-file deployment without a writer.
- After: a keyword `read_only: bool = False` (the same function `ccf.deployment.load_config_and_boot` re-exports).
- Why: FW-2.
- Migration: none.

## ccf.replay.environment.RecordedEnvironment

- Surface: ccf.replay.environment.RecordedEnvironment
- Public surface: true
- Change type: behavior
- Before: its `fabric` was documented only as "the booted fabric to read through". Every boot took the writer lease, so beside a live writer there was no fabric to pass.
- After: its documented fabric is a read-only boot (`load_config_and_boot(..., read_only=True)`), which reads beside the live writer with a boot-minted authority on every view. A writer boot is still accepted where no live writer holds the graph. The class's code and signature are unchanged.
- Why: FW-2, whole-branch review I-1.
- Migration: a replay tool that reopens a fabric beside a live writer passes `read_only=True` to the deployment door it boots through.
