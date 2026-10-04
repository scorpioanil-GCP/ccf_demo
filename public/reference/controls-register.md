# Controls register — the validation gates, the binder, and the consumer-side check

**What this page is.** The one place that says, for every control the SDK
advertises on the served path, **on which path it can actually fail and which
test turns red when it is removed**. A bank's assurance reviewer reads this page
to be pointed at the control that fails rather than at one that cannot
(`D-IMPL-364`, SEC-011 C2; the Gate 2 disposition at `D-IMPL-86`, `D-IMPL-300`
and `D-IMPL-358` D10). Every row cites a test by `path::name`. A docs test
(`tools/docs_tests/test_gate_assurance_surfaces.py`) refuses the page when a
`GATE_*` token defined in `src/ccf/products/gates.py` has no row or a cited test
does not resolve, so this page cannot quietly lag the module.

**How to read "can fail".** A control that compares a value with a copy of itself
cannot fail and is not a control (`D-IMPL-86`). The rows separate three cases: a
control that fails on the **governed path** (a live serve through
`GovernedResolver.__call__`); one that fails only when its runner is **called
directly**, because an upstream refusal makes its condition unreachable on the
governed path; and one that is **self-satisfying by construction** on the
governed path, kept for assembly-path integrity, with the failable control named
beside it.

## The gate tokens (`src/ccf/products/gates.py`)

The two runners' rosters are pinned by set equality at
`tests/products/test_structural_gates.py::test_both_runners_register_exactly_the_recorded_tokens`
(`RUN_GATES_TOKENS`, `RUN_FEDERATED_GATES_TOKENS`); the "registered by" column
below restates those rosters and the census is the measurement.

| token | registered by | what it refuses | path on which it can fail | the test that reddens it |
| --- | --- | --- | --- | --- |
| `empty-operator-guard` | `run_gates`, `run_federated_gates` | a product whose lineage names no operators | **Direct call only.** On the governed path the declared operator set is `required_operator_keys`, and both documents that declare it — `src/ccf/controlplane/artifacts.py::ProductClassDeclaration` and `src/ccf/controlplane/artifacts.py::ProjectionRequirements` — declare it with `min_length=1`, so an empty set is refused at artifact validation before any gate runs. The guard's own refusal is reachable only by calling the runner directly (`D-IMPL-364` SEC-011 C3). | `tests/products/test_empty_operator_halves.py::test_the_declared_half_refuses_a_product_that_declares_no_operators` |
| `lineage-strict-equality` | `run_gates` | a lineage whose operator set differs from the declaration's | **Self-satisfying on the governed path, by construction** (`D-IMPL-86` element 4; `D-IMPL-300`; `D-IMPL-364` SEC-011 B1): the engine runs exactly the operators the declaration names, so the gate verifies assembly-path integrity — the engine transcribed the plan — and cannot witness a misdeclaration. **The failable control is the pre-execution binder** in the next table. | `tests/products/test_gate_two_call_shape.py::test_no_call_site_fills_both_gate_arguments_from_one_source` (the one-source tripwire); the token's registration is pinned by `tests/products/test_structural_gates.py::test_both_runners_register_exactly_the_recorded_tokens` |
| `lineage-attributability` | `run_federated_gates` | a federated product whose signed-bytes address does not attribute its lineage | **Governed path, federated products.** Independently derived from the producer's signed bytes, so it can fail where strict equality cannot. | `tests/gates/test_federated_gates.py::test_attributability_is_checked_before_ttl` |
| `ttl-bounds` | `run_gates`, `run_federated_gates` | `expires_at <= served_at`, or `expires_at > served_at + MAX_TTL` | **Governed path.** The comparand is the fabric instant `served_at` (`D-IMPL-358` D3; `D-IMPL-364` SEC-011 A1), never the caller's; `MAX_TTL` is resolved from the Control Plane at gate time. | `tests/products/test_served_at_severings.py::test_severing_Gate_the_comparand_returns_to_the_decision_instant`; `tests/gates/test_product_gates.py::test_expiry_beyond_max_ttl_is_refused` |
| `ttl-anchor-unresolvable` | neither runner — minted in `src/ccf/products/expiry.py` where the entity-freshness anchor is resolved, before the gates run | an entity-freshness TTL anchor the record cannot resolve | **Governed path**, `from_entity_freshness` classes. | `tests/products/test_d_impl_341_ttl_anchor.py::test_c5_a_served_set_with_no_source_instant_refuses_by_its_own_reason` |
| `source-attestation` | `run_gates` | a pinned source below the class's accepted attestation modes | **Governed path.** | `tests/projection/test_attestation.py::test_run_gates_refuses_a_below_accepted_modes_pin` |
| `dependency-invalidation` | `run_gates` | a product that touched an entity superseded since it was derived | **Governed path.** | `tests/products/test_dependency_invalidation.py::test_a_product_that_touched_the_changed_entity_is_refused` |
| `declared-obligations` | `run_gates`, `run_federated_gates` | a lineage obligation the declaration names and the product dropped | **Governed path.** | `tests/products/test_structural_gates.py::test_a_declared_lineage_obligation_refuses_a_dropped_member` |

## The controls that are not gate tokens

| control | where | what it refuses | path on which it can fail | the test that reddens it |
| --- | --- | --- | --- | --- |
| the pre-execution binder, `refuse_operator_set_divergence` | `src/ccf/deployment/binder.py::refuse_operator_set_divergence`, called by the resolver before the plan executes | a class declaration whose operator set disagrees with the projection's own requirements artifact (`ccf.projection-requirements`); a second operator set from outside the Control Plane | **Governed path, before execution.** This is the control the lineage gate cannot be: it compares two independently authored documents. | `tests/products/test_resolver_seam.py::test_a_plan_contradicting_the_class_is_refused_before_it_is_executed`; `tests/deployment/test_binder.py::test_one_edited_operator_key_in_one_document_is_refused` |
| the consumer-side expiry check | `src/ccf/agents/agent.py::Agent.consume` | a product the consuming agent is handed that is TTL-expired at its `now`, from another tenant, or outside its contract | **The consume boundary.** `ttl-bounds` bounds the producer's hand-over; this is the consumer's own check at the instant it consumes (`D-IMPL-358` D9: both, named). | `tests/agents/test_agent.py::test_consume_refuses_an_expired_product_rather_than_degrading` |

## What this page does not claim

It does not claim Gate 2 can fail on the governed path; it says where that work
is done instead. It does not claim the empty-operator guard is exercised by a
served product; it says why it is not. It lists every `GATE_*` constant the
module defines, including the one no runner registers, so that a token with no
row cannot exist.
