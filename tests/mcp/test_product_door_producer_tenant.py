"""The standard door holds its declared producer tenant to the product's tenant (`D-IMPL-343` R-6).

Lane ``378d-replayfix`` of ``D-IMPL-378``, Defect 2, found by lane
``378d-hw1door`` (its O1). R-6 (Dave, verbatim: *"Registration declares it; door
assertion is held to it; the child's served tenant_id never authorizes. Do not
derive tenant from the answer."*) is enforced where a ``door:`` section is
DERIVED — ``src/ccf/deployment/config.py::_refuse_door_tenant_disagreement`` —
so a paved-road deployment asserting another tenant is refused at boot. A
deployment composed by hand reaches
``runtime/ccf_runtime/mcp/product_door.py::open_door`` with its own
:class:`~ccf.controlplane.artifacts.EgressDoorBinding`, and that structural path
held nothing: the door opened, registered its entitlement policy and scope
mapping, and would assert the other tenant on every outcome it served — to be
refused ``producer-tenant-mismatch`` by every consumer registered for this
deployment's tenant, at the first remote question rather than at composition.

Held here, for both constructors: the mismatch is refused by R-6's own rule and
wording, as R-6's error type (``ValueError``), before the door registers
anything on the product's Control Plane; and a door whose binding states the
product's tenant still opens.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ccf_runtime.mcp.product_door import open_door, open_door_with_verifier
from tests.mcp.test_product_door_composition import TENANT, _Product

#: A tenant the product does not run as.
_ELSEWHERE = "someone-else"

#: R-6's refusal, by its own words: both tenants named, and the rule cited.
_R6 = (
    rf"asserts producer_tenant '{_ELSEWHERE}' and this deployment's tenant is"
    rf" '{TENANT}'; the door asserts the tenant the deployment declares and a"
    r" consumer holds the assertion to its own registration \(D-IMPL-343 R-6;"
    r" D-IMPL-340 ruling 2\)"
)


class _NeverVerifies:
    """A deployment's own verifier, never reached by a refused composition."""

    async def verify_token(self, token: str) -> Any:  # pragma: no cover - never reached
        raise AssertionError("a refused door verified a credential")


def _opens(product: _Product, constructor: str) -> Any:
    if constructor == "open_door":
        return open_door(product, environ={"DOOR_TOKEN": "t"})
    return open_door_with_verifier(
        product, token_verifier=_NeverVerifies(), environ={"DOOR_TOKEN": "t"}
    )


@pytest.mark.parametrize("constructor", ["open_door", "open_door_with_verifier"])
def test_a_door_binding_asserting_another_tenant_is_refused_before_anything_is_registered(
    tmp_path: Path, constructor: str
) -> None:
    product = _Product(tmp_path)
    product.door = product.door.model_copy(update={"producer_tenant": _ELSEWHERE})
    before = product.control_plane.audit_log.events()

    with pytest.raises(ValueError, match=_R6):
        _opens(product, constructor)

    # Refused before the composition: no composition decision recorded and no
    # entitlement policy or scope mapping registered for a door that never opened.
    assert product.control_plane.audit_log.events() == before


@pytest.mark.parametrize("constructor", ["open_door", "open_door_with_verifier"])
def test_a_door_binding_stating_the_products_tenant_still_opens(
    tmp_path: Path, constructor: str
) -> None:
    product = _Product(tmp_path)
    assert product.door.producer_tenant == product.tenant_id == TENANT
    door = _opens(product, constructor)
    assert door.tenant_id == TENANT and door.producer_id == product.door.producer_id
