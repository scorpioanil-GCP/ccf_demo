# 358-08 — the tenant-bound temporal write guard at governed ingress

`D-IMPL-358` Wave 2 step 8. An envelope whose ingestion instant falls outside the
tenant's declared `TemporalBoundaryPolicy` window is refused **before** L2's single
writer sees it.

**The guard is NOT in `AssemblyWorker`**, by ruling. The worker acquires no clock and
invents no tenant; it gains no field and no parameter. The guard is a shared admission
function beside `refuse_foreign_envelope` — the boundary check the paved road already
runs on every envelope — holding composition state: the boot-frozen tenant roster and
the temporal policy **pinned per roster tenant**. Nothing on the judging path consults
the registry, so there is no `resolve_latest` per envelope.

**`envelope.tenant_id` is a CLAIM, not a selector.** A tenant absent from the roster is
refused in the `refuse_foreign_envelope` family; a tenant present on it selects the
policy pinned FOR IT at composition. No envelope can introduce a tenant, cause a
resolution, or reach an unpinned policy.

**Out of scope by ruling:** `SignalEnvelope.observed_time` / claim `valid_from`. That is
valid time — how far back a fact may have been true — not the window in which the fabric
may accept a write, and bounding it would refuse legitimate back-dated valid-time.

## ccf.signal.envelope.IngressTemporalBound

- Surface: ccf.signal.envelope.IngressTemporalBound
- Public surface: true
- Change type: added
- Before: absent. `SignalEnvelope.ingestion_timestamp` carried NO validation of any kind — measured: a naive `1900-01-01` instant constructs cleanly, and a ten-year-out-of-window envelope wrote two entities and one relationship straight into the graph
- After: a frozen dataclass minted once at the composition root by `at_composition(registry=…, tenant_ids=…)`, holding each roster tenant's resolved `PinnedTemporalBoundary | TemporalBoundaryUndeclared`. `refuse_outside_window(envelope, *, now)` judges only `ingestion_timestamp`, reusing `refuse_temporal_bound`'s arithmetic through a deferred import rather than restating it — `ccf.products.product` imports this module, so a module-level import would close a cycle. An UNDECLARED policy is pinned as its own absence rather than raising at boot: composition succeeds and the refusal happens at the write, where it can name the envelope it refused
- Why: `D-IMPL-358` step 8 with ruling 11. The write path was the one governed boundary where an out-of-window instant could still land, and `D-IMPL-159` forbids the writer reading a clock — so the instant is handed in by the ingress caller, read once per acquisition
- Migration: none for an existing deployment; the paved road composes it automatically at `OpenedProduct._acquisition_seam`. A deployment ingesting on its own path composes one at its own composition root

## ccf.signal.envelope.TemporalWriteRefused

- Surface: ccf.signal.envelope.TemporalWriteRefused
- Public surface: true
- Change type: added
- Before: absent
- After: a `ValueError` carrying `envelope_id`, `tenant_id`, `instant`, `policy_key`, `reason` and `detail` as ATTRIBUTES, not only prose — ruling 11 admits no default and no fabricated binding, so an operator must be able to act on the refusal, which means knowing which key was consulted and why it refused. The instant is carried VERBATIM: not rounded, clamped or restamped
- Why: `D-IMPL-358` step 8. A `ValueError` matches this module's existing refusal idiom (`refuse_foreign_envelope`) and the worker's own (`IdentityRefused`) rather than inventing a new failure family
- Migration: none — a new type on a path that previously admitted everything. A caller that wants to distinguish it from `refuse_foreign_envelope`'s refusal catches the type; one that does not still catches `ValueError`
