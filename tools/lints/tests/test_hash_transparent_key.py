"""CINV-06 — the ``ccf_hash_transparent`` key on every sentinel-defaulted contract field.

``D-IMPL-243`` amendment 1; whitepaper §7.10; CLAUDE.md §7.4. The checker is
``tools/lints/hash_transparent_key.py``; see its docstring for the rule and
for its **registration status** — written and NOT registered under ``--all``,
because its first run over the tree found the roster pinned at the bottom of
this module, and widening the allowlist beyond the fifteen is a ruling.

Two kinds of proof here. The mechanism, on scratch trees under ``tmp_path``:
a planted keyless field is RED naming ``Class.field``; ``True`` and ``False``
are silent; anything else under the key is red; required fields, private
attributes and ``ClassVar``s are outside the rule; subclassing is followed
across files. And the tree: the fifteen are found, silent, and are exactly
the amendment's fifteen; the AST universe equals the imported universe; the
roster the first run measured is what the tree still says.
"""

from __future__ import annotations

import importlib
import pathlib
import pkgutil
import textwrap
from collections.abc import Mapping

import pytest

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


def test_the_allowlist_is_honored_by_qualified_name_only(tmp_path: pathlib.Path) -> None:
    """The fifteen are ``Class.field``; a same-named field elsewhere is not one."""
    base = _tree(
        tmp_path,
        m="""
        from scratch.base import CCFContract

        class PolicyBindingsSnapshot(CCFContract):
            hitl_actions: str = "none"

        class Other(CCFContract):
            hitl_actions: str = "none"
        """,
    )
    assert _qualified(checker.check_tree(base)) == ["Other.hitl_actions"]


# --- the tree -----------------------------------------------------------------------


#: The amendment's fifteen, in its own dotted spelling — a second spelling of
#: the checker's ``Class.field`` roster, so the two cannot drift apart.
_AMENDMENT_FIFTEEN = {
    "context_fabric_snapshot": ("ContextFabricSnapshot", ["source_attestation"]),
    "policy_bindings": (
        "PolicyBindingsSnapshot",
        ["hitl_actions", "survivor_cap", "graph_adapter", "graph_adapter_version", "graph_secret_refs"],
    ),
    "model_version": ("ModelVersionRecord", ["harness_trace"]),
    "content_generation_path": (
        "ContentGenerationPath",
        [
            "workflow_step_sequence", "assembly_refusal", "graph_query_sequence", "debt",
            "debt_evidence", "source_refresh_recency", "obligation_in_force", "request",
        ],
    ),
}


def test_the_allowlist_is_exactly_the_amendments_fifteen_by_name() -> None:
    expected = {
        f"{cls}.{field}"
        for cls, fields in _AMENDMENT_FIFTEEN.values()
        for field in fields
    }
    assert checker.ALLOWLISTED_PRE_243_FIELDS == expected
    assert len(expected) == 15


def test_each_of_the_fifteen_is_a_defaulted_field_the_tree_declares() -> None:
    """The allowlist is not dead: every entry names a real, keyless default."""
    by_name = {f.qualified: f for f in checker.defaulted_fields(REPO)}
    for name in sorted(checker.ALLOWLISTED_PRE_243_FIELDS):
        assert name in by_name, name
        assert by_name[name].declared is None, name
        assert by_name[name].path == REPO / "src" / "ccf" / "replay" / "record.py"


def test_the_fifteen_are_silent_on_the_real_tree() -> None:
    named = set(_qualified(checker.check_tree(REPO)))
    assert not (named & checker.ALLOWLISTED_PRE_243_FIELDS)


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


# --- registration status and the measured roster ------------------------------


def test_the_checker_is_not_registered_pending_the_roster_ruling() -> None:
    """Honest status: written, tested, NOT under ``--all``.

    Flip this to an ``in`` assertion in the same commit that registers the
    checker — after the ruling on the roster below — and delete the roster.
    """
    assert "hash-transparent-key" not in WHOLE_TREE_CHECKERS
    assert "hash-transparent-key" not in CHECKERS


#: Measured by the checker's first run over the tree with the fifteen
#: allowlisted (24.5-FIX-01, ``D-IMPL-243`` amendment 1). Eight are 24.5's own
#: additions (not at ``13bd250``); the rest predate Phase 24.5. Every entry is
#: a sentinel-defaulted ``CCFContract`` field without the key. A roster, not
#: a count: the ruling on the allowlist's width is taken against these names.
UNDECLARED_ADDED_IN_24_5: tuple[str, ...] = (
    "ExecutionResult.empty_results",
    "ExecutionResult.store_snapshot_pin",
    "HalfLifeEntry.half_life_seconds",
    "ResolvedEntity.resolved_by",
    "ServeObligations.debt_ceiling",
    "ServeObligations.lineage_inputs_at",
    "TraversalDescendantsParameters.admitted_entity_classes",
)

UNDECLARED_BEFORE_24_5: tuple[str, ...] = (
    "AuditEvent.actor",
    "AuditEvent.artifact_class",
    "AuthzDecisionAuditEvent.authz_action_id",
    "AuthzDecisionAuditEvent.authz_matched_pattern",
    "ChangeEvent.after",
    "ChangeEvent.before",
    "ContextContract.emits",
    "ContextProductContract.debt",
    "ContextProductContract.debt_evidence",
    "ContextProductContract.obligation_in_force",
    "ContextProductContract.source_refresh_recency",
    "DebtAssessment.scorers",
    "DebtProfile.signal_obligations",
    "DeploymentConfig.backend_secrets",
    "DeploymentConfig.debt_profile",
    "DeploymentConfig.default_perspective",
    "DeploymentConfig.half_life",
    "DeploymentConfig.operators",
    "DeploymentConfig.policy",
    "DeploymentConfig.policy_bundle_key",
    "DeploymentConfig.request_contract",
    "DeploymentConfig.resolution",
    "DeploymentConfig.resolution_spec_key",
    "DeploymentConfig.survivor_cap",
    "DeploymentConfig.tenant_id",
    "DeploymentManifest.backend_secrets",
    "DeploymentManifest.survivor_cap",
    "DeploymentManifest.tenant_id",
    "EntityClaim.attributes",
    "EntityRecord.superseded_at",
    "EntityRecord.superseded_by",
    "EntityResolutionRule.attribute_keys",
    "EntityResolutionSpec.relationship_rules",
    "ExecutionResult.acquisitions",
    "ExecutionResult.executed_queries",
    "ExecutionResult.source_attestation",
    "ExecutionResult.survivor_cap",
    "FederatedIngestSpec.record_key_aliases",
    "FlureeConnection.partition",
    "GraphQuery.allowed_entities",
    "GraphQuery.classification_attribute_by_class",
    "GraphQuery.permitted_classifications",
    "GraphQuery.permitted_policy_bundle_versions",
    "GraphQuery.require_valid_at_boundary",
    "GraphQuery.seeds",
    "GraphQuery.traverse",
    "GraphView.entities",
    "GraphView.relationships",
    "HarnessTrace.harness_id",
    "HarnessTrace.input_tokens",
    "HarnessTrace.model_version",
    "HarnessTrace.output_tokens",
    "HarnessTrace.trace_id",
    "HarnessTrace.trace_provider",
    "HitlActionSubmission.annotation",
    "HitlActionSubmission.signed_binding",
    "HitlPolicy.signed_binding_required",
    "IngestResult.entities",
    "IngestResult.relationships",
    "LineageEntry.passage_anchor",
    "ModelVersionRecord.model_version",
    "MongoConnection.partition",
    "Neo4jConnection.partition",
    "Observation.subject",
    "OperatorProvenance.index_version",
    "OperatorProvenance.upstream",
    "PendingHitlEvent.policy_ref",
    "PerspectiveConditioning.agent_definition_hash",
    "PerspectiveConditioning.agent_definition_uri",
    "PerspectiveConditioning.archetype_composition",
    "PerspectiveConditioning.delegation_chain",
    "PerspectiveConditioning.grant_set_hash",
    "PostgresConnection.schema_name",
    "ProductClassDeclaration.accepted_lineage_modes",
    "ProductClassDeclaration.accepted_policy_binding_modes",
    "ProductClassDeclaration.addressability",
    "ProductClassDeclaration.constituent_validity_floors",
    "ProductClassDeclaration.discovery",
    "ProductClassDeclaration.freshness_sla",
    "ProductClassDeclaration.payload_schema_key",
    "ProductClassDeclaration.request_contract_key",
    "ProductDiscovery.audiences",
    "QueryFragment.classification_attribute_by_class",
    "QueryFragment.permitted_classifications",
    "QueryFragment.permitted_policy_bundle_versions",
    "QueryFragment.require_valid_at_boundary",
    "QueryFragment.traverse",
    "RegisteredProductClass.accepted_lineage_modes",
    "RegisteredProductClass.accepted_policy_binding_modes",
    "RegisteredProductClass.addressability",
    "RegisteredProductClass.constituent_validity_floors",
    "RegisteredProductClass.discovery",
    "RegisteredProductClass.freshness_sla",
    "RegisteredProductClass.payload_schema_key",
    "RegisteredProductClass.payload_schema_version",
    "RegisteredProductClass.request_contract_key",
    "RegisteredProductClass.request_contract_version",
    "RelationshipClaim.attributes",
    "RelationshipRecord.superseded_at",
    "RelationshipRecord.superseded_by",
    "ResolvedPins.entries",
    "SignalEnvelope.observed_time",
    "SignalEnvelope.source_metadata",
    "SkillArgumentElement.properties",
    "SkillArgumentElement.required",
    "SkillArgumentProperty.items",
    "SkillArgumentProperty.properties",
    "SkillArgumentProperty.required",
    "TaskDefinition.instruction_bindings",
    "TaskStep.ref",
    "UpsertResult.superseded_claim_id",
    "WebhookDeliveryOutcome.error",
    "WorkflowDefinition.exception_refs",
    "WorkflowDefinition.gate_policies",
    "_TemporalClaim.valid_to",
)


def test_the_first_run_roster_is_what_the_tree_still_says() -> None:
    named = sorted(_qualified(checker.check_tree(REPO)))
    assert named == sorted(UNDECLARED_ADDED_IN_24_5 + UNDECLARED_BEFORE_24_5)
