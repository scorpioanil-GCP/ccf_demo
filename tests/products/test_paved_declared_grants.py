"""A deployment DECLARES the grants its agent needs; composition requests them through the ledger (cp-14 / G3).

**SDK-defined** (CLAUDE.md §11). Dave, 2026-10-11 16:23 MST, ruling 4: *"Provide
the supported way for a deployment to declare the grants its agent needs,
registered at composition through the existing grant governance (policy-regime
compatibility check, audit, replay capture) ... Preserve ... cp-14's actual grant
requirements ... Do not obtain success by bypassing a gate or inventing a grant."*

``ccf_config.yaml``'s ``grants:`` lists ``skills:`` labels the deployment grants its
``agent:``. ``open_product`` requests each through
:meth:`~ccf.skills.grants.GrantLedger.request` under a ``DeclaredSkillGrant``
minted at composition for exactly the agent definition — the same tier 1 and tier 2
a door grant runs, the same audit and state records.

Held here, permitted beside refused, over the plain Control Plane a deployment opens
(nobody pre-granted anything):

* the declared, policy-compatible grant is in force, by the ledger's own record and
  under the composition principal, and the composite SERVES;
* a skill declared under ``skills:`` but NOT under ``grants:`` is not granted —
  ``GrantNotInForce``, as before;
* a declared grant the regime does not permit is refused by the ledger's tier-1 check
  (``RequirementsExceedRegime``), and open refuses by name;
* a regime requiring approval refuses a declared grant on the refusing sink — the
  declaration does not bypass tier 2;
* ``grants:`` naming a label no ``skills:`` entry declares is refused by name;
* the door's ``SkillGrant`` kind is still not mintable at composition.
"""

from __future__ import annotations

import pathlib

import pytest

from ccf.authz.capability import (
    COMPOSITION_PRINCIPAL,
    CapabilityBypassError,
    SkillGrant,
    mint_at_composition,
)
from ccf.contracts.canonical import content_hash
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.products.contract import SUBJECT_WITHHOLDING_NEVER
from ccf.products.product import DeclaredGrantRefused, GrantNotInForce
from ccf.replay.serve import ServedProduct
from ccf.skills.catalog import SkillCatalog
from ccf.skills.grants import GrantLedger, RequirementsExceedRegime

from tests.composition import declare_wide_temporal_boundary
from tests.products import paved_fixture as fixture
from tests.products.paved_fixture import SKILL
from tests.products.test_paved_consumer import (  # noqa: F401 - `producer_url` is a fixture
    _open,
    _question,
    _the_row,
    _tree,
    producer_url,
)


def _plain_plane() -> ControlPlaneRegistry:
    """The plane a deployment opens over: its temporal boundary, and NO grant made by anyone."""
    registry = ControlPlaneRegistry()
    declare_wide_temporal_boundary(registry, tenant_id=fixture.CONSUMER_TENANT)
    return registry


def _config(**overrides: object) -> dict[str, object]:
    return fixture.consumer_config(subject_withholding=SUBJECT_WITHHOLDING_NEVER, **overrides)  # type: ignore[arg-type]


# --- permitted -------------------------------------------------------------------------


def test_a_declared_policy_compatible_grant_is_in_force_and_the_composite_serves(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    root = _tree(tmp_path, config=_config(grants=[SKILL]))
    with _open(root, tmp_path / "scratch", producer_url, control_plane=_plain_plane()) as opened:
        assert opened.agent is not None
        ledger = GrantLedger(
            control_plane=opened.control_plane,
            catalog=SkillCatalog(opened.control_plane),
            sink=None,  # type: ignore[arg-type] - read only
            clock=lambda: fixture.ADMITTED_AT,
        )
        bound = ledger.bound_view(content_hash(opened.agent))
        assert SKILL in bound, "the declared grant is not in force"
        # Granted by the composition root, on the audit log, by the ledger's own events.
        granted = [
            event
            for event in opened.control_plane.audit_log.events()
            if event.action == "grant_effective"
        ]
        assert granted and all(event.actor == COMPOSITION_PRINCIPAL for event in granted), granted
        served = opened.answer(_question(opened))
        assert isinstance(served, ServedProduct), getattr(served, "detail", served)
        assert _the_row(opened, served).outcome_status == "admitted"


# --- refused, beside it -----------------------------------------------------------------


def test_a_declared_skill_not_listed_under_grants_is_not_in_force(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    root = _tree(tmp_path, config=_config())  # skills: declared, grants: absent
    with pytest.raises(GrantNotInForce, match=SKILL) as refused:
        _open(root, tmp_path / "scratch", producer_url, control_plane=_plain_plane())
    assert not isinstance(refused.value, DeclaredGrantRefused)


def test_a_declared_grant_the_regime_does_not_permit_is_refused_by_the_ledger(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    config = _config(
        grants=[SKILL],
        skills={
            SKILL: fixture.skill_section(
                requirements={"required_scopes": ["scope:x"], "required_context_products": []}
            )
        },
    )
    root = _tree(tmp_path, config=config)
    with pytest.raises(DeclaredGrantRefused, match=SKILL) as refused:
        _open(root, tmp_path / "scratch", producer_url, control_plane=_plain_plane())
    assert isinstance(refused.value.refusal, RequirementsExceedRegime), refused.value.refusal


def test_a_regime_requiring_approval_refuses_a_declared_grant_on_the_refusing_sink(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    config = _config(
        grants=[SKILL], governance={"grant_requires_approval": True, "permitted_scopes": []}
    )
    root = _tree(tmp_path, config=config)
    # The refusing sink's own refusal (tier 2): the declaration grants nothing around it.
    with pytest.raises(ValueError, match="requires approval for grant 'child-ask'"):
        _open(root, tmp_path / "scratch", producer_url, control_plane=_plain_plane())


def test_grants_naming_an_undeclared_skill_is_refused_by_name(
    tmp_path: pathlib.Path, producer_url: str  # noqa: F811
) -> None:
    root = _tree(tmp_path, config=_config(grants=[SKILL, "not-a-declared-skill"]))
    with pytest.raises(ValueError, match="not-a-declared-skill"):
        _open(root, tmp_path / "scratch", producer_url, control_plane=_plain_plane())


def test_the_doors_grant_kind_is_still_not_mintable_at_composition() -> None:
    with pytest.raises(CapabilityBypassError):
        mint_at_composition(
            SkillGrant,  # type: ignore[call-overload]
            tenant="t",
            principal=COMPOSITION_PRINCIPAL,
            resource="t/ccf.agent-definition/a",
            decision_id="d",
        )
