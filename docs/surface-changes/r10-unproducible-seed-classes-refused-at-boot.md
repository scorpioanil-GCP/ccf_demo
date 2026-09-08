# R-10 — a walk seeded on a class no resolution rule can mint is refused at boot

Applied 2026-09-08 under `D-IMPL-279` (Dave), on cp-05's `CP-SPEC-005` §F.4 finding 7:
*"The Control Plane should reject provably incompatible declarations at boot/config
validation time. If the operator requires seed classes that the declared
resolution/admission path cannot produce, that is a compositional configuration error, not
a runtime 'empty graph' result. Only validate what can be proven statically; do not infer
dynamic cardinality."*

## What did NOT change, stated first

- **No public surface is added.** `_refuse_unproducible_seed_classes` is module-private,
  beside `_refuse_operator_set_divergence`, and called from the same site on the same
  before-materialisation ordering. Nothing is exported.
- **No shipped config is affected.** All seven example configs derive unchanged — measured,
  one by one. cp-04 and cp-05 both seed on a class their own `entity_rules` declares.
- **Nothing runtime is inferred.** The comparison is between two declared SETS. It says
  nothing about whether an entity of a producible class will exist, how many there will be,
  or whether a walk seeded on one will reach anything.
- **The check is silent where nothing can be proven** — no `resolution` section, no
  `entity_rules`, or an operator declaring no `seed_entity_classes` — which is the honest
  posture for *cannot be proven*, not a permissive default.

## THE LIMIT, STATED SO THE FINDING IS NOT READ AS CLOSED

**This check would have passed cp-05's own failure.** `CP-SPEC-005` §F.4 finding 7 was a
*runtime minting* error, not a declaration error: cp-05 declared both `exposure_anchor` and
`exposure_member` correctly and its interpreter passed the wrong flag, so every node minted
as a member while the walk seeded on an anchor that existed nowhere. This change closes the
statically provable subset of that finding — the subset `D-IMPL-279` authorizes — and no
more. `tests/deployment/test_unproducible_seed_class.py::test_the_cp_05_failure_this_does_not_catch`
asserts the boundary with cp-05's real shape so a reader cannot mistake it.

## Regression evidence

`tests/deployment/test_unproducible_seed_class.py`: one test asserting the refusal names the
operator, the seeded class and the producible set, with a satisfiable control in the same
test; three parametrized silence cases for what cannot be proven; and the boundary test
above. Sabotage-verified: with the refusal neutralized the regression goes red and the four
controls stay green, which is what proves the controls are not passing vacuously.
