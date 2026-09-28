"""A default declared RELATIVE to the request's own ``asked_at`` (``D-IMPL-325``).

The gap this closes was measured in ``examples/cp-07-client-360-coverage-graph``
as ``CP07-F-03``. ``CP-SPEC-007`` §B.2 declares the ``since`` default as
**−365 days**; :attr:`~ccf.products.request.ProductRequestContract.defaults`
holds literal values, so the artifact could only carry the absolute
``"2024-09-01"`` — a value that **ages silently**. On the day it was written it
meant two years of history; a year on it means three, the fan-out grows, and
nothing anywhere says the default drifted. Computing it in the deployment is
strictly worse: a governance value back in code, and a second authority for one
bound (``D-IMPL-315``).

**What is proven here, and why each one is its own test.**

* **The declaration refuses what it cannot honor**, every offender named at
  once, on the ``defaults`` validator's own precedent: an undeclared name, an
  inert name, a name declared in ``defaults`` *and* here (two authorities for
  one bound), and a ``render`` the declared type cannot hold.
* **A non-negative offset refuses by name.** ``0`` is not a relative default —
  it is the literal ``asked_at``, and the message says to use ``defaults``.
* **Resolution reads ``request.asked_at`` and nothing else.** Held by a
  sabotage on a scratch copy of ``constraints.py``: a resolution that reached
  for a wall clock is GREEN on the tree and RED on the copy.
* **An explicit caller value still wins**, because a default is what omission
  means and never a competitor to a value the caller stated.
* **The computed value gets the normal domain and conformity check** — Dave's
  ruling against the option offered: *"a dynamic default can legitimately be
  refused at request time if the computed date falls outside its governed
  domain. That is not weaker governance; the value simply does not exist until
  ``asked_at`` exists."* And its converse, asserted separately: a relative
  default is **not** refused merely because a domain exists.
* **Replay records the resolved LITERAL**, with ``authority="default"`` and the
  contract's own pin — never the rule. Dave: *"Replay records the resolved
  absolute value and ``authority=default``, not a rule that gets recomputed
  later."*
* **The hash distinction Grok asked for, both halves.** Empty is transparent,
  so every contract written before this field keeps its content address; any
  populated mapping changes the hash, so two products with different
  relative-window rules cannot share one contract identity.

Every instant, offset, parameter name and date below is this module's own
fixture vocabulary. ``src/`` holds no window and no offset (CINV-01).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from ccf.contracts.canonical import content_hash, hash_transparent_fields
from ccf.products import constraints as constraints_module
from ccf.products.constraints import resolve_effective_request
from ccf.products.provenance import ProvenanceSource
from ccf.products.request import (
    ArgumentDomain,
    ProductRequest,
    ProductRequestContract,
    ProductRequestViolation,
    RelativeDefault,
)
from ccf.projection.plan import Perspective
from ccf.skills.catalog import SkillArgumentProperty, SkillArgumentSchema

CLASS_NAME = "fixture.windowed-product"
CLASS_VERSION = "1.0.0"
TENANT = "fixture-tenant"
INTENT = "fixture-intent"

#: The decision instant every expectation below is computed against. Stated
#: once, so no test carries a date this module did not derive.
INSTANT = datetime(2026, 9, 10, 14, 30, 0, tzinfo=UTC)

#: One fixture year, in the SDK's declared duration vocabulary — seconds, the
#: unit `HalfLifeEntry.half_life_seconds` already uses (`D-IMPL-325` ruling 2).
ONE_FIXTURE_YEAR = -31_536_000

SINCE = "since"
LABEL = "label"
DEPTH = "depth"

PERSPECTIVE = Perspective(principal_id="fixture-principal", role="fixture-role")
DECLARED_SOURCE = ProvenanceSource(
    kind="artifact", identity="contract-key", version="1.0.0"
)

CONSTRAINTS_SOURCE = pathlib.Path(constraints_module.__file__).read_bytes()


def _arguments() -> SkillArgumentSchema:
    """A string window bound, a string label, and an integer with a magnitude."""
    return SkillArgumentSchema(
        properties={
            SINCE: SkillArgumentProperty(
                type="string", description="the earliest date considered"
            ),
            LABEL: SkillArgumentProperty(
                type="string", description="a fixture label"
            ),
            DEPTH: SkillArgumentProperty(
                type="integer", description="a fixture depth"
            ),
        },
        required=(),
    )


def _contract(**overrides: Any) -> ProductRequestContract:
    fields: dict[str, Any] = {
        "semver": "1.0.0",
        "schema_name": CLASS_NAME,
        "schema_version": CLASS_VERSION,
        "arguments": _arguments(),
    }
    fields.update(overrides)
    return ProductRequestContract(**fields)


def _request(**parameters: Any) -> ProductRequest:
    return ProductRequest(
        schema_name=CLASS_NAME,
        schema_version=CLASS_VERSION,
        subject="fixture:subject/one",
        intent=INTENT,
        freshness="fixture-freshness",
        asked_at=INSTANT,
        parameters=parameters,
    )


def _resolve(
    contract: ProductRequestContract,
    request: ProductRequest,
    *,
    module: types.ModuleType | None = None,
) -> Any:
    target = module or constraints_module
    return target.resolve_effective_request(
        request=request,
        declared=contract,
        declared_source=DECLARED_SOURCE,
        constraints=(),
        capabilities=(),
        capability_bindings={},
        verified_overrides=(),
        perspective=PERSPECTIVE,
        tenant=TENANT,
        served_at=request.asked_at,
    )


def _effective(outcome: Any, name: str) -> Any:
    """The one resolved parameter named ``name``, off the evidence's tuple.

    :attr:`~ccf.products.provenance.EffectiveRequest.parameters` is a tuple
    rather than a mapping so the record has a declaration order and one
    canonical rendering, so a reader states which entry it means.
    """
    matches = [entry for entry in outcome.evidence.parameters if entry.name == name]
    assert len(matches) == 1, f"{name} resolved {len(matches)} times"
    return matches[0]


# --- (a) the declared shape --------------------------------------------------


def test_a_relative_default_declares_an_offset_and_a_render() -> None:
    """``D-IMPL-325``: ``offset_seconds: int`` and ``render: date | timestamp``.

    Asserted by field enumeration rather than described, because a later
    contributor adding a third field — a timezone, a rounding mode, a
    calendar — would be adding a second authority over one computed value.
    """
    assert set(RelativeDefault.model_fields) == {"offset_seconds", "render"}


@pytest.mark.parametrize("render", ["date", "timestamp"])
def test_both_declared_renders_are_accepted(render: str) -> None:
    RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render=render)


def test_a_render_the_contract_does_not_declare_refuses() -> None:
    """The closed world one level down: ``render`` is a Literal, not free text."""
    with pytest.raises(ValueError):
        RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="epoch")


@pytest.mark.parametrize("offset", [1, 86_400, 31_536_000])
def test_a_POSITIVE_offset_refuses(offset: int) -> None:
    """A default in the future describes no window a caller could have observed.

    This is the half of the original rule that survives ``D-IMPL-328``. The
    other half — that ``0`` refuses — was measured wrong from the other side
    and is now the identity offset; see the zero-offset section below.
    """
    with pytest.raises(ValueError) as refusal:
        RelativeDefault(offset_seconds=offset, render="date")
    assert "positive" in str(refusal.value)


# --- the identity offset (`D-IMPL-328`) --------------------------------------
#
# `0` was refused until `CP-SPEC-008` measured the original reading wrong from
# the other side. A bitemporal product's `as_of` and `known_as_of` default to
# *today* and *now* — the request's own instant, unchanged — and the literal
# `defaults` surface cannot express that, because any date written there ages
# (`CP07-F-03`). The two available moves were to admit `0` or to let the
# deployment inject `asked_at` in code; the second puts a governance value back
# in the spine (`D-IMPL-315`).
#
# **What must hold is that zero is ordinary.** Not a special case with its own
# path, its own authority, or its own replay treatment — the same branch, the
# same pin, the same recorded literal, with the arithmetic an identity.


def test_a_zero_offset_is_accepted_and_means_the_instant_unchanged() -> None:
    """The identity offset, and it is the whole point of ``D-IMPL-328``."""
    spec = RelativeDefault(offset_seconds=0, render="date")
    assert spec.resolve(INSTANT) == INSTANT.date().isoformat()
    assert RelativeDefault(offset_seconds=0, render="timestamp").resolve(
        INSTANT
    ) == INSTANT.isoformat()


def test_a_zero_offset_resolves_with_authority_default_like_any_other() -> None:
    """It is a DEFAULT, not a caller value and not a deployment-injected one.

    The authority is what a later examiner reads to know who decided the
    instant. A zero offset that resolved with any other authority — or with no
    provenance — would be `asked_at` smuggled in wearing a default's name.
    """
    contract = _contract(
        relative_defaults={SINCE: RelativeDefault(offset_seconds=0, render="date")}
    )
    outcome = _resolve(contract, _request())
    assert outcome.refusal is None
    resolved = _effective(outcome, SINCE)
    assert resolved.authority == "default"
    assert resolved.source == DECLARED_SOURCE
    assert resolved.value == INSTANT.date().isoformat()


def test_a_zero_offset_still_MOVES_with_the_question() -> None:
    """The property that makes it relative rather than a literal.

    A literal `defaults` entry holding today's date would answer the same
    string tomorrow. This must not: two instants, two values, from one
    declaration that never changed.
    """
    contract = _contract(
        relative_defaults={SINCE: RelativeDefault(offset_seconds=0, render="date")}
    )
    later = _request().model_copy(update={"asked_at": INSTANT + timedelta(days=9)})
    first = _effective(_resolve(contract, _request()), SINCE).value
    second = _effective(_resolve(contract, later), SINCE).value
    assert second > first


def test_a_zero_offset_records_the_resolved_literal_and_no_offset() -> None:
    """Replay carries the instant it served, never the rule — zero included."""
    from ccf.contracts.canonical import canonical_bytes  # noqa: PLC0415

    contract = _contract(
        relative_defaults={SINCE: RelativeDefault(offset_seconds=0, render="date")}
    )
    served = _resolve(contract, _request())
    assert _effective(served, SINCE).value == INSTANT.date().isoformat()
    rendered = canonical_bytes(served.evidence).decode("utf-8")
    assert "offset_seconds" not in rendered

    # And the control that separates "the rule is absent" from "nothing is
    # there": the resolved instant IS present, so the absence above is a claim
    # about the offset rather than about an empty record.
    assert INSTANT.date().isoformat() in rendered


def test_a_caller_value_still_beats_a_zero_offset() -> None:
    """Zero is a default, and a default never competes with a stated value."""
    contract = _contract(
        relative_defaults={SINCE: RelativeDefault(offset_seconds=0, render="date")}
    )
    stated = "2019-01-01"
    resolved = _effective(_resolve(contract, _request(**{SINCE: stated})), SINCE)
    assert resolved.authority == "caller"
    assert resolved.value == stated


def test_zero_and_a_negative_offset_are_two_contract_identities() -> None:
    """Admitting zero did not make it hash-invisible.

    A contract defaulting to the request instant and one defaulting to a year
    back are different governed questions and must not share an address.
    """
    identity = _contract(
        relative_defaults={SINCE: RelativeDefault(offset_seconds=0, render="date")}
    )
    year = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    assert content_hash(identity) != content_hash(year)
    assert content_hash(identity) != content_hash(_contract())


# --- (b) what the declaration refuses ----------------------------------------


def test_a_relative_default_for_an_undeclared_parameter_refuses() -> None:
    with pytest.raises(ValueError) as refusal:
        _contract(
            relative_defaults={
                "never_declared": RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                )
            }
        )
    assert "never_declared" in str(refusal.value)


def test_a_relative_default_for_an_inert_parameter_refuses() -> None:
    """A default for a parameter the tier step always refuses fills nothing."""
    with pytest.raises(ValueError) as refusal:
        _contract(
            unsupported_arguments={SINCE: "not_supported_at_tier, by fixture"},
            relative_defaults={
                SINCE: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                )
            },
        )
    assert SINCE in str(refusal.value)


def test_one_parameter_may_not_carry_two_default_authorities() -> None:
    """``defaults`` and ``relative_defaults`` over one name is ``D-IMPL-315``.

    Two documents saying what omission means for one parameter, with no rule
    that orders them — which is the shape one authority per bound exists to
    keep out. Refused where the author can still fix it.
    """
    with pytest.raises(ValueError) as refusal:
        _contract(
            defaults={SINCE: "2024-09-01"},
            relative_defaults={
                SINCE: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                )
            },
        )
    message = str(refusal.value)
    assert SINCE in message
    assert "defaults" in message


def test_a_render_the_declared_type_cannot_hold_refuses() -> None:
    """Both renders produce a string, so an integer parameter cannot take one."""
    with pytest.raises(ValueError) as refusal:
        _contract(
            relative_defaults={
                DEPTH: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                )
            }
        )
    message = str(refusal.value)
    assert DEPTH in message
    assert "integer" in message


def test_every_offender_is_named_in_one_message() -> None:
    """The exhaustive message is the behavior, not a nicety (``24.6-L-07``).

    An author fixing a declaration one exception at a time is the papercut the
    sibling validators already exist to close.
    """
    with pytest.raises(ValueError) as refusal:
        _contract(
            defaults={LABEL: "a fixture label"},
            unsupported_arguments={SINCE: "not_supported_at_tier, by fixture"},
            relative_defaults={
                "never_declared": RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                ),
                SINCE: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                ),
                LABEL: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                ),
                DEPTH: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                ),
            },
        )
    message = str(refusal.value)
    for offender in ("never_declared", SINCE, LABEL, DEPTH):
        assert offender in message, f"{offender} was not named: {message}"


def test_a_declared_relative_default_the_class_can_honor_is_accepted() -> None:
    """The positive control for every refusal above."""
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    assert contract.relative_defaults[SINCE].offset_seconds == ONE_FIXTURE_YEAR


# --- (c) resolution against the request's own instant ------------------------


def test_a_relative_default_resolves_against_asked_at() -> None:
    """Dave's worked case, with the expectation DERIVED rather than pinned.

    ``asked_at`` + ``-31_536_000`` seconds under ``render: date``. The
    expectation is computed here from the same two declared inputs the SDK
    reads, so the test states the RELATIONSHIP and could not be satisfied by a
    hard-coded string that happens to match today.
    """
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    outcome = _resolve(contract, _request())
    assert outcome.refusal is None
    resolved = _effective(outcome, SINCE)
    assert resolved.value == (
        INSTANT + timedelta(seconds=ONE_FIXTURE_YEAR)
    ).date().isoformat()


def test_the_timestamp_render_keeps_the_instant_rather_than_the_day() -> None:
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(
                offset_seconds=ONE_FIXTURE_YEAR, render="timestamp"
            )
        }
    )
    outcome = _resolve(contract, _request())
    assert outcome.refusal is None
    assert _effective(outcome, SINCE).value == (
        INSTANT + timedelta(seconds=ONE_FIXTURE_YEAR)
    ).isoformat()


def test_the_two_renders_differ_on_one_declaration() -> None:
    """The control for the pair: ``render`` selects, and is not decoration."""

    def _window(render: str) -> Any:
        return _effective(
            _resolve(
                _contract(
                    relative_defaults={
                        SINCE: RelativeDefault(
                            offset_seconds=ONE_FIXTURE_YEAR, render=render
                        )
                    }
                ),
                _request(),
            ),
            SINCE,
        )

    assert _window("date").value != _window("timestamp").value


def test_two_different_instants_resolve_two_different_values() -> None:
    """The whole point of the field: the window MOVES with the question.

    This is the property the absolute date in cp-07 could not have. Asserted
    as a relationship — later question, later window — so no date is pinned.
    """
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    later = _request()
    later = later.model_copy(update={"asked_at": INSTANT + timedelta(days=400)})
    first = _effective(_resolve(contract, _request()), SINCE).value
    second = _effective(_resolve(contract, later), SINCE).value
    assert second > first


def test_the_same_instant_resolves_the_same_value_every_time() -> None:
    """Replay determinism, stated over the resolution rather than the record."""
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    values = {
        _effective(_resolve(contract, _request()), SINCE).value
        for _ in range(3)
    }
    assert len(values) == 1


def test_an_explicit_caller_value_wins_over_a_relative_default() -> None:
    """A default is what omission MEANS, never a competitor to a stated value."""
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    outcome = _resolve(contract, _request(**{SINCE: "2019-01-01"}))
    assert outcome.refusal is None
    resolved = _effective(outcome, SINCE)
    assert resolved.value == "2019-01-01"
    assert resolved.authority == "caller"


# --- (d) what replay records -------------------------------------------------


def test_replay_records_the_resolved_literal_and_never_the_rule() -> None:
    """Dave's stated invariant, and the reason it is the important one.

    *"Replay records the resolved absolute value and ``authority=default``, not
    a rule that gets recomputed later."* A rule re-evaluated at replay time
    would make one decision answer differently on two days.
    """
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    resolved = _effective(_resolve(contract, _request()), SINCE)
    assert resolved.authority == "default"
    assert resolved.source == DECLARED_SOURCE
    assert isinstance(resolved.value, str)
    assert str(ONE_FIXTURE_YEAR) not in str(resolved.value)


def test_the_contracts_own_pin_is_the_provenance_of_a_relative_default() -> None:
    """A value with no provenance is the collapse ``D-IMPL-253`` Q1 forbids."""
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    outcome = _resolve(contract, _request())
    assert DECLARED_SOURCE in outcome.evidence.applied


# --- (e) the domain split Dave ruled -----------------------------------------


def test_a_relative_default_is_not_refused_merely_because_a_domain_exists() -> None:
    """Dave ruled AGAINST the declaration-time refusal that was offered.

    *"Do not forbid ``relative_defaults`` when an ``argument_domain`` exists."*
    """
    contract = _contract(
        argument_domains={
            SINCE: ArgumentDomain(
                members=(
                    (INSTANT + timedelta(seconds=ONE_FIXTURE_YEAR))
                    .date()
                    .isoformat(),
                )
            )
        },
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        },
    )
    assert _resolve(contract, _request()).refusal is None


def test_a_computed_value_outside_its_domain_refuses_at_request_time() -> None:
    """*"The value simply does not exist until ``asked_at`` exists."*

    The same declaration as the test above, asked at an instant whose computed
    window falls outside the declared member set. Nothing about the contract
    changed; the question did.
    """
    contract = _contract(
        argument_domains={
            SINCE: ArgumentDomain(
                members=(
                    (INSTANT + timedelta(seconds=ONE_FIXTURE_YEAR))
                    .date()
                    .isoformat(),
                )
            )
        },
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        },
    )
    elsewhere = _request().model_copy(
        update={"asked_at": INSTANT + timedelta(days=1)}
    )
    refusal = _resolve(contract, elsewhere).refusal
    assert isinstance(refusal, ProductRequestViolation)


# --- (f) the hash distinction ------------------------------------------------


def test_an_empty_relative_defaults_preserves_the_contract_hash() -> None:
    """Backward compatibility: every contract written before this field.

    Not asserted by reading the marker — asserted over the bytes, so a later
    author who drops the marker fails here and not only in a schema test.
    """
    assert "relative_defaults" in hash_transparent_fields(ProductRequestContract)
    assert content_hash(_contract()) == content_hash(_contract(relative_defaults={}))


def test_a_populated_relative_defaults_changes_the_contract_hash() -> None:
    """Grok's constraint, and the identity defect it prevents."""
    assert content_hash(_contract()) != content_hash(
        _contract(
            relative_defaults={
                SINCE: RelativeDefault(
                    offset_seconds=ONE_FIXTURE_YEAR, render="date"
                )
            }
        )
    )


def test_two_different_windows_are_two_different_contract_identities() -> None:
    """*"That prevents two products with different relative-window rules from
    sharing the same contract identity."*"""
    one_year = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    two_years = _contract(
        relative_defaults={
            SINCE: RelativeDefault(
                offset_seconds=ONE_FIXTURE_YEAR * 2, render="date"
            )
        }
    )
    same_window_other_render = _contract(
        relative_defaults={
            SINCE: RelativeDefault(
                offset_seconds=ONE_FIXTURE_YEAR, render="timestamp"
            )
        }
    )
    addresses = {
        content_hash(one_year),
        content_hash(two_years),
        content_hash(same_window_other_render),
    }
    assert len(addresses) == 3


# --- (g) the declared artifact round trip ------------------------------------


def test_a_relative_default_survives_the_declared_artifact_round_trip() -> None:
    """It is a Control Plane artifact key or it is code (CLAUDE.md §6.4)."""
    from ccf.controlplane.artifacts import DeclaredArtifact

    contract = ProductRequestContract.from_declared(
        DeclaredArtifact(
            class_id="fixture.request-contract",
            semver="1.0.0",
            declaration={
                "schema_name": CLASS_NAME,
                "schema_version": CLASS_VERSION,
                "arguments": _arguments().model_dump(),
                "relative_defaults": {
                    SINCE: {"offset_seconds": ONE_FIXTURE_YEAR, "render": "date"}
                },
            },
        )
    )
    assert contract.relative_defaults[SINCE] == RelativeDefault(
        offset_seconds=ONE_FIXTURE_YEAR, render="date"
    )


def test_a_malformed_relative_defaults_key_refuses_by_shape() -> None:
    from ccf.controlplane.artifacts import DeclaredArtifact

    with pytest.raises(ValueError) as refusal:
        ProductRequestContract.from_declared(
            DeclaredArtifact(
                class_id="fixture.request-contract",
                semver="1.0.0",
                declaration={
                    "schema_name": CLASS_NAME,
                    "schema_version": CLASS_VERSION,
                    "arguments": _arguments().model_dump(),
                    "relative_defaults": [SINCE],
                },
            )
        )
    assert "relative_defaults" in str(refusal.value)


# --- (h) the sabotage: resolution reads asked_at and never a clock -----------


def _scratch_constraints(
    tmp_path: pathlib.Path, *, name: str, needle: str, replacement: str
) -> types.ModuleType:
    """A copy of ``constraints.py`` with one fragment rewritten, loaded by name.

    The count is asserted BEFORE the mutation, so a needle that has drifted
    fails loudly here instead of producing a copy identical to the original —
    a green control being worse than none.
    """
    source = CONSTRAINTS_SOURCE.decode("utf-8")
    assert source.count(needle) == 1, f"the needle must appear exactly once: {needle!r}"
    path = tmp_path / f"{name}.py"
    path.write_text(source.replace(needle, replacement, 1), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_a_resolution_that_reached_for_a_clock_is_red_on_the_copy(
    tmp_path: pathlib.Path,
) -> None:
    """GREEN on the tree, RED on a copy that resolves from ``now`` instead.

    The property is not *"the value looks like a date"* — it is *"the value is
    a function of the REQUEST'S instant"*. Only a sabotage separates the two.
    """
    contract = _contract(
        relative_defaults={
            SINCE: RelativeDefault(offset_seconds=ONE_FIXTURE_YEAR, render="date")
        }
    )
    expected = (INSTANT + timedelta(seconds=ONE_FIXTURE_YEAR)).date().isoformat()
    assert _effective(_resolve(contract, _request()), SINCE).value == expected

    sabotaged = _scratch_constraints(
        tmp_path,
        name="constraints_wall_clock",
        needle="relative.resolve(request.asked_at)",
        replacement="relative.resolve(datetime.now(tz=_SABOTAGE_ZONE))",
    )
    sabotaged._SABOTAGE_ZONE = UTC  # type: ignore[attr-defined]
    drifted = _resolve(contract, _request(), module=sabotaged)
    assert _effective(drifted, SINCE).value != expected
    assert CONSTRAINTS_SOURCE == pathlib.Path(
        constraints_module.__file__
    ).read_bytes()
