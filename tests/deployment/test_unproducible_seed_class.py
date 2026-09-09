"""R-10 — a walk seeded on a class no resolution rule can mint is refused at boot.

`D-IMPL-279` (Dave, 2026-09-08): *"The Control Plane should reject provably
incompatible declarations at boot/config validation time. If the operator
requires seed classes that the declared resolution/admission path cannot
produce, that is a compositional configuration error, not a runtime 'empty
graph' result. Only validate what can be proven statically; do not infer
dynamic cardinality."*

**What this protects, in one sentence:**
`ccf.deployment.config::_refuse_unproducible_seed_classes` refuses a config
whose operator seeds on an entity class the `resolution.entity_rules` section
declares no rule for — naming both sides — and stays silent on every config
where the incompatibility cannot be proven from the two declarations alone.

**Why it is one test with its controls.** `D-IMPL-276` asks for one direct
regression test naming the SDK behavior it protects. The refusal is one
comparison, so it is one test; the three silence cases are its controls, and
without them a function that refused every config would satisfy the first
assertion. They are `parametrize` cases of one control rather than three
separate tests, because they assert one property: *cannot be proven means
silent, never permissive-by-default and never refusing.*

**THE LIMIT OF THIS CHECK, ASSERTED RATHER THAN DESCRIBED.**
`test_the_cp_05_failure_this_does_not_catch` pins the boundary Dave's ruling
draws. cp-05's own instance of a seed/entity incompatibility
(`CP-SPEC-005` §F.4 finding 7) was a **runtime minting** error: its config
declared both classes correctly and its interpreter passed the wrong flag, so
every node minted as a member while the walk seeded on an anchor that existed
nowhere. This check passes that config, and the test says so with cp-05's real
shape, so nobody reads the finding as closed by this change.
"""

from __future__ import annotations

from typing import Any

import pytest

from ccf.controlplane.artifacts import parse_artifact
from ccf.deployment.config import DEPLOYMENT_CONFIG, DeploymentConfig, derive_deployment

#: The two entity classes a family-shaped product declares — an anchor to seed
#: the walk and a member for everything the walk reaches. cp-04 and cp-05 both
#: use this shape; the names here are the test's own.
ANCHOR, MEMBER = "fixture_anchor", "fixture_member"
TRAVERSAL = "traversal.typed-neighborhood"


def _config(*, seeds: list[str] | None, minted: list[str]) -> DeploymentConfig:
    """A config that derives cleanly except for what the caller varies.

    `required_operator_keys` and the `operators:` keys are kept in agreement so
    the sibling refusal (`R2`, operator-set divergence) cannot fire and be
    mistaken for this one.
    """
    operator_body: dict[str, Any] = {"depth_limit": 3}
    if seeds is not None:
        operator_body["seed_entity_classes"] = seeds
    document: dict[str, Any] = {
        "semver": "1.0.0",
        "backend": "sqlite",
        "product_class": {
            "schema_name": "fixture.product",
            "required_operator_keys": [TRAVERSAL],
        },
        "operators": {TRAVERSAL: operator_body},
        "resolution": {
            "entity_rules": [
                {
                    "match_key": f"{name}_ref",
                    "entity_class": name,
                    "identity_keys": ["entity_uri"],
                }
                for name in minted
            ]
        },
        "policy": {
            "class_id": "acme.policy-bundle",
            "role": "register",
            "registration": "typed",
            "regime": "fixture-regime",
        },
    }
    parsed = parse_artifact(document, DEPLOYMENT_CONFIG)
    assert isinstance(parsed, DeploymentConfig)
    return parsed


def test_a_seed_class_no_entity_rule_can_mint_is_refused_at_boot() -> None:
    """The regression, then the control that makes it mean something.

    **The refusal.** An operator seeding on `fixture_anchor` against a
    resolution spec that can mint only `fixture_member` is unsatisfiable by
    construction: every request this deployment could ever serve would walk
    from a class nothing produces. Both sides are named, so an author is not
    left to work out which of the two declarations they meant.

    **The control.** The SAME config with the anchor rule restored derives
    silently. Without it, a `derive_deployment` that refused every config would
    pass the assertion above.
    """
    with pytest.raises(ValueError) as raised:
        derive_deployment(_config(seeds=[ANCHOR], minted=[MEMBER]))
    message = str(raised.value)
    assert "unproducible seed class" in message
    assert TRAVERSAL in message, "the refusal names WHICH operator"
    assert ANCHOR in message, "the refusal names what was seeded on"
    assert MEMBER in message, "the refusal names what the spec can actually mint"

    # CONTROL — the same shape, satisfiable, derives with no refusal.
    derive_deployment(_config(seeds=[ANCHOR], minted=[ANCHOR, MEMBER]))


@pytest.mark.parametrize(
    ("seeds", "minted", "why"),
    [
        (None, [MEMBER], "an operator declaring no seed classes constrains nothing"),
        ([ANCHOR], [], "an empty entity_rules proves nothing about producibility"),
        ([ANCHOR, MEMBER], [ANCHOR, MEMBER], "every seed is producible"),
    ],
)
def test_what_cannot_be_proven_statically_is_silent(
    seeds: list[str] | None, minted: list[str], why: str
) -> None:
    """Silence where the incompatibility cannot be proven from two declarations.

    *"Only validate what can be proven statically; do not infer dynamic
    cardinality."* Each case below is a shape where refusing would be inventing
    a verdict: no seeds declared, no rules declared, or a satisfiable pair.
    """
    derive_deployment(_config(seeds=seeds, minted=minted))


def test_the_cp_05_failure_this_does_not_catch() -> None:
    """THE BOUNDARY, PINNED — cp-05's own instance passes this check.

    `CP-SPEC-005` §F.4 finding 7 is a **runtime minting** error, not a
    declaration error: cp-05 declared both `exposure_anchor` and
    `exposure_member` and its interpreter passed the wrong flag, so every node
    minted as a member while the walk seeded on an anchor that existed nowhere.
    The declarations were compatible throughout.

    This test asserts that this check passes such a config, so that a reader
    meeting `_refuse_unproducible_seed_classes` does not read finding 7 as
    closed by it. What would catch that failure is a runtime observation, and
    `D-IMPL-279` deliberately does not authorize one here.
    """
    derive_deployment(_config(seeds=[ANCHOR], minted=[ANCHOR, MEMBER]))
