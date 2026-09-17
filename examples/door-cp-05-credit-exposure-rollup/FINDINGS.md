# Findings — door-cp-05

Findings raised while exposing frozen cp-05 through the SDK's standard door (the CP-14
completion GO, exposure option 3, 2026-09-17). Classified under
`docs/EXAMPLE-EVALUATION-CRITERIA.md` §B before any repair. Findings are raised, not
resolved. The close-report sections follow §K.

## 1 · SDK capability proven

| §D item | how this tree exercised it |
|---|---|
| local and remote boundaries | the frozen low road's minted `ServedProduct` and recorded `RefusalEnvelope` cross the SDK's standard door unchanged; the door and the in-process run serve ONE content address |
| refuse correctly | the governed tolerance withholds with the producer's reason retained on the consumer's record; wrong producer id and wrong tenant refuse independently; a question at another instant is refused by name with a record |
| preserve product identity | the consumer admits the child under the registration's producer id and tenant with `provider-controls`; the retained child is cp-05's own contract under cp-05's tenant |
| identity confusion prevented | the door asserts the specimen's tenant as its producer tenant (the consumer's admission holds the contract's tenant to it) |
| the exposure relationships (`D-IMPL-299`) | materiality moves the material roster and floor and nothing in the totals; the limit regime governs deduplication and adjustment; reconciliation reports the served gross — all through the door, from another process |

## 2 · SDK friction observed (§E) — the escape-hatch cost, measured

| measure | value |
|---|---|
| adapter, physical / code lines | 190 / ~80 (`adapter.py`) |
| door launcher | 67 physical / 27 code — identical in shape to every paved producer's |
| documents | 2 (`artifacts/door.yaml`, `ccf_environment.yaml`), 0 values |
| SDK names imported by the adapter | 12 |
| door, resolver, recorder, assertion, replay machinery re-implemented | 0 |
| what the paved road would have removed | the nine attributes and `resolve` (~60 code lines) — the road derives all of them from two documents |

**This producer does NOT prove that the high-level facade supports post-traversal
aggregation.** `CP14-F-33` stands as a paved-road coverage limitation; the hatch is the
structural door over the low road, and the aggregation lives where the specimen put it.

| id | finding | class | disposition |
|---|---|---|---|
| `CP05D-F-01` | **The frozen tree takes no instant, freshness or family from the wire.** `produce_governed` has no `asked_at`, `freshness` or `families` keyword; it answers at the instant `artifacts/question.yaml` pins and stamps the pinned family token. The adapter refuses any other instant BY NAME (a served contract at the pin, presented as the caller's, would pass a consumer's admission only by coincidence — CP-14's instant equals the pin); `freshness` and `families` are disclosed, not refused (the specimen never judged the first; the second is an acquisition-boundary label, not a business input). Replay dimension 2 of a served child records the pinned family token while the door's echo carries the consumer's. A successor tree, not a wrapper, would lift this | 4 · frozen-tree limitation, disclosed | not changed; refused where it would mislead |
| `CP05D-F-02` | **The consumer retains the producer's refusal kind, reason and key, not its prose.** The instant refusal's detail names the pin on the producer's record; the consumer's record says `not-supported-at-tier at 'asked_at'` and no more. Enough to act on; not enough to reproduce without the producer's store (`D-IMPL-342`'s neighborhood: no producer replay reference on a refused row) | 3 · SDK, already OPEN under `D-IMPL-342` | recorded |
| `CP05D-F-03` | **Two Control Planes, two store instances.** The frozen tree boots a registry per question and accepts none, so the door's entitlement policy lives in the adapter's registry and in-resolver refusals keep the specimen's minimal disclosure posture; the door's recorder and each question's resolver are two `FileArtifactStore` objects over ONE directory under the specimen's own replay binding. Records land in one place under one class — the same shape the specimen's pre-340 door ran | 4 · frozen-tree limitation | disclosed |
| `CP05D-F-04` | **`D-IMPL-304` carried, visibly.** A materiality above the regime's ceiling is judged correctly by the frozen tree BEFORE its resolver runs and raises `RequestRefused`; the door reports a runtime failure and the consumer's row reads `producer-unavailable` with no replay reference. Asserted as the carry it is; the assertion moves when the carry closes | 3 · SDK OPEN (`D-IMPL-304`) | not worked around |
| `CP05D-F-06` | **The environment document's loader was reachable only through a wiring-package submodule.** `ServesProducts.environment` is an `EnvironmentDocument`; `load_environment_document` lived in `ccf.deployment.environment` and was not exported from `ccf.deployment`, while the docs gate (`tools/docs_tests/test_advisory_discharge.py::test_a1_no_submodule_import_is_taught_or_demonstrated`) forbids an example from teaching that spelling. The first shipped structural conformer to the door needs the loader. Lightweight remediation (CLAUDE.md §9): the two names are re-exported from `ccf.deployment` — two lines, no behavior — and the adapter imports them there. The one SDK touch in this completion, flagged for the merge ruling | 2 · SDK surface gap, FIXED in this candidate (lightweight remediation) | `src/ccf/deployment/__init__.py` re-exports `EnvironmentDocument`, `load_environment_document` |
| `CP05D-F-05` | **The specimen's own pre-assembly refusals no longer construct.** `ProductRequestViolation` changed shape after the frozen door was written (`parameter=` → `key=`, underscored reasons → hyphenated, four required fields); the frozen `server/serve.py`'s `_wrong_address` and `_no_standing_answer` would raise today. The adapter builds its two refusals in the current shape; the frozen tree is not edited | 4 · frozen-tree drift, disclosed | recorded for the specimen's ledger |

## 3 · Launch blockers

None raised by this tree. `D-IMPL-304` and `D-IMPL-342` are inherited and stay OPEN.

## 4 · Backlog candidates (§I)

**A paved successor for cp-05** would lift `CP05D-F-01`, `F-03` and `F-05` together and
is the only route by which `CP14-F-33`'s limitation could be re-measured; it is out of
this completion's scope by ruling and is not started.

## 5 · Estate / example limitations

cp-05's balances are 324–396 hours old against a four-hour λ_c, so `D_c` reads 1.0
`fail_closed` for every anchor and the governed tolerance always withholds; the served
path is reachable only at the labeled diagnostic tolerance. The CP-14 obligor (BGC Group)
resolves in both stores: family 88, gross committed 24,336,505,256, two material entities
at 5 %, no guarantee path to deduplicate; the specimen's own anchor (Regis) carries the
deduplication case. The consumer's instant equals the specimen's pin by the specification's
choice, not by mechanism.

## 6 · Product result

Through the door, for BGC Group at the pin: served at tolerance 1.0 (`D_c` 1.0,
`fail_closed`), withheld at 0.25; material roster 2 at 5 % and 4 at 2 % over one gross
total; for Regis, `group-limit-test` deduplicates one guarantee path and adjusts committed
exposure below gross, `internal-appetite` counts neither guarantees nor undrawn. A consumer
can rely on: the totals being independent of materiality; the regime being named in the
payload. A consumer cannot rely on: a served exposure at the governed tolerance against
this estate; the wire's `freshness` or `families` reaching the assembly.

## Test record

`tests/examples/test_door_cp_05_exposure.py`: 10 passed against the estate (nine
proofs, two of them parametrized). Not sabotaged by hand: this tree carries no gate
roster of its own; its proofs are CP-14's exposure evidence and are claimed there.
