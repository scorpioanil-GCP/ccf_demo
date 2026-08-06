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
(e) The versioned-registerable mapping matches the contracts that actually
    declare an ``artifact_version``, the two SDK mappings are disjoint and both
    precede the envelope, the reserved ``ccf.`` prefix is refused and no other
    namespace is (D-IMPL-84), and
    :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes` is held in
    **both** directions (D-IMPL-85).

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

import importlib
import json
import pathlib
import pkgutil
from typing import Any

import pytest

from tools.dump_surface import build_surface, diff_surfaces

import ccf

from ccf.controlplane import artifacts
from ccf.controlplane.artifacts import (
    ArtifactClass,
    DeclaredArtifact,
    parse_artifact,
)
from ccf.deployment import (
    SDK_ARTIFACT_CLASSES,
    SDK_VERSIONED_ARTIFACT_CLASSES,
    refuse_registration_the_sdk_fixes,
    resolve_artifact_class,
)

_EDIT_ME = "ccf/deployment/classes.py"

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LIVE_MANIFEST = _REPO_ROOT / "docs" / "surface" / "v0.2-surface.json"
#: The frozen phase-start copy — the "before" side of the accumulated diff this
#: module cross-checks the fragments against. See
#: :func:`test_the_phases_fragments_claim_exactly_what_was_added` for why the
#: *frozen* file and not the live one.
_FROZEN_BASELINE = (
    _REPO_ROOT / "docs" / "surface" / "v0.2-surface-baseline.json"
)
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


# --- (e) the versioned-registerable mapping, and the ccf. reservation ---------


def _every_sdk_artifact_class() -> dict[str, ArtifactClass]:
    """Every ``ArtifactClass`` instance any module under ``ccf`` exposes.

    Wider than :func:`_exported_artifact_classes` on purpose: the
    author-versioned classes live in ``ccf.workflow``, ``ccf.agents`` and
    ``ccf.skills``, not in ``ccf.controlplane.artifacts``, so the narrower scan
    cannot see the set this section is about.
    """
    discovered: dict[str, ArtifactClass] = {}
    for module_info in pkgutil.walk_packages(ccf.__path__, "ccf."):
        try:
            module = importlib.import_module(module_info.name)
        except ImportError:  # pragma: no cover - optional extras
            continue
        for name, value in vars(module).items():
            if not name.startswith("_") and isinstance(value, ArtifactClass):
                discovered[value.class_id] = value
    return discovered


def _author_versioned_class_ids() -> set[str]:
    """SDK class ids whose contract declares an ``artifact_version`` field.

    **Computed, never listed.** A hand-written list here would be a second copy
    of :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES` checked
    against the first — which proves the two lists agree and nothing about
    either agreeing with the code.
    """
    return {
        class_id
        for class_id, artifact_class in _every_sdk_artifact_class().items()
        if "artifact_version" in artifact_class.contract.model_fields
    }


def test_the_wider_artifact_class_scan_found_something() -> None:
    """The same non-vacuity guard the narrow scan carries, for the same reason.

    A walker that silently imported nothing would make every assertion below
    trivially true — and these are the assertions that keep the versioned
    mapping from falling behind.
    """
    discovered = _every_sdk_artifact_class()
    assert len(discovered) > len(_exported_artifact_classes()), discovered
    assert _author_versioned_class_ids(), (
        "no SDK artifact class declares artifact_version — the scan reached no"
        " author-versioned module"
    )


def test_every_author_versioned_class_is_in_the_versioned_mapping() -> None:
    """The anti-drift assertion, computed from the contracts themselves.

    An SDK class that declares an ``artifact_version`` and is absent from
    :data:`~ccf.deployment.classes.SDK_VERSIONED_ARTIFACT_CLASSES` is a class a
    manifest can only reach down the ``typed`` path — which is CR-1 reopening
    under a new class id.
    """
    author_versioned = _author_versioned_class_ids()
    missing = author_versioned - set(SDK_VERSIONED_ARTIFACT_CLASSES)
    assert not missing, (
        "these SDK classes declare artifact_version but no manifest can name"
        f" them for versioned registration: {sorted(missing)} — add them to"
        f" {_EDIT_ME}."
    )
    stowaways = set(SDK_VERSIONED_ARTIFACT_CLASSES) - author_versioned
    assert not stowaways, (
        f"{sorted(stowaways)} are in SDK_VERSIONED_ARTIFACT_CLASSES but their"
        " contracts declare no artifact_version, so register_versioned would"
        " raise TypeError on them."
    )


def test_the_two_sdk_mappings_are_disjoint_and_both_precede_the_envelope() -> None:
    """Typed-registerable and versioned-registerable are different sets.

    Disjointness is not a tidiness claim: it is what makes
    :func:`~ccf.deployment.classes.refuse_registration_the_sdk_fixes`
    unambiguous, since a class in both would be simultaneously refused for
    declaring ``typed`` and for declaring ``versioned``.

    The second half is the T-15-06-01 shadowing assertion extended to the new
    mapping — an SDK class resolving to the permissive envelope is the squat the
    reservation exists to close.
    """
    assert set(SDK_ARTIFACT_CLASSES) & set(SDK_VERSIONED_ARTIFACT_CLASSES) == set()
    for class_id, artifact_class in SDK_VERSIONED_ARTIFACT_CLASSES.items():
        resolved = resolve_artifact_class(class_id)
        assert resolved is artifact_class
        assert resolved.contract is not DeclaredArtifact


@pytest.mark.parametrize(
    "class_id",
    ["ccf.made-up-class", "ccf.not-a-real-class", "ccf."],
)
def test_a_ccf_prefixed_id_the_sdk_does_not_ship_is_refused(class_id: str) -> None:
    """D-IMPL-84 — the reservation, at the lookup rather than at the manifest.

    ``tests/deployment/test_manifest.py`` asserts the same fact end to end,
    through ``load_and_boot``. This asserts it at the function that owns the
    rule, so a refactor that moved the check out of ``resolve_artifact_class``
    and into the manifest loader would fail here and say why.
    """
    with pytest.raises(ValueError, match="D-IMPL-84"):
        resolve_artifact_class(class_id)


def test_an_adopters_own_namespace_still_takes_the_envelope() -> None:
    """The reservation is one prefix wide and no wider.

    Without this the refusal above would pass just as well for an
    implementation that refused *every* unrecognized id — which would break
    every deployment-authored class in the tree.
    """
    for class_id in ("acme.policy-bundle", "ccfx.policy-bundle", "notccf.thing"):
        assert resolve_artifact_class(class_id).contract is DeclaredArtifact


@pytest.mark.parametrize(
    ("class_id", "registration", "expect_refusal"),
    [
        # An author-versioned class: `typed` skips the D-05 bump check, and
        # `versioned` is the path the class exists for.
        ("ccf.workflow-definition", "typed", True),
        ("ccf.workflow-definition", "versioned", False),
        # A typed-only SDK class: `versioned` would raise TypeError from inside
        # register_versioned, because the contract declares no artifact_version.
        ("ccf.half-life-table", "versioned", True),
        # A deployment-authored class: in neither mapping, so the SDK does not
        # check it at all and the adopter's declaration stands.
        ("meridian-bank.policy-bundle", "typed", False),
    ],
)
def test_refuse_registration_the_sdk_fixes_refuses_and_admits(
    class_id: str, registration: str, expect_refusal: bool
) -> None:
    """Both directions, and **neither half is optional**.

    ``tests/products/test_gate_independence.py:184-187`` states the discipline
    in these words: "a gate that always refuses passes the first, a gate that
    always admits passes the second, and only the pair says the comparison is
    live". The same applies exactly here. Two rows expect a refusal and two
    expect admission; a function that raised unconditionally would pass the
    first two and a no-op would pass the last two, so **do not delete either
    half as redundant** — deleting either one leaves a check that cannot
    distinguish a working refusal from a broken one.

    Each half was observed to fail under the opposite forced behavior when this
    test was written; the observation is recorded in
    ``.planning/phases/15.1-ergonomics-gap-closure/15.1-03-SUMMARY.md``.

    The admit rows assert ``is None`` rather than merely "did not raise", so a
    future signature change that started *returning a corrected mode* — the
    silent-correction shape both D-IMPL-80 and D-IMPL-85 refuse — fails here
    instead of passing quietly.
    """
    if expect_refusal:
        with pytest.raises(ValueError) as raised:
            refuse_registration_the_sdk_fixes(class_id, registration)  # type: ignore[arg-type]
        message = str(raised.value)
        assert class_id in message
        assert "D-IMPL-85" in message
    else:
        assert (
            refuse_registration_the_sdk_fixes(class_id, registration)  # type: ignore[arg-type]
            is None
        )


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
        # The end-of-file sentinel must survive `.strip()`. A bare "## " does
        # not — strip removes the trailing space and the flush branch, which
        # tests `startswith("## ")`, never fires. That silently dropped the
        # **last section of the last fragment**, which went unnoticed only
        # because 15-09's happened to be `Public surface: false` (found by
        # 15-10, whose last section is a public addition).
        for line in fragment.read_text(encoding="utf-8").splitlines() + ["## eof"]:
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

    **The "before" side is the frozen baseline, not the live manifest.** Both
    sides of this comparison accumulate across the phase: ``claimed`` is the
    union of every fragment (see :func:`_fragment_public_added` for why), so
    the diff it is checked against has to be the accumulated one too. Between
    15-01 and 15-21 the two files are byte-identical and either read gives the
    same answer — which is why this originally read the live manifest and was
    correct for nineteen waves. It stops being correct the instant 15-21
    regenerates the live manifest: ``diff(live, live)`` is empty, and the
    ``claimed <= added`` direction then fails for all 52 legitimately-claimed
    names. Reading the frozen file is correct in *both* regimes, and the
    baseline's immutability is itself asserted, by digest and by commit
    provenance, in ``tests/test_surface_completeness.py``.
    """
    baseline = json.loads(_FROZEN_BASELINE.read_text(encoding="utf-8"))
    added = set(diff_surfaces(baseline, build_surface())["added"])
    claimed = _fragment_public_added()
    assert added <= claimed, f"added but unclaimed: {sorted(added - claimed)}"
    assert claimed <= added, f"claimed but not added: {sorted(claimed - added)}"


def test_this_plan_left_the_surface_manifests_alone() -> None:
    """The single-owner rule (docs/surface-changes/README.md): only 15-01 and
    15-21 write these files."""
    assert _LIVE_MANIFEST.is_file()
    assert (_LIVE_MANIFEST.parent / "v0.2-surface-baseline.json").is_file()
