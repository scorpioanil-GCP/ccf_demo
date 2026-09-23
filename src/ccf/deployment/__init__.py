"""The adopter-facing wiring package — how a deployment is assembled, not run.

SDK-defined mechanism (CLAUDE.md §6.4 and §10). The whitepaper specifies the
Control Plane artifacts and the invariants that hold over them; it does not
specify the wiring that loads those artifacts and hands the assembled pieces to
a fabric. That wiring is the SDK's own extension, and this package is its home.
Nothing here is whitepaper-derived, and nothing here may quietly become an
implementation of something the whitepaper *does* specify.

The package began empty on purpose: it existed from the moment the phase's
standing guard existed (``tests/products/test_gate_independence.py``) so that the
guard had a real, non-vacuous target rather than being retrofitted around helpers
already written.

Modules
-------

* :mod:`ccf.deployment.binder` — the refusal that binds the product class's
  authored operator claim to the projection plan's own requirements (design E2,
  D-IMPL-86 as corrected 2026-08-05). It compares two authored documents; it
  does not run, and cannot feed, a validation gate.
* :mod:`ccf.deployment.classes` — class-id → ``ArtifactClass`` resolution, with
  deployment-authored schemas landing on the declared envelope by design, the
  ``ccf.`` prefix reserved so no envelope may wear an SDK class name
  (D-IMPL-84), and the roles and registration paths the SDK fixes for the
  classes where it owns the answer (D-IMPL-80, D-IMPL-85).
* :mod:`ccf.deployment.config` — the single-file `ccf_config.yaml` loader
  (D-IMPL-134, D-IMPL-136). ``derive_deployment`` derives a
  ``DeploymentManifest`` plus one materialised document per section from a
  parsed ``DeploymentConfig``, pure: no file is read and nothing is
  registered or booted. ``load_config_and_boot`` (`16-30`) is the front door
  that reads a real ``ccf_config.yaml``, derives, and boots — the config
  form's sibling to ``load_and_boot`` below, sharing its preflight and its
  register loop rather than carrying copies of either.
* :mod:`ccf.deployment.pins` — the plain ``(key, version, class_id)`` record a
  manifest load produces, with exactly one accessor and no binding-selection
  helpers.
* :mod:`ccf.deployment.manifest` — the load-validate-register-boot entry point.
  It wires a deployment together; it does not run the deployment.
* :mod:`ccf.deployment.operators` — the two-phase, view-aware operator-registry
  builder. The view is in the signature because the similarity index is built
  from a corpus read at a boundary the deployment named, never lazily at first
  invocation.

CINV-03: "algorithmic" means no model call, not no I/O
------------------------------------------------------

This package is tagged ``__ccf_mode__ = "algorithmic"`` and it will read files —
artifact documents, manifests, schema bundles. That is not a contradiction, and
the reading is written down here so the next contributor does not have to
re-derive it.

The CINV-03 checker, :mod:`tools.lints.algorithmic`, says exactly one thing: a
tagged module may not import the LLM client Protocol (``ccf.llm``) or a vendor
model SDK, at module scope or deferred inside a function. It says nothing at all
about the filesystem. The invariant is Algorithmic ⇄ Semantic Alternation —
LLMs never see raw signal (whitepaper §7.6.6) — and file I/O is orthogonal to
it. Two precedents in the tree carry the tag while doing I/O:

* ``src/ccf/boot.py`` carries the tag while opening SQLite files.
* ``src/ccf/controlplane/artifacts.py`` carries the tag while importing
  ``yaml`` to parse artifact documents.

The abstraction line: D-15A and the ``run_gates`` worked example
----------------------------------------------------------------

The defining risk of an ergonomics package is that a convenience helper
silently deletes a whitepaper invariant. The worked example is
:func:`ccf.products.gates.run_gates`.

That function takes the engine's resolved operator set *separately* from the
product's own lineage claim::

    run_gates(candidate, engine_resolved=..., now=..., registry=...,
              product_class=...)

``candidate.lineage.operators_invoked`` is the producer's Control Plane
*claim*, transcribed into the Contract from the ``ccf.product-class``
declaration; ``engine_resolved`` is what the projection engine reports from
executing the plan. Lineage strict equality (whitepaper §7.6, INV-CH7-47)
therefore verifies **assembly-path integrity** — that a served product matches
the assembly path the deployment said produced it. It is *not* an independent
witness of whether the claim was right to begin with: the engine builds
``operators_invoked`` and ``steps`` in one loop over the same operator plan
(``ccf.projection.engine``), so it has no return path where invoked ≠ planned.
It is a faithful transcriber (``D-IMPL-86`` and the ``D-IMPL-57`` correction of
2026-08-05).

That is precisely why the abstraction line below is drawn where it is, and the
corrected premise makes the case *stronger* rather than weaker. A helper that
computed both arguments from one input would leave the gate with nothing at all
to compare — not even a transcription — so it would be tautological, still
green, and a whitepaper invariant would be gone with no failing test to say so.
Where **authorable** drift fails instead is upstream, at
:func:`~ccf.deployment.binder.refuse_operator_set_divergence`, which compares
the product-class claim against the projection's own
``ccf.projection-requirements`` artifact. The two must not be blurred; blurring
them is what produced CR-2.

So this package draws its line here, operationally and without exception:

* No module in this package may import ``ccf.products.gates``. This is enforced
  by the ``cinv02-deployment-gates`` lint rule in
  ``tools/lints/harness_imports.py``, which takes no allowlist.
* No function in this package may accept a ``ProjectionExecution`` and return a
  ``ProductLineage`` — that signature *is* the collapse, whatever it is called.
* Gate execution stays in adopter code. This package wires a deployment
  together; it does not run the deployment's validation gates on the adopter's
  behalf.

Algorithmic package (CINV-03).
"""

from __future__ import annotations

from ccf.controlplane.artifacts import DeploymentManifest, ManifestEntry
from ccf.deployment.binder import refuse_operator_set_divergence
from ccf.deployment.classes import (
    SDK_ARTIFACT_CLASSES,
    SDK_ARTIFACT_ROLES,
    SDK_VERSIONED_ARTIFACT_CLASSES,
    refuse_registration_the_sdk_fixes,
    refuse_role_the_sdk_fixes,
    resolve_artifact_class,
)
from ccf.deployment.config import (
    DerivedDeployment,
    derive_deployment,
    load_config_and_boot,
)
from ccf.deployment.manifest import (
    BootedFabric,
    load_and_boot,
    register_manifest_entries,
)
from ccf.deployment.operators import (
    SimilarityCorpusAttributeError,
    build_operator_registry,
)
from ccf.deployment.pins import ArtifactPin, ResolvedPins, UnpinnedArtifactError
from ccf.deployment.environment import EnvironmentDocument, load_environment_document

__ccf_mode__ = "algorithmic"

__all__ = [
    "SDK_ARTIFACT_CLASSES",
    "SDK_ARTIFACT_ROLES",
    "SDK_VERSIONED_ARTIFACT_CLASSES",
    "ArtifactPin",
    "BootedFabric",
    "DeploymentManifest",
    "DerivedDeployment",
    "EnvironmentDocument",
    "ManifestEntry",
    "ResolvedPins",
    "SimilarityCorpusAttributeError",
    "UnpinnedArtifactError",
    "build_operator_registry",
    "derive_deployment",
    "load_and_boot",
    "load_config_and_boot",
    "load_environment_document",
    "refuse_operator_set_divergence",
    "refuse_registration_the_sdk_fixes",
    "refuse_role_the_sdk_fixes",
    # `D-GATE-cp-20` follow-up (Dave, 2026-09-22). ADDITIVE ONLY — the symbol
    # was already public at `ccf.deployment.manifest`, already in the
    # committed surface, and unchanged in behavior; what was missing was the
    # package-level spelling every adopter is told to use.
    #
    # The omission was accidental rather than deliberate, and the evidence is
    # its own siblings: `manifest.__all__` names three symbols and the other
    # two — `BootedFabric` and `load_and_boot` — were re-exported here from
    # the start. A public name reachable ONLY by the submodule path it is a
    # convention violation to write (`A-1`) is a surface with no legal
    # spelling, which is how cp-20 came to write the illegal one.
    "register_manifest_entries",
    "resolve_artifact_class",
]
