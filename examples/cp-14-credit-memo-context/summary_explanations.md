# cp-14 — what each run shows, what you would have missed, and how it works

Three readers are served here: a **technical product manager** deciding whether a
composite context product is worth having, an **engineer** who has to build or
extend one, and a **credit SME** who knows what a memo built from five sources costs
to get wrong. Each run is given as *the output*, *what you would have missed*, and
*how the mechanism produces it*. Both runs were captured against the same snapshot:
the five producers' doors live, BGC Group at `2026-09-07T12:00:00+00:00`, the
committed transcript in `page/run-transcript.txt`.

**Scope, first.** This delivery proves five-provider acquisition, admitted-content
composition, governed refusal, and reconstruction. It does not complete the full
memo-assembly specification: the memo's own template sections, evidence references,
peer benchmarks and policy-derived tolerance are planned obligations of `CP-SPEC-014`,
not passed ones (`FINDINGS.md`, `CP14-F-37`).

---

## Run 1 — the governed question

```
make -s example-cp-14
```

BGC Group, the memo's own tolerance (0.25 — the v2 policy's default at that instant),
facility `FAC-5B8418`, five doors live.

### The output

```
outcome     : REFUSED kind=composite-child-refusal reason=child_admission
child rows  : 5
  - credit-risk.spread                       ineligible   producer=cp-03-canonical-obligor-financial-spread-egress
  - reference.corporate-family               admitted     producer=cp-04-canonical-corporate-family-tree-egress
  - credit-risk.exposure-rollup              ineligible   producer=cp-05-credit-exposure-rollup-egress
  - credit-risk.collateral-coverage          admitted     producer=cp-06-canonical-collateral-and-setoff-coverage-egress
  - credit-risk.covenant-cross-reference     ineligible   producer=cp-13-canonical-covenant-cross-reference-egress
```

### What you would have missed

**For the SME.** Three of the five things a memo needs were withheld by the people
who make them — the spread, the exposure roll-up and the covenant chain each measured
more Context Debt than this memo will act on. A memo that printed anyway would have
printed a family tree and a collateral figure and left the three that matter blank or
stale without saying which. This one says which, by producer.

**For the PM.** The refusal is the product working. Five producers were asked, five
answered, two were admitted, three declined to be relied on at this tolerance; the
whole determination is on one record with five rows.

**For the engineer.** The disclosed envelope carries no child reason token — the
default disclosure level. The record carries the FIRST blocking producer's reason and
identity (the spread's `tolerance-exceeded`); the other two withheld rows carry the
admission verdict `ineligible`, not their producers' reasons — that per-row reason is
`D-IMPL-342`'s open item. The admitted family and collateral contracts are retained by
bytes even though the composite refused: retention follows admission, not composition
success.

### How it works

`deployment.MemoQuestions` maps the memo's effective request onto five child questions.
The SDK asks each producer over its door, holds each answer to the registration, admits
or refuses each child, and on a required refusal refuses the composite — persisting five
rows through the one recorder before it returns.

---

## Run 2 — the labeled diagnostic

```
make -s example-cp-14 DEBT_TOLERANCE=--debt-tolerance=1.0
```

The same question with a tolerance nobody would act on, to show the serving path.

### The output

```
outcome     : SERVED  product address 4f40ae4d692aee155a259fd119704f76583bba5114a518b7428c84babe2237d1
              record address  331d3041d418adce593d48e2fb346c79d548dbc68e8a5b9c43237217f1447f20
memo        : credit-risk.credit-memo-context@1.0.0  D_c=1.000000000000000000000000000  signal=fail_closed  expires 2026-09-07T16:00:00+00:00
              F=0E-18  C=0.2000  S=0.8333333333333333333333333333
  § credit-risk.collateral-coverage       facility=FAC-5B8418  commitment=40000000  coverage_ratio=5.497249422375  collateral_after_haircuts=9371046.375
  § credit-risk.covenant-cross-reference  sources=2  chain_nodes=10  checked_citations=2  explained_absences=8  documents_in_force=36
  § credit-risk.exposure-rollup           limit_regime=limit_definition/internal-appetite  family_entities=88  gross_committed=24336505256  adjusted_com
  § credit-risk.spread                    periods=13  latest_filed_in_payload=2026-08-10  basis_applied=as-reported
  § reference.corporate-family            depth_served=3  entities=17  relationships=66  resolved=17  ownership_circuits=15
```

### What you would have missed

**For the SME.** The memo's Context Debt is 1.0 and its signal is `fail_closed` even
though all five children served. The exposure roll-up's balances are days old against a
four-hour half-life, so its freshness is zero, and the memo inherits the worst factor
per axis rather than an average. A memo that averaged would have read as moderately
stale; this one reads as not fit to act on, which is the truth of the inputs.

**For the PM.** Every section names the content address it was composed from, and that
address is the one the admission row recorded. What the memo prints is what the
producers served, and nothing the memo computed from their sources — and each printed
field names the child member it is, held by a test to the retained child. The first
delivered result had printed the collateral child's *total* (collateral plus set-off)
as collateral after haircuts; the corrected memo keeps the two apart, as the collateral
product was built to.

**For the engineer.** The memo expires at 16:00 — with its stalest admitted child, the
exposure roll-up's four-hour window — not at its own twelve-hour ceiling. The product's
content address and the replay record's address are two identities: the runner prints
both, and asserts the persisted record names the product it served. Asked a second time
against unchanged inputs, the memo hashes to the same product address.

### How it works

`produce.MemoPlanFactory.build_with_children` hands the five admitted contracts to Π;
`projection._summary` reads each by name. The SDK composes lineage by set-union, expiry
by the stalest constituent, and debt by the per-factor minimum.

---

## Run 3 — reconstruction without the providers

Not a command; a test (`tests/examples/test_cp_14_fourth_slice.py`). With every producer
process exited, replay resolves the five retained contracts from the consumer's own
store, hands them to the memo's own plan factory, re-executes the recorded operator path
and reproduces the served product's address exactly — the address the record names as its product, not the record's own. The governed refusal reconstructs along its recorded
no-read path with the two admitted addresses intact.

### What you would have missed

**For the SME.** A memo that could only be re-read while its five sources were still
answering could not be audited a year later. This one can.

**For the engineer.** The replay environment is assembled by hand in the test — the
one friction this tree records against the SDK (`CP06C-F-01`'s third copy).

---

## The three things this rung exists to teach

1. **A consumer holds a producer to an identity and a lane, never to an implementation.**
   Two of the five producers were replaced by paved successors and one was reached
   through a wrapper door during this rung; the consumer's registration changed by two
   names and its question mapping did not change at all.
2. **Determining a question is not answering it.** The covenant mapping reads the
   obligor's document keys and the anchors they carry — and stops at the anchor.
3. **Both outcomes are the product.** The governed refusal and the diagnostic serve are
   the same mechanism at two tolerances; the transcript carries both.

## Vocabulary, in two readings

| term | the engineer's reading | the SME's reading |
|---|---|---|
| admitted | the child's contract passed the registration, lane, instant and provenance checks | the producer's answer is one the memo may rely on |
| ineligible | the producer's door refused; the reason is retained on the row | the producer declined to be relied on at this tolerance |
| `fail_closed` | the composed debt exceeds the fail-closed threshold | not fit to act on without a human |
| per-factor minimum | `F`, `C`, `S` each taken as the minimum across parent and children (on this estate the exposure child is already at `D_c` 1, so the scalar reads the same as `max(child D_c)`; an isolated control shows the two part) | the memo is as stale as its stalest input and as incomplete as its thinnest |

## Where each claim is enforced

| claim | where |
|---|---|
| five rows on every exit after acquisition | `test_the_governed_question_withholds_where_producers_withhold_and_refuses_the_composite` |
| sections composed from the admitted addresses | `test_acquisition_and_composition_use_the_same_admitted_child_contracts` |
| every printed field is the declared child member | `test_every_summary_field_reads_the_declared_child_member` |
| product identity is not record identity | `test_the_diagnostic_admits_every_child_that_serves_and_the_composite_outcome_is_measured` |
| the same question twice, one product | `test_the_same_diagnostic_question_yields_one_product_address_twice` |
| a memo type the delivery does not implement is refused | `test_a_memo_type_outside_the_implemented_domain_is_refused` |
| a child-content change moves its section only | `test_a_meaningful_child_content_change_changes_the_corresponding_parent_field` |
| reconstruction with the providers exited | `test_served_reconstruction_uses_retained_inputs_without_calling_any_provider` |
| the covenant question names the obligor's own anchors | `test_the_covenant_question_names_the_obligors_own_evidence_nodes` |

## What the runs do NOT show

A served memo at the governed tolerance against this estate — no producer's balances are
fresh enough; the memo's own template sections, peer benchmarks, evidence references and
policy-version tolerance default (spec §B.1, §D.2), which remain unbuilt and are named in
`FINDINGS.md` as scope, not as an estate limitation; every withheld producer's own reason
on its row (`D-IMPL-342`); the exact historical child question read back from the store
(`CP14-F-35`); and the scalar difference between the per-factor minimum and
`max(child D_c)` on this estate, which an isolated control shows instead.
