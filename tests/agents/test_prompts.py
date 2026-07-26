"""Jinja2 parse-only prompt-artifact validation (D-13; CLAUDE.md §6.2 axis 6).

Written before the implementation per the TDD discipline. The claims pinned:

* A prompt artifact whose ``declared_parameters`` exactly equal the set
  ``jinja2.meta.find_undeclared_variables`` reports for its template validates
  (RESEARCH Assumption A1, verified here against the installed 3.1.6).
* Any disagreement in either direction — a template variable nobody declared,
  or a declared parameter the template never uses — is a
  ``PromptValidationError`` naming the offending parameter.
* A template that does not parse fails with ``PromptValidationError`` chained
  from ``jinja2.TemplateSyntaxError``.
* An instruction binding whose ``parameters`` mismatch the artifact's
  ``declared_parameters`` fails ``validate_instruction_binding``.

The template text lives in the banking fixture YAML; no prompt string literal
appears in this module. Negative cases are constructed by mutating the
fixture-loaded artifact (No-Hardcoding Rule, §6.4).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jinja2
import pytest
import yaml

from ccf.agents.definitions import (
    AGENT_DEFINITION,
    PROMPT_ARTIFACT,
    AgentDefinition,
    PromptArtifact,
)
from ccf.agents.errors import PromptValidationError
from ccf.agents.prompts import validate_instruction_binding, validate_prompt_artifact
from ccf.controlplane.artifacts import parse_artifact

FIXTURES = Path(__file__).parent.parent / "fixtures" / "banking"


def _artifact() -> PromptArtifact:
    loaded = yaml.safe_load((FIXTURES / "prompts" / "covenant_summary.yaml").read_text())
    artifact = parse_artifact(loaded["prompt_artifact"], PROMPT_ARTIFACT)
    assert isinstance(artifact, PromptArtifact)
    return artifact


def _mutated(**overrides: Any) -> PromptArtifact:
    return _artifact().model_copy(update=overrides)


def _definition() -> AgentDefinition:
    loaded = yaml.safe_load(
        (FIXTURES / "agents" / "covenant_analytics.yaml").read_text()
    )
    definition = parse_artifact(loaded["agent_definition"], AGENT_DEFINITION)
    assert isinstance(definition, AgentDefinition)
    return definition


# --- validate_prompt_artifact -------------------------------------------------


def test_exact_parameter_agreement_validates() -> None:
    artifact = _artifact()
    validate_prompt_artifact(artifact)  # returns None, raises on defect
    # A1 pinned against the installed Jinja2: the declared set is exactly what
    # parse-only introspection reports.
    ast = jinja2.Environment().parse(artifact.template)
    assert set(artifact.declared_parameters) == jinja2.meta.find_undeclared_variables(
        ast
    )


def test_an_undeclared_template_variable_is_refused_by_name() -> None:
    artifact = _mutated(declared_parameters=("entity_name",))  # drops as_of
    with pytest.raises(PromptValidationError, match="as_of"):
        validate_prompt_artifact(artifact)


def test_a_declared_but_unused_parameter_is_refused_by_name() -> None:
    artifact = _mutated(
        declared_parameters=(*_artifact().declared_parameters, "jurisdiction")
    )
    with pytest.raises(PromptValidationError, match="jurisdiction"):
        validate_prompt_artifact(artifact)


def test_a_syntactically_invalid_template_chains_the_jinja_error() -> None:
    broken = _mutated(template=_artifact().template + "{% endfor %}")
    with pytest.raises(PromptValidationError) as excinfo:
        validate_prompt_artifact(broken)
    assert isinstance(excinfo.value.__cause__, jinja2.TemplateSyntaxError)


# --- validate_instruction_binding ----------------------------------------------


def test_a_matching_binding_validates() -> None:
    binding = _definition().instruction_bindings[0]
    validate_instruction_binding(binding, _artifact())


def test_a_binding_parameter_mismatch_is_refused() -> None:
    binding = _definition().instruction_bindings[0].model_copy(
        update={"parameters": ("entity_name",)}
    )
    with pytest.raises(PromptValidationError, match="as_of"):
        validate_instruction_binding(binding, _artifact())
