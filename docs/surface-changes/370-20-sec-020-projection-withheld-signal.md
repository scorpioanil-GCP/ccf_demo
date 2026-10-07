# 370-20 — SEC-020: a projection can withhold a subject, and a withheld subject reads as a nonexistent one

`D-IMPL-370` (and `D-IMPL-368`/`D-IMPL-369`), row SEC-020, ruling Q12 (a) of
`docs/superpowers/specs/2026-10-05-remaining-rows-rulings-batch.md`
(constant-fill). Measured before this entry: a Policy-OPERATOR withhold was
already indistinguishable from a nonexistent subject, because the debt, the
empty finding and the TTL anchor are computed from the operator view. A
PROJECTION-level withhold was not. When Π returned a missing subject's payload
for an admitted subject, the served vessel differed from a nonexistent
subject's at `computed_empty`, `debt.debt`, `debt.factors.freshness` and
`debt.scorers`. A `from_entity_freshness` class also SERVED the withheld subject
on its observation instant, where the nonexistent subject was refused
`ttl-anchor-refusal`. `ProjectionOutput` had no way to say "withheld", so the
resolver could not tell a withhold from a legitimately empty answer. The exploit
test is `tests/products/test_withheld_is_indistinguishable_from_absent.py`.

**Constant-fill, as finally ruled (`D-IMPL-371`):** when the signal is
raised, the product's debt, empty finding and TTL anchor are those of the same
plan RE-EXECUTED WITHOUT THE REQUEST SEED. That is the walk an identifier that
names nothing gets by construction: walk starts are the union of the plan's
seed classes and the request seed (`GQ-11`, unchanged), and a nonexistent
identifier's seed matches nothing. The withheld subject's own records stay in
that view if and only if a class seed reaches them, exactly as for the
nonexistent identifier. No record is masked.

The two earlier versions are kept here as measured history:
- Round 1 rendered an EMPTY view. On a class-seeded fabric that created a
  serve-versus-refuse existence oracle.
- Round 2 MASKED the subject's records. That left a residual whenever the
  subject's evidence was fresher or staler than its siblings', because the
  nonexistent identifier's walk reads those records.

The signal is the only key into the branch. An empty payload without it keeps
the debt and finding its real view earned.

**Scope, as amended by `377-01` (`D-IMPL-376` (3), route A).** As first
integrated, equality held with a nonexistent subject asked on the SAME fabric.
On the paved road, acquisition populates each question's fabric with the asked
subject's claims before the plan runs, so the unseeded walk still read them,
while a nonexistent subject's own question walks a fabric acquisition added
nothing to. `377-01` renders the withheld subject over the fabric as it stood
before its question's acquisition; its own scope note says for which
acquisition shape that is exact.

## ccf.projection.plan.ProjectionOutput

- Surface: ccf.projection.plan.ProjectionOutput
- Public surface: true
- Change type: reshaped
- Before: `plan_id: str`, `payload: Mapping[str, Any]`. A projection that withheld a subject could only do so silently.
- After: adds `withheld: bool = False`, which is hash-transparent at `False`, so every output written before the field existed is byte-identical. A projection sets `withheld=True` and returns, as `payload`, exactly what it returns for a subject it cannot see. The governed resolver then computes the product's debt, empty finding, TTL anchor, the staleness gate's touched set and a declared product gate's evidence from the same plan re-executed without the request seed (`ProjectionEngine.execute_without_request_seed`), over the fabric as it stood before this request's acquisition (`377-01`). The replay record keeps the execution that ran.
- Why: SEC-020 and Q12 (a). The withheld subject's claims must not move any member a consumer reads. A withhold is never inferred from an empty payload (`D-IMPL-242` amendment 1).
- Migration: none for a projection that does not withhold. A projection that withholds today by returning an empty payload should set `withheld=True` to get the constant-fill rendering.

## ccf.projection.engine.ProjectionEngine

- Surface: ccf.projection.engine.ProjectionEngine
- Public surface: true
- Change type: reshaped
- Before: no way to re-execute a plan as a question naming nothing would execute it.
- After: adds the method `execute_without_request_seed(*, executed, plan, perspective, tenant_id, temporal_boundary)`. It re-executes the operator plan on a fresh engine with this engine's registry and survivor cap and with `seeds=None`. That is the only difference from the real execution. Every query is answered at `executed.store_snapshot_pin` where the store can pin. Acquired content is re-fed from `executed`, never re-acquired. The result carries the real execution's attestation and pin.
- Why: SEC-020, `D-IMPL-371`. This is the one definition of "what a subject that names nothing reads" that the resolver's constant-fill branch reads.
- Migration: none. The method is additive.

## ccf.replay.record.ContentGenerationPath

- Surface: ccf.replay.record.ContentGenerationPath
- Public surface: true
- Change type: reshaped
- Before: dimension 5 did not carry the served product's empty finding. `RecordedEnvironment.rehydrate_product` therefore rebuilt every product served WITH a finding without one, and replay failed with `ReplayDivergence` on its content address. That covered a computed-empty answer, a nonexistent subject on an empty per-request fabric, and every withheld subject.
- After: adds `computed_empty: ComputedEmptyFinding | None = None`, hash-transparent at `None`, so every record written before it existed keeps its bytes and address. `build_replay_record` copies the product's finding, as it copies `ttl_anchor_at`. `src/ccf/replay/environment.py::RecordedEnvironment.rehydrate_product` copies it back.
- Why: SEC-020, corrective round. A withheld decision must replay to its own address. The same change closes the pre-existing divergence for every empty-finding product.
- Migration: none for records. A hand-written `ReplayEnvironment` that rebuilds products should copy `path.computed_empty`.
