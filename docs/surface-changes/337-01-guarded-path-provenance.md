# 337-01 — guarded-path provenance: the declared registry and two verifiers

Recorded at the `f0656746` qualification (2026-09-19) from the introducing commit `c676603f`
(*feat(D-IMPL-337): guarded-path provenance at every governed boundary*, 2026-09-14), which
shipped without a surface-change fragment. `D-IMPL-337`'s governing rule, recorded in
`docs/DECISIONS.md`: a consumer that relies on authority established by a guarded construction
path must positively verify that the supplied value passed through that path; nominal type
identity, structural compatibility, Protocol conformance or `isinstance` alone is insufficient.
This fragment claims exactly the five public names `c676603f` added and nothing else. The
boundaries the commit converted from an `isinstance` check to a verifier call are behavior
inside existing names, and the guarded types the later `D-IMPL-340` declared are `340-01`'s.

## ccf.contracts.guarded.GUARDED_TYPES

- Surface: ccf.contracts.guarded.GUARDED_TYPES
- Public surface: true
- Change type: added
- Before: absent — which types were token-guarded was known only to an AST census, a heuristic the design work found wrong three times in three different ways
- After: `Final[tuple[GuardedTypeDeclaration, ...]]` — the declared registry, one `GuardedTypeDeclaration` per guarded type, every field a `module:QualName` string so the registry imports none of the types it names and the lint resolves them at lint time
- Why: `D-IMPL-337` (`c676603f`) — the census is a candidate instrument and this declaration is the truth; a guarded type that fails to declare itself here is a lint failure at the type
- Migration: none for a consumer. A deployment that adds a guarded type declares it here, naming its mint, its verifier and every governed boundary

## ccf.contracts.guarded.GuardedTypeDeclaration

- Surface: ccf.contracts.guarded.GuardedTypeDeclaration
- Public surface: true
- Change type: added
- Before: absent
- After: a frozen dataclass — `type_path`, `authority`, `mint`, `verifier` (or `None` where a type carries no verifier yet and the gap is declared rather than hidden), `boundaries`, `propagation`, `residual`, `verifier_aliases`, `notes` — everything drift enforcement needs about one guarded type
- Why: `D-IMPL-337` (`c676603f`) — conclusion 4 permits equivalent construction-path proofs and canonizes no single physical marker, so the record states which mechanism each type uses rather than performing a check itself
- Migration: none

## ccf.contracts.guarded.declaration_for

- Surface: ccf.contracts.guarded.declaration_for
- Public surface: true
- Change type: added
- Before: absent
- After: `declaration_for(type_path: str) -> GuardedTypeDeclaration | None` — the registry lookup by `module:QualName`; `None` for a type that declares nothing
- Why: `D-IMPL-337` (`c676603f`) — the lint and the tests read the registry through one function rather than each scanning the tuple
- Migration: none

## ccf.peering.admission.verify_admission_provenance

- Surface: ccf.peering.admission.verify_admission_provenance
- Public surface: true
- Change type: added
- Before: absent — the path toward L3 accepted an `AdmittedProduct` on its type, and `isinstance` admits a subclass that skipped the guarded `__init__` and admits `object.__new__`
- After: `verify_admission_provenance(admitted: object) -> AdmittedProduct` — establishes that the value came through Control Plane peering admission, raises `AdmissionBypassError` otherwise, and returns the value narrowed so a caller cannot verify and then forget to use the result
- Why: `D-IMPL-337` (`c676603f`) — the check is the provenance, not the type; an unverified federated product reaching the path toward L3 breaches the single-writer invariant (CLAUDE.md §10) and `D-IMPL-16`'s commitment that an inbound A2A product is inadmissible until the consuming Control Plane validates it
- Migration: none on the shipped paths; a deployment that hands a peering boundary an `AdmittedProduct`-shaped value of its own making is now refused by name

## ccf.products.gates.verify_gate_provenance

- Surface: ccf.products.gates.verify_gate_provenance
- Public surface: true
- Change type: added
- Before: absent — a served product was accepted on `isinstance(product, ServableProduct)`; measured before the change, both a subclass that skipped the guarded `__init__` and `object.__new__` reached a served product with no gate having run
- After: `verify_gate_provenance(product: object) -> ServableProduct` — establishes that the value came through the three validation gates (the declared mint is `ccf.products.gates::run_gates`), raises `GateBypassError` otherwise, and returns the value narrowed
- Why: `D-IMPL-337` (`c676603f`) — the check is the provenance, not the type, and the difference is exploitable rather than academic
- Migration: none on the shipped paths; a caller at a boundary it owns writes `product = verify_gate_provenance(product)` and cannot forget to use the result
