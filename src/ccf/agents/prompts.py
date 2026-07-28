"""Prompt-artifact validation and the sandboxed render (CLAUDE.md §6.2 axis 6 — SDK-defined; D-13).

Instruction bindings are the sixth specialization axis: references to
versioned prompt artifacts, never inline text (No-Hardcoding Rule, §6.4).
The D-13 ruling fixes what I.2 does with them — **full construction-time
validation, no render-to-LLM**. That validation is still here, unchanged in
substance: ``.parse()`` plus ``jinja2.meta.find_undeclared_variables()``,
introspection only. It now runs on the same sandboxed environment the render
uses, so this module has exactly **one** environment idiom and no reviewer has
to decide which of two is the safe one.

**The exact-match rule, both directions.** ``declared_parameters`` must equal
the template's undeclared-variable set exactly. A template variable nobody
declared is the obvious defect; a declared-but-unused parameter is refused
too, because a declaration the template ignores is a claim the artifact makes
and does not honor — a caller supplying that parameter believes it conditions
the output, and it never does. Silent asymmetry here is the prompt-shaped
version of a silent default (D-IMPL-38).

**The render surface, and what actually holds it shut** (I.3; T-06-60).
:func:`render_instruction` is the SDK's *only* render entry point, added here
rather than inside an adapter because the seam that calls it — context
injection, CLAUDE.md §7.3 seam 1 — has three implementations and one of them
getting the sandbox wrong would be three chances to get it wrong. I.2's
"nothing renders, so there is no SSTI surface" posture no longer applies: I.3
makes artifact sources remote-influenced (MCP artifact stores, A2A federation),
so a prompt template is attacker-influenced input that becomes executable.

Two controls, both structural, and both stated at the scope they actually
enforce (D-21) rather than as "no path":

* **The environment is** ``jinja2.sandbox.SandboxedEnvironment``, never a plain
  ``jinja2.Environment``. Attribute traversal to ``__class__``, ``__globals__``,
  ``__subclasses__`` and the rest of the escape vocabulary raises
  ``jinja2.exceptions.SecurityError``, which this module converts into a typed
  :class:`~ccf.agents.errors.PromptRenderRefused`. This is Jinja2's own control,
  not a filter written here: a hand-rolled denylist of dunder names is the
  version of this control that gets bypassed.
* **The render context is built only from the pinned parameters**, and by
  *shape* rather than by discipline: :func:`render_instruction` takes the
  binding and a value mapping whose keys must equal the binding's declared
  parameters exactly, so there is no argument through which a caller could
  widen the context. No Context Product content, no skill-invocation result, no
  inbound A2A payload, and no MCP response can enter — not because callers are
  trusted not to pass them, but because there is no parameter that accepts them.
  Values are ``str``, so no object with an interesting attribute graph reaches
  the template in the first place.

**The adapter must not re-resolve prompt artifacts.** ``PHASE_I2_GATE.md`` §5 is
explicit that the Agent Factory already resolves and pins prompt artifacts onto
the agent; the context-injection seam *consumes* them
(:meth:`ccf.agents.agent.Agent.instruction_artifact`). Re-resolution in an
adapter would let two decisions under the same agent version render different
instructions, which makes the agent version a claim the record cannot honor
(T-06-64). Adapter authors in 06-12 through 06-14: this paragraph is for you.

Text and contracts in, refusals out — file I/O stays with callers, in the
same discipline as :func:`ccf.controlplane.artifacts.load_artifact`.

Algorithmic module (CINV-03).
"""

from __future__ import annotations

from collections.abc import Mapping

import jinja2
import jinja2.meta
import jinja2.sandbox

from ccf.agents.definitions import InstructionBinding, PromptArtifact
from ccf.agents.errors import PromptRenderRefused, PromptValidationError

__ccf_mode__ = "algorithmic"

__all__ = [
    "render_instruction",
    "validate_instruction_binding",
    "validate_prompt_artifact",
]


def _sandbox() -> jinja2.sandbox.SandboxedEnvironment:
    """The module's one Jinja2 environment, sandboxed (T-06-60).

    Both the parse-only validators and :func:`render_instruction` use this, so
    there is no plain ``Environment`` anywhere in the module for a later edit to
    reach for by mistake. No loader: there is nothing to ``include`` from, and a
    loader would be a second source of template text this module does not
    validate. ``StrictUndefined`` so an unpinned name is an error rather than an
    empty string (D-IMPL-38).
    """
    return jinja2.sandbox.SandboxedEnvironment(
        undefined=jinja2.StrictUndefined,
        autoescape=False,  # instructions are prose for a model, not markup
    )


def _template_parameters(artifact: PromptArtifact) -> frozenset[str]:
    """Return the template's undeclared-variable set, or refuse the artifact.

    Raises:
        PromptValidationError: the template does not parse; chained from the
            underlying ``jinja2.TemplateSyntaxError``.
    """
    environment = _sandbox()
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


def render_instruction(
    *,
    binding: InstructionBinding,
    artifact: PromptArtifact,
    parameter_values: Mapping[str, str],
) -> str:
    """Render ``artifact``'s template under the binding's pinned parameters.

    The SDK's **only** render entry point (T-06-60), and the one the harness
    context-injection seam calls (CLAUDE.md §7.3 seam 1). See the module
    docstring for the two structural controls; the shape of this signature is
    the second of them.

    ``parameter_values`` keys must equal ``binding.parameters`` exactly — both
    directions, matching the D-13 exact-match rule the validators already
    apply to names. A surplus key is refused rather than dropped, because a
    caller supplying it believes it conditions the output and the *reason* it
    would not is precisely the control this function exists to enforce; a
    silently-ignored extra key is how a widened render context looks from the
    outside. A missing key is refused rather than defaulted (D-IMPL-38).

    The binding and artifact are re-validated first, so a render can never
    succeed against a prompt that :func:`validate_instruction_binding` would
    refuse — which also means the template's variable set is exactly
    ``binding.parameters`` by the time anything renders, and a name from the
    surrounding scope is not something the template can reach for.
    ``StrictUndefined`` holds the same line a second time, in the case where a
    future caller reaches this function by another route.

    Deterministic: the same artifact version and the same values render the
    same string, every time. Nothing here reads a clock, an environment
    variable, or a file.

    Args:
        binding: The instruction binding the agent pinned (axis 6).
        artifact: The prompt artifact ``binding`` references, already resolved
            by the Agent Factory. **Do not re-resolve it in an adapter** — see
            the module docstring (T-06-64).
        parameter_values: Values for exactly the binding's declared parameters.

    Returns:
        The rendered instruction string.

    Raises:
        PromptValidationError: the artifact or binding is inadmissible (D-13).
        PromptRenderRefused: the supplied keys are not exactly the binding's
            declared parameters, or the template attempted a sandbox escape.
    """
    validate_instruction_binding(binding, artifact)

    pinned = frozenset(binding.parameters)
    supplied = frozenset(parameter_values)
    if supplied != pinned:
        missing = sorted(pinned - supplied)
        surplus = sorted(supplied - pinned)
        raise PromptRenderRefused(
            f"render context for {artifact.name!r} is not exactly the pinned"
            f" parameters: missing {missing}, surplus {surplus}. The render"
            " context is built only from the binding's pinned parameters —"
            " no Context Product content, skill result, MCP response, or"
            " inbound A2A payload may enter it (T-06-60; CLAUDE.md §6.2 axis 6)"
        )

    # Sandboxed, never a plain environment: prompt templates are versioned
    # artifacts and I.3 makes artifact sources remote-influenced, so a plain
    # environment is server-side template injection with extra steps.
    environment = _sandbox()
    try:
        template = environment.from_string(artifact.template)
    except jinja2.TemplateSyntaxError as error:  # pragma: no cover - validated above
        raise PromptRenderRefused(
            f"prompt artifact {artifact.name!r} does not parse: {error}"
        ) from error

    # The context is constructed here, from the pinned values and nothing else.
    # There is no argument through which a caller could add to it.
    context = {name: parameter_values[name] for name in binding.parameters}
    try:
        return template.render(context)
    except jinja2.exceptions.SecurityError as error:
        raise PromptRenderRefused(
            f"prompt artifact {artifact.name!r} attempted an operation the"
            f" Jinja2 sandbox forbids: {error}. Templates are versioned"
            " artifacts from sources I.3 makes remote-influenced; the escape"
            " is refused, never rendered around (T-06-60)"
        ) from error
    except jinja2.UndefinedError as error:
        raise PromptRenderRefused(
            f"prompt artifact {artifact.name!r} referenced a name outside its"
            f" pinned parameters: {error}. Undefined names resolve to nothing"
            " from the surrounding scope, and rendering an empty string in"
            " their place would be a silent default (D-IMPL-38)"
        ) from error
