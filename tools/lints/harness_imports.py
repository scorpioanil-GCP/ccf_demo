"""CINV-02 — zero harness imports in core, plus the GraphWriter restriction.

CLAUDE.md §7.3 ("Zero harness imports in core") and §10 (single-writer
invariant). SDK-defined enforcement mechanism, not whitepaper-derived.

Three rules, one AST walk:

``cinv02-harness``
    Lint-enforced: no module outside ``ccf_runtime.adapters.*`` may import a
    harness package. A harness import in ``/src`` is a defect of the same class
    as an LLM client in an algorithmic module. The vendor LLM SDK
    (``anthropic``) is on the deny list everywhere *except* the LLM adapter
    path, where it is the adapter's whole purpose (D-IMPL-09).

``cinv02-graph-writer``
    The guarded set is a *class* of modules, not one path: the neutral write
    base ``ccf.graph._writer`` plus every per-backend write module
    ``ccf.graph.backends.<name>_write`` (D-01). This is layer 2 of the
    single-writer defence: even with a writer implementation on disk, no other
    module can name it.

    Naming the class rather than the instance is the lesson D-GATE-15.3 records
    the project learning three times in one phase. A rule pinned to one file
    stops enforcing anything the moment that file splits, and it stops
    *silently* — the rule still runs, still passes, and guards nothing. The
    membership test is therefore a predicate, :func:`is_write_module`, and a
    seventh adapter's write module joins the guarded set on arrival with no
    edit here.

    Two permitted-importer sets, not one, because the neutral base has one more
    legitimate consumer than a per-backend write module does. A per-backend
    write module keeps exactly today's permitted set — L2 (``ccf.assembly``)
    and the composition root (``ccf.boot``), i.e. ``WRITER_OK_MODULES``. The
    neutral base additionally permits ``ccf.graph.registry`` and the guarded
    write modules themselves (``NEUTRAL_WRITER_OK_MODULES``), because each
    write module subclasses ``BaseGraphWriter`` and implements the ``_GraphTxn``
    Protocol and so must be able to name the base.

    The registry carve-out has two limits and both are deliberate. It exists
    because the registry *types* the write seam — it names ``BaseGraphWriter``
    and ``BootToken`` so ``BackendRegistration.make_writer`` can be typed under
    ``mypy --strict`` — and it stops there: the registry never mints a token
    and never calls the factory. And it covers the neutral base only, never a
    per-backend write module; a test pins that asymmetry so widening one set
    cannot quietly widen the other.

    **Both spellings of an import are read** (review finding CR-02). The rule
    used to reason only about the names
    :func:`~tools.lints.imported_module_names` reports, which meant
    ``from ccf.graph import _writer`` was seen as ``ccf.graph`` and matched
    nothing — so any module under ``src/`` or ``runtime/`` could reach
    ``mint_boot_token`` and name a concrete writer class with zero findings,
    and a reader module could name a *different* adapter's write module with
    zero findings. Both spellings bind the submodule at runtime, so both are
    now resolved through :func:`~tools.lints.reached_module_names`, and the
    check reports at most one finding per import statement rather than one per
    spelling that statement matches.

    **Every half of the walk reads the same name set** (review finding F0). It
    did not always: the harness and vendor-LLM deny loop was left on
    :func:`~tools.lints.imported_module_names` when CR-02 moved the
    write-module check across, on the argument that expanding a *distribution*
    name would be a claim about a package this rule has no business making.
    That argument was wrong in the one direction that mattered. ``google.adk``
    is a deny entry with a dot in it, ``from google import adk`` is the
    idiomatic spelling of it, and under the old helper that statement produced
    no finding at all — while ``from google.adk import agents`` produced one.
    Expansion cannot over-reach here, because an expanded name only ever
    matches when it *equals or descends from* a deny entry: ``from google
    import protobuf`` expands to ``google.protobuf``, which matches nothing.

``cinv02-deployment-gates``
    The adopter-facing wiring package ``ccf.deployment`` may not import
    ``ccf.products.gates`` (D-15A). ``run_gates`` compares the product's
    declared lineage against the engine's resolved operator set, and the
    comparison is a real check only because those two values arrive from two
    independent sources. A wiring helper that ran the gate would be one step
    from deriving both from one input, which leaves the gate green, tautological,
    and a whitepaper invariant (§7.6, INV-CH7-47) deleted with nothing failing.
    Gate execution stays in adopter code. The paired mechanism is
    ``tests/products/test_gate_independence.py``, which refuses the *shape*
    where this rule refuses the *import*.

Scope, stated precisely (D-21 — claims are scoped to their enforcement).
``cinv02-harness`` is lint-enforced as: *no module outside
``ccf_runtime.adapters.*`` may import a harness package*. That narrows the
rule's scope to match CLAUDE.md §7.3's own word — "zero harness imports in
**core**" — rather than granting an exception to it; the adapter path is where
§7.3 places harness bindings, so a harness import there is the module's whole
purpose (D-IMPL-53, D-24).

No rule here takes an allowlist. Carve-outs are module-path constants in this
file, reviewed with the code, never a data file or per-module opt-out — a
data allowlist would void the invariant it exists to enforce.
"""

from __future__ import annotations

import ast
import pathlib

from tools.lints import (
    format_finding,
    matches_module,
    package_for,
    read_tree,
    reached_module_names,
)

RULE_HARNESS = "cinv02-harness"
RULE_GRAPH_WRITER = "cinv02-graph-writer"
RULE_DEPLOYMENT_GATES = "cinv02-deployment-gates"

#: Agent harnesses the SDK must never import. CCF layers onto a harness as the
#: trust-and-control plane; it never absorbs the loop (CLAUDE.md §7.3).
HARNESS_DENY: frozenset[str] = frozenset(
    {"google.adk", "langgraph", "claude_agent_sdk"}
)

#: Vendor LLM SDKs, permitted only inside the LLM adapter path below.
VENDOR_LLM_DENY: frozenset[str] = frozenset({"anthropic"})

#: Modules allowed to import a vendor LLM SDK (the LLMClientProtocol adapters).
LLM_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf.llm", "ccf_runtime.llm"})

#: The only module path where a harness import is the module's whole purpose:
#: the HarnessAdapterProtocol reference adapters, which CLAUDE.md §7.3 places in
#: ``runtime/adapters/<harness>/``. Match is dot-bounded, so ``adapters_evil``
#: and every other sibling remain denied.
HARNESS_ADAPTER_MODULES: frozenset[str] = frozenset({"ccf_runtime.adapters"})

#: The orchestrator-driver tree's OWN considered carve-out entry (D-IMPL-60
#: consequence (c)) — a distinct constant, not a widened prefix on the entry
#: above: each carve-out is reviewed on its own terms, and the D-24/D-IMPL-53
#: negative tests (a harness import in ``ccf_runtime.peering`` or
#: ``ccf_runtime.cdc`` still fails) prove the pair is not an unguarded prefix
#: match. Match is dot-bounded, so ``orchestration_evil`` and every other
#: sibling remain denied. An orchestrator SDK import is this tree's whole
#: purpose: each driver drives a CCF workflow through that SDK's own topology
#: surface (D-IMPL-17's second seam), with the CCF engine authoritative.
ORCHESTRATION_MODULES: frozenset[str] = frozenset({"ccf_runtime.orchestration"})

#: The neutral write base. Substrate-neutral machinery only after D-03: the
#: transaction Protocols, ``BootToken``, and ``BaseGraphWriter``.
WRITER_MODULE = "ccf.graph._writer"

#: The adapter package, and the suffix that marks a module inside it as a write
#: module. Together they are the guarded set's second half — see
#: :func:`is_write_module`. Neither names a substrate, so the set grows by
#: itself.
BACKENDS_PACKAGE = "ccf.graph.backends"
WRITE_MODULE_SUFFIX = "_write"

#: Permitted importers of a **per-backend** write module: L2 and the
#: composition root. Unchanged from before the writer split.
WRITER_OK_MODULES: frozenset[str] = frozenset({"ccf.assembly", "ccf.boot"})

#: The backend registry, which is permitted to name the *neutral base* only.
#: A reviewed named constant, not an allowlist line (D-13).
REGISTRY_MODULE = "ccf.graph.registry"

#: Permitted importers of the **neutral base**: the two above, plus the
#: registry (which types the seam without exercising it), plus any guarded
#: write module — each subclasses ``BaseGraphWriter`` and implements
#: ``_GraphTxn``, so each must be able to name the base. The write modules are
#: admitted by predicate in :func:`check_source` rather than by enumeration,
#: for the same reason the guarded set itself is a predicate.
NEUTRAL_WRITER_OK_MODULES: frozenset[str] = WRITER_OK_MODULES | {REGISTRY_MODULE}

#: The gate module and the one package denied it (D-15A). Both matches are
#: dot-bounded, so ``ccf.deployment_evil`` is not caught by accident while
#: ``ccf.deployment.manifest`` is. This rule is a denial, not a permission, so
#: it is the inverse shape of ``WRITER_OK_MODULES`` above: everything may import
#: the gates except this one package.
GATES_MODULE = "ccf.products.gates"
GATES_DENIED_IMPORTER = "ccf.deployment"


def is_write_module(name: str) -> bool:
    """True when `name` is a module the single-writer rule guards.

    That is: the neutral base :data:`WRITER_MODULE`, or a module inside
    :data:`BACKENDS_PACKAGE` whose final dotted segment ends with
    :data:`WRITE_MODULE_SUFFIX`. The package match is dot-bounded via
    :func:`~tools.lints.matches_module`, so a sibling package that merely shares
    a string prefix is not a member.
    """
    if name == WRITER_MODULE:
        return True
    return matches_module(name, (BACKENDS_PACKAGE,)) and name.rpartition(".")[
        2
    ].endswith(WRITE_MODULE_SUFFIX)


def check_source(source: str, path: pathlib.Path, module_name: str) -> list[str]:
    """Check already-read `source` attributed to `path` / `module_name`."""
    tree = read_tree(source, path)
    findings: list[str] = []
    package = package_for(path, module_name)
    in_llm_adapter = matches_module(module_name, LLM_ADAPTER_MODULES)
    in_deployment = matches_module(module_name, (GATES_DENIED_IMPORTER,))
    in_harness_adapter = matches_module(
        module_name, HARNESS_ADAPTER_MODULES
    ) or matches_module(module_name, ORCHESTRATION_MODULES)

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", 0)
        # Every name the statement reaches, for every rule in this walk — see
        # "Both spellings of an import are read" in the module docstring. One
        # finding per statement per rule, never one per spelling it matches:
        # `from google import adk` reaches both `google` and `google.adk`, and
        # naming the line twice is noise rather than evidence.
        reached = reached_module_names(node, package=package)

        denied_harness = sorted(n for n in reached if matches_module(n, HARNESS_DENY))
        if denied_harness and not in_harness_adapter:
            findings.append(
                format_finding(
                    path,
                    lineno,
                    RULE_HARNESS,
                    f"harness import {denied_harness[0]!r} is forbidden in core"
                    " (CLAUDE.md §7.3); bind harnesses in"
                    " runtime/adapters/<harness>/ instead",
                )
            )

        denied_vendor = sorted(n for n in reached if matches_module(n, VENDOR_LLM_DENY))
        if denied_vendor and not in_llm_adapter:
            findings.append(
                format_finding(
                    path,
                    lineno,
                    RULE_HARNESS,
                    f"vendor LLM import {denied_vendor[0]!r} is allowed only"
                    " inside the LLMClientProtocol adapter path"
                    f" ({', '.join(sorted(LLM_ADAPTER_MODULES))})",
                )
            )

        guarded = sorted(n for n in reached if is_write_module(n))
        if guarded:
            name = guarded[0]
            neutral = name == WRITER_MODULE
            permitted = NEUTRAL_WRITER_OK_MODULES if neutral else WRITER_OK_MODULES
            allowed = matches_module(module_name, permitted) or (
                neutral and is_write_module(module_name)
            )
            if not allowed:
                where = ", ".join(sorted(permitted))
                if neutral:
                    where += ", and any guarded write module"
                findings.append(
                    format_finding(
                        path,
                        lineno,
                        RULE_GRAPH_WRITER,
                        f"GraphWriter module {name!r} is importable only"
                        f" from {where}"
                        f" (single-writer invariant, CLAUDE.md §10);"
                        f" {module_name!r} may not name it",
                    )
                )

        if not in_deployment:
            continue
        # One finding per import statement, not one per spelling it matches:
        # ``from ccf.products.gates import run_gates`` matches on both the
        # module name and the expanded ``...gates.run_gates``, and reporting
        # the same line twice is noise, not evidence.
        denied = sorted(n for n in reached if matches_module(n, (GATES_MODULE,)))
        if denied:
            findings.append(
                format_finding(
                    path,
                    getattr(node, "lineno", 0),
                    RULE_DEPLOYMENT_GATES,
                    f"{module_name!r} may not import {denied[0]!r}. Gate execution"
                    " stays in adopter code so run_gates keeps two"
                    " independently sourced inputs (D-15A; whitepaper §7.6).",
                )
            )

    return findings


def check(path: pathlib.Path, module_name: str) -> list[str]:
    """Check the Python file at `path`, whose dotted name is `module_name`."""
    return check_source(path.read_text(encoding="utf-8"), path, module_name)
