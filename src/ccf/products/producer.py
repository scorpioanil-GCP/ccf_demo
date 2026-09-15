"""The producer assertion a door stamps on its answers (`D-IMPL-340`).

Its own module, below :mod:`ccf.products.door` and :mod:`ccf.products.composite`
alike, because both need the type and the door imports the refusal module,
which imports the composite: a contract this small must not be the reason two
layers import each other. Algorithmic module (CINV-03).
"""

from __future__ import annotations

from ccf.contracts.base import CCFContract

__all__ = ["ProducerAssertion"]


class ProducerAssertion(CCFContract):
    """Who a door says it is, stamped on the answer (`D-IMPL-340`, ruling 2).

    Two values the *deployment* passed to its door builder — a producer
    identity and the tenant the producer governs under — so a consumer can hold
    the answer to the registration it resolved. **A claim, never an
    authority**: the consumer's expectation comes from its own governed
    producer registration, and this assertion can only *fail* to match it. A
    payload cannot authorize itself by claiming the expected producer.
    """

    producer_id: str
    tenant_id: str
