"""``D-IMPL-59`` part 4 as a property: a Peering declares trust inputs, never
the verdict.

Dave's ruling of 2026-07-27 names the federation seam **Peering** and states
part 4 in as many words: *a Peering declares trust inputs and never the verdict —
core runs the one admission gate uniformly over every Peering and constructs the
admitted value L2 accepts.* Every module in the seam now says so in prose. This
module is what makes it a **property**, which is the distinction the whole
gap-closure wave exists to enforce: a claim stated only in a docstring is a claim
that drifts, and part 4 is the ruling that closes the wave, so it does not get to
be the one exception.

Three assertions, each narrow (D-21):

(a) A **conforming** :class:`~ccf.peering.protocol.PeeringProtocol` that tries to
    produce an :class:`~ccf.peering.admission.AdmittedProduct` without going
    through :meth:`~ccf.peering.admission.PeeringAdmissionGate.admit` fails at
    construction. Asserted against a purpose-built *non-conforming* Peering
    rather than against the two shipped transports, which do not attempt it — a
    test that only exercised the shipped transports would pass on a fabric where
    the token had been removed, because neither of them would notice.
(b) No discovered transport module can run a check of its own or name the
    verdict: over the *discovered* set, so a third transport is covered on
    arrival rather than on someone remembering. This is the structural half of
    "core runs the gate uniformly" — uniformity is not that each transport calls
    the same gate, it is that no transport is in a position to call anything else.
(c) The gate offers exactly one admission entry point, so "the one gate" is a
    fact about its surface rather than a description of current call sites.

**What this module does not claim.** It does not claim the token is unforgeable.
That claim was deliberately scoped down by 06-21 (wave 8) to *no unforced path
exists; forging requires naming a private module member*, and
``tests/crossproc/test_peering_exchange.py`` holds both edges of that scope. The
wording there is not restated here and must not be strengthened here either;
this module asserts the *unforced* path only, which is the path a conforming
Peering implementation actually has.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import pkgutil
import types
from collections.abc import Iterator

import pytest

import ccf_runtime.peering
from ccf.peering.admission import (
    AdmissionBypassError,
    AdmittedProduct,
    PeeringAdmissionGate,
)
from ccf.peering.protocol import (
    EmitReceipt,
    InboundProduct,
    PeeringProtocol,
    PeerRef,
)

pytestmark = pytest.mark.crossproc

#: Identifiers a transport module must not name. ``AdmittedProduct`` is the
#: verdict's value and ``PeeringAdmissionGate`` is the only thing that reaches
#: it; ``_ADMISSION_TOKEN`` is the private member 06-21's scoped claim is about.
#: A transport naming any of them is a transport in a position to conclude in its
#: own favour, whether or not it currently does.
VERDICT_NAMES = frozenset(
    {"AdmittedProduct", "PeeringAdmissionGate", "_ADMISSION_TOKEN"}
)


def _transport_modules() -> tuple[types.ModuleType, ...]:
    """Every module ``ccf_runtime.peering`` ships, discovered rather than listed.

    The same discovery shape ``tests/invariants/test_peering_single_writer.py``
    uses, and for the same reason: a hand-maintained list is one a later
    transport can be added without joining, and the module that joined nothing
    is exactly the one that would carry the violation.
    """
    found = [ccf_runtime.peering]
    for info in pkgutil.walk_packages(
        ccf_runtime.peering.__path__, prefix=ccf_runtime.peering.__name__ + "."
    ):
        found.append(importlib.import_module(info.name))
    return tuple(found)


TRANSPORT_MODULES = _transport_modules()


def _identifiers(module: types.ModuleType) -> set[str]:
    """Every name and attribute identifier in ``module``'s source.

    Identifiers, never source text: a text scan cannot tell a violation from a
    docstring that documents compliance, and every module in this seam documents
    exactly this compliance in prose. String constants are not identifiers, so
    they are outside this set and cannot trip it; a genuine use *is* an
    identifier and cannot escape it.
    """
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.rsplit(".", 1)[-1])
    return names


class _ForgingPeering:
    """A conforming Peering that tries to conclude its own admission.

    Purpose-built and deliberately *not* one of the shipped transports: neither
    ``lf_a2a`` nor ``typed_http`` attempts this, so a test written against them
    would stay green on a fabric where the construction check had been removed.
    Structurally conforming — :func:`isinstance` against the ``runtime_checkable``
    Protocol passes — which is the point: the refusal is not a conformance
    failure, it is the seam refusing to hand a conforming implementation the
    verdict.
    """

    def emit(
        self, *, peer: PeerRef, signed: object
    ) -> EmitReceipt:  # pragma: no cover - never carried
        raise NotImplementedError

    def receive(self) -> Iterator[InboundProduct]:  # pragma: no cover
        raise NotImplementedError

    def admit_myself(self) -> AdmittedProduct:
        """What a Peering is structurally unable to do."""
        return AdmittedProduct(None, None, None, object())  # type: ignore[arg-type]


def test_a_conforming_peering_cannot_produce_the_verdict() -> None:
    """Part 4, the unforced path: the seam refuses, at construction.

    Both halves are needed. ``isinstance`` establishes that this really is a
    conforming Peering — otherwise the refusal could be read as a conformance
    problem rather than as the seam's own boundary — and the raise establishes
    that conformance buys no route to the verdict.

    What would fail here: dropping ``AdmittedProduct``'s construction token, at
    which point every docstring in the seam would still read correctly and mean
    nothing.
    """
    peering = _ForgingPeering()

    assert isinstance(peering, PeeringProtocol)

    with pytest.raises(AdmissionBypassError):
        peering.admit_myself()


def test_transport_modules_were_actually_discovered() -> None:
    """The parametrized scan below is worth nothing if it scanned nothing.

    What would fail here: a discovery helper that silently returned an empty
    tuple, which would make the next test vacuously true for every transport —
    the quietest way an invariant test stops being one.
    """
    assert len(TRANSPORT_MODULES) >= 3
    discovered = {module.__name__ for module in TRANSPORT_MODULES}
    assert "ccf_runtime.peering.typed_http" in discovered
    assert "ccf_runtime.peering.lf_a2a" in discovered


@pytest.mark.parametrize("module", TRANSPORT_MODULES, ids=lambda m: m.__name__)
def test_no_discovered_transport_names_the_verdict(
    module: types.ModuleType,
) -> None:
    """Part 4 over the discovered set: uniformity is structural, not habitual.

    Core runs *one* gate over every Peering. What makes that uniform is not that
    each transport happens to call the same gate — it is that no transport is
    handed anything else to call. A module that named the gate could run it with
    arguments of its own choosing; a module that named ``AdmittedProduct`` or the
    private token could skip it.

    What would fail here: a transport that reached for the gate to "pre-check"
    its own inbound products, or one that constructed the verdict directly. Both
    are the per-transport check D-12 rejected, arriving by a different door.
    """
    named = _identifiers(module) & VERDICT_NAMES

    assert not named, (
        f"{module.__name__} names {sorted(named)}; a Peering transport declares"
        " trust inputs and never the verdict (D-IMPL-59 part 4)"
    )


def test_the_gate_offers_exactly_one_admission_entry_point() -> None:
    """"The one gate" as a fact about the surface, not about call sites.

    A second public method that admitted would make "one gate, uniformly over
    every Peering" true only of today's callers. Private helpers are excluded
    deliberately — the gate factors its checks into private steps by design
    (06-18 did exactly that), and this claim is about the *offered* surface.

    What would fail here: adding a public ``admit_fast``, ``admit_trusted`` or
    similar — the fast path for a high-trust peer that D-IMPL-16 rules out.
    """
    public_admitting = {
        name
        for name, _ in inspect.getmembers(PeeringAdmissionGate, inspect.isfunction)
        if not name.startswith("_") and "admit" in name
    }

    assert public_admitting == {"admit"}
