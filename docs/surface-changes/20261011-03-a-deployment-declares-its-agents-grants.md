# 20261011-03 — a deployment declares the grants its agent needs; composition requests them through the ledger

Dave, 2026-10-11 16:23 MST, ruling 4 (the bounded SDK round). Finding G3 (cp-14): since `D-IMPL-353` the paved road
cannot grant (a grant is the `skill.grant` door action, `Authorized[SkillGrant]`, which a composition root may not
mint), and no example-reachable door could put a composite's grants in force, so cp-14 refused `GrantNotInForce` at
open. `GrantNotInForce`'s own docstring recorded the open question for D-IMPL-354: whether a deployment's DECLARED
grants are a composition-time act. Ruling 4 answers it.

The supported path: `ccf_config.yaml` lists, under `grants:`, the `skills:` labels the deployment grants its `agent:`.
`open_product` requests each through `GrantLedger.request` under a new composition kind, `DeclaredSkillGrant`, minted for
exactly the agent definition's key from a recorded `composition` decision. The ledger runs what a door grant runs: tier
1 (the policy regime's compatibility check), tier 2 (the regime's approval rule, on the deployment's `approval_sink=`),
the `grant_requested` / `grant_effective` / `grant_refused` audit events and grant-state records, under the composition
principal. Nothing is granted that the deployment did not declare: a skill under `skills:` that is not under `grants:`
still refuses `GrantNotInForce`. The door's `SkillGrant` stays unmintable at composition. Measured in
`tests/products/test_paved_declared_grants.py`.

## ccf.authz.capability.DeclaredSkillGrant

- Surface: ccf.authz.capability.DeclaredSkillGrant
- Public surface: true
- Change type: added
- Before: absent
- After: a composition kind (`composition.skill-grant`) in `COMPOSITION_KINDS`; no door declares it and `kind_for_action` refuses its id by name. Admitted by `GrantLedger.request` (bound to one agent definition), by the grant-state writer (`STATE_WRITE_KINDS`) and by the ledger's derived registration (`DERIVED_REGISTER_KINDS`)
- Why: ruling 4 (Dave, 2026-10-11 16:23 MST). Red test: `tests/products/test_paved_declared_grants.py::test_a_declared_policy_compatible_grant_is_in_force_and_the_composite_serves`
- Migration: none

## ccf.products.product.DeclaredGrantRefused

- Surface: ccf.products.product.DeclaredGrantRefused
- Public surface: true
- Change type: added
- Before: absent
- After: a `GrantNotInForce` subclass raised at open when the ledger refuses a DECLARED grant (`refusal` carries the ledger's `GrantRefusal`, e.g. `RequirementsExceedRegime`)
- Why: ruling 4. Test: `tests/products/test_paved_declared_grants.py::test_a_declared_grant_the_regime_does_not_permit_is_refused_by_the_ledger`
- Migration: none

## ccf.controlplane.artifacts.DeploymentConfig

- Surface: ccf.controlplane.artifacts.DeploymentConfig
- Public surface: true
- Change type: reshaped
- Before: no `grants` key
- After: an optional, hash-transparent `grants: tuple[str, ...] | None` — `skills:` labels the deployment grants its agent; a label naming no declared skill is refused by name at open
- Why: ruling 4. Test: `tests/products/test_paved_declared_grants.py::test_grants_naming_an_undeclared_skill_is_refused_by_name`
- Migration: a composite whose agent's grants were made by hand (or could not be made) lists its `skills:` labels under `grants:`

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: requested no grant; refused `GrantNotInForce` for every declared skill not already bound on the Control Plane handed in
- After: requests each `grants:` skill through the ledger at composition before that check; refuses `DeclaredGrantRefused` when the ledger refuses one, and `GrantNotInForce` (unchanged) for a declared skill that is not under `grants:` and not bound
- Why: ruling 4. Severing proof: granting every `skills:` entry regardless of `grants:` reddens `::test_a_declared_skill_not_listed_under_grants_is_not_in_force` (DID NOT RAISE)
- Migration: none

## ccf.skills.grants.GrantLedger.request

- Surface: ccf.skills.grants.GrantLedger.request
- Public surface: true
- Change type: behavior
- Before: required `Authorized[SkillGrant]`
- After: requires `Authorized[SkillGrant]` or `Authorized[DeclaredSkillGrant]`, verified as minted, bound to the one definition; the two tiers, audit and state records are unchanged
- Why: ruling 4
- Migration: none
