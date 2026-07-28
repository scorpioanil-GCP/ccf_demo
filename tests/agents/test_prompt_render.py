"""T-06-60 — the first ``render(...)`` in ``/src``, and what holds it shut.

`PHASE_I2_GATE.md` §5 deferred the Jinja2 SSTI question on the stated grounds
that nothing in `/src` rendered. `ccf.agents.prompts.render_instruction` is the
render that ends that deferral, so these tests are the control, not a
description of it. Each one fails if the corresponding control is removed:

* remove ``SandboxedEnvironment`` → :func:`test_a_sandbox_escape_is_refused`
  and the three attribute-traversal cases fail (verified by temporary edit);
* widen the render context → :func:`test_the_context_is_exactly_the_pinned_parameters`
  fails;
* make the render non-deterministic → :func:`test_rendering_twice_is_identical`
  fails.
"""

from __future__ import annotations

import inspect

import pytest

from ccf.agents.definitions import InstructionBinding, PromptArtifact
from ccf.agents.errors import PromptRenderRefused
from ccf.agents.prompts import render_instruction

PROMPT_URI = "ccf-artifact://tenant-a/ccf.prompt-artifact/covenant-brief@1.0.0"


def _artifact(template: str, parameters: tuple[str, ...]) -> PromptArtifact:
    return PromptArtifact(
        name="covenant-brief",
        tenant="tenant-a",
        schema_version="1.0.0",
        artifact_version="1.0.0",
        template=template,
        declared_parameters=parameters,
    )


def _binding(parameters: tuple[str, ...]) -> InstructionBinding:
    return InstructionBinding(prompt=PROMPT_URI, parameters=parameters)


# --------------------------------------------------------------------------
# The sandbox (T-06-60)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "escape",
    [
        "{{ borrower.__class__ }}",
        "{{ borrower.__class__.__mro__ }}",
        "{{ borrower.__init__.__globals__ }}",
        "{{ borrower.__class__.__base__.__subclasses__() }}",
    ],
)
def test_a_sandbox_escape_is_refused(escape: str) -> None:
    """The escape vocabulary is refused by the sandbox, never executed.

    This is the test that fails if ``SandboxedEnvironment`` is swapped for a
    plain ``jinja2.Environment`` — under which ``{{ borrower.__class__ }}``
    renders ``<class 'str'>`` and the rest walk out of the template into the
    interpreter.
    """
    with pytest.raises(PromptRenderRefused) as refusal:
        render_instruction(
            binding=_binding(("borrower",)),
            artifact=_artifact(escape, ("borrower",)),
            parameter_values={"borrower": "Northwind Freight"},
        )
    assert "sandbox" in str(refusal.value)


def test_the_module_uses_the_sandboxed_environment_and_not_a_plain_one() -> None:
    """Pinned at the source level too — the swap must be visible, not subtle."""
    from ccf.agents import prompts

    source = inspect.getsource(prompts)
    assert "SandboxedEnvironment" in source
    # Not merely "the render is sandboxed" — there is no plain environment
    # anywhere in the module for a later edit to reach for by mistake.
    assert "jinja2.Environment(" not in source


# --------------------------------------------------------------------------
# The pinned-parameters-only context (T-06-60)
# --------------------------------------------------------------------------


def test_the_context_is_exactly_the_pinned_parameters() -> None:
    """Enumerate the context: what renders is what was pinned, and only that."""
    rendered = render_instruction(
        binding=_binding(("borrower", "facility")),
        artifact=_artifact(
            "{{ borrower }} holds {{ facility }}.", ("borrower", "facility")
        ),
        parameter_values={"borrower": "Northwind Freight", "facility": "FAC-1"},
    )
    assert rendered == "Northwind Freight holds FAC-1."


def test_the_signature_admits_no_arbitrary_context_argument() -> None:
    """The control is the *shape*: there is no parameter that widens the context.

    No ``**kwargs``, no ``context``, no ``extra`` — a caller holding a Context
    Product, an MCP response, or an inbound A2A payload has nowhere to put it.
    """
    signature = inspect.signature(render_instruction)
    assert set(signature.parameters) == {"binding", "artifact", "parameter_values"}
    for parameter in signature.parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_a_surplus_value_is_refused_rather_than_dropped() -> None:
    """A silently-ignored extra key is what a widened context looks like."""
    with pytest.raises(PromptRenderRefused) as refusal:
        render_instruction(
            binding=_binding(("borrower",)),
            artifact=_artifact("{{ borrower }}", ("borrower",)),
            parameter_values={
                "borrower": "Northwind Freight",
                "smuggled_product_payload": "…",
            },
        )
    assert "surplus ['smuggled_product_payload']" in str(refusal.value)


def test_a_missing_value_is_refused_rather_than_defaulted() -> None:
    """D-IMPL-38: the SDK ships no silent default, here least of all."""
    with pytest.raises(PromptRenderRefused) as refusal:
        render_instruction(
            binding=_binding(("borrower", "facility")),
            artifact=_artifact(
                "{{ borrower }} {{ facility }}", ("borrower", "facility")
            ),
            parameter_values={"borrower": "Northwind Freight"},
        )
    assert "missing ['facility']" in str(refusal.value)


def test_a_name_outside_the_pinned_parameters_resolves_to_nothing() -> None:
    """No reach into the surrounding scope, and no empty string in its place.

    The D-13 exact-match validator refuses the artifact first, which is the
    outer control; the point of the test is that the outcome is a refusal
    rather than a template that quietly renders around the unknown name.
    """
    with pytest.raises((PromptRenderRefused, ValueError)):
        render_instruction(
            binding=_binding(("borrower",)),
            artifact=_artifact(
                "{{ borrower }} {{ render_instruction }}", ("borrower",)
            ),
            parameter_values={"borrower": "Northwind Freight"},
        )


# --------------------------------------------------------------------------
# Determinism (T-06-64)
# --------------------------------------------------------------------------


def test_rendering_twice_is_identical() -> None:
    """One agent version renders one instruction — the adapter re-resolves nothing."""
    binding = _binding(("borrower",))
    artifact = _artifact("Assess {{ borrower }}.", ("borrower",))
    values = {"borrower": "Northwind Freight"}
    first = render_instruction(
        binding=binding, artifact=artifact, parameter_values=values
    )
    second = render_instruction(
        binding=binding, artifact=artifact, parameter_values=values
    )
    assert first == second == "Assess Northwind Freight."


def test_the_stale_no_render_claim_is_gone() -> None:
    """The module no longer claims something that stopped being true."""
    from ccf.agents import prompts

    source = inspect.getsource(prompts)
    assert "there is no ``render`` call" not in source
    assert "no ``render`` call in this module" not in source
