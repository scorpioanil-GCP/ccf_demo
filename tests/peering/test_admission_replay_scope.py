"""`SEC-022` residuals: the replay scope is the KEY, and the default seen-set is the process's.

Row ``SEC-022`` closed its replay defense for one gate and one observed peer id
(``tests/peering/test_admission_refuses_replay.py``). The owner's main-merge
record ``29a3c5a4`` held two residuals as "NOT accepted as closure evidence",
and both executed as admitted replays at ``8fceec83``:

* **SEC-022-C-01.** The nonce was scoped by the OBSERVED peer id
  (``src/ccf/peering/admission.py::PeeringAdmissionGate.admit``, the replay
  consult). A trust policy listing one signing key under two peer ids admitted
  the identical signed bytes once under each. **Ruling:** the replay key is
  scoped by the key the signature verified under, never by the observed or
  claimed peer id; the same signed bytes under an alias peer id with the same
  key are refused ``replayed``.
* **SEC-022-R1.** A second gate built with the DEFAULT seen-set admitted a
  replay the first gate had already admitted; sharing was a documented
  obligation, not an enforced one. **Ruling (executor's, for the owner to
  confirm — it changes Q14's "per gate" to "per process"):** the default is
  ONE seen-set shared by every gate in the process, behind the existing
  Protocol; an explicitly supplied seen-set still wins; a deployment whose
  receivers span processes must supply a shared implementation.

Both cases are written in the FIXED direction: each asserts the replay is
refused, so a failure names a residual that is present.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from joserfc.jwk import ECKey

from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.peering.admission import ADMISSION_RECORD, AdmittedProduct
from ccf.peering.identity import DetachedJwsIdentityProvider, JsonWebKey
from ccf.peering.protocol import InboundProduct, PeerRef
from ccf.peering.trust_policy import PeerTrustGrant
from ccf.products.contract import RegisteredProductClass

from tests.peering.issuance_fixture import issuance_member, window
from tests.peering.test_admission import (  # noqa: F401  (pytest fixtures)
    BOUNDARY,
    PEER_A,
    PEER_A_KID,
    PEER_A_PRODUCER,
    POLICY_REGIME,
    PRODUCER_ASSERTION_HEADER,
    PRODUCT_CLASS,
    TENANT,
    _gate,
    _register_ceiling,
    _register_policy,
    artifact_store,
    banking_product,
    consumer_lineage,
    key_dir,
    keys,
    product_class,
    provider,
    registry,
)

#: The refusal token the issuance check and the replay consult share.
GATE_ISSUANCE = "peering-issuance"

#: A second peer id the receiver's trust policy lists with peer A's own key.
PEER_ALIAS = "acme-bank-alias"


def _now() -> datetime:
    return BOUNDARY + timedelta(seconds=1)


def _signed_once(provider: DetachedJwsIdentityProvider) -> object:
    """One honest envelope signed by peer A's key, with a fresh nonce."""
    body = banking_product()
    assertions = {PRODUCER_ASSERTION_HEADER: PEER_A_PRODUCER}
    assertions.update(issuance_member(product=body, issued_at=BOUNDARY))
    return provider.sign(product=body, key_id=PEER_A_KID, assertions=assertions)


def _presented(signed: object, *, as_peer: str) -> InboundProduct:
    return InboundProduct(
        observed_peer=PeerRef(tenant_id=TENANT, peer_id=as_peer),
        signed=signed,  # type: ignore[arg-type]
    )


def _grant_over(document: JsonWebKey) -> PeerTrustGrant:
    """Peer A's entitlements, with ``document`` as the key under peer A's kid."""
    return PeerTrustGrant(
        signing_keys={PEER_A_KID: document},
        permitted_producer_hashes=frozenset({PEER_A_PRODUCER}),
        permitted_schema_names=frozenset({PRODUCT_CLASS["schema_name"]}),
        permitted_policy_regimes=frozenset({POLICY_REGIME}),
        **window(),
    )


def _as_written(key: ECKey) -> JsonWebKey:
    """The public JWK exactly as the primary grant writes it."""
    return dict(key.as_dict(private=False))


def _rewritten(key: ECKey) -> JsonWebKey:
    """The SAME key material, written with different non-key members.

    No ``kid`` member and an added ``use``: a different JWK document, the same
    key. A scope computed from the document rather than from the key would let
    the replay through here and nowhere else.
    """
    document = dict(key.as_dict(private=False))
    document.pop("kid", None)
    document["use"] = "sig"
    return document


def _events(registry: ControlPlaneRegistry, action: str) -> list[object]:
    return [e for e in registry.audit_events() if e.action == action]


# --- SEC-022-C-01: one key listed under two peer ids --------------------------


@pytest.mark.parametrize(
    "alias_rendering",
    [
        pytest.param(_as_written, id="same-jwk-document"),
        pytest.param(_rewritten, id="same-key-other-jwk-members"),
    ],
)
def test_c01_the_same_envelope_under_an_alias_peer_id_with_the_same_key_is_refused_replayed(
    alias_rendering: object,
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """The identical signed bytes, admitted as peer A, are refused as the alias.

    One gate, one trust policy listing peer A's key under two peer ids; the
    second presentation is observed as the alias, thirty seconds later, inside
    every window.
    """
    render = alias_rendering
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={
            PEER_A: _grant_over(_as_written(keys[PEER_A_KID])),
            PEER_ALIAS: _grant_over(render(keys[PEER_A_KID])),  # type: ignore[operator]
        },
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    gate = _gate(
        provider=provider,
        registry=registry,
        product_class=product_class,
        tenant_id=TENANT,
        policy_version=policy_version,
        ceiling_version=ceiling_version,
        artifact_store=artifact_store,  # type: ignore[arg-type]
    )
    signed = _signed_once(provider)

    first = gate.admit(
        inbound=_presented(signed, as_peer=PEER_A),
        consumer_lineage=consumer_lineage(),
        now=_now(),
    )
    assert isinstance(first, AdmittedProduct), first

    again = gate.admit(
        inbound=_presented(signed, as_peer=PEER_ALIAS),
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    assert not isinstance(again, AdmittedProduct), (
        "SEC-022-C-01: the identical signed bytes were ADMITTED a second time"
        f" under alias peer id {PEER_ALIAS!r}, signed by the same key"
        f" ({PEER_A_KID!r}), by the SAME gate"
    )
    assert getattr(again, "gate", None) == GATE_ISSUANCE, again
    assert getattr(again, "failure", None) == "replayed", again
    assert getattr(again, "peer_id", None) == PEER_ALIAS, again

    assert len(_events(registry, "peering_admitted")) == 1
    versions = artifact_store.versions(  # type: ignore[attr-defined]
        tenant_id=TENANT,
        artifact_class=ADMISSION_RECORD.class_id,
        name=first.content_address,
    )
    assert len(versions) == 1, versions


# --- SEC-022-R1: two gates, each with the default seen-set --------------------


def test_r1_a_second_gate_with_the_default_seen_set_refuses_the_replay_the_first_admitted(
    provider: DetachedJwsIdentityProvider,
    keys: dict[str, ECKey],
    registry: ControlPlaneRegistry,
    product_class: RegisteredProductClass,
    artifact_store: object,
) -> None:
    """Two receivers in one process, neither handed a seen-set: one admission.

    Both gates are built exactly as a composition that never heard of the
    seen-set would build them — no ``seen=`` — over the same Control Plane.
    """
    policy_version = _register_policy(
        registry,
        tenant_id=TENANT,
        peers={PEER_A: _grant_over(_as_written(keys[PEER_A_KID]))},
    )
    ceiling_version = _register_ceiling(registry, tenant_id=TENANT)
    gates = [
        _gate(
            provider=provider,
            registry=registry,
            product_class=product_class,
            tenant_id=TENANT,
            policy_version=policy_version,
            ceiling_version=ceiling_version,
            artifact_store=artifact_store,  # type: ignore[arg-type]
        )
        for _ in range(2)
    ]
    assert gates[0] is not gates[1]
    inbound = _presented(_signed_once(provider), as_peer=PEER_A)

    first = gates[0].admit(
        inbound=inbound, consumer_lineage=consumer_lineage(), now=_now()
    )
    assert isinstance(first, AdmittedProduct), first

    again = gates[1].admit(
        inbound=inbound,
        consumer_lineage=consumer_lineage(),
        now=_now() + timedelta(seconds=30),
    )
    assert not isinstance(again, AdmittedProduct), (
        "SEC-022-R1: a second gate built with the DEFAULT seen-set ADMITTED the"
        " identical signed bytes the first gate had already admitted"
    )
    assert getattr(again, "gate", None) == GATE_ISSUANCE, again
    assert getattr(again, "failure", None) == "replayed", again
    assert len(_events(registry, "peering_admitted")) == 1
