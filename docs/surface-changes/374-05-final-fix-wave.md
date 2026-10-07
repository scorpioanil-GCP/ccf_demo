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

**FW-4 (I-3, M-1, M-4, M-7, M-8, T1-c and the T4 residuals; documentation
only, no surface changes shape).** §4.10 of the security deployment page now
states what an erasure is not: there is no graph erasure — the Context Graph
keeps the subject's attributes and every product assembled afterwards carries
them — it is whole-artifact only, it destroys nothing and it makes no
legal-compliance claim. It corrects four overclaims (a record without a
verifying door signature is `index-unsupported` — true since FW-1, a
malformed header included; neither HITL-policy registration authority nor an
approver's key suffices without the door key; `policy_head` covers content
only where a version is its content hash, as in the reference registry; and
the door refuses by name where the consult withholds and audits), and adds
the residuals: a forged entry in one tenant withholding another tenant's
content on tenantless reads (the by-URI naming check, fixed by FW-7); the
single-tenant door; the door signature living in the index entry; door-key
rotation stranding an in-flight completion; the undeclared
`hitl_policy_key` on `HITLTransportProtocol`; the index's `flock` and
`O_APPEND` assumptions with the short-write behavior PC1 added; and another
tenant's governed filing of identical bytes changing the owner's reads over
the MCP artifact server (panel C8, carried). §4.6 and fragment 374-01 say to
declare one spelling of each server address across every writer of a graph,
for Fluree, MongoDB (multi-host and replica-set forms included) and Neo4j. The
stale §4.9 pointers that meant erasure now say §4.10, and the pin in
`tests/erasure/test_sec009_fix5_rulings.py` reads exactly §4.10 and the
in-process adapter's bullet. The adapter-authoring guide carries SEC-023's
obligation for a reader that does not subclass `BaseGraphReader`; the cp-05
specimen note states its SEC-009 change exactly; and the `ApiDependencies`
module docstring counts five required handles and six optional ones.

## ccf.boot.boot

- Surface: ccf.boot.boot
- Public surface: true
- Change type: reshaped
- Before: every boot minted a boot token, so every boot built a writer and took the store's writer lease. Beside a live writer on a persistent store the boot was refused with `SingleWriterViolation`.
- After: a keyword `read_only: bool = False`. `True` resolves and type-checks the pinned resolution spec, builds L2 over it (validating and auditing the policy-bundle pin as before), mints the classification authority through the same private mint path as the writer boot, and returns a handle whose reader is governed exactly like a writer boot's. It mints no boot token, so no writer exists, no writer lease is taken, no graph is marked live, and no invalidation-register capability is minted. Because it takes no lease, it sets the connection's writer-lease setting (`writer_lease_lock_dir`) aside before validation: that setting is neither validated nor handed to the store (N-2, the scoped re-review), so an examiner on another host or under another account boots read-only with the deployment's settings unchanged. `False` is the writer boot. Separately (PM10, panel C10), every step after a writer boot's mint — the worker build, the SEC-023 authority wrap and the handle's construction — now runs inside one guard that retires the writer and gives back its writer lease on failure; before, only the worker build did, and a raise in the other two stranded the writer in this process and its cross-process lease for the process's life.
- Why: FW-2, whole-branch review I-1 (`D-IMPL-374`). Whitepaper §7.10 replay must be able to read a classification decision beside the live writer. PM10: a corrected retry must boot. N-2: a read-only boot was refused for a lock directory only a writer uses. Red tests: `tests/replay/test_fw2_read_only_replay.py`, `tests/graph/test_pm10_boot_strand.py`, `tests/deployment/test_n2_read_only_boot_lease_settings.py`.
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
- After: a keyword `read_only: bool = False`, handed to `ccf.boot.boot` unchanged. The registration loop runs either way, into the caller's registry. With `True`, the connection preflight sets the writer-lease setting aside as the boot does, so it is neither validated nor used (N-2).
- Why: FW-2. `ccf.replay.environment.RecordedEnvironment` takes a `BootedFabric`, which the deployment doors build. Without the keyword the replay road would boot a writer.
- Migration: none.

## ccf.deployment.manifest.load_and_boot

- Surface: ccf.deployment.manifest.load_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a manifest deployment without a writer.
- After: a keyword `read_only: bool = False` (the same function `ccf.deployment.load_and_boot` re-exports). With `True`, the writer-lease setting is neither validated nor used (N-2).
- Why: FW-2.
- Migration: none.

## ccf.deployment.load_config_and_boot

- Surface: ccf.deployment.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a single-file deployment without a writer.
- After: a keyword `read_only: bool = False`, handed through the shared registration spine to `ccf.boot.boot`. With `True`, the connection preflight sets the writer-lease setting aside as the boot does, so it is neither validated nor used (N-2).
- Why: FW-2. This is the door the paved road's replay reopens a fabric through.
- Migration: none. To replay beside a live writer, pass `read_only=True`.

## ccf.deployment.config.load_config_and_boot

- Surface: ccf.deployment.config.load_config_and_boot
- Public surface: true
- Change type: reshaped
- Before: no way to boot a single-file deployment without a writer.
- After: a keyword `read_only: bool = False` (the same function `ccf.deployment.load_config_and_boot` re-exports). With `True`, the writer-lease setting is neither validated nor used (N-2).
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

**FW-3 (I-2, SEC-009 x SEC-024).** An erasure crossed the SDK's MCP doors as
raw exception prose naming the erased address, at every disclosure level. The
egress tool's opaque clause did not cover the class, and the Experience seams
passed it through. The ruled repair renders an erasure by disclosure level
exactly as the HTTP doors and the MCP artifact server already did. The red
tests are `tests/mcp/test_fw3_erasure_at_mcp_doors.py`, including probes X1
and X2.

## ccf_runtime.authz.delivery_boundary.govern_erasure

- Surface: ccf_runtime.authz.delivery_boundary.govern_erasure
- Public surface: true
- Change type: added
- Before: absent. An `ErasedContentRefused` raised under an MCP product door or an Experience seam reached the transport, which rendered its text.
- After: the governed determination for an erasure a door met while answering. It envelopes an `ErasedContentRefusal` under the surface's own request and resource identity, records it through the door's recorder at every level, and returns it disclosed: at `minimal` the not-found shell (`TRANSLATED_AT_MINIMAL`, the shell `govern_absence` answers), at `reasoned` with the reason and instant, at `full` with the record address too. Dimension 2 states `ResolutionNotApplicable("no-resolution-step")`. The erased address is in no envelope.
- Why: FW-3, whole-branch review I-2 (`D-IMPL-374`); U11. Red tests: `tests/mcp/test_fw3_erasure_at_mcp_doors.py`.
- Migration: none. A deployment-built door that catches `ErasedContentRefused` calls it the way the SDK's doors do.

## ccf.erasure.errors.ErasedContentRefused

- Surface: ccf.erasure.errors.ErasedContentRefused
- Public surface: true
- Change type: behavior
- Before: the text was `'<content address>' was erased and is not served (SEC-009)`.
- After: the text names no address: `the requested content was erased by a recorded decision and is not served (SEC-009)`. `content_address`, `erasure_record_address`, `reason` and `erased_at` are unchanged structured attributes.
- Why: FW-3. The text is what a transport that renders exception prose puts on a wire, and the review measured exactly that.
- Migration: an in-process caller that parsed the address out of the text reads `content_address`.

## ccf.erasure.ErasedContentRefused

- Surface: ccf.erasure.ErasedContentRefused
- Public surface: true
- Change type: behavior
- Before: the text named the erased address.
- After: the text names no address (the same class `ccf.erasure.errors.ErasedContentRefused`, re-exported).
- Why: FW-3.
- Migration: read `content_address`.

## ccf_runtime.mcp.egress.build_egress_server

- Surface: ccf_runtime.mcp.egress.build_egress_server
- Public surface: true
- Change type: behavior
- Before: an `ErasedContentRefused` from the resolver left the product tool, the addressed resource and the standing resource as the exception's prose, at every level.
- After: it is `govern_erasure`'s recorded determination, delivered through each surface's one emission site: the not-found shell at `minimal`, the `erased-content` shell above it. The egress resources still have no opaque wrapper for other exceptions (pre-existing); this adds the erasure case only.
- Why: FW-3, probe X2.
- Migration: none.

## ccf_runtime.mcp.experience.build_experience_server

- Surface: ccf_runtime.mcp.experience.build_experience_server
- Public surface: true
- Change type: behavior
- Before: an `ErasedContentRefused` raised by the product resolver or by the `get_context`, `get_lineage` or `get_replay_record` seam crossed as the tool's or resource's error text, naming the erased address, at every level. A deployment directory's own exception on `invoke_agent`, raised before authorization while reading a rostered caller's reach, crossed as its text.
- After: the product resource answers the recorded `erased-content` determination (its not-found shell at `minimal`). The three tools have no not-found rendering, so at `minimal` they answer the opaque `ccf-runtime-failure:<id>` and record nothing; above it, the recorded `erased-content` shell. A directory failure on `invoke_agent` is the existing opaque pre-authorization roster refusal; only its type reaches the log.
- Why: FW-3, probe X1; the SEC-017 carry "a deployment directory exception propagates unchanged".
- Migration: none.

## ccf_runtime.mcp.artifact_server.build_artifact_server

- Surface: ccf_runtime.mcp.artifact_server.build_artifact_server
- Public surface: true
- Change type: behavior
- Before: the name-resolution resource resolved a versioned URI through the raw store, so an address the caller's tenant erased answered `found: true` with the address. The blob, presence and names resources beside it already read through the consulting store.
- After: the resolution reads the caller's own tenant view of the consulting store. An erased address answers the resolution's own not-found rendering (`found: false`, no address), so `ccf.artifacts.mcp_store.McpArtifactStore.resolve_uri` refuses it as the in-process consulting store does.
- Why: FW-6, whole-branch review M-2 (`D-IMPL-374`); the CLAUDE.md §7.4 parity claim. Red test: `tests/mcp/test_fw6_artifact_resolution_consults.py`.
- Migration: none.

## ccf_runtime.authz.delivery_boundary.govern_dereference

- Surface: ccf_runtime.authz.delivery_boundary.govern_dereference
- Public surface: true
- Change type: behavior
- Before: on the by-URI path the naming check after the holds called the TENANTLESS store's `resolve_uri`, and an `ErasedContentRefused` there was recorded as `cause="nonexistent"`. Another tenant's entry naming the caller's record address (genuine, or forged and unsupported) therefore made an entitled examiner read "absent" by URI while the by-address read served.
- After: the naming check reads the same view the consult read, the caller's verified tenant's. Another tenant's entry changes nothing for the caller, and an erasure the check meets in the caller's own tenant is the erased reading at the caller's level (the not-found shell at `minimal`, `erased-content` above it), not an absence. Separately (PM5, panel C5), a `store` that is not an `ErasureConsultingStore` is refused with `UnconsultedDeliveryBoundaryError`, right after the capability check and before anything is read, recorded or clocked; before, the consult was skipped and an uncomposed store served erased bytes. Every shipped caller (the HTTP artifact and replay routes, the MCP artifact server) passes a composed store.
- Why: FW-7, whole-branch review M-3 (`D-IMPL-374`); probe X4. PM5: U12, composed always. Red tests: `tests/http_api/test_fw7_by_uri_naming_check.py`, `tests/authz/test_pm5_dereference_requires_consult.py`.
- Migration: none.

**The cross-AI panel's verified findings (PC1-PC3, PM4-PM10), folded into this wave.**

## ccf.erasure.errors.ErasureIndexWriteFailed

- Surface: ccf.erasure.errors.ErasureIndexWriteFailed
- Public surface: true
- Change type: added
- Before: absent. `FileErasureIndex.append` ignored `os.write`'s count, so a write that stopped short without raising (ENOSPC part-way, `RLIMIT_FSIZE`, a network filesystem) returned normally over a torn line. The door then completed and returned a record while the address was still served, and the next append corrupted the index.
- After: an `OSError` the append raises when its line cannot be written whole. The append writes until every byte is written; when it cannot, it truncates the file back to its pre-append length, fsyncs, and raises this. The entry is not in the index. `ErasureDoor.complete` propagates it by name before the workflow resumes and files no record; a retry completes the erasure.
- Why: PC1, panel C1 (`D-IMPL-374`). Red tests: `tests/erasure/test_pc1_index_short_write.py`.
- Migration: none. A caller of the door treats it as an I/O failure and retries.

## ccf.erasure.ErasureIndexWriteFailed

- Surface: ccf.erasure.ErasureIndexWriteFailed
- Public surface: true
- Change type: added
- Before: absent.
- After: re-export of `ccf.erasure.errors.ErasureIndexWriteFailed`.
- Why: PC1.
- Migration: none.

## ccf.erasure.FileErasureIndex

- Surface: ccf.erasure.FileErasureIndex
- Public surface: true
- Change type: behavior
- Before: `append` issued one `os.write` and ignored its count.
- After: `append` writes its whole line or nothing, raising `ErasureIndexWriteFailed` with the file left as it was. A new read-only property `head` returns the chain head (the SHA-256 of the last line read, `GENESIS` when empty), which the decorating store's composition memo is now keyed by (PM4, panel C4): a tail entry rewritten in place keeps the count and a valid chain, and a warm memo served its forged reason where a cold process read `index-unsupported`. An index that exposes no `head` is keyed by the digest of its entries.
- Why: PC1; PM4. Red tests: `tests/erasure/test_pc1_index_short_write.py`, `tests/erasure/test_pm4_memo_chain_head.py`.
- Migration: none.

## ccf.erasure.approval.verify_erasure_approval

- Surface: ccf.erasure.approval.verify_erasure_approval
- Public surface: true
- Change type: behavior
- Before: an `AmbiguousPinnedVersionError` resolving the erasure gate's approval policy (two contents declaring its pinned version) was refused with `reason_code="approver-not-eligible"`.
- After: it is refused with its own `reason_code="approval-policy-ambiguous"`. Both still fail closed; only the cause the audit and the door name changes.
- Why: PM6, panel C6 (`D-IMPL-374`). The ambiguity is the Control Plane's, not the approver's. Red test: `tests/erasure/test_pm6_ambiguous_policy_reason.py`.
- Migration: a deployment that alerts on `approver-not-eligible` adds `approval-policy-ambiguous`.

## ccf.erasure.verify_erasure_approval

- Surface: ccf.erasure.verify_erasure_approval
- Public surface: true
- Change type: behavior
- Before: the ambiguity was coded `approver-not-eligible`.
- After: `approval-policy-ambiguous` (the same function, re-exported).
- Why: PM6.
- Migration: as above.

## ccf_runtime.authz.delivery_boundary.UnconsultedDeliveryBoundaryError

- Surface: ccf_runtime.authz.delivery_boundary.UnconsultedDeliveryBoundaryError
- Public surface: true
- Change type: added
- Before: absent; `govern_dereference` skipped the erasure consult for a store that was not an `ErasureConsultingStore`.
- After: a `TypeError` `govern_dereference` raises for such a store, after the capability check and before anything is read, recorded or clocked. The message names `ccf.erasure.compose_erasure_consult`.
- Why: PM5, panel C5 (`D-IMPL-374`); U12.
- Migration: an out-of-tree door composes its store with `compose_erasure_consult` before calling `govern_dereference`.

## ccf.replay.engine.RefusalReplayOutcome

- Surface: ccf.replay.engine.RefusalReplayOutcome
- Public surface: true
- Change type: behavior
- Before: `child_contract_addresses`, documented as every admitted child "resolved from the store and re-hashed to itself", also listed an admitted child whose retained contract was erased. The no-fabric-read path skips that child unread and discloses it on `erased_content`.
- After: an erased child's address is not in `child_contract_addresses`; it is reported, positively, on `erased_content`. The docstrings say so.
- Why: PM7, panel C7 (`D-IMPL-374`). The evidence type's own field overstated what was verified. Red test: `tests/replay/test_pm7_refusal_children_exclude_erased.py`.
- Migration: a caller that compared `child_contract_addresses` with the record's admitted rows also reads `erased_content`.

## ccf_runtime.mcp.tenancy.TenantGuardedServer

- Surface: ccf_runtime.mcp.tenancy.TenantGuardedServer
- Public surface: true
- Change type: behavior
- Before: for a caller whose grant declares a product roster, on a surface whose product reach is resolved from a directory (`invoke_agent`), every directory outcome refused with one opaque reason before the authorizer, but an agent that existed and was on the roster reached the authorizer, whose deny read `tenant-unauthorized`. A rostered principal without invoke permission learned which agents exist.
- After: for that caller on that surface, the authorizer's deny is the same opaque pre-authorization refusal, byte-identical to every other outcome; the specific reason is logged server-side only. The unrostered path, and every surface whose reach is an argument or a declaration, is unchanged.
- Why: PC2, panel C2 (`D-IMPL-374`); the residual of SEC-017's I-NEW-1 class. Red test: `tests/mcp/test_pc2_invoke_oracle.py`, which compares all six rostered outcomes pairwise.
- Migration: none.

## ccf_runtime.mcp.tenancy.ProductReach

- Surface: ccf_runtime.mcp.tenancy.ProductReach
- Public surface: true
- Change type: behavior
- Before: `ProductReach(declared=frozenset())` constructed, although the class promises no empty statement, and the roster hold then passed every call, an empty roster's included.
- After: an empty `declared` is refused at construction with `ValueError`, like an empty `argument`, `undeclared` or `unknown`.
- Why: PM9, panel C9 (`D-IMPL-374`). An adopter registration that derives its classes from configuration and gets an empty set would otherwise be silently roster-unbound. Red test: `tests/mcp/test_pm9_empty_declared_reach.py`.
- Migration: a registration whose declared classes can be empty declares an `undeclared` or `unknown` reach instead.

## ccf.graph.leases.require_private_lock_directory

- Surface: ccf.graph.leases.require_private_lock_directory
- Public surface: true
- Change type: added
- Before: absent. A declared lock directory was checked only for being absolute, and it was resolved at each acquisition.
- After: `require_private_lock_directory(value) -> str`, the config-validation half of the lock-directory rule. It refuses, by name, a path that differs from its real path (any symbolic-link component; the message names the real path to declare), one that does not exist or is not a directory, one not owned by the effective user, and one that is group- or world-writable.
- Why: PC3, panel C3 (`D-IMPL-374`; SEC-013). A link retargeted between two writers' acquisitions gave one network graph two lock files, and both writers minted (two processes measured). Red tests: `tests/graph/test_pc3_lock_dir_symlink.py`.
- Migration: declare the lock directory's real path, owned by the user every writer runs as, mode `0700` or `0755`.

## ccf.graph.leases.AbsoluteLockDirectory

- Surface: ccf.graph.leases.AbsoluteLockDirectory
- Public surface: true
- Change type: reshaped
- Before: `Annotated[str, AfterValidator(require_absolute_lock_directory)]`.
- After: `Annotated[str, AfterValidator(require_absolute_lock_directory), AfterValidator(require_private_lock_directory)]`.
- Why: PC3.
- Migration: as above.

## ccf.graph.leases.lock_directory_writer_lease

- Surface: ccf.graph.leases.lock_directory_writer_lease
- Public surface: true
- Change type: behavior
- Before: the declared directory was resolved at each acquisition, through any symbolic link.
- After: a directory reached through a symbolic link is refused at construction (`ValueError` naming the real path), and every acquisition re-checks that the directory is still its own real path. Ownership and mode are judged at config validation; a deployment constructing the lease directly keeps them itself.
- Why: PC3.
- Migration: construct it over the directory's real path.

## ccf.graph.backends.fluree_write.FlureeConnection

- Surface: ccf.graph.backends.fluree_write.FlureeConnection
- Public surface: true
- Change type: reshaped
- Before: `writer_lease_lock_dir` was validated as an absolute path.
- After: it is also validated by `require_private_lock_directory` (PC3).
- Why: PC3.
- Migration: as for `require_private_lock_directory`.

## ccf.graph.backends.mongo_write.MongoConnection

- Surface: ccf.graph.backends.mongo_write.MongoConnection
- Public surface: true
- Change type: reshaped
- Before: `writer_lease_lock_dir` was validated as an absolute path.
- After: it is also validated by `require_private_lock_directory` (PC3).
- Why: PC3.
- Migration: as for `require_private_lock_directory`.

## ccf.graph.backends.neo4j_write.Neo4jConnection

- Surface: ccf.graph.backends.neo4j_write.Neo4jConnection
- Public surface: true
- Change type: reshaped
- Before: `writer_lease_lock_dir` was validated as an absolute path.
- After: it is also validated by `require_private_lock_directory` (PC3).
- Why: PC3.
- Migration: as for `require_private_lock_directory`.

## ccf --local

- Surface: runtime/ccf_runtime/cli/main.py
- Public surface: false
- Change type: behavior
- Before: `ccf --local --local-root DIR` refused with `--local requires --local-hitl-policy-key KEY`, and with the key it built the local bundle (store directories, the erasure index file) before reporting that the mode is suspended.
- After: after the `--local-root` check, a CLI invocation with no embedder authority reports `--local` suspended first, demanding no further flag and building nothing.
- Why: FW-9, whole-branch review M-9 (`D-IMPL-374`). A suspended mode should not ask for a flag only a working mode would need. The suspension test is restored to pass no key.
- Migration: none.

## ccf.controlplane.audit.REGISTRATION_ACTIONS

- Surface: ccf.controlplane.audit.REGISTRATION_ACTIONS
- Public surface: true
- Change type: added
- Before: absent; the registration actions were named only inside the erasure approval module.
- After: the frozenset `{"register", "register_typed", "register_versioned"}`: the actions whose resolved events make up the registration history. `AuditLog` now folds each such event, as it is appended, into a digest it serves as the read-only property `AuditLog.registration_head` in O(1) under its lock.
- Why: FW-10, whole-branch review M-5 (`D-IMPL-374`). `ccf.erasure.approval.policy_head` copied and scanned the whole audit log on every erased read and composition, linear in uptime on a door that audits each request. Red tests: `tests/erasure/test_fw10_policy_head_cost.py`, measured by events read, not time.
- Migration: none.

## ccf.erasure.approval.policy_head

- Surface: ccf.erasure.approval.policy_head
- Public surface: true
- Change type: behavior
- Before: every call copied the Control Plane's whole audit log and folded its registrations.
- After: a Control Plane whose audit log serves `registration_head` (the reference registry's) is read in O(1), with the same bytes folded, so the value is unchanged. Any other Control Plane falls back to the fold over its audit events. The docstring states the head's condition: it digests registration metadata, which suffices where a version IS its content (the reference registry), and a third-party Control Plane must uphold that.
- Why: FW-10.
- Migration: none.
