"""The operator registry: what a fabric may run, and under what identity.

Whitepaper §7.4 (INV-CH7-29 — an operator key is unique within a fabric);
DESIGN.md §2B.1; D-IMPL-37 (explicit boot-time registration, never import side
effects).

Registration is an explicit call at the composition root. No entry points, no
decorators, no import side effects — a registry populated by imports has a
population that depends on import order, and an operator plan is only
deterministic if the registry it resolves against is.

**The registry records metadata, not just the callable.** Each registration
carries the operator's category, its declared parameter *schema* class, and the
version the deployment assigned it. That triple is what lets the planner order
by category without asking the operator at plan time, lets the CLI and the
Control Plane describe the fabric's operator surface without instantiating
anything, and lets a replay say which parameter contract was in force — not
merely which values it held.

**Append-only, like the Control Plane it mirrors.** There is no ``unregister``
and no overwrite: a duplicate key is fatal at boot rather than a silent
last-writer-wins. Two operators answering to one key means every plan naming it
is ambiguous, and keeping one of them makes the ambiguity invisible.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from dataclasses import dataclass

from ccf.operators.base import (
    CATEGORY_ORDER,
    Operator,
    OperatorCategory,
    OperatorParameters,
)

__ccf_mode__ = "algorithmic"

__all__ = [
    "DuplicateOperatorKey",
    "OperatorRegistration",
    "OperatorRegistry",
    "UnregisteredOperator",
]


class DuplicateOperatorKey(ValueError):
    """An operator key was registered twice (INV-CH7-29 — a boot failure)."""


class UnregisteredOperator(LookupError):
    """A plan declared an operator key the registry does not hold."""


@dataclass(frozen=True)
class OperatorRegistration:
    """One registered operator together with the metadata plans resolve against.

    Attributes:
        key: Registry identity, unique within a fabric (INV-CH7-29).
        category: Canonical category, which fixes the operator's position in
            the dependency order (INV-CH7-28).
        parameters_schema: The declared parameter *contract class* in force —
            the type, not the values. Recorded so the fabric's parameter
            surface is describable without instantiating an operator, and so a
            replay can name the contract a decision's parameters validated
            against.
        version: The version the deployment assigned this operator, or ``None``
            where it assigned none. ``None`` is a positive statement — "this
            deployment did not version this operator" — and never a placeholder
            the SDK invented, which is why it is not the string ``"0"`` or
            ``"unknown"``.
        operator: The registered instance itself.
    """

    key: str
    category: OperatorCategory
    parameters_schema: type[OperatorParameters]
    version: str | None
    operator: Operator


class OperatorRegistry:
    """Boot-time operator registry with fail-fast duplicate detection."""

    def __init__(self) -> None:
        self._registrations: dict[str, OperatorRegistration] = {}

    def register(self, operator: Operator, *, version: str | None = None) -> None:
        """Register ``operator`` under its own key.

        The category and parameter schema are read off the operator rather than
        passed in: a registration that could declare a category different from
        the one the operator reports would let the planner order an operator
        into a position it does not belong in, which is precisely the
        Policy-after-Similarity failure INV-CH7-26 forbids.

        Raises:
            DuplicateOperatorKey: the key is already registered. Deliberately
                fatal: two operators answering to one key means every plan
                naming it is ambiguous, and silently keeping one of them makes
                the ambiguity invisible.
        """
        if operator.key in self._registrations:
            raise DuplicateOperatorKey(
                f"operator key {operator.key!r} is already registered"
            )
        if operator.category not in CATEGORY_ORDER:
            raise ValueError(
                f"operator {operator.key!r} reports category "
                f"{operator.category!r}, which is not one of the four canonical "
                f"categories {CATEGORY_ORDER}"
            )
        self._registrations[operator.key] = OperatorRegistration(
            key=operator.key,
            category=operator.category,
            parameters_schema=type(operator.parameters),
            version=version,
            operator=operator,
        )

    def resolve(self, key: str) -> Operator:
        """Return the operator registered under ``key``.

        Raises:
            UnregisteredOperator: nothing is registered under ``key``.
        """
        return self.registration(key).operator

    def registration(self, key: str) -> OperatorRegistration:
        """Return the full registration recorded under ``key``.

        Raises:
            UnregisteredOperator: nothing is registered under ``key``.
        """
        try:
            return self._registrations[key]
        except KeyError:
            raise UnregisteredOperator(
                f"no operator registered under {key!r}"
            ) from None

    def keys(self) -> tuple[str, ...]:
        """Every registered key, sorted — introspection for the CLI and tests."""
        return tuple(sorted(self._registrations))

    def registrations(self) -> tuple[OperatorRegistration, ...]:
        """Every registration, in canonical dependency then key order.

        The same total order the planner imposes, so "what can this fabric run"
        and "in what order would it run" are answered by one enumeration rather
        than by two that could drift apart.
        """
        return tuple(
            sorted(
                self._registrations.values(),
                key=lambda entry: (CATEGORY_ORDER.index(entry.category), entry.key),
            )
        )

    def by_category(self, category: OperatorCategory) -> tuple[OperatorRegistration, ...]:
        """Every registration in ``category``, in key order."""
        return tuple(
            entry for entry in self.registrations() if entry.category == category
        )

    def __contains__(self, key: object) -> bool:
        return key in self._registrations

    def __len__(self) -> int:
        return len(self._registrations)
