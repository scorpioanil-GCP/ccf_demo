"""The declared payload schema of a product class, and its one comparison.

SDK-defined; the rulings of record are ``docs/DECISIONS.md`` **D-IMPL-97**
(ruling 1 — a Context Product is one standardised vessel whose domain payload
is disciplined by a *declared schema* the class registers), **D-IMPL-102**
(where the two checks land), and **D-IMPL-103** (the schema shape). CLAUDE.md
§11 requires an SDK extension to cite this project's own record rather than
the whitepaper, and this is an extension: whitepaper §7.6 read the payload as
carried by a per-product subclass, and D-IMPL-97 corrected the wording — *"a
wording correction to §7.6, not a reversal of it"* — without reversing its
intent, which was a typed payload with the cross-cutting invariants living
once on the base.

**The payload was the substantive gap the vessel model exposed.**
``ContextProductContract.payload`` is a ``Mapping[str, Any]``. Under a class
hierarchy that was tolerable, because a per-product subclass could type it;
under one standardised vessel, nothing types it unless the class *declares*
what it must look like. This module is that declaration and the comparison
that reads it.

**Where the two checks land, and where they deliberately do not (D-IMPL-102).**
Dave ruled, verbatim: *"Schema validity at registration + payload conformity
at Bind (request time). Gate scripts remain structural only."* Three parts,
and the third is as load-bearing as the first two:

1. **Schema validity at registration.** A malformed *declaration* is refused
   at wiring time, before any request exists. Enforced structurally rather
   than by a check that could be forgotten: a malformed
   :data:`ProductPayloadSchema` cannot be constructed at all, and
   :func:`~ccf.products.contract.register_product_class` refuses an artifact
   registered under a class's payload-schema key that is not one.
2. **Payload conformity at bind — request time.** The actual payload meets the
   class's declared schema where a request binds to a class, which is the
   surface D-IMPL-98's typed request contract creates. That limb is plan
   ``15.5-09``'s and this module supplies the comparison it calls.
3. **No fourth gate.** The three shipped validation gates — the empty-operator
   guard, lineage strict equality, TTL bounds — stay at three, and nothing
   here is added to :func:`ccf.products.gates.run_gates`. The whitepaper's
   three-validation-gate commitment is kept intact rather than widened, and
   :class:`PayloadSchemaViolation` therefore deliberately does **not** derive
   from :class:`~ccf.products.gates.GateRefusal`: it is not a gate verdict and
   must not be able to travel as one.

**One comparison, two call sites, on purpose.** :func:`refuse_payload` is a
single pure function for the same reason
:func:`~ccf.products.gates.refuse_attestation` is: registration-time binding
and request-time checking must not drift into two readings of "conforms".

**The refusal is a returned value, not an exception** — the posture
``ccf.products.gates`` states at its own head: *"A refusal returned as data
cannot be swallowed by a bare except"*. A payload that does not match its
declared schema is a bad **product**, not a broken deployment, and this tree
reports those differently.

**Bounding the MCP analogy, because it is easy to over-apply.** The declared
schema is MCP-shaped in its *typing discipline* — it is literally the shape
MCP tools declare ``inputSchema`` in, rendered by the same one derivation. It
is not "just MCP": MCP carries no governance semantics, being a capability and
transport standard, whereas the vessel this schema disciplines carries the
policy versions in force, lineage that must strictly equal what ran, a
freshness SLA, debt, and a replay record that must exist before delivery.
MCP-shaped in typing, with a governance envelope MCP has no equivalent for.

This module holds no property name, no domain type mapping and no threshold
of any kind (CLAUDE.md §11, CINV-01). The JSON Schema type names it compares
against are the mechanism's own closed vocabulary, not anybody's data model.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any, Literal

from ccf.contracts.base import CCFContract
from ccf.skills.catalog import (
    JsonSchemaType,
    SkillArgumentMember,
    SkillArgumentProperty,
    SkillArgumentSchema,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "PayloadSchemaViolation",
    "PayloadViolationReason",
    "ProductPayloadSchema",
    "refuse_payload",
]

#: A product class's declared payload schema — :class:`
#: ~ccf.skills.catalog.SkillArgumentSchema` itself, under a name that says
#: what it is doing here.
#:
#: **An alias, never a copy** (D-IMPL-103, branch (i), Dave 2026-08-11):
#: *"Extend SkillArgumentSchema in place ... the change is a widening, not a
#: replacement."* The alternative the ruling declined — a nesting-capable
#: sibling declared here — was measured at five duplicated symbols, which is
#: the second machinery D-IMPL-97 explicitly asked this work not to invent.
#: ``ProductPayloadSchema is SkillArgumentSchema`` is therefore ``True``, and
#: a test asserts it rather than a comment claiming it.
ProductPayloadSchema = SkillArgumentSchema

#: Why a payload did not conform. Three reasons because there are three ways a
#: closed, typed, partially-required declaration can be missed, and naming
#: which one happened is what lets a caller act without re-deriving anything.
PayloadViolationReason = Literal[
    "undeclared-key", "missing-required-key", "type-mismatch"
]


class PayloadSchemaViolation(CCFContract):
    """A payload does not match the schema its product class declared.

    Deliberately **not** a :class:`~ccf.products.gates.GateRefusal`. Under
    D-IMPL-102 no payload gate joins ``run_gates``, and a violation that
    inherited the gate refusal type could be returned from the gate path by a
    later caller who assumed the type meant it belonged there. The type keeps
    the shipped three-gate commitment true structurally rather than by
    convention.

    Both sides of the comparison are carried, in the
    :class:`~ccf.products.gates.AttestationRefusal` voice: a caller reading
    this never re-derives either side to learn what the gap was.

    Attributes:
        reason: Which of the three ways the payload missed.
        key: Where, as a path. A nested member reads ``parent.member``; an
            element of a declared list reads ``parent[].member``. A path
            rather than a bare name because D-IMPL-103's widening made
            "which key" ambiguous at one level down.
        declared_type: The JSON Schema type declared at ``key``, or ``None``
            when the reason is not a type mismatch.
        presented_type: The Python type name the payload presented at ``key``,
            or ``None`` for the same reason.
        declared_keys: Every key the schema declares **at the level the
            violation occurred**, so an undeclared key is readable against
            the set it was not in.
        presented_keys: Every key the payload presented at that same level.
        detail: The human-readable statement, for the operator reading a log.
            The typed fields above are the machine-readable version.
    """

    reason: PayloadViolationReason
    key: str
    declared_type: str | None
    presented_type: str | None
    declared_keys: frozenset[str]
    presented_keys: frozenset[str]
    detail: str


def _matches(declared: JsonSchemaType, value: object) -> bool:
    """Does one value satisfy one declared JSON Schema type?

    Two readings are deliberate and both are stated where they are made:

    * ``bool`` is not an ``integer`` and not a ``number``. It subclasses
      ``int`` in Python and does not in JSON Schema, and the language's
      accident is not the contract's meaning.
    * ``float`` is not a ``number`` **in this tree**.
      :mod:`ccf.contracts.canonical` refuses ``float`` outright, because
      binary floating point is not bit-stable across platforms, so admitting
      one here would declare conformant a payload that cannot reach a content
      address. ``int`` and ``Decimal`` are this fabric's numeric forms.
    """
    if declared == "boolean":
        return isinstance(value, bool)
    if isinstance(value, bool):
        # Checked before the numeric branches, for the reason above.
        return False
    if declared == "string":
        return isinstance(value, str)
    if declared == "integer":
        return isinstance(value, int)
    if declared == "number":
        return isinstance(value, (int, Decimal))
    if declared == "array":
        return isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        )
    return isinstance(value, Mapping)


def _refuse_shape(
    *,
    presented: Mapping[str, Any],
    declared: Mapping[str, JsonSchemaType],
    required: tuple[str, ...],
    path: str,
) -> PayloadSchemaViolation | None:
    """One object level: closed world, required keys, declared types.

    Takes the declared **types** rather than the declared specs, so the one
    function serves the root, a nested object and a list element identically
    — the levels differ in what they may declare *below* them, never in what
    conformance means at the level itself.

    The order is fixed — undeclared keys, then missing required keys, then
    type mismatches — and every scan is over ``sorted`` names, so the refusal
    a given (payload, schema) pair produces does not depend on the order the
    payload's keys happened to be built in. A comparison whose verdict moved
    with insertion order would be a comparison replay could not reproduce.
    """
    declared_keys = frozenset(declared)
    presented_keys = frozenset(presented)

    for name in sorted(presented_keys - declared_keys):
        return PayloadSchemaViolation(
            reason="undeclared-key",
            key=f"{path}{name}",
            declared_type=None,
            presented_type=type(presented[name]).__name__,
            declared_keys=declared_keys,
            presented_keys=presented_keys,
            detail=(
                f"payload key {path + name!r} is not declared by the product"
                f" class's payload schema, which declares"
                f" {sorted(declared_keys)}; the declared world is closed"
                " (D-IMPL-97, D-IMPL-103)"
            ),
        )

    for name in sorted(set(required) - presented_keys):
        return PayloadSchemaViolation(
            reason="missing-required-key",
            key=f"{path}{name}",
            declared_type=declared[name],
            presented_type=None,
            declared_keys=declared_keys,
            presented_keys=presented_keys,
            detail=(
                f"payload is missing required key {path + name!r}, declared"
                f" {declared[name]!r} by the product class's payload schema;"
                f" the payload presents {sorted(presented_keys)}"
            ),
        )

    for name in sorted(presented_keys & declared_keys):
        value = presented[name]
        if not _matches(declared[name], value):
            return PayloadSchemaViolation(
                reason="type-mismatch",
                key=f"{path}{name}",
                declared_type=declared[name],
                presented_type=type(value).__name__,
                declared_keys=declared_keys,
                presented_keys=presented_keys,
                detail=(
                    f"payload key {path + name!r} is declared"
                    f" {declared[name]!r} and presented"
                    f" {type(value).__name__!r}"
                ),
            )

    return None


def _member_types(
    properties: Mapping[str, SkillArgumentMember],
) -> dict[str, JsonSchemaType]:
    return {name: member.type for name, member in properties.items()}


def _refuse_below(
    *, spec: SkillArgumentProperty, value: object, path: str
) -> PayloadSchemaViolation | None:
    """Descend into one already-type-checked property, if it declares below.

    A property that declares neither ``properties`` nor ``items`` has nothing
    below it — which is why a declaration written before the D-IMPL-103
    widening is checked exactly as it was checked before, by
    :func:`_refuse_shape` alone.

    The descent is one level and stops there because the *types* stop there:
    :class:`~ccf.skills.catalog.SkillArgumentMember` has no nesting fields at
    all, so there is no third level to walk.
    """
    if spec.properties is not None and isinstance(value, Mapping):
        return _refuse_shape(
            presented=value,
            declared=_member_types(spec.properties),
            required=spec.required,
            path=f"{path}.",
        )
    if spec.items is None or isinstance(value, (str, bytes, bytearray)):
        return None
    if not isinstance(value, Sequence):
        return None
    element_spec = spec.items
    for element in value:
        if not _matches(element_spec.type, element):
            return PayloadSchemaViolation(
                reason="type-mismatch",
                key=f"{path}[]",
                declared_type=element_spec.type,
                presented_type=type(element).__name__,
                declared_keys=frozenset(),
                presented_keys=frozenset(),
                detail=(
                    f"an element of payload list {path!r} is declared"
                    f" {element_spec.type!r} and presented"
                    f" {type(element).__name__!r}"
                ),
            )
        if element_spec.properties is None or not isinstance(element, Mapping):
            continue
        violation = _refuse_shape(
            presented=element,
            declared=_member_types(element_spec.properties),
            required=element_spec.required,
            path=f"{path}[].",
        )
        if violation is not None:
            return violation
    return None


def refuse_payload(
    *,
    payload: Mapping[str, Any],
    declared: ProductPayloadSchema,
) -> PayloadSchemaViolation | None:
    """The one payload-conformity comparison — shared by both D-IMPL-102 limbs.

    Called by the registration-time binding in
    :func:`~ccf.products.contract.register_product_class`'s neighbourhood
    (limb 1, where a class declares the schema a payload will later be held
    to) and by the bind-time conformity check on the typed request surface
    D-IMPL-98 creates (limb 2, plan ``15.5-09``). One function, so the two
    layers cannot drift into two readings of "conforms" — the reason
    :func:`~ccf.products.gates.refuse_attestation` is one function.

    Pure over its arguments: no I/O, no clock, no query, no registry lookup.
    A conformity verdict that moved with the time of day or with what was
    registered elsewhere would not be reproducible at replay, which is the
    one property every comparison in this package is required to have.

    Returns:
        ``None`` when the payload matches the declaration at every level,
        otherwise the :class:`PayloadSchemaViolation` naming the first
        failure in the fixed undeclared-then-missing-then-mistyped order,
        carrying both sides of the comparison that failed.
    """
    shape = _refuse_shape(
        presented=payload,
        declared={
            name: spec.type for name, spec in declared.properties.items()
        },
        required=declared.required,
        path="",
    )
    if shape is not None:
        return shape
    for name in sorted(frozenset(payload) & frozenset(declared.properties)):
        below = _refuse_below(
            spec=declared.properties[name], value=payload[name], path=name
        )
        if below is not None:
            return below
    return None
