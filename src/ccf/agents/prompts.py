"""Parse-only prompt-artifact validation (CLAUDE.md §6.2 axis 6 — SDK-defined; D-13).

Instruction bindings are the sixth specialization axis: references to
versioned prompt artifacts, never inline text (No-Hardcoding Rule, §6.4).
The D-13 ruling fixes what I.2 does with them — **full construction-time
validation, no render-to-LLM**. This module is that validation:
``jinja2.Environment().parse()`` plus
``jinja2.meta.find_undeclared_variables()``, introspection only.

**The exact-match rule, both directions.** ``declared_parameters`` must equal
the template's undeclared-variable set exactly. A template variable nobody
declared is the obvious defect; a declared-but-unused parameter is refused
too, because a declaration the template ignores is a claim the artifact makes
and does not honor — a caller supplying that parameter believes it conditions
the output, and it never does. Silent asymmetry here is the prompt-shaped
version of a silent default (D-IMPL-38).

**No rendering surface exists.** There is no ``render`` call in this module
or anywhere in ``/src``; rendering into harness-ready strings is I.3 adapter
work. Parse-only is also the SSTI posture for I.2 (threat T-05-03, accepted):
no user-controlled render context exists because nothing renders.

Text and contracts in, refusals out — file I/O stays with callers, in the
same discipline as :func:`ccf.controlplane.artifacts.load_artifact`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

import jinja2
import jinja2.meta

from ccf.agents.definitions import InstructionBinding, PromptArtifact
from ccf.agents.errors import PromptValidationError

__ccf_mode__ = "algorithmic"

__all__ = ["validate_instruction_binding", "validate_prompt_artifact"]


def _template_parameters(artifact: PromptArtifact) -> frozenset[str]:
    """Return the template's undeclared-variable set, or refuse the artifact.

    Raises:
        PromptValidationError: the template does not parse; chained from the
            underlying ``jinja2.TemplateSyntaxError``.
    """
    environment = jinja2.Environment()  # no loader: nothing to include from
    try:
        ast = environment.parse(artifact.template)
    except jinja2.TemplateSyntaxError as error:
        raise PromptValidationError(
            f"prompt artifact {artifact.name!r} does not parse: {error}"
        ) from error
    return frozenset(jinja2.meta.find_undeclared_variables(ast))


def validate_prompt_artifact(artifact: PromptArtifact) -> None:
    """Hold a prompt artifact to exact parameter agreement (D-13).

    Parse-only: the template is introspected, never rendered. Validation
    succeeds exactly when ``declared_parameters`` equals the set of variables
    the template actually uses.

    Raises:
        PromptValidationError: the template does not parse, uses a variable
            the artifact never declared, or declares a parameter the template
            never uses.
    """
    used = _template_parameters(artifact)
    declared = frozenset(artifact.declared_parameters)
    undeclared = used - declared
    if undeclared:
        raise PromptValidationError(
            f"prompt artifact {artifact.name!r} uses template parameter(s)"
            f" {sorted(undeclared)} it never declares (D-13: declared"
            " parameters and template variables must match exactly)"
        )
    unused = declared - used
    if unused:
        raise PromptValidationError(
            f"prompt artifact {artifact.name!r} declares parameter(s)"
            f" {sorted(unused)} its template never uses (D-13 exact-match:"
            " an ignored declaration is a claim the artifact does not honor)"
        )


def validate_instruction_binding(
    binding: InstructionBinding, artifact: PromptArtifact
) -> None:
    """Hold an instruction binding to the artifact it references (D-13).

    The binding's declared parameter names must equal the artifact's — order
    is the binding's business, membership is not. The artifact itself is
    re-validated first, so a binding can never validate against a prompt that
    would itself be refused.

    Raises:
        PromptValidationError: the artifact fails :func:`validate_prompt_artifact`,
            or the binding's parameters mismatch the artifact's declaration.
    """
    validate_prompt_artifact(artifact)
    bound = frozenset(binding.parameters)
    declared = frozenset(artifact.declared_parameters)
    if bound != declared:
        missing = sorted(declared - bound)
        surplus = sorted(bound - declared)
        raise PromptValidationError(
            f"instruction binding for {artifact.name!r} mismatches the"
            f" artifact's declared parameters: missing {missing},"
            f" surplus {surplus} (CLAUDE.md §6.2 axis 6; D-13)"
        )
