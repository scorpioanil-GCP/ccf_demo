"""WorkflowDefinition — syntactic validation only (D-11/D-12/D-13/D-IMPL-61).

Written before the implementation per the TDD discipline. The claims pinned
here are exactly the checks the wrapper can perform **locally** — URI
pinning, internal transition-graph consistency, terminal declaration and
reachability, gate-policy keys within the declared graph, and the D-IMPL-61
absent-exception-ref semantics (option-a, propagate-to-terminal). Checks
that need the referenced TaskDefinition (step-name existence, step-kind
agreement, exception-ref resolvability) are the WorkflowFactory's semantic
layer and are pinned in ``tests/workflow/test_factory.py``, not here.

Every definition in this module is loaded **from the banking fixture
artifact** (CLAUDE.md §6.4); mutants are fixture mutations, never inline
documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from ccf.workflow.definitions import (
    WORKFLOW_DEFINITION,
    WORKFLOW_FAILED_STATE,
    WorkflowDefinition,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _workflow_fixture() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(
        (FIXTURES / "workflows" / "covenant_review_workflow.yaml").read_text()
    )
    return loaded


def _document() -> dict[str, Any]:
    document: dict[str, Any] = _workflow_fixture()["workflow_definition"]
    return document


def _definition(**mutations: Any) -> WorkflowDefinition:
    document = _document()
    document.update(mutations)
    return WorkflowDefinition.model_validate(document)


# --- the supported shape ------------------------------------------------------


def test_the_fixture_workflow_validates() -> None:
    definition = _definition()
    assert definition.name == "covenant-review-workflow"
    assert definition.task_definition_ref.startswith("ccf-artifact://")
    assert definition.start == "fetch-certificates"


def test_the_artifact_class_is_registered_as_ccf_workflow_definition() -> None:
    assert WORKFLOW_DEFINITION.class_id == "ccf.workflow-definition"
    validated = WORKFLOW_DEFINITION.validate(_definition())
    assert isinstance(validated, WorkflowDefinition)


# --- pinned-ref discipline (D-12; D-IMPL-26) ---------------------------------


def test_a_latest_task_definition_ref_is_refused() -> None:
    with pytest.raises(ValidationError, match="latest"):
        _definition(
            task_definition_ref=(
                "ccf-artifact://acme-bank/ccf.task-definition/"
                "covenant-review@latest"
            )
        )


def test_an_unpinned_exception_ref_is_refused() -> None:
    with pytest.raises(ValidationError, match="latest"):
        _definition(
            exception_refs={
                "fetch-certificates": (
                    "ccf-artifact://acme-bank/exception-handler/"
                    "certificate-fetch-failed@latest"
                )
            }
        )


# --- internal transition-graph consistency (syntactic) ------------------------


def test_a_transition_to_an_undeclared_node_is_refused() -> None:
    document = _document()
    document["transitions"].append(
        {"source": "analyze-covenants", "target": "no-such-node"}
    )
    with pytest.raises(ValidationError, match="no-such-node"):
        WorkflowDefinition.model_validate(document)


def test_a_start_node_outside_the_transition_graph_is_refused() -> None:
    with pytest.raises(ValidationError, match="start"):
        _definition(start="no-such-node")


def test_a_terminal_state_with_outgoing_transitions_is_refused() -> None:
    document = _document()
    document["transitions"].append(
        {"source": "approved", "target": "fetch-certificates"}
    )
    with pytest.raises(ValidationError, match="terminal"):
        WorkflowDefinition.model_validate(document)


# --- terminal declaration and reachability -----------------------------------


def test_a_workflow_with_no_terminal_state_is_refused() -> None:
    with pytest.raises(ValidationError, match="terminal"):
        _definition(terminal_states=[])


def test_a_node_from_which_no_terminal_is_reachable_is_refused() -> None:
    """A cycle with no exit to a terminal is refused at contract validation.

    Computed from the wrapper's own transition graph: the D-IMPL-61 implicit
    exception transition to ``failed`` is an *exception* path, never the
    nominal path, so it does not rescue a nominal dead-end.
    """
    document = _document()
    document["transitions"] = [
        {"source": "fetch-certificates", "target": "analyze-covenants"},
        {"source": "analyze-covenants", "target": "fetch-certificates"},
    ]
    document["gate_policies"] = {}
    with pytest.raises(ValidationError, match="terminal"):
        WorkflowDefinition.model_validate(document)


def test_an_unreachable_node_is_refused() -> None:
    """A node never a transition target and not the start node is refused."""
    document = _document()
    document["transitions"].append(
        {"source": "orphan-step", "target": "approved"}
    )
    with pytest.raises(ValidationError, match="orphan-step"):
        WorkflowDefinition.model_validate(document)


# --- D-IMPL-61: absent exception ref = propagate-to-terminal ------------------


def test_an_absent_exception_ref_validates_per_d_impl_61() -> None:
    """Option-a, propagate-to-terminal: absence is defined, not an error."""
    definition = _definition(exception_refs={})
    assert definition.exception_refs == {}


def test_the_reserved_failed_state_is_a_declared_terminal() -> None:
    """The schema declares the terminal ``failed`` state (D-IMPL-61)."""
    definition = _definition()
    assert WORKFLOW_FAILED_STATE == "failed"
    assert WORKFLOW_FAILED_STATE in definition.effective_terminal_states


def test_a_transition_may_target_the_reserved_failed_state() -> None:
    """``failed`` is a defined transition target without local declaration."""
    document = _document()
    document["transitions"].append(
        {"source": "analyze-covenants", "target": WORKFLOW_FAILED_STATE}
    )
    definition = WorkflowDefinition.model_validate(document)
    assert WORKFLOW_FAILED_STATE in definition.effective_terminal_states


def test_the_reserved_failed_state_cannot_be_a_source() -> None:
    document = _document()
    document["transitions"].append(
        {"source": WORKFLOW_FAILED_STATE, "target": "approved"}
    )
    with pytest.raises(ValidationError, match="failed"):
        WorkflowDefinition.model_validate(document)


def test_an_exception_ref_key_outside_the_graph_is_refused() -> None:
    with pytest.raises(ValidationError, match="no-such-node"):
        _definition(
            exception_refs={
                "no-such-node": (
                    "ccf-artifact://acme-bank/exception-handler/"
                    "certificate-fetch-failed@1.0.0"
                )
            }
        )


# --- gate policies (syntactic subset only; kind check is the factory's) -------


def test_a_gate_policy_key_outside_the_declared_graph_is_refused() -> None:
    with pytest.raises(ValidationError, match="no-such-node"):
        _definition(
            gate_policies={
                "no-such-node": (
                    "ccf-artifact://acme-bank/approval-policy/"
                    "credit-officer@1.0.0"
                )
            }
        )


def test_a_gate_policy_on_a_declared_node_passes_syntactically() -> None:
    """Whether the node is hitl-gate-kind is the factory's semantic check."""
    definition = _definition(
        gate_policies={
            "analyze-covenants": (
                "ccf-artifact://acme-bank/approval-policy/"
                "credit-officer@1.0.0"
            )
        }
    )
    assert "analyze-covenants" in definition.gate_policies


# --- the deferred semantic checks are named, not silently absent --------------


def test_the_module_names_its_factory_deferred_checks() -> None:
    import ccf.workflow.definitions as module

    assert module.__doc__ is not None
    assert "WorkflowFactory" in module.__doc__


# --- gate_routes: verdict -> declared target (D-IMPL-357 A1) ------------------


def _base(**overrides: Any) -> dict[str, Any]:
    document = {
        "schema_version": "2.0.0",
        "artifact_version": "1.0.0",
        "name": "w",
        "tenant": "acme-bank",
        "task_definition_ref": "ccf-artifact://acme-bank/ccf.task-definition/t@1.0.0",
        "start": "fetch",
        "transitions": [
            {"source": "fetch", "target": "gate"},
            {"source": "gate", "target": "approved"},
            {"source": "gate", "target": "rejected"},
        ],
        "terminal_states": ["approved", "rejected"],
        "gate_routes": {"gate": {"approve": "approved", "reject": "rejected"}},
    }
    document.update(overrides)
    return document


def test_gate_routes_maps_each_verdict_to_a_declared_target_from_that_gate() -> None:
    definition = WorkflowDefinition.model_validate(_base())
    assert definition.gate_routes["gate"]["reject"] == "rejected"


def test_a_route_to_a_target_not_declared_from_that_gate_is_refused() -> None:
    with pytest.raises(ValidationError, match="not a declared transition target from"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"gate": {"approve": "approved", "reject": "fetch"}})
        )


def test_a_verdict_outside_GATE_ACTIONS_is_refused() -> None:
    with pytest.raises(ValidationError, match="GATE_ACTIONS"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"gate": {"approve": "approved", "escalate": "rejected"}})
        )


def test_a_route_keyed_by_an_undeclared_node_is_refused() -> None:
    with pytest.raises(ValidationError, match="appear nowhere"):
        WorkflowDefinition.model_validate(
            _base(gate_routes={"phantom": {"approve": "approved"}})
        )


def test_gate_routes_is_a_generation_boundary_not_a_transparent_default() -> None:
    from ccf.contracts.canonical import HASH_TRANSPARENT_KEY

    field = WorkflowDefinition.model_fields["gate_routes"]
    assert (field.json_schema_extra or {}).get(HASH_TRANSPARENT_KEY) is False
