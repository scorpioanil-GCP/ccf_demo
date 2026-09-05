"""CINV-06 — the ``ccf_hash_transparent`` key on every sentinel-defaulted contract field NEW since ``13bd250``.

``D-IMPL-243`` amendments 1 and 2; whitepaper §7.10; CLAUDE.md §7.4. The
checker is ``tools/lints/hash_transparent_key.py``; the base roster it reads
is ``tools/lints/hash_transparent_base_roster.json``, whose own proofs are in
``test_base_roster.py``. The checker is registered under ``--all``
(``test_runner.py`` holds the registry equal by name).

Two kinds of proof here. The mechanism, on scratch trees under ``tmp_path``:
a planted keyless field is RED naming ``Class.field``; ``True`` and ``False``
are silent; anything else under the key is red; required fields, private
attributes and ``ClassVar``s are outside the rule; subclassing is followed
across files; and the roster boundary is module-qualified — a scratch class
that happens to share a roster entry's ``Class.field`` in a different module
is still in the universe. And the tree: the seven fields amendment 2 ticks
are declared ``True`` by name; every field in the base roster is silent
whatever it declares (130 keyless pre-phase fields, zero findings); the AST
universe equals the imported universe; and the tree is clean.
"""

from __future__ import annotations

import importlib
import pathlib
import pkgutil
import textwrap
from collections.abc import Mapping

import pytest

from tools.lints import base_roster
from tools.lints import hash_transparent_key as checker
from tools.lints.__main__ import CHECKERS, WHOLE_TREE_CHECKERS

REPO = pathlib.Path(__file__).resolve().parents[3]

_BASE_MODULE = """
from pydantic import BaseModel, ConfigDict


class CCFContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
"""


def _tree(tmp_path: pathlib.Path, **modules: str) -> pathlib.Path:
    """A scratch ``src/`` tree with the contract base and the given modules."""
    root = tmp_path / "src" / "scratch"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text("")
    (root / "base.py").write_text(_BASE_MODULE)
    for name, source in modules.items():
        (root / f"{name}.py").write_text(textwrap.dedent(source))
    return tmp_path


def _qualified(findings: list[str]) -> list[str]:
    """``Class.field`` from each finding — the third whitespace field."""
    return [line.split()[2] for line in findings]


# --- the mechanism -----------------------------------------------------------------


def test_a_planted_keyless_default_is_red_naming_the_field(tmp_path: pathlib.Path) -> None:
    base = _tree(
        tmp_path,
        m="""
        from scratch.base import CCFContract

        class Planted(CCFContract):
            a: int
            forgotten: int = 0
        """,
    )
    findings = checker.check_tree(base)
    assert _qualified(findings) == ["Planted.forgotten"]
    assert findings[0].split()[1] == checker.RULE_HASH_TRANSPARENT_KEY
    assert "D-IMPL-243" in findings[0]
    assert str(base / "src" / "scratch" / "m.py") + ":6" in findings[0]


@pytest.mark.parametrize(
    "declaration",
    [
        "Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: True})",
        "Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: False})",
        "Field(default_factory=dict, json_schema_extra={HASH_TRANSPARENT_KEY: True})",
        "Field(0, json_schema_extra={HASH_TRANSPARENT_KEY: False})",
        'Field(default=0, json_schema_extra={"ccf_hash_transparent": True})',
        "Field(default=0, json_schema_extra={canonical.HASH_TRANSPARENT_KEY: False})",
    ],
)
def test_a_declared_true_or_false_is_silent(tmp_path: pathlib.Path, declaration: str) -> None:
    base = _tree(
        tmp_path,
        m=f"""
        from pydantic import Field
        from scratch.base import CCFContract
        from ccf.contracts import canonical
        from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

        class Declared(CCFContract):
            a: int
            f: object = {declaration}
        """,
    )
    assert checker.check_tree(base) == []


@pytest.mark.parametrize(
    "declaration",
    [
        "Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: 1})",
        'Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: "true"})',
        "Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: None})",
        "Field(default=0, json_schema_extra=EXTRA)",
        "Field(default=0, json_schema_extra={})",
        "Field(default=0, description='no key at all')",
        "Field(default_factory=list)",
        "0",
        "None",
        "SENTINEL",
    ],
)
def test_anything_else_is_red(tmp_path: pathlib.Path, declaration: str) -> None:
    base = _tree(
        tmp_path,
        m=f"""
        from pydantic import Field
        from scratch.base import CCFContract
        from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
        EXTRA = {{HASH_TRANSPARENT_KEY: True}}
        SENTINEL = object()

        class Undeclared(CCFContract):
            a: int
            f: object = {declaration}
        """,
    )
    assert _qualified(checker.check_tree(base)) == ["Undeclared.f"]


def test_required_fields_private_attributes_and_classvars_are_outside_the_rule(
    tmp_path: pathlib.Path,
) -> None:
    base = _tree(
        tmp_path,
        m="""
        from typing import ClassVar
        from pydantic import Field
        from scratch.base import CCFContract

        class Shape(CCFContract):
            required: int
            described: int = Field(description="required, with metadata")
            _private: int = 0
            CONSTANT: ClassVar[int] = 0
        """,
    )
    assert checker.check_tree(base) == []


def test_subclassing_is_followed_across_files_and_through_intermediates(
    tmp_path: pathlib.Path,
) -> None:
    base = _tree(
        tmp_path,
        a="""
        from scratch.base import CCFContract

        class Middle(CCFContract):
            a: int
        """,
        b="""
        from scratch import a
        from scratch.base import CCFContract as Renamed

        class Leaf(a.Middle):
            forgotten: int = 0

        class ViaAttribute(Renamed):
            pass

        class Unrelated:
            not_a_field: int = 0
        """,
    )
    assert _qualified(checker.check_tree(base)) == ["Leaf.forgotten"]


# --- the roster boundary --------------------------------------------------------------


def test_the_roster_boundary_is_module_qualified(tmp_path: pathlib.Path) -> None:
    """A roster entry is ``module.Class.field``; the same ``Class.field`` in
    another module is a different declaration and stays in the universe."""
    base = _tree(
        tmp_path,
        m="""
        from scratch.base import CCFContract

        class PolicyBindingsSnapshot(CCFContract):
            hitl_actions: str = "none"
        """,
    )
    record = tmp_path / "src" / "ccf" / "replay"
    record.mkdir(parents=True)
    (tmp_path / "src" / "ccf" / "__init__.py").write_text("")
    (record / "__init__.py").write_text("")
    (record / "record.py").write_text(
        textwrap.dedent(
            """
            from scratch.base import CCFContract

            class PolicyBindingsSnapshot(CCFContract):
                hitl_actions: str = "none"
            """
        )
    )
    assert "ccf.replay.record.PolicyBindingsSnapshot.hitl_actions" in base_roster.load()
    findings = checker.check_tree(base)
    assert _qualified(findings) == ["PolicyBindingsSnapshot.hitl_actions"]
    assert str(base / "src" / "scratch" / "m.py") in findings[0]


def test_a_scratch_roster_bounds_the_universe(tmp_path: pathlib.Path) -> None:
    base = _tree(
        tmp_path,
        m="""
        from scratch.base import CCFContract

        class Old(CCFContract):
            kept: int = 0

        class New(CCFContract):
            forgotten: int = 0
        """,
    )
    roster = frozenset({"scratch.m.Old.kept"})
    assert _qualified(checker.check_tree(base, roster=roster)) == ["New.forgotten"]
    assert _qualified(checker.check_tree(base, roster=frozenset())) == [
        "Old.kept",
        "New.forgotten",
    ]


def test_a_roster_field_is_silent_whatever_it_declares(tmp_path: pathlib.Path) -> None:
    """In the roster means outside the universe: keyless, ``True``, ``False``
    and unreadable are all silent — the field predates the mark."""
    base = _tree(
        tmp_path,
        m="""
        from pydantic import Field
        from scratch.base import CCFContract
        from ccf.contracts.canonical import HASH_TRANSPARENT_KEY
        EXTRA = {HASH_TRANSPARENT_KEY: True}

        class Old(CCFContract):
            keyless: int = 0
            true: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: True})
            false: int = Field(default=0, json_schema_extra={HASH_TRANSPARENT_KEY: False})
            unreadable: int = Field(default=0, json_schema_extra=EXTRA)
        """,
    )
    roster = frozenset(
        f"scratch.m.Old.{name}" for name in ("keyless", "true", "false", "unreadable")
    )
    assert checker.check_tree(base, roster=roster) == []
    assert _qualified(checker.check_tree(base, roster=frozenset())) == [
        "Old.keyless",
        "Old.unreadable",
    ]


# --- the tree -----------------------------------------------------------------------


#: Amendment 2's seven ticks, ``module.Class.field``, all ``True`` — the
#: fields the first roster-bounded sweep named and nothing else.
THE_SEVEN: tuple[str, ...] = (
    "ccf.assembly.worker.ResolvedEntity.resolved_by",
    "ccf.controlplane.artifacts.HalfLifeEntry.half_life_seconds",
    "ccf.operators.params.TraversalDescendantsParameters.admitted_entity_classes",
    # 24.6-04: the same field under its new name (`D-IMPL-253` Q9). It was
    # one of amendment 2's seven; a rename does not move it to the roster of
    # what came after.
    "ccf.products.contract.ServeObligations.default_debt_tolerance",
    "ccf.products.contract.ServeObligations.lineage_inputs_at",
    "ccf.projection.engine.ExecutionResult.empty_results",
    "ccf.projection.engine.ExecutionResult.store_snapshot_pin",
)


def _at_head() -> dict[str, checker.DefaultedField]:
    return {checker.module_qualified(f, REPO): f for f in checker.defaulted_fields(REPO)}


def test_the_seven_are_declared_true_and_outside_the_roster() -> None:
    at_head = _at_head()
    roster = base_roster.load()
    for name in THE_SEVEN:
        assert name in at_head, name
        assert at_head[name].declared is True, name
        assert name not in roster, name


#: Fields added AFTER amendment 2's sweep, ``module.Class.field``, all
#: ``True``. Named rather than left to the universe check below, on the
#: "verify rosters, not counts" discipline: the universe check would pass just
#: as happily if one of these silently lost its key and another gained one.
#: `THE_SEVEN` above is a CLOSED historical record of the sweep and is not
#: extended — a field added later was never one of its seven.
NAMED_SINCE_THE_SWEEP: tuple[str, ...] = (
    # 24.6-01, the fifth declaration key (`24.6-L-07`, `D-IMPL-253` Q2).
    "ccf.products.request.ProductRequestContract.defaults",
    # 24.6-03, the sixth declaration key (`D-IMPL-253` Q21), the request's
    # override list and the grant that entitles one (Q7).
    "ccf.products.request.ProductRequestContract.capability_bindings",
    "ccf.products.request.ProductRequest.policy_overrides",
    "ccf.products.entitlement.ProductEntitlementGrant.overridable_policies",
    # 24.6-03, the resolution pinned into replay dimension 2 (`D-IMPL-254`).
    "ccf.replay.record.PolicyBindingsSnapshot.request_resolution",
    # 24.6-05, the search behind an empty answer (`24.6-L-06`, `D-IMPL-242`
    # amendment 1). `None` = "no operator returned empty", which every
    # pre-phase product already said.
    "ccf.products.contract.ContextProductContract.computed_empty",
    # 24.6-07, the refusal shell's six governance members (`24.6-L-08`,
    # `D-IMPL-253` Q13/Q14) and the resource-request identity of a
    # delivery-boundary denial (`D-IMPL-256` (1)).
    "ccf.products.refusal.RefusalEnvelope.policy_bindings",
    "ccf.products.refusal.RefusalEnvelope.replay_reference",
    "ccf.products.refusal.RefusalEnvelope.evidence",
    "ccf.products.refusal.RefusalEnvelope.provenance",
    "ccf.products.refusal.RefusalEnvelope.disclosure",
    "ccf.products.refusal.RefusalEnvelope.resource",
    # 24.6-07, the two optional members of the permitted-evidence bundle. A
    # brand-new model, so there is no earlier generation to be a boundary
    # against and `True` is the only coherent declaration.
    "ccf.products.refusal.RefusalEvidence.debt",
    "ccf.products.refusal.RefusalEvidence.computed_empty",
    # 24.6-08, the typed code a subject-unavailable determination carried
    # (`24.6-L-21`). Brand-new model, and the field a disclosed shell blanks
    # below `full` — so it renders absent rather than as an explicit null.
    "ccf.products.refusal.SubjectUnavailableRefusal.error_code",
    # 24.6-08, the disclosure posture in force (`24.6-L-16`, `D-IMPL-253`
    # Q17): `minimal` on the tenant policy, `None` on the per-principal
    # override. Silent at both sentinels, so no registered policy's content
    # address moves.
    "ccf.products.entitlement.ProductEntitlementPolicy.disclosure_level",
    "ccf.products.entitlement.ProductEntitlementGrant.disclosure_level",
    # 24.6-07, the assembler in force on replay dimension 4 (`D-IMPL-253`
    # Q16, `D-IMPL-245` am.1) and the disclosure decision on dimension 5
    # (`D-IMPL-254`).
    "ccf.replay.record.PerspectiveConditioning.assembler_id",
    "ccf.replay.record.PerspectiveConditioning.assembler_version",
    "ccf.replay.record.ContentGenerationPath.disclosure_decision",
    # 24.6-14, the seventh declaration key (`D-IMPL-259`): a parameter's valid
    # domain, and the two optional ends of one. Silent at the empty mapping
    # and at an absent end, so no committed request contract's address moves.
    "ccf.products.request.ProductRequestContract.argument_domains",
    "ccf.products.request.ArgumentDomain.minimum",
    "ccf.products.request.ArgumentDomain.maximum",
)


def test_the_fields_named_since_the_sweep_declare_true_and_are_outside_the_roster() -> (
    None
):
    at_head = _at_head()
    roster = base_roster.load()
    for name in NAMED_SINCE_THE_SWEEP:
        assert name in at_head, name
        assert at_head[name].declared is True, name
        assert name not in roster, name


def test_the_two_tree_rosters_are_disjoint() -> None:
    """`THE_SEVEN` is the sweep's record and `NAMED_SINCE_THE_SWEEP` is what
    came after; a name in both would mean one of the two is lying about when
    the field arrived."""
    assert not set(THE_SEVEN) & set(NAMED_SINCE_THE_SWEEP)


def test_every_field_new_since_base_declares_the_key() -> None:
    """The universe, enumerated: every defaulted field outside the roster
    declares ``True`` or ``False``. A roster of names, so a future field that
    forgets the key is named here as well as by ``make lint``."""
    roster = base_roster.load()
    undeclared = sorted(
        name
        for name, field in _at_head().items()
        if name not in roster and field.declared not in (True, False)
    )
    assert undeclared == []


def test_the_tree_is_clean() -> None:
    assert checker.check_tree(REPO) == []


def test_the_roster_fields_are_keyless_on_the_tree_and_silent() -> None:
    """The 130 pre-phase fields carry no key (the ``D-IMPL-89`` lineage) and
    the lint names none of them — silence by construction, not by allowlist."""
    at_head = _at_head()
    roster = base_roster.load()
    keyless = {name for name in roster if at_head[name].declared is None}
    assert keyless == roster
    assert len(roster) == 130
    # The positive control: with the roster taken away the lint names every
    # one of the 130 — so their silence is the roster's doing and nothing else.
    unbounded = checker.check_tree(REPO, roster=frozenset())
    assert len(unbounded) == 130
    assert set(_qualified(unbounded)) == {".".join(n.rsplit(".", 2)[1:]) for n in roster}


def _imported_universe() -> dict[str, str]:
    """``Class.field`` -> declared key state, for every defaulted field, by import.

    The compensating control for the AST's name-based subclass closure: every
    ``ccf.*`` / ``ccf_runtime.*`` module is imported, every ``CCFContract``
    subclass walked, and each defaulted field attributed to the class that
    DECLARES it (the first class in the MRO whose annotations name it) — which
    is the unit the AST reports.
    """
    import ccf
    import ccf_runtime
    from pydantic import BaseModel
    from pydantic_core import PydanticUndefined

    from ccf.contracts.base import CCFContract

    for package in (ccf, ccf_runtime):
        for module in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
            importlib.import_module(module.name)

    found: dict[str, str] = {}
    seen: set[type] = set()

    def declaring_class(cls: type, name: str) -> type:
        for klass in cls.__mro__:
            if name in getattr(klass, "__annotations__", {}):
                return klass
        raise AssertionError((cls, name))

    def walk(cls: type[BaseModel]) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            if sub.__module__.startswith(("ccf.", "ccf_runtime.")):
                for name, field in sub.model_fields.items():
                    defaulted = (
                        field.default is not PydanticUndefined
                        or field.default_factory is not None
                    )
                    if not defaulted:
                        continue
                    extra = field.json_schema_extra
                    key = extra.get(checker.KEY_NAME) if isinstance(extra, Mapping) else None
                    owner = declaring_class(sub, name)
                    found[f"{owner.__name__}.{name}"] = str(key) if isinstance(key, bool) else "None"
            walk(sub)

    walk(CCFContract)
    return found


def test_the_ast_universe_equals_the_imported_universe() -> None:
    by_ast = {f.qualified: str(f.declared) for f in checker.defaulted_fields(REPO)}
    by_import = _imported_universe()
    assert set(by_ast) == set(by_import)
    assert by_ast == by_import


# --- registration ---------------------------------------------------------------


def test_the_checker_is_registered_under_all() -> None:
    """``D-IMPL-243`` amendment 2: registered, whole-tree, by this name."""
    assert WHOLE_TREE_CHECKERS["hash-transparent-key"] is checker.check_tree
    assert "hash-transparent-key" not in CHECKERS
