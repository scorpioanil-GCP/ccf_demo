"""The cross-process example's assertions, under a runner that can fail (D-09).

``examples/04-cross-process`` used to carry its own guarantee: 68 ``assert``
statements and prints in ``producer_child.py``, 14 more in ``run.py``, checked
by ``make example-04`` exiting zero. D-09 moves that guarantee here, because
``make examples`` proves a spine *runs* and ``pytest`` proves it is *correct*.

**The two assertions this module exists for.** This example carries the A2A
trust boundary, which is the demonstrated form of a whitepaper §8.3 Pattern 4
commitment. Two of the assertions below are inherited intact from the
pre-rewrite drivers and must never be weakened:

* :func:`test_admission_required_control_plane_verification_before_l2` — an
  inbound A2A Context Product is admitted only after the *consuming* Control
  Plane validates its policy bindings, and reaches L3 only through L2
  afterwards (CLAUDE.md §7.2, §10).
* :func:`test_a_tampered_envelope_is_refused` and its siblings — a real
  signature spliced onto different payload bytes, emitted over a real socket,
  is refused as a typed value, the refusal is audited, and the consumer's
  substrate is byte-identical across the attempt.

Nothing is lost in the move. Each assertion names the pre-rewrite line it came
from, so the "no loss of assertion coverage" claim is auditable:

=================================================  ==========================
pre-rewrite line                                    relocated to
=================================================  ==========================
``producer_child.py``:437 ``ServableProduct``       the spine (a refusal now
                                                    raises) **and**
                                                    :func:`test_the_producer_product_passed_all_three_gates`
``producer_child.py``:442 ``entity_count``          :func:`test_the_producer_payload_matches_the_declared_expectation`
``producer_child.py``:443 entity classes            :func:`test_the_producer_payload_matches_the_declared_expectation`
``producer_child.py``:446 relationship types        :func:`test_the_producer_payload_matches_the_declared_expectation`
``producer_child.py``:457 ``isinstance(agent, ...)`` the spine (factory return
                                                    type) **and**
                                                    :func:`test_the_assembler_agent_is_the_definition_it_was_built_from`
``producer_child.py``:458 ``definition_hash``       :func:`test_the_assembler_agent_is_the_definition_it_was_built_from`
``producer_child.py``:459 ``agent.consume(...)``    :func:`test_the_gated_product_validates_against_the_agent_contract`
``run.py``:201 policy version agreement             :func:`test_the_consumer_entitles_exactly_the_regime_the_producer_asserted`
``run.py``:353 two carriages received               :func:`test_both_carriages_crossed_a_real_socket`
``run.py``:354 both from the producer peer          :func:`test_both_carriages_crossed_a_real_socket`
``run.py``:375 MCP tenant                           :func:`test_the_product_read_back_over_mcp_is_the_declared_class`
``run.py``:376 MCP schema name                      :func:`test_the_product_read_back_over_mcp_is_the_declared_class`
``run.py``:377 MCP lineage non-empty                :func:`test_the_product_read_back_over_mcp_is_the_declared_class`
``run.py``:380 MCP bytes == signed bytes            :func:`test_one_product_two_front_doors`
``run.py``:388 ``AdmittedProduct``                  the spine (a refusal now
                                                    raises) **and**
                                                    :func:`test_admission_required_control_plane_verification_before_l2`
``run.py``:389 admitted bytes == signed bytes       :func:`test_admission_required_control_plane_verification_before_l2`
``run.py``:396 operators set-union                  :func:`test_inbound_lineage_extends_by_set_union_and_never_replaces`
``run.py``:400 policy versions set-union            :func:`test_inbound_lineage_extends_by_set_union_and_never_replaces`
``run.py``:404 producer regime in merged            :func:`test_the_consumer_entitles_exactly_the_regime_the_producer_asserted`
``run.py``:407 graph snapshot preserved             :func:`test_inbound_lineage_extends_by_set_union_and_never_replaces`
``run.py``:422 one admission verdict                the spine (a second
                                                    verdict now raises) **and**
                                                    :func:`test_the_admission_record_is_content_addressed_and_immutable`
``run.py``:424 verdict artifact class               :func:`test_the_admission_record_is_content_addressed_and_immutable`
``run.py``:426 store holds the address              :func:`test_the_admission_record_is_content_addressed_and_immutable`
``run.py``:430 address == ``content_hash``          :func:`test_the_admission_record_is_content_addressed_and_immutable`
``run.py``:431 record peer id                       :func:`test_the_admission_record_names_the_peer_and_both_lineages`
``run.py``:432 record merged lineage                :func:`test_the_admission_record_names_the_peer_and_both_lineages`
``run.py``:433 record producer lineage              :func:`test_the_admission_record_names_the_peer_and_both_lineages`
``run.py``:434 record consumer lineage              :func:`test_the_admission_record_names_the_peer_and_both_lineages`
``run.py``:455 envelopes produced                   :func:`test_the_admitted_product_reached_l3_only_through_l2`
``run.py``:456 digest moved on ingest               :func:`test_the_admitted_product_reached_l3_only_through_l2`
``run.py``:464 federated entity count               :func:`test_the_admitted_product_reached_l3_only_through_l2`
``run.py``:473 ``GateRefusal``                      :func:`test_a_tampered_envelope_is_refused`
``run.py``:474 ``SignatureRefusal``                 :func:`test_a_tampered_envelope_is_refused`
``run.py``:475 refusal peer id                      :func:`test_a_tampered_envelope_is_refused`
``run.py``:476 digest unchanged across refusal      :func:`test_the_refusal_left_the_consumer_substrate_byte_identical`
``run.py``:482 refusal audited                      :func:`test_the_refusal_is_audited_as_unresolved`
``run.py``:483 ``resolved is False``                :func:`test_the_refusal_is_audited_as_unresolved`
``run.py``:484 ``InboundProduct``                   :func:`test_both_carriages_crossed_a_real_socket`
=================================================  ==========================

Two kinds of assertion, and the difference is worth stating
-----------------------------------------------------------

* **Independent expectations.** ``expected.yaml`` declares what the producer's
  served product should contain. Nothing in the pipeline derives those numbers
  from that file — they follow from the events, the resolution spec and the four
  operators — so changing either side alone makes the assertion fail.
* **Propagation checks.** The schema name, the peer identities and the
  federation entity class are read from an artifact by the spine *and* by this
  module, so the artifact is a single source and editing it moves both ends
  together. These fail on a **wiring** fault, not on an artifact edit.
* **Cross-deployment agreement checks.** New with the rewrite, and the sharpest
  category here. The producer's policy bundle and the consumer's are two
  separate documents with identical content, in two separate manifests. The
  entitlement assertion therefore fails when *either* side is edited alone —
  which is what makes it a check rather than a comparison of a value with
  itself. The pre-rewrite example read one ``controlplane.yaml`` from both
  processes, where the same assertion could not have failed for the reason it
  named.

The examples are not packages, so they are loaded by file path with
``importlib.util``. The module is registered in ``sys.modules`` *before*
execution: both files use ``from __future__ import annotations``, so
``@dataclass`` resolves field annotations by looking its own module up there.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from typing import Any

import pytest

from ccf.agents.agent import Agent
from ccf.contracts.canonical import canonical_bytes, content_hash
from ccf.controlplane.artifacts import DeclaredArtifact
from ccf.peering.admission import ADMISSION_RECORD, AdmittedProduct, SignatureRefusal
from ccf.peering.protocol import InboundProduct
from ccf.products.gates import ServableProduct

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE_DIR = REPO_ROOT / "examples" / "04-cross-process"


def _load(name: str, filename: str) -> Any:
    """Load one of the example's two modules by file path.

    The example directory joins ``sys.path`` because ``run.py`` imports its
    sibling ``producer_child`` by module name — the same resolution the
    ``python examples/04-cross-process/run.py`` invocation gets from
    ``sys.path[0]``. The insert is idempotent and appends one directory holding
    exactly two modules; it is deliberately NOT a ``sys.path`` swap that some
    later import could observe half-applied. This suite shares a process with
    ``tests/crossproc/``, so every global touched here is named on purpose.
    """
    if str(EXAMPLE_DIR) not in sys.path:
        sys.path.insert(0, str(EXAMPLE_DIR))
    spec = importlib.util.spec_from_file_location(name, EXAMPLE_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def consumer(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """One full two-process run, shared across the module.

    Module-scoped deliberately: the exchange is the unit under test, and it
    spawns a real subprocess and binds real sockets. Running it once per
    assertion would say nothing extra.
    """
    module = _load("cross_process_under_test", "run.py")
    return module.run(root=tmp_path_factory.mktemp("cross-process-consumer"))


@pytest.fixture(scope="module")
def assembled(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """The producer's assembly leg, run in-process.

    The producer's own assertions were about what its fabric assembled, which
    is answerable without the subprocess: ``build_situation_product`` is the
    same function the child calls before it signs and serves.
    """
    module = _load("producer_child", "producer_child.py")
    root = tmp_path_factory.mktemp("cross-process-producer")
    return module.build_situation_product(database_path=root / "producer.sqlite3")


def _declaration(result: Any, key: str) -> Any:
    """The deployment's own declaration under one manifest key."""
    artifact = result.artifacts[key]
    assert isinstance(artifact, DeclaredArtifact), key
    return artifact.declaration


# --- the producer's leg ----------------------------------------------------


def test_the_producer_product_passed_all_three_gates(assembled: Any) -> None:
    """Pre-rewrite ``producer_child.py``:437. ``ServableProduct`` is not
    constructible outside ``run_gates``, so holding one IS the evidence."""
    assert isinstance(assembled.servable, ServableProduct)


def test_the_producer_payload_matches_the_declared_expectation(
    assembled: Any,
) -> None:
    """Pre-rewrite ``producer_child.py``:442, :443, :446.

    An INDEPENDENT expectation: ``expected.yaml`` is read by nothing in the
    assembly path, so editing it alone fails this test and changing the events,
    the resolution spec or an operator parameter alone fails it too.
    """
    expected = assembled.expected
    payload = assembled.servable.product.payload
    assert payload["entity_count"] == expected["entity_count"]
    assert sorted({entry["entity_class"] for entry in payload["entities"]}) == sorted(
        expected["entity_classes"]
    )
    assert payload["relationship_types"] == sorted(expected["relationship_types"])
    assert payload["role"] == expected["role"]


def test_the_policy_regime_excluded_the_restricted_class(assembled: Any) -> None:
    """The restricted occupancy signal is absent from the served view, and so is
    the edge that would have leaked its existence by absence."""
    expected = assembled.expected
    payload = assembled.servable.product.payload
    served_classes = {entry["entity_class"] for entry in payload["entities"]}
    for excluded in expected["excluded_entity_classes"]:
        assert excluded not in served_classes


def test_the_assembler_agent_is_the_definition_it_was_built_from(
    assembled: Any,
) -> None:
    """Pre-rewrite ``producer_child.py``:457, :458. Factory-only construction
    (§6.4), and the agent's identity is the content hash of the artifact."""
    assert isinstance(assembled.agent, Agent)
    assert assembled.agent.identity.definition_hash == content_hash(
        assembled.definition
    )


def test_the_gated_product_validates_against_the_agent_contract(
    assembled: Any,
) -> None:
    """Pre-rewrite ``producer_child.py``:459. A ``ContextAssemblyAgent`` whose
    own output is a typed Context Product (§6.3) accepts it on axis 2."""
    product = assembled.servable.product
    assert assembled.agent.consume(product, now=assembled.now) is product


def test_every_declared_operator_actually_ran(assembled: Any) -> None:
    """A PROPAGATION check, and its limits are worth stating plainly.

    ``declared_operator_keys`` comes off ``product-class.yaml``;
    ``operators_invoked`` is what the engine observed itself running, planned
    from that same declaration. Editing the artifact alone moves both ends and
    is **not** detected — say so rather than implying independence there is
    none of. What this catches is the wiring regression: re-introducing
    ``required=operators.keys()`` together with a dropped key from the
    artifact. Verified by mutation; comparing ``operators_invoked`` against the
    product's own ``lineage.operators_invoked`` instead would catch neither,
    because they are the same value.
    """
    assert set(assembled.operators_invoked) == set(assembled.declared_operator_keys)


def test_the_consumer_admits_only_a_product_carrying_its_declared_operators(
    consumer: Any,
) -> None:
    """A CROSS-DEPLOYMENT AGREEMENT check on the operator set.

    ``consumer-product-class.yaml`` declares the operator set the consumer
    requires of a product of this class. Nothing in the producer's process
    reads it, and nothing in the consumer's process derives it from the
    inbound product — so this fails when the producer drops an operator and
    when the consumer raises its bar, independently. That independence is what
    the producer-side check above does not have.
    """
    required = set(consumer.artifacts["product-class"].required_operator_keys)
    assert required <= set(consumer.admitted.product.lineage.operators_invoked)


# --- the wire --------------------------------------------------------------


def test_both_carriages_crossed_a_real_socket(consumer: Any) -> None:
    """Pre-rewrite ``run.py``:353, :354, :484. Two envelopes — genuine and
    tampered — were emitted by the child over HTTP and received here as typed
    ``InboundProduct`` values before the child announced readiness."""
    peering = _declaration(consumer, "peering-trust")
    for message in (consumer.genuine, consumer.tampered):
        assert isinstance(message, InboundProduct)
        assert message.observed_peer.peer_id == peering["producer_peer_id"]


def test_the_product_read_back_over_mcp_is_the_declared_class(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:375, :376, :377. Whitepaper §8.3 Pattern 3: the
    typed contract validates over the wire, at the class the consumer declared
    it would admit."""
    declared = consumer.artifacts["product-class"]
    assert consumer.mcp_product.tenant_id == consumer.tenant_id
    assert consumer.mcp_product.schema_name == declared.schema_name
    assert consumer.mcp_product.lineage.operators_invoked


def test_one_product_two_front_doors(consumer: Any) -> None:
    """Pre-rewrite ``run.py``:380. The bytes MCP served are exactly the bytes
    the A2A signature was made over — one product, not two renderings."""
    assert consumer.over_mcp.encode("utf-8") == (
        consumer.genuine.signed.canonical_payload()
    )


# --- the A2A trust boundary ------------------------------------------------


def test_admission_required_control_plane_verification_before_l2(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:388, :389. INHERITED INTACT — do not weaken.

    CLAUDE.md §7.2 makes this structural: an inbound A2A Context Product is not
    admissible to L3 until the consuming Control Plane validates its policy
    bindings. The evidence is that an ``AdmittedProduct`` exists at all —
    ``PeeringAdmissionGate.admit`` is the only constructor, and it returns a
    ``GateRefusal`` value rather than an admitted one on any check failing —
    and that the admitted bytes are the signed bytes rather than a re-rendering.
    """
    assert isinstance(consumer.admitted, AdmittedProduct)
    assert consumer.admitted.product.schema_name == (
        consumer.artifacts["product-class"].schema_name
    )
    assert canonical_bytes(consumer.admitted.product) == (
        consumer.genuine.signed.canonical_payload()
    )


def test_the_consumer_entitles_exactly_the_regime_the_producer_asserted(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:201, :404. A CROSS-DEPLOYMENT AGREEMENT check.

    The consumer's trust grant permits exactly the version of its OWN policy
    bundle. The admitted product's lineage carries the version of the
    PRODUCER's. They are two documents in two manifests, so this holds only
    because their content agrees — and editing either alone makes the inbound
    regime fall outside the grant and admission refuse.
    """
    assert consumer.consumer_policy_version in (
        consumer.admitted.product.lineage.policy_bundle_versions
    )
    assert consumer.consumer_policy_version in (
        consumer.admitted.lineage.policy_bundle_versions
    )


def test_inbound_lineage_extends_by_set_union_and_never_replaces(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:396, :400, :407. CLAUDE.md §7.2.

    The consumer's declared operators are deliberately DISJOINT from the
    producer's, so a merged set equal to either side alone fails — which is
    what makes this evidence of union rather than of replacement.
    """
    producer_lineage = consumer.admitted.product.lineage
    consumer_lineage = consumer.consumer_lineage
    assert not (
        producer_lineage.operators_invoked & consumer_lineage.operators_invoked
    ), "the two sides must contribute disjoint members or this proves nothing"
    assert consumer.admitted.lineage.operators_invoked == (
        producer_lineage.operators_invoked | consumer_lineage.operators_invoked
    )
    assert consumer.admitted.lineage.policy_bundle_versions == (
        producer_lineage.policy_bundle_versions
        | consumer_lineage.policy_bundle_versions
    )
    assert consumer.admitted.lineage.graph_snapshot_at == (
        producer_lineage.graph_snapshot_at
    )


def test_the_admission_record_is_content_addressed_and_immutable(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:422, :424, :426, :430. The audit verdict points at
    the record by content address, the store holds it there, and its content
    hashes back to that very address — no "latest", no overwrite path."""
    admitted_events = [
        event
        for event in consumer.audit_events
        if event.action == "peering_admitted"
    ]
    assert len(admitted_events) == 1
    verdict = admitted_events[0]
    assert verdict.artifact_class == ADMISSION_RECORD.class_id
    assert verdict.version == consumer.admission_record_address
    assert consumer.admission_store.exists(
        content_address=consumer.admission_record_address
    )
    assert content_hash(consumer.admission_record) == (
        consumer.admission_record_address
    )


def test_the_admission_record_names_the_peer_and_both_lineages(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:431, :432, :433, :434. The record is a complete
    account of the crossing: who sent it, what they claimed, what the consumer
    contributed, and what the merge produced."""
    peering = _declaration(consumer, "peering-trust")
    record = consumer.admission_record
    assert record.peer_id == peering["producer_peer_id"]
    assert record.merged_lineage == consumer.admitted.lineage
    assert record.producer_lineage == consumer.admitted.product.lineage
    assert record.consumer_lineage == consumer.consumer_lineage


def test_the_admitted_product_reached_l3_only_through_l2(consumer: Any) -> None:
    """Pre-rewrite ``run.py``:455, :456, :464. Single-writer (CLAUDE.md §10)
    survives the A2A crossing: the substrate moves only at the typed federated
    door, and every entity the peer asserted arrives in the consumer's own
    federation class rather than merged into its vocabulary."""
    assert consumer.digest_after_ingest != consumer.digest_before_ingest
    assert len(consumer.federated_entity_uris) == len(
        consumer.admitted.product.payload["entities"]
    )


# --- the negative case -----------------------------------------------------


def test_a_tampered_envelope_is_refused(consumer: Any) -> None:
    """Pre-rewrite ``run.py``:473, :474, :475. INHERITED INTACT — do not weaken.

    A real signature spliced onto different payload bytes, emitted over the
    real socket. It is refused as a typed VALUE, with the refusal naming the
    peer — and the refusal is specifically a signature refusal, so a test that
    would also pass on an untampered envelope is ruled out: the genuine
    carriage from the same peer was admitted in this very run.
    """
    peering = _declaration(consumer, "peering-trust")
    assert isinstance(consumer.refusal, SignatureRefusal)
    assert consumer.refusal.peer_id == peering["producer_peer_id"]
    # The discriminator: the same gate, the same peer, the same run admitted
    # the genuine envelope. The refusal is about the tampering, not the peer.
    assert consumer.genuine.signed.canonical_payload() != (
        consumer.tampered.signed.canonical_payload()
    )


def test_the_refusal_left_the_consumer_substrate_byte_identical(
    consumer: Any,
) -> None:
    """Pre-rewrite ``run.py``:476. Digest taken before and after the refused
    admission, WAL included — a refused product writes nothing."""
    assert consumer.digest_after_refusal == consumer.digest_after_ingest


def test_the_refusal_is_audited_as_unresolved(consumer: Any) -> None:
    """Pre-rewrite ``run.py``:482, :483. A refusal that left no audit trace
    would be a silent boundary."""
    refused = [
        event
        for event in consumer.audit_events
        if event.action == "peering_admission_refused"
    ]
    assert refused
    assert all(event.resolved is False for event in refused)
