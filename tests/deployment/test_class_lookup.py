"""The class-id lookup: SDK coverage, declared fallthrough, and anti-drift.

**What these tests enforce, exactly.** Four things, each narrow:

(a) Every entry in :data:`~ccf.deployment.classes.SDK_ARTIFACT_CLASSES` resolves
    to the *same object* :mod:`ccf.controlplane.artifacts` exposes — object
    identity, not equality, so an equal-looking copy that has drifted from the
    real constant cannot pass.
(b) Every ``ArtifactClass`` constant :mod:`ccf.controlplane.artifacts` exposes
    appears in the mapping. This is the assertion that makes a hand-maintained
    mapping safe: an SDK artifact class that a manifest cannot address is a class
    no adopter can register, and the failure message names the file to edit.
(c) An id the SDK does not own resolves to the ``DeclaredArtifact`` envelope and
    a document parses through it, class-id intact.
(d) An empty or whitespace-only id is refused.

**What they do not enforce.** Nothing here says a given class-id is *correct*
for a given artifact document. That is the manifest author's decision, and the
closed-world contract's job to reject when it is wrong — the lookup's only claim
is that the string reaches a contract at all.

**Why (b) scans module attributes rather than ``__all__``.** 15-06 specified (b)
over ``ccf.controlplane.artifacts.__all__``, but that set was *vacuous* for the
purpose at the time: ``__all__`` listed the classes and functions while the
shipped ``ArtifactClass`` **instances** were absent from it, so an
``__all__``-only scan would have found zero instances and passed while proving
nothing. 15-07 owns ``artifacts.py`` and has since added ``HALF_LIFE_TABLE``,
``DEBT_PROFILE`` and ``RESOLUTION_SPEC`` to ``__all__``, closing that gap. The
attribute scan is kept regardless, because it is a *superset* of the ``__all__``
names: it still catches a constant that is declared but never exported, which is
exactly the drift an ``__all__``-only scan would now wave through.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from tools.dump_surface import build_surface, diff_surfaces

from ccf.controlplane import artifacts
from ccf.controlplane.artifacts import (
    ArtifactClass,
    DeclaredArtifact,
    parse_artifact,
)
from ccf.deployment import SDK_ARTIFACT_CLASSES, resolve_artifact_class

_EDIT_ME = "ccf/deployment/classes.py"

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LIVE_MANIFEST = _REPO_ROOT / "docs" / "surface" / "v0.2-surface.json"
_FRAGMENT_DIR = _REPO_ROOT / "docs" / "surface-changes"


def _exported_artifact_classes() -> dict[str, ArtifactClass]:
    """Every public ``ArtifactClass`` instance the artifacts module exposes."""
    return {
        name: value
        for name, value in vars(artifacts).items()
        if not name.startswith("_") and isinstance(value, ArtifactClass)
    }


# --- the scan is only worth anything if it scanned something ------------------


def test_the_sdk_artifact_classes_were_actually_discovered() -> None:
    """A discovery helper that silently found nothing is the quietest way this
    anti-drift test stops being one — see the module docstring's deviation
    note for why an ``__all__`` scan would have been exactly that."""
    discovered = _exported_artifact_classes()
    assert len(discovered) >= 2, discovered
    assert {"HALF_LIFE_TABLE", "DEBT_PROFILE"} <= set(discovered)
    assert SDK_ARTIFACT_CLASSES, "the lookup mapping is empty"


# --- (a) SDK ids resolve to the SDK's own object ------------------------------


@pytest.mark.parametrize("class_id", sorted(SDK_ARTIFACT_CLASSES))
def test_an_sdk_class_id_resolves_to_the_constant_itself(class_id: str) -> None:
    resolved = resolve_artifact_class(class_id)
    assert resolved is SDK_ARTIFACT_CLASSES[class_id]
    assert resolved.class_id == class_id


def test_every_mapping_entry_is_the_module_constant() -> None:
    """Identity against the artifacts module, so a copy cannot pass."""
    by_id = {value.class_id: value for value in _exported_artifact_classes().values()}
    for class_id, artifact_class in SDK_ARTIFACT_CLASSES.items():
        assert artifact_class is by_id[class_id], class_id


# --- (b) the mapping cannot fall behind the SDK's own exports -----------------


def test_every_exported_artifact_class_is_manifest_addressable() -> None:
    missing = {
        name: value.class_id
        for name, value in _exported_artifact_classes().items()
        if value.class_id not in SDK_ARTIFACT_CLASSES
    }
    assert not missing, (
        "ccf.controlplane.artifacts exports ArtifactClass constants that no"
        f" manifest can address: {missing}. An SDK class that a manifest cannot"
        f" name is a class no adopter can register — add it to {_EDIT_ME}."
    )


# --- (c) a class-id the SDK does not own takes the declared envelope ----------


def test_an_unknown_class_id_takes_the_declared_envelope() -> None:
    resolved = resolve_artifact_class("acme.policy-bundle")
    assert resolved.contract is DeclaredArtifact
    assert resolved.class_id == "acme.policy-bundle"


def test_a_declared_document_parses_through_the_fallthrough() -> None:
    resolved = resolve_artifact_class("acme.policy-bundle")
    document: dict[str, Any] = {
        "semver": "0.1.0",
        "class_id": "acme.policy-bundle",
        "declaration": {"anything": "the deployment says"},
    }
    parsed = parse_artifact(document, resolved)
    assert isinstance(parsed, DeclaredArtifact)
    assert parsed.class_id == resolved.class_id


def test_the_declared_path_cannot_shadow_an_sdk_class() -> None:
    """SDK ids resolve from the reviewed constant first (T-15-06-01)."""
    for class_id in SDK_ARTIFACT_CLASSES:
        assert resolve_artifact_class(class_id).contract is not DeclaredArtifact


# --- (d) refusal --------------------------------------------------------------


@pytest.mark.parametrize("class_id", ["", " ", "\t\n"])
def test_an_unnamed_class_id_is_refused(class_id: str) -> None:
    with pytest.raises(ValueError, match="empty artifact class id"):
        resolve_artifact_class(class_id)


# --- this plan's own surface claim, checked at its own wave -------------------


def _fragment_public_added() -> set[str]:
    """``Surface`` values across **every** fragment that are ``added`` + public.

    Every fragment, not only this plan's. The manifest is frozen between 15-01
    and 15-21, so its accumulated ``added`` set grows with each merged plan in
    between; scanning one fragment would make this test fail for plan *N* the
    moment plan *N+1* added a name — a permanent false red that says nothing
    about either plan's correctness (found in wave 4 by 15-07, whose seven
    additions broke a single-fragment scan).

    Both assertion directions survive the widening. ``added <= claimed`` still
    catches an entry any plan forgot to write, because no other fragment claims
    a name its author never recorded; ``claimed <= added`` still catches a
    fragment claiming a name the tree does not actually export.
    """
    claimed: set[str] = set()
    for fragment in sorted(_FRAGMENT_DIR.glob("*.md")):
        if fragment.name == "README.md":
            continue
        surface: str | None = None
        public = False
        change: str | None = None
        for line in fragment.read_text(encoding="utf-8").splitlines() + ["## "]:
            stripped = line.strip()
            if stripped.startswith("## ") or stripped.startswith("- Surface: "):
                if surface and public and change == "added":
                    claimed.add(surface)
                surface, public, change = None, False, None
            if stripped.startswith("- Surface: "):
                surface = stripped.removeprefix("- Surface: ").strip()
            elif stripped.startswith("- Public surface: "):
                public = stripped.removeprefix("- Public surface: ").strip() == "true"
            elif stripped.startswith("- Change type: "):
                change = stripped.removeprefix("- Change type: ").strip()
    return claimed


def test_the_phases_fragments_claim_exactly_what_was_added() -> None:
    """Subset-equality in **both** directions, asserted at each plan's own wave.

    An entry a plan forgot to write fails here, at the wave that added it,
    rather than in 15-21's completeness cross-check at wave 14 — the most
    expensive point in the phase to discover it.
    """
    committed = json.loads(_LIVE_MANIFEST.read_text(encoding="utf-8"))
    added = set(diff_surfaces(committed, build_surface())["added"])
    claimed = _fragment_public_added()
    assert added <= claimed, f"added but unclaimed: {sorted(added - claimed)}"
    assert claimed <= added, f"claimed but not added: {sorted(claimed - added)}"


def test_this_plan_left_the_surface_manifests_alone() -> None:
    """The single-owner rule (docs/surface-changes/README.md): only 15-01 and
    15-21 write these files."""
    assert _LIVE_MANIFEST.is_file()
    assert (_LIVE_MANIFEST.parent / "v0.2-surface-baseline.json").is_file()
