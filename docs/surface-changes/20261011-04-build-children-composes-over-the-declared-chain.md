# 20261011-04 — `build_children=` composes over the SDK-derived, composition-registered chain

Dave, 2026-10-11 16:23 MST, ruling 4 (the bounded SDK round). Finding G4-F-08 (cp-20): a composite with a
REQUEST-SCOPED optional child (cp-20's `include_federated`) needs the child-resolution seam, reached only through
`build_children=`, which `open_product` refused beside a declared `agent:`/`skills:` chain. So cp-20 registered its agent
and skill and requested its grant by hand inside the factory; D-IMPL-353 refuses those writes (`CapabilityBypassError`),
and the composite could not open at all, federation on or off.

The supported path: the deployment DECLARES the chain (`producers:`, `skills:`, `agent:`, `grants:`) and passes both
`questions=` and `build_children=`. `open_product` derives the chain exactly as the derived road does — registered and
granted at composition (`grants:`, fragment 20261011-03) — and hands it to the factory as
`ConsumerContext.derived_children` (with `ConsumerContext.agent`). The factory decides only whether THIS request asks
the optional child, and writes nothing; whether a missing child refuses stays the requirement's own `required` /
`absence_treatment`, judged by the composite. A half-declared chain beside `build_children=` is still refused by name;
`children=` beside a declared chain is still refused. Measured in `tests/products/test_paved_optional_child_switch.py`
against a real producer door: default request served without the child (`optional-absent`, nothing dispatched);
switched on, served with the admitted child; the same switch over a REQUIRED child refused
(`composite-child-refusal` / `child_admission`); the factory adds no Control Plane event.

## ccf.products.product.ConsumerContext

- Surface: ccf.products.product.ConsumerContext
- Public surface: true
- Change type: reshaped
- Before: `tenant_id`, `control_plane`, `artifact_store`, `mcp_skills`, `clock`
- After: adds `derived_children: QuestionBoundChildResolver | None = None` and `agent: AgentDefinition | None = None` — the chain the SDK derived from the deployment's declarations, present when a complete chain is declared beside `build_children=`
- Why: G4-F-08; ruling 4. Red test: `tests/products/test_paved_optional_child_switch.py::test_the_default_request_serves_without_the_optional_child`
- Migration: a factory that registered an agent/skill or requested a grant moves them to `skills:`, `agent:`, `grants:` and wraps `context.derived_children`

## ccf.products.product.open_product

- Surface: ccf.products.product.open_product
- Public surface: true
- Change type: behavior
- Before: refused `build_children=` beside a declared `agent:`/`skills:` chain, and `build_children=` beside `questions=`
- After: admits `build_children=` beside a COMPLETE declared chain plus `questions=`, derives the chain first and hands it to the factory; every half-declared chain is refused as before
- Why: G4-F-08; ruling 4. Severing proof: not deriving the chain for the factory reddens four tests by assertion
- Migration: none
