"""`D-IMPL-136` §10's compatibility commitment, proved rather than argued —
half B: content-address equivalence against HW-1, read-only.

Whitepaper §7.8 (Control Plane artifacts, typed and versioned); CLAUDE.md
§6.4 and §10 for the SDK-defined single-file loader. Design spec
`docs/superpowers/specs/2026-08-14-ccf-config-consolidation-design.md` §3's
argument, executed: two independently authored byte streams — HW-1's ten
committed multi-file documents and a hand-authored single-file fixture —
register to **one** content address per artifact, through two different
parse paths.

**Why this module lives here and not in `tests/deployment/`.**
`tests/deployment/conftest.py`'s own `deployment` fixture docstring states
the reason for itself: *"written to disk here rather than reached for in
`examples/` — a test that read an example's artifacts would fail whenever
that example was rewritten, for reasons having nothing to do with the
manifest."* Half A (`tests/deployment/test_config_equivalence.py`) honours
that by building its corpus entirely under `tmp_path`. This module is the
deliberate exception: it *needs* to read a real, committed, measured
deployment to prove the compatibility claim on something realer than a
synthetic fixture, and going red when `examples/s1-00-companies-over-revenue`
changes is `tests/examples/`'s normal, expected behaviour — the same
directory `test_s1_00_output.py` and `test_spine_separation.py` already
exercise that example under.

**`examples/` is read-only for this whole module, and for this whole plan
set.** Every document under `examples/s1-00-companies-over-revenue/artifacts
/config/` is opened for reading only; nothing here writes to it (Dave's
dual-model ruling, 2026-08-14 — no example is converted, now or by
implication).

**What this module enforces, exactly.**

1. HW-1's eight committed artifact documents (read from
   :data:`HW1_MULTIFILE_DIR`, learning which class each is from HW-1's own
   `manifest.yaml` rather than a hard-coded pairing) register at content
   addresses **identical** to the same eight artifacts derived from the
   hand-authored fixture `tests/examples/fixtures/s1_00_ccf_config.yaml`.
2. The parsed objects compare equal, not merely their content hashes.
3. The `(class_id, role, registration)` triple of each derived entry equals
   HW-1's committed manifest entry for the same artifact (paired by
   `class_id`, since the two forms use different key vocabularies by design
   — `~ccf.deployment.config`'s own module docstring and the 16-29 SUMMARY's
   HW-1 comparison table).
4. Exactly **one** `role: load` entry on each side.
5. Non-vacuous: the comparison is asserted to have covered exactly **8**
   artifacts.
6. The two `MEASUREMENT.md` recipes — 10 files, 99 non-comment YAML lines —
   are reproduced here as an assertion, so this module also stands as the
   check that nothing under `examples/` moved while this plan set ran.

**The repointing seam for `16-31`.** `16-31` converts HW-1 to the
single-file form, which means `examples/s1-00-companies-over-revenue
/artifacts/config/` stops holding the nine multi-file documents this module
reads. `16-31`'s first task freezes those nine documents into
`tests/deployment/fixtures/s1-00-multifile/` before converting anything, and
this module is written so that repointing at that fixture is a **one-line
change**: every read in this module goes through the single named constant
:data:`HW1_MULTIFILE_DIR` below, never a path threaded through a second
helper.
"""

from __future__ import annotations

import pathlib

from ccf.controlplane.artifacts import (
    DEPLOYMENT_CONFIG,
    DEPLOYMENT_MANIFEST,
    DeploymentConfig,
    DeploymentManifest,
    load_artifact,
    parse_artifact,
)
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment.classes import resolve_artifact_class
from ccf.deployment.config import derive_deployment

#: The single named constant `16-31` must change to repoint this module at
#: the frozen fixture (`tests/deployment/fixtures/s1-00-multifile/`) once
#: HW-1 converts to the single-file form. Every other path in this module is
#: computed from this one — see the module docstring's "repointing seam".
HW1_MULTIFILE_DIR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "examples"
    / "s1-00-companies-over-revenue"
    / "artifacts"
    / "config"
)

#: The hand-authored single-file transcription, committed beside this test —
#: never under `examples/` (see the module docstring).
FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "s1_00_ccf_config.yaml"

#: The two `MEASUREMENT.md` recipes' committed figures — reproduced as an
#: assertion so a change under `examples/s1-00-companies-over-revenue
#: /artifacts/config/` cannot silently drift this module's premise.
_EXPECTED_YAML_FILE_COUNT = 10
_EXPECTED_NON_COMMENT_YAML_LINE_COUNT = 99


def _non_comment_line_count(path: pathlib.Path) -> int:
    """The `MEASUREMENT.md` recipe, executed in Python rather than shelled out to
    `command grep`, over one file. Comments (`#`) are stripped before counting,
    and blank lines are not counted — the same two rules the committed shell
    recipe applies.
    """
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("#"):
            continue
        if line.strip():
            count += 1
    return count


def test_examples_measurement_recipes_still_print_their_committed_figures() -> None:
    """The floor `T-16-30-08` names: `examples/` is untouched by this plan set.

    Reproduces `examples/s1-00-companies-over-revenue/MEASUREMENT.md`'s own
    two recipes (10 files, 99 lines) rather than trusting the committed
    document not to have drifted from the tree.
    """
    yaml_files = sorted(HW1_MULTIFILE_DIR.glob("*.yaml"))
    assert len(yaml_files) == _EXPECTED_YAML_FILE_COUNT

    total = sum(_non_comment_line_count(path) for path in yaml_files)
    assert total == _EXPECTED_NON_COMMENT_YAML_LINE_COUNT


def test_hw1_eight_documents_register_at_identical_content_addresses_in_both_forms() -> (
    None
):
    manifest_text = (HW1_MULTIFILE_DIR / "manifest.yaml").read_text(encoding="utf-8")
    hw1_manifest = load_artifact(manifest_text, DEPLOYMENT_MANIFEST)
    assert isinstance(hw1_manifest, DeploymentManifest)
    assert len(hw1_manifest.artifacts) == 8

    registry_x = ControlPlaneRegistry()
    x_version_by_class: dict[str, str] = {}
    x_triple_by_class: dict[str, tuple[str, str, str]] = {}
    x_load_role_count = 0
    for entry in hw1_manifest.artifacts:
        # HW-1's own committed manifest is the authority for which class
        # each document is — read here, not hard-coded, so the pairing is a
        # comparison rather than a restatement.
        text = (HW1_MULTIFILE_DIR / entry.path).read_text(encoding="utf-8")
        artifact_class = resolve_artifact_class(entry.class_id)
        parsed = load_artifact(text, artifact_class)
        version = registry_x.register_typed(entry.key, parsed, artifact_class)
        x_version_by_class[entry.class_id] = version
        x_triple_by_class[entry.class_id] = (
            entry.class_id,
            entry.role,
            entry.registration,
        )
        if entry.role == "load":
            x_load_role_count += 1

    fixture_text = FIXTURE_PATH.read_text(encoding="utf-8")
    config = load_artifact(fixture_text, DEPLOYMENT_CONFIG)
    assert isinstance(config, DeploymentConfig)
    derived = derive_deployment(config)
    assert len(derived.manifest.artifacts) == 8

    registry_y = ControlPlaneRegistry()
    y_version_by_class: dict[str, str] = {}
    y_triple_by_class: dict[str, tuple[str, str, str]] = {}
    y_load_role_count = 0
    parsed_objects: dict[str, object] = {}
    for entry in derived.manifest.artifacts:
        document = derived.documents[entry.key]
        artifact_class = resolve_artifact_class(entry.class_id)
        parsed = parse_artifact(document, artifact_class)
        version = registry_y.register_typed(entry.key, parsed, artifact_class)
        y_version_by_class[entry.class_id] = version
        y_triple_by_class[entry.class_id] = (
            entry.class_id,
            entry.role,
            entry.registration,
        )
        parsed_objects[entry.class_id] = parsed
        if entry.role == "load":
            y_load_role_count += 1

    # --- (4) exactly one `role: load` entry, both sides
    assert x_load_role_count == 1
    assert y_load_role_count == 1

    # --- the pairing is total: both sides name the same eight classes
    assert set(x_version_by_class) == set(y_version_by_class)

    # --- (1), (2), (3), (5): identical content addresses, equal parsed
    # objects, matching triples — the eight-row table, printed for the
    # SUMMARY.
    compared = 0
    rows: list[tuple[str, str, str]] = []
    for class_id, x_version in sorted(x_version_by_class.items()):
        y_version = y_version_by_class[class_id]
        assert x_version == y_version, (
            f"content address diverges for {class_id!r}:"
            f" multi-file={x_version} single-file={y_version}"
        )
        assert x_triple_by_class[class_id] == y_triple_by_class[class_id]
        rows.append((class_id, x_version, y_version))
        compared += 1
    assert compared == 8, f"expected to compare 8 artifacts, compared {compared}"

    # Printed so a failure — or a passing run's own SUMMARY table — carries
    # the eight real addresses rather than only "equal": an equivalence
    # claim with no printed addresses is an assertion again.
    for class_id, x_version, y_version in rows:
        print(f"{class_id}: multi-file={x_version} single-file={y_version}")
