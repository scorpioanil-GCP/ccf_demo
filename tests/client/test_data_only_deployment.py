"""`17-13` — the 2026-08-16 spec's criteria 2 and 3′, end to end.

Criterion 2 asks that *"a deployment directory containing only*
``ccf_config.yaml`` *and a data-only* ``binding.yaml`` *produces a working
gated product"*, and **Amendment A.4** replaced criterion 3 with 3′:

    *"The first example's* ``deployment/`` *contains* ``ccf_config.yaml``\\ *, a
    data-only* ``binding.yaml``\\ *, and exactly one Python module — the
    projection. The* ``binding.yaml`` *loader refuses any other*
    ``module:attribute`` *reference by name, so the exception cannot widen
    silently into the* ``D-IMPL-141`` *shape that was rejected."*

That last clause is the load-bearing one, and A.4 says why: *"an exception with
no mechanism holding it narrow is not an exception; it is a precedent."*

What this module adds that `17-12`'s does not
----------------------------------------------
``tests/client/test_binding_document.py`` proves the loader's refusals at the
**loader's** boundary, and it proves the deployment holds one module. Two things
it cannot reach, and this module is here for both:

1. **The whole chain.** A refusal that fires in ``load_binding_document`` and is
   then caught, defaulted around or never called on the path a client actually
   takes is a gate wired to nothing — the shape this phase has now hit six
   times. So every refusal here is driven through
   :meth:`~ccf.client.client.ProductClient.ask`, from a ``CCF_BINDING``
   environment variable, exactly as an adopter reaches it.
2. **That the produced product is gated and content-addressed, with debt the
   SDK's own scorer measured.** ``17-13`` made
   :class:`~ccf.products.debt_scorer.AssemblyDebtScorer` the default inside
   :func:`~ccf.products.resolver.build_governed_resolver`, and the
   :class:`~ccf.halflife.assessment.ScorerPin`\\ s that reach the **client's**
   ``Result`` are where that is observable from outside the producer. A test
   asserting only that ``result.debt`` exists would pass on a deployment that
   supplied its own scorer, which is the thing this work exists to stop
   requiring.

Every assertion is a module-level function taking the deployment **root** as a
parameter, so a control hands the *shipped* assertion a divergent root.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from ccf.client.adapters.binding_document import (
    BINDING_DOCUMENT_NAME,
    REFERENCE_KEYS,
    RULED_OUT_KEYS,
    looks_like_a_reference,
)
from ccf.client.adapters.inprocess import SCHEME
from ccf.client.client import ProductClient
from ccf.client.errors import BindingError, TransportError
from ccf.client.result import Result
from ccf.halflife.debt import FRESHNESS_SCORER_ID
from ccf.products.debt_scorer import DECLARED_FACTOR_SCORER_ID

from tests.client.conftest import config_document
from tests.client.test_binding_document import assert_one_python_module

#: The one declared parameter the fixture's request contract requires.
THRESHOLD = "minimum_score"

#: The scorer identities a product carries when the **SDK** measured its debt.
#: Read off the shipped constants, so a version bump in ``src/`` cannot leave
#: this module asserting an identity nothing carries any more.
SDK_SCORER_IDS = frozenset({FRESHNESS_SCORER_ID, DECLARED_FACTOR_SCORER_ID})


# ---------------------------------------------------------------------------
# THE DEPLOYMENT-SHAPE GATE — criterion 3′, as a function of the root.
# ---------------------------------------------------------------------------


def _positions(value: Any, *, position: str) -> Iterator[tuple[str, Any]]:
    """Every scalar in ``value``, with its dotted position.

    The traversal is local; the **predicate is the shipped one**. That split is
    deliberate: :func:`~ccf.client.adapters.binding_document.looks_like_a_reference`
    is the load-bearing half — it decides that ``asked_at:
    2026-03-02T12:00:00+00:00`` is data and ``projection.py:build_projection``
    is not — and a gate carrying its own copy of that judgement would drift from
    the loader it is supposed to be checking. Walking a nested mapping is not a
    judgement.
    """
    if isinstance(value, dict):
        for key, nested in value.items():
            yield from _positions(nested, position=f"{position}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            yield from _positions(nested, position=f"{position}[{index}]")
        return
    yield position, value


def assert_the_deployment_is_data_and_one_projection(root: Path) -> None:
    """Criterion 3′ over a deployment root: one module, and one reference.

    Three limbs, and the **positive** one is not decoration:

    * exactly one Python module — delegated to ``17-12``'s shipped
      :func:`~tests.client.test_binding_document.assert_one_python_module`
      rather than re-counted here, because two copies of a count are two things
      to keep in step and only one of them would be watched failing;
    * ``plan:`` **is** a reference. Without this limb an empty ``binding.yaml``
      would satisfy the whole gate by carrying no references at all, which is
      the empty case in its purest form — a check that stops checking without
      going red;
    * nothing **else** is a reference, at any depth. A document is data plus one
      exception, and a reference smuggled through ``question.subject`` or
      ``operator_parameter_keys[0]`` would widen the exception by nobody's
      decision.

    Args:
        root: The deployment root to hold to the criterion. A parameter rather
            than a constant, so a control can hand this function a divergent
            root and be watched failing.

    Raises:
        AssertionError: the root breaks any of the three limbs. The message
            names the position, because a gate that does not say what to fix
            costs the reader the diagnosis it already performed.
    """
    assert_one_python_module(root)

    document = root / BINDING_DOCUMENT_NAME
    parsed = yaml.safe_load(document.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise AssertionError(
            f"{document} parsed as `{type(parsed).__name__}`, not a mapping —"
            " a deployment whose wiring is not a document has no shape to hold"
            " to criterion 3′"
        )

    unreferenced = sorted(
        key for key in REFERENCE_KEYS if not looks_like_a_reference(parsed.get(key))
    )
    if unreferenced:
        raise AssertionError(
            f"{document} states no `<module-path>:<attribute>` reference under"
            f" {unreferenced} — Amendment A.3 grants this deployment one Python"
            " module and the document is where it is named. A document"
            " carrying no reference at all would satisfy a 'nothing else is a"
            " reference' check perfectly while naming no projection, which is"
            " the empty case this limb exists to close"
        )

    offenders = [
        (position, value)
        for key, section in parsed.items()
        if str(key) not in REFERENCE_KEYS
        for position, value in _positions(section, position=str(key))
        if looks_like_a_reference(value)
    ]
    if offenders:
        raise AssertionError(
            f"{document} carries a `<module-path>:<attribute>` reference in a"
            f" data position: {offenders}. This deployment is data plus exactly"
            f" one reference, under {', '.join(REFERENCE_KEYS)} — a second one"
            " is the rejected `D-IMPL-141` shape returning through a key the"
            " schema happens to permit"
        )


# ---------------------------------------------------------------------------
# Driving the whole chain, the way an adopter does.
# ---------------------------------------------------------------------------


def _bound_client(root: Path, monkeypatch: pytest.MonkeyPatch) -> ProductClient:
    """A client reaching ``root`` through ``CCF_BINDING`` and nothing else.

    The environment variable rather than ``binding=`` on purpose: ``D-04``
    makes the scheme prefix the only place a transport is named and puts it in
    the environment, so an end-to-end test that passed the address in code
    would be exercising a path an adopter does not take.
    """
    monkeypatch.setenv("CCF_BINDING", f"{SCHEME}:{root}")
    return ProductClient.for_product(
        str(config_document(root)["product_class"]["schema_name"])
    )


def _document(root: Path) -> dict[str, Any]:
    return dict(
        yaml.safe_load((root / BINDING_DOCUMENT_NAME).read_text(encoding="utf-8"))
    )


def _rewrite(root: Path, body: dict[str, Any]) -> None:
    (root / BINDING_DOCUMENT_NAME).write_text(
        yaml.safe_dump(body), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Criterion 2 — the data-only deployment produces a gated, addressed product.
# ---------------------------------------------------------------------------


def test_a_data_only_deployment_produces_a_gated_content_addressed_product(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spec's criterion 2, driven from ``CCF_BINDING`` to a ``Result``.

    The four post-assembly fields are asserted **together**. A result carrying a
    payload and no content address would satisfy a narrower test while being
    useless for the audit story the client exists to serve, and one carrying an
    address but no replay reference would name a decision nobody could resolve.
    """
    result = _bound_client(seeded_root, monkeypatch).ask(
        parameters={THRESHOLD: 20}
    )

    assert isinstance(result, Result)
    assert not result.refused

    assert result.payload["count"] == 2
    assert [widget["name"] for widget in result.payload["widgets"]] == [
        "beta",
        "gamma",
    ]
    assert result.debt is not None
    assert len(result.content_address) == 64
    assert result.replay_ref is not None
    assert result.replay_ref.startswith("ccf-artifact://")


def test_the_debt_on_the_wire_was_measured_by_the_sdk_reference_scorer(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The default reached the **client**, and the pins are how that is visible.

    This is `17-13`'s own criterion at the far end of the chain. The deployment
    names no scorer anywhere — ``binding.yaml`` declares the two Control Plane
    keys and the two factors the SDK cannot measure, and nothing else — so a
    product arriving with the SDK's scorer identities on it is proof that
    :func:`~ccf.products.resolver.build_governed_resolver` selected the
    reference and that the reference ran.

    Asserted as a **whole-set equality over three pinned factors**, so an
    assessment carrying no pins fails here rather than passing an ``issubset``.
    """
    result = _bound_client(seeded_root, monkeypatch).ask(
        parameters={THRESHOLD: 20}
    )

    assert result.debt is not None
    pinned = {pin.factor: pin.scorer_id for pin in result.debt.scorers}
    assert pinned == {
        "freshness": FRESHNESS_SCORER_ID,
        "completeness": DECLARED_FACTOR_SCORER_ID,
        "semantic_consistency": DECLARED_FACTOR_SCORER_ID,
    }
    assert set(pinned.values()) <= SDK_SCORER_IDS


def test_the_deployment_declares_no_scorer_and_no_resolver_anywhere(
    seeded_root: Path,
) -> None:
    """The other half of the claim: the deployment's one module is a projection.

    A deployment could carry the SDK's pins *and* still hold a scorer it never
    wired, which would leave the *"never has to know the Protocol exists"*
    property (spec §6) true only by accident. Read from the module's source
    rather than by importing it — a gate that runs its subject to measure it is
    a gate the subject can influence.
    """
    from ccf.client.adapters.binding_document import load_binding_document

    module = seeded_root / load_binding_document(seeded_root).plan.partition(":")[
        0
    ].strip()
    source = module.read_text(encoding="utf-8")

    for absent in (
        "AssemblyDebtScorerProtocol",
        "AssemblyDebtScorer",
        "DebtFactors",
        "DebtAssessment",
        "FreshnessScorer",
        "GovernedResolver",
    ):
        assert absent not in source, (
            f"{module} names `{absent}` — after `17-13` the SDK selects its own"
            " debt scorer and builds its own resolver, so a deployment that"
            " still names either is carrying producer machinery the ruling"
            " removed"
        )


# ---------------------------------------------------------------------------
# Criterion 3′ — the shape, and the controls that feed it divergent roots.
# ---------------------------------------------------------------------------


def test_the_committed_deployment_satisfies_the_shape_gate(
    deployment_root: Path,
) -> None:
    """The honest subject. First, so no control below can be met by a broken one."""
    assert_the_deployment_is_data_and_one_projection(deployment_root)


def test_the_shape_gate_fires_on_a_second_python_module(
    deployment_root: Path,
) -> None:
    """CONTROL — a divergent root: the exception has widened to two modules."""
    (deployment_root / "scorer.py").write_text(
        "def build_scorer() -> None: ...\n", encoding="utf-8"
    )

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(deployment_root)

    assert "2 Python modules" in str(fired.value)


def test_the_shape_gate_fires_on_zero_python_modules(tmp_path: Path) -> None:
    """CONTROL — **the empty case** for the count limb.

    A root with no module has no projection at all, and a gate written *"no more
    than one"* would call that purer rather than broken.
    """
    empty = tmp_path / "no-modules"
    empty.mkdir()
    (empty / BINDING_DOCUMENT_NAME).write_text("plan: p.py:go\n", encoding="utf-8")

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(empty)

    assert "0 Python modules" in str(fired.value)


def test_the_shape_gate_fires_on_a_reference_in_a_data_position(
    deployment_root: Path,
) -> None:
    """CONTROL — a divergent root: a second reference under a permitted key.

    ``question.subject`` is a key the schema allows, so a count of modules and a
    check of key *names* both pass. This is the limb that sees it.
    """
    body = _document(deployment_root)
    body["question"]["subject"] = "projection.py:build_projection"
    _rewrite(deployment_root, body)

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(deployment_root)

    message = str(fired.value)
    assert "question.subject" in message
    assert "data position" in message


def test_the_shape_gate_fires_on_a_reference_nested_in_a_sequence(
    deployment_root: Path,
) -> None:
    """CONTROL — the same widening one level down, where a flat scan misses it."""
    body = _document(deployment_root)
    body["operator_parameter_keys"] = ["projection.py:build_projection"]
    _rewrite(deployment_root, body)

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(deployment_root)

    assert "operator_parameter_keys[0]" in str(fired.value)


def test_the_shape_gate_fires_when_the_document_names_no_projection(
    deployment_root: Path,
) -> None:
    """CONTROL — **the empty case** for the reference limb.

    A document carrying no reference at all passes *"nothing else is a
    reference"* perfectly. Without the positive limb, an empty ``binding.yaml``
    beside one Python module would be the purest possible pass.
    """
    body = _document(deployment_root)
    body["plan"] = "a plain string, naming nothing"
    _rewrite(deployment_root, body)

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(deployment_root)

    assert "states no `<module-path>:<attribute>` reference" in str(fired.value)


def test_the_shape_gate_fires_on_a_document_that_is_not_a_mapping(
    deployment_root: Path,
) -> None:
    """CONTROL — the unreadable subject, which must go red rather than quiet."""
    (deployment_root / BINDING_DOCUMENT_NAME).write_text(
        "- not\n- a\n- mapping\n", encoding="utf-8"
    )

    with pytest.raises(AssertionError) as fired:
        assert_the_deployment_is_data_and_one_projection(deployment_root)

    assert "not a mapping" in str(fired.value)


# ---------------------------------------------------------------------------
# The negative, driven END TO END — the narrowing holds where an adopter is.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ruled_out", sorted(RULED_OUT_KEYS))
def test_a_ruled_out_key_is_refused_end_to_end_not_only_at_the_loader(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch, ruled_out: str
) -> None:
    """A deployment carrying the rejected shape cannot answer a question.

    **Driven through** :meth:`~ccf.client.client.ProductClient.ask`, which is
    the point. ``17-12`` proved the loader refuses; a loader whose refusal is
    caught, defaulted around, or simply never reached on the path a client takes
    is a gate wired to nothing — the defect this phase has now met six times.

    Parameterized over :data:`~ccf.client.adapters.binding_document.RULED_OUT_KEYS`
    rather than over ``resolver`` alone, so a third ruled-out key gets its own
    end-to-end control the day it is named.
    """
    body = _document(seeded_root)
    body[ruled_out] = "projection.py:build_projection"
    _rewrite(seeded_root, body)

    client = _bound_client(seeded_root, monkeypatch)

    with pytest.raises(BindingError) as refused:
        client.ask(parameters={THRESHOLD: 20})

    message = str(refused.value)
    assert f"`{ruled_out}`" in message
    assert "ruled out" in message
    assert "2026-08-16-reference-plan-factory-and-debt-scorer" in message


def test_a_reference_smuggled_into_a_data_key_is_refused_end_to_end(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other half of the narrowing, also through ``ask``.

    Refusing ruled-out key *names* cannot see a reference arriving under a key
    the schema permits. Both refusals exist for that reason, and both are worth
    reaching from the end of the chain rather than from the loader's own
    doorstep.
    """
    body = _document(seeded_root)
    body["question"]["intent"] = "projection.py:build_projection"
    _rewrite(seeded_root, body)

    client = _bound_client(seeded_root, monkeypatch)

    with pytest.raises(BindingError) as refused:
        client.ask(parameters={THRESHOLD: 20})

    assert "question.intent" in str(refused.value)
    assert "data** position" in str(refused.value)


def test_a_debt_key_naming_no_control_plane_section_is_refused_end_to_end(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`17-13` moved the λ_c lookup behind the helper; the voice survived.

    ``build_governed_resolver`` raises
    :class:`~ccf.products.resolver.ProductNotResolvable`, which names a
    *manifest* key. At boot every key it could miss was written in
    ``binding.yaml``, so the adapter translates rather than letting an adopter
    infer which document to edit — and the translated refusal is still a
    :class:`~ccf.client.errors.TransportError`, so one ``except`` clause covers
    every way the wire never spoke.
    """
    body = _document(seeded_root)
    body["debt"]["half_life_key"] = "no-such-section"
    _rewrite(seeded_root, body)

    client = _bound_client(seeded_root, monkeypatch)

    with pytest.raises(BindingError) as refused:
        client.ask(parameters={THRESHOLD: 20})

    message = str(refused.value)
    assert isinstance(refused.value, TransportError)
    assert "no-such-section" in message
    assert BINDING_DOCUMENT_NAME in message


def test_the_unmutated_deployment_still_answers(
    seeded_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control every refusal above depends on.

    Each of them asserts that a *mutated* deployment fails. An expectation of
    failure is satisfied by any breakage at all — including a fixture that never
    answered in the first place — so the unmutated copy is driven down the same
    path and required to succeed.
    """
    result = _bound_client(seeded_root, monkeypatch).ask(
        parameters={THRESHOLD: 20}
    )

    assert not result.refused
    assert len(result.content_address) == 64
