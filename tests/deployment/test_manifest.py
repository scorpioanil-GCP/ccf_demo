"""D-06 / D-08 / D-IMPL-80 — what ``load_and_boot`` refuses, and what it pins.

Whitepaper §7.8 (the Control Plane declares what the fabric may do) and §7.10
(a decision resolves the configuration in force when it was made); CLAUDE.md
§6.4 and §10 for the SDK-defined ``ccf.deployment`` package these cover.

**What these tests enforce.**

1. Two loads of one manifest produce a byte-identical pin set.
2. A glob-shaped path is refused at parse.
3. Dropping an unlisted file into the artifacts directory does not change the
   pin set — D-06's actual claim, and the reason globs are refused.
4. A declared ``postgres`` backend with no DSN fails loudly, and **no SQLite
   file is created**: the fallback is absent, not merely unused.
5. ``tenant_id`` comes from exactly one of two sources, and both-absent and a
   conflicting pair are each refused.
6. The returned handle exposes no writer (C-5, single-writer).
7. ``ResolvedPins`` has exactly one public method — a standing guard against a
   later convenience making binding *selection* implicit.
8. ``role`` is required, so the register-versus-load choice is never silent.
9. A ``role: load`` entry is parsed, returned, and absent from the pin set
   **and from the audit log**, and flipping it to ``register`` flips all three.
10. Duplicate keys are refused; duplicate paths under distinct keys are not.
11. A malformed document registers nothing.
12. An author-versioned class declared ``registration: typed`` is refused, an
    envelope-shaped squat on any ``ccf.``-prefixed class id is refused, and the
    ``versioned`` path both dispatches and turns a D-05 bump refusal into a
    loud failure that pins nothing (D-IMPL-84, D-IMPL-85).

**What they do not enforce.** They do not enforce that a manifest names the
*right* artifacts for a deployment — which artifacts a deployment needs is the
adopter's policy decision and D-06 deliberately keeps it explicit. They do not
cover a Postgres backend actually connecting; test 4 exercises the refusal path,
which is the one that can silently do the wrong thing. And they say nothing
about what happens *after* boot: operator execution, projection, and the three
validation gates are outside this entry point by construction, and
``tests/products/test_gate_independence.py`` is what holds that line.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from ccf.contracts.base import CCFContract
from ccf.controlplane.artifacts import ArtifactLoadError, SignalBatch
from ccf.controlplane.registry import ControlPlaneRegistry
from ccf.deployment import load_and_boot
from ccf.deployment.pins import ResolvedPins, UnpinnedArtifactError

from tests.deployment.conftest import (
    ARTIFACT_SET,
    POLICY_BUNDLE_KEY,
    RESOLUTION_SPEC_KEY,
    SIGNAL_BATCH_KEY,
    TENANT,
    Deployment,
    manifest_document,
    write_artifact,
)

#: The manifest entry index whose document test 11 corrupts. Fourth, so there
#: are three entries before it whose absence from the registry is the assertion.
FOURTH = 3


def _boot(
    deployment: Deployment,
    tmp_path: pathlib.Path,
    *,
    registry: ControlPlaneRegistry | None = None,
    manifest: pathlib.Path | None = None,
    name: str = "graph.sqlite3",
    **kwargs: Any,
) -> Any:
    """Boot the fixture deployment onto its own SQLite file."""
    return load_and_boot(
        manifest or deployment.manifest_path,
        registry=registry if registry is not None else ControlPlaneRegistry(),
        database_path=str(tmp_path / name),
        **kwargs,
    )


# --- (1) determinism ----------------------------------------------------------


def test_two_loads_of_one_manifest_produce_an_identical_pin_set(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-06. Content-addressed registration makes this true; the test pins it.

    Each load gets its own graph file and its own registry, so nothing but the
    manifest and the artifact documents is shared between them — which is the
    point: the pin set is a function of the documents, not of the run.
    """
    first = _boot(deployment, tmp_path, name="one.sqlite3")
    try:
        first_pins = first.pins.model_dump_json()
    finally:
        first.handle.close()

    second = _boot(deployment, tmp_path, name="two.sqlite3")
    try:
        second_pins = second.pins.model_dump_json()
    finally:
        second.handle.close()

    assert first_pins == second_pins


# --- (2) globs ----------------------------------------------------------------


@pytest.mark.parametrize("pattern", ["*.yaml", "artifacts/?alf-life.yaml", "[a-z].yaml"])
def test_a_glob_shaped_path_is_refused_at_parse(
    deployment: Deployment, tmp_path: pathlib.Path, pattern: str
) -> None:
    """A manifest enumerates. The message must say so."""
    body = manifest_document()
    body["artifacts"][0] = dict(body["artifacts"][0], path=pattern)
    path = deployment.variant_manifest("globbed.yaml", body)

    with pytest.raises(ArtifactLoadError) as raised:
        _boot(deployment, tmp_path, manifest=path)
    assert "glob" in str(raised.value)
    assert "enumerates" in str(raised.value)


# --- (3) directory contents do not change what is in force --------------------


def test_an_unlisted_file_in_the_artifacts_directory_changes_nothing(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-06's actual claim, and the reason globs are refused.

    What is in force is what the manifest names. A file dropped into the
    directory is not named, so it is not in force, and no pin moves.
    """
    before = _boot(deployment, tmp_path, name="before.sqlite3")
    try:
        baseline = before.pins.model_dump_json()
    finally:
        before.handle.close()

    write_artifact(
        deployment.root,
        "dropped-in.yaml",
        {"semver": "9.9.9", "entries": {"not-in-the-manifest": {}}},
    )

    after = _boot(deployment, tmp_path, name="after.sqlite3")
    try:
        assert after.pins.model_dump_json() == baseline
    finally:
        after.handle.close()


# --- (4) the backend kind, and the loud failure -------------------------------


def test_postgres_declared_with_no_dsn_fails_loudly_and_creates_no_sqlite_file(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-08. The fallback must be **absent**, not merely unused.

    A fabric that guessed its substrate could boot against a development file in
    production and still pass every test. So the assertion is not only that the
    call raised — it is that nothing SQLite-shaped exists anywhere under
    ``tmp_path`` afterwards.
    """
    path = deployment.variant_manifest(
        "postgres.yaml", manifest_document(backend="postgres")
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        load_and_boot(path, registry=registry)

    message = str(raised.value)
    assert "postgres" in message
    assert "postgres_dsn" in message
    assert not any(
        candidate.suffix in {".sqlite3", ".sqlite", ".db"}
        for candidate in tmp_path.rglob("*")
    )


def test_the_backend_preflight_runs_before_anything_is_registered(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The refusal path leaves the Control Plane exactly as it found it.

    A manifest declaring ``postgres`` with no DSN *parses* perfectly well, so a
    backend check placed beside the ``boot`` call would have registered every
    artifact before failing — leaving Control Plane state from a fabric that
    never booted. That is a replay-integrity problem, not an untidiness: the
    registry would answer "what was in force" for a deployment that never ran.
    Asserted against the audit log as well as the version index, because an
    audited attempt is state too.
    """
    path = deployment.variant_manifest(
        "postgres-preflight.yaml", manifest_document(backend="postgres")
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError):
        load_and_boot(path, registry=registry)

    for key, _filename, _class_id, _role, _registration, _document in ARTIFACT_SET:
        assert registry.versions(key) == ()
    assert registry.audit_events() == ()


def test_sqlite_declared_with_no_database_path_fails_the_same_way(
    deployment: Deployment,
) -> None:
    """The symmetric refusal: the declared backend's argument is required."""
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        load_and_boot(deployment.manifest_path, registry=registry)
    assert "database_path" in str(raised.value)
    assert registry.audit_events() == ()


def test_supplying_the_other_backends_argument_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Declaring ``sqlite`` and supplying a DSN is a contradiction, not a choice."""
    registry = ControlPlaneRegistry()
    with pytest.raises(ValueError) as raised:
        load_and_boot(
            deployment.manifest_path,
            registry=registry,
            database_path=str(tmp_path / "graph.sqlite3"),
            postgres_dsn="postgresql://fixture/never-connected",
        )
    assert "postgres_dsn" in str(raised.value)
    assert registry.audit_events() == ()


# --- (5) tenant resolution ----------------------------------------------------


def test_the_manifest_may_supply_the_tenant(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    booted = _boot(deployment, tmp_path)
    try:
        assert booted.tenant_id == TENANT
    finally:
        booted.handle.close()


def test_the_caller_may_supply_the_tenant(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Optional on the manifest because D-IMPL-05 makes tenancy a runtime axis."""
    body = manifest_document()
    del body["tenant_id"]
    path = deployment.variant_manifest("untenanted.yaml", body)

    booted = _boot(deployment, tmp_path, manifest=path, tenant_id=TENANT)
    try:
        assert booted.tenant_id == TENANT
    finally:
        booted.handle.close()


def test_a_tenant_absent_from_both_sources_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    body = manifest_document()
    del body["tenant_id"]
    path = deployment.variant_manifest("no-tenant.yaml", body)

    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, manifest=path)
    assert "tenant_id" in str(raised.value)


def test_a_conflicting_tenant_pair_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """Refused rather than resolved by precedence — the fabric does not choose."""
    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, tenant_id="a-different-tenant")
    assert "conflict" in str(raised.value)


# --- (6) single-writer --------------------------------------------------------


def test_the_returned_handle_exposes_no_writer(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """C-5. The entry point returns the same ``FabricHandle`` ``boot`` does.

    The assertion is deliberately crude — no attribute name on the handle
    contains ``writ`` — because the property being defended is that there is
    nothing on the handle to *reach for*, and a crude scan is the honest shape
    of that claim. It does not prove no write path exists anywhere; the
    composition root and the CINV-02 import lint carry that.
    """
    booted = _boot(deployment, tmp_path)
    try:
        assert not any("writ" in name for name in dir(booted.handle))
    finally:
        booted.handle.close()


# --- (7) the pin record grows no projection helpers ---------------------------


def test_resolved_pins_has_exactly_one_public_method() -> None:
    """A standing guard against the §5.3 risk, not a snapshot of today's code.

    A convenience like ``pins.policy_bindings()`` would move the *selection* of
    which bindings are in force out of the adopter's code and into the SDK —
    dimension 2 of the replay record assembled by a rule nobody wrote down.
    ``version_for`` is lookup, not selection, which is why it is the only one.
    """
    inherited = set(dir(CCFContract))
    declared = {
        name
        for name in vars(ResolvedPins)
        if not name.startswith("_") and callable(getattr(ResolvedPins, name, None))
    }
    assert declared == {"version_for"}
    assert not any(
        "binding" in name or "policy" in name
        for name in dir(ResolvedPins)
        if not name.startswith("_") and name not in inherited
    )


# --- (8) role and registration are required -----------------------------------


def test_a_manifest_entry_naming_no_role_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-IMPL-80. The choice is never made silently, and never by the SDK.

    Either default would have the SDK deciding a replay-dimension-2 boundary on
    the adopter's behalf — the objection ``boot()`` already raises against every
    other default.
    """
    body = manifest_document()
    entry = dict(body["artifacts"][0])
    del entry["role"]
    body["artifacts"][0] = entry
    path = deployment.variant_manifest("roleless.yaml", body)

    with pytest.raises(ArtifactLoadError) as raised:
        _boot(deployment, tmp_path, manifest=path)
    assert "role" in str(raised.value)


def test_a_manifest_entry_naming_no_registration_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-IMPL-85. Either default would have the SDK choosing the governance path
    by silence — inheriting or losing the D-05 bump check with no document
    saying so.

    Modelled line for line on
    :func:`test_a_manifest_entry_naming_no_role_is_refused` above, which is the
    precedent this copies: the requiredness of a no-default field is a standing
    guarantee, so something in the suite has to fail if a later plan adds a
    default "to make the migration easier".
    """
    body = manifest_document()
    entry = dict(body["artifacts"][0])
    del entry["registration"]
    body["artifacts"][0] = entry
    path = deployment.variant_manifest("registrationless.yaml", body)

    with pytest.raises(ArtifactLoadError) as raised:
        _boot(deployment, tmp_path, manifest=path)
    assert "registration" in str(raised.value)


def test_the_sdk_refuses_a_register_role_on_the_signal_batch(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-IMPL-80, machine-checkable. The required field stops the choice being
    made *silently*; this stops it being made *wrongly* for the one class where
    the SDK knows the answer — and it fires before anything is registered."""
    body = manifest_document()
    body["artifacts"] = [
        dict(entry, role="register") if entry["key"] == SIGNAL_BATCH_KEY else entry
        for entry in body["artifacts"]
    ]
    path = deployment.variant_manifest("batch-registered.yaml", body)
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, registry=registry, manifest=path)
    assert "ccf.signal-batch" in str(raised.value)
    assert registry.audit_events() == ()


# --- (9) role: load is parsed, returned, and never registered -----------------


def test_a_load_role_entry_is_returned_but_never_registered(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """D-IMPL-80, both directions.

    The absence is proven against the **Control Plane's own audit record**, not
    only against the pin set: an audit log with no event for the key is the
    Control Plane saying it never saw it. The flip case is what keeps the test
    honest — without it, a loader that silently ignored the entry entirely would
    pass every assertion above.
    """
    registry = ControlPlaneRegistry()
    booted = _boot(deployment, tmp_path, registry=registry)
    try:
        assert isinstance(booted.artifacts[SIGNAL_BATCH_KEY], SignalBatch)
        with pytest.raises(UnpinnedArtifactError):
            booted.pins.version_for(SIGNAL_BATCH_KEY)
        assert not any(
            event.key == SIGNAL_BATCH_KEY for event in registry.audit_events()
        )
    finally:
        booted.handle.close()

    # The mirror: the same entry under a class the SDK does not fix a role for,
    # declared `role: register`, flips all three.
    body = manifest_document()
    body["artifacts"] = [
        dict(entry, role="register", class_id="fixture.batch-as-declared")
        if entry["key"] == SIGNAL_BATCH_KEY
        else entry
        for entry in body["artifacts"]
    ]
    write_artifact(
        deployment.root,
        "declared-batch.yaml",
        {
            "semver": "1.0.0",
            "class_id": "fixture.batch-as-declared",
            "declaration": {"events": ["fixture"]},
        },
    )
    body["artifacts"] = [
        dict(entry, path="declared-batch.yaml")
        if entry["key"] == SIGNAL_BATCH_KEY
        else entry
        for entry in body["artifacts"]
    ]
    path = deployment.variant_manifest("batch-as-declared.yaml", body)

    flipped_registry = ControlPlaneRegistry()
    flipped = _boot(
        deployment,
        tmp_path,
        registry=flipped_registry,
        manifest=path,
        name="flipped.sqlite3",
    )
    try:
        assert SIGNAL_BATCH_KEY in flipped.artifacts
        assert flipped.pins.version_for(SIGNAL_BATCH_KEY)
        assert any(
            event.key == SIGNAL_BATCH_KEY
            for event in flipped_registry.audit_events()
        )
    finally:
        flipped.handle.close()


# --- (10) duplicate keys ------------------------------------------------------


def test_two_entries_sharing_a_key_are_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """C-9. A repeated key makes both the pin and the parsed artifact ambiguous."""
    body = manifest_document()
    body["artifacts"] = list(body["artifacts"]) + [
        dict(body["artifacts"][2], key=RESOLUTION_SPEC_KEY)
    ]
    path = deployment.variant_manifest("duplicate-key.yaml", body)

    with pytest.raises(ArtifactLoadError) as raised:
        _boot(deployment, tmp_path, manifest=path)
    assert RESOLUTION_SPEC_KEY in str(raised.value)


def test_two_entries_sharing_a_path_under_distinct_keys_parse(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The asymmetry is a decision: one document may be in force under two names,
    and nothing about that is ambiguous."""
    body = manifest_document()
    twin = dict(body["artifacts"][2], key="fixture/half-life-table-twin")
    body["artifacts"] = list(body["artifacts"]) + [twin]
    path = deployment.variant_manifest("duplicate-path.yaml", body)

    booted = _boot(deployment, tmp_path, manifest=path)
    try:
        assert booted.pins.version_for(
            "fixture/half-life-table-twin"
        ) == booted.pins.version_for(ARTIFACT_SET[2][0])
    finally:
        booted.handle.close()


# --- (11) a malformed document registers nothing ------------------------------


def test_a_malformed_document_at_the_fourth_entry_registers_nothing(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The two-phase parse-then-register ordering, asserted rather than assumed.

    Without it, entries one through three would be registered before entry four
    failed — partial Control Plane state produced by a deployment that never
    booted.

    **What is still not guaranteed:** a failure *inside* the registration loop —
    a backend error, say — can still leave earlier entries registered. That is
    accepted rather than papered over. Registration is content-addressed and
    audited, so a corrected re-run registers identical content to identical
    versions and the audit log shows both attempts; a Control Plane that
    silently un-registers is worse than one that records a retry.
    """
    fourth_key, fourth_file, _class_id, _role, _registration, _document = ARTIFACT_SET[
        FOURTH
    ]
    write_artifact(deployment.root, fourth_file, {"semver": "1.0.0"})
    registry = ControlPlaneRegistry()

    with pytest.raises(ArtifactLoadError):
        _boot(deployment, tmp_path, registry=registry)

    for key, _f, _c, _r, _g, _d in ARTIFACT_SET[:FOURTH]:
        assert registry.versions(key) == ()
    assert registry.versions(fourth_key) == ()
    assert registry.audit_events() == ()


# --- the pins the adopter hands onward ----------------------------------------


def test_the_pin_set_covers_every_register_role_entry_and_no_other(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """``pins`` is the record of what was put in force; ``artifacts`` is not."""
    booted = _boot(deployment, tmp_path)
    try:
        pinned = {pin.key for pin in booted.pins.entries}
        expected = {
            key for key, _f, _c, role, _g, _d in ARTIFACT_SET if role == "register"
        }
        assert pinned == expected
        assert set(booted.artifacts) == {
            key for key, _f, _c, _r, _g, _d in ARTIFACT_SET
        }
        assert booted.pins.version_for(RESOLUTION_SPEC_KEY)
        assert booted.pins.version_for(POLICY_BUNDLE_KEY)
    finally:
        booted.handle.close()


# --- (12) D-IMPL-84 / D-IMPL-85 — the refusals CR-1 needs ---------------------
#
# Five tests. Every one of them was confirmed to FAIL with plan 15.1-03's source
# change reverted and to pass with it — the confirmation is recorded in
# `.planning/phases/15.1-ergonomics-gap-closure/15.1-03-SUMMARY.md`, because a
# refusal nobody has watched fire is a refusal that might be matching nothing
# (the discipline `tests/products/test_required_operators_guard.py:250-300`
# states).


#: A minimal valid ``ccf.prompt-artifact`` — an SDK-owned, AUTHOR-VERSIONED
#: class, so its contract declares a string ``artifact_version`` and
#: ``register_versioned``'s D-05 bump check has something to hold content
#: identity against. Fixture values only; no SDK code reads one (CINV-01).
def _prompt_artifact(*, version: str = "1.0.0", body: str = "fixture body") -> dict[str, Any]:
    return {
        "schema_version": "1.0.0",
        "artifact_version": version,
        "name": "fixture-prompt",
        "tenant": TENANT,
        "template": body,
        "declared_parameters": [],
    }


#: A document that is a perfectly valid ``DeclaredArtifact`` — ``semver``,
#: ``class_id``, ``declaration`` and nothing else. This is the squat's payload:
#: before D-IMPL-84 it satisfied the open envelope that any unrecognized
#: ``ccf.``-prefixed id resolved to.
def _envelope_squat(class_id: str) -> dict[str, Any]:
    return {
        "semver": "1.0.0",
        "class_id": class_id,
        "declaration": {"anything": "at all"},
    }


def _with_extra_entry(
    deployment: Deployment,
    *,
    name: str,
    filename: str,
    key: str,
    class_id: str,
    registration: str,
    document: dict[str, Any],
) -> pathlib.Path:
    """Write ``document`` beside the fixture set and name it from a new manifest.

    One helper rather than five copies of the same six lines — the *variation*
    between these tests is the class id and the registration mode, and a helper
    that leaves those in the caller keeps the variation legible at each call
    site.
    """
    write_artifact(deployment.root, filename, document)
    body = manifest_document()
    body["artifacts"] = [
        *body["artifacts"],
        {
            "path": filename,
            "key": key,
            "class_id": class_id,
            "role": "register",
            "registration": registration,
        },
    ]
    return deployment.variant_manifest(name, body)


def test_an_author_versioned_class_declared_typed_registration_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """CR-1's core, asserted as a refusal rather than as the examples' good behavior.

    ``tests/examples/test_workflow_hitl_output.py::test_the_author_versioned_definitions_kept_their_bump_check``
    proves example 05 registers its four author-versioned documents through
    ``register_versioned``. That is a test **that the example does it right**,
    and it cannot fail for a manifest the example does not contain — which is
    exactly the shape ROADMAP Criterion 1 asks for the other side of. This is
    that other side: a manifest that *does* contain the pattern.

    ``ccf.prompt-artifact`` declares a string ``artifact_version``, so
    ``register_typed`` would register it with **no D-05 bump check** — the
    author's version claim never held against content identity. The refusal
    fires in preflight, before the document is read.

    **Fails before plan 15.1-03's source change, passes after.** Before it,
    ``ccf.prompt-artifact`` was in neither SDK mapping, so this manifest entry
    resolved the open envelope and failed at *parse* on the real document's
    shape — a different error for a different reason. The assertion on the
    message is what distinguishes the two.
    """
    path = _with_extra_entry(
        deployment,
        name="versioned-class-typed.yaml",
        filename="prompt-artifact.yaml",
        key="fixture/prompt-artifact",
        class_id="ccf.prompt-artifact",
        registration="typed",
        document=_prompt_artifact(),
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, registry=registry, manifest=path)
    message = str(raised.value)
    assert "ccf.prompt-artifact" in message
    # The registration MODE, named — not merely "something failed". A refusal
    # that does not say which of the two paths was wrong sends the adopter to
    # read the source.
    assert "'typed'" in message
    assert "D-IMPL-85" in message
    assert registry.audit_events() == ()


def test_an_envelope_squat_on_an_sdk_class_id_is_refused(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The reachable form of CR-1 (D-IMPL-84), and the review's description was
    inaccurate as to mechanism.

    CR-1 as reviewed says a manifest routes a *real* author-versioned document
    around the bump check. Phase 15.1 research executed that and it fails
    loudly — 13 validation errors, because the open envelope's ``extra=forbid``
    rejects the real document's shape. What *was* reachable is this: a document
    that **is** a valid ``DeclaredArtifact`` and merely *claims*
    ``class_id: ccf.hitl-policy``. Before D-IMPL-84 it booted, registered,
    pinned, bound the Control Plane key to the SDK class id, and entered
    Decision Replay dimension 2 with arbitrary content and no bump check — and
    the registry's class-binding check compares ``class_id`` strings, which
    match, so a later *correct* ``register_versioned`` on the same key was
    admitted on top of it.

    ``ccf.hitl-policy`` is used deliberately: it is an SDK-owned class that is
    not manifest-addressable at all, so nothing but the namespace reservation
    stands between the squat and the registry.

    **Fails before the source change, passes after** — before it, this booted.
    """
    path = _with_extra_entry(
        deployment,
        name="envelope-squat.yaml",
        filename="squat.yaml",
        key="fixture/squatted-key",
        class_id="ccf.hitl-policy",
        registration="typed",
        document=_envelope_squat("ccf.hitl-policy"),
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, registry=registry, manifest=path)
    assert "D-IMPL-84" in str(raised.value)
    assert registry.audit_events() == ()
    assert registry.versions("fixture/squatted-key") == ()


@pytest.mark.parametrize(
    ("class_id", "decision_id"),
    [
        # Verified squattable before this plan (15.1-RESEARCH.md, §CR-1
        # Verification, "Generality"). The SDK owns no contract for the first
        # two spellings, so the NAMESPACE RESERVATION is what refuses them.
        ("ccf.hitl-policy", "D-IMPL-84"),
        ("ccf.made-up-class", "D-IMPL-84"),
        # The third is refused a stop earlier, by the class-property check: the
        # SDK does now own a contract for it, so it is in
        # SDK_VERSIONED_ARTIFACT_CLASSES and `registration: typed` contradicts
        # the contract. Both mechanisms close the same squat; which one fires
        # depends only on whether the SDK ships a contract for the id, and
        # neither leaves the open envelope reachable under a `ccf.` name.
        ("ccf.skill-grant", "D-IMPL-85"),
    ],
)
def test_the_ccf_namespace_reservation_is_wide_not_a_four_id_list(
    deployment: Deployment,
    tmp_path: pathlib.Path,
    class_id: str,
    decision_id: str,
) -> None:
    """D-IMPL-84 is namespace-wide by Dave's explicit choice over a four-id list.

    A list of the four author-versioned ids would close roughly a third of the
    hole: the squat was verified reachable for ``ccf.hitl-policy``,
    ``ccf.skill-grant`` and a **wholly invented** ``ccf.made-up-class``, none of
    which a four-id list names. This test is what makes the width a standing
    fact rather than a docstring — ``ccf.made-up-class`` in particular can only
    be refused by a rule about the *prefix*, because there is nothing else about
    it to recognize.

    **Every row fails before the source change and passes after** — each of the
    three booted, registered and pinned before it.
    """
    path = _with_extra_entry(
        deployment,
        name=f"reservation-{class_id.replace('.', '-')}.yaml",
        filename=f"squat-{class_id.replace('.', '-')}.yaml",
        key="fixture/squatted-key",
        class_id=class_id,
        registration="typed",
        document=_envelope_squat(class_id),
    )
    registry = ControlPlaneRegistry()

    with pytest.raises(ValueError) as raised:
        _boot(deployment, tmp_path, registry=registry, manifest=path)
    assert decision_id in str(raised.value)
    assert registry.audit_events() == ()


def test_the_versioned_dispatch_runs_the_bump_check(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """The admit direction: a real author-versioned document, through the manifest.

    Without this the four tests above would all pass against a loader that
    refused *everything* — the failure mode T-15.1-03-06 names. Evidence comes
    from the Control Plane's **own audit record**, which is where
    ``register_versioned`` writes ``action="register_versioned"``, plus the mode
    recorded on the returned pin (D-IMPL-83).

    **Fails before the source change, passes after**: before it,
    ``ccf.prompt-artifact`` resolved the open envelope, and ``register_versioned``
    on a ``DeclaredArtifact`` raises ``TypeError`` — the envelope declares no
    ``artifact_version``, so the bump check had nothing to verify.
    """
    key = "fixture/prompt-artifact"
    path = _with_extra_entry(
        deployment,
        name="versioned-dispatch.yaml",
        filename="prompt-artifact.yaml",
        key=key,
        class_id="ccf.prompt-artifact",
        registration="versioned",
        document=_prompt_artifact(),
    )
    registry = ControlPlaneRegistry()

    booted = _boot(deployment, tmp_path, registry=registry, manifest=path)
    try:
        actions = {
            event.action
            for event in registry.audit_events()
            if event.key == key
        }
        assert actions == {"register_versioned"}
        assert "register_typed" not in actions
        pin = next(entry for entry in booted.pins.entries if entry.key == key)
        assert pin.registration == "versioned"
        assert isinstance(pin.version, str)
    finally:
        booted.handle.close()


def test_an_unbumped_change_refusal_mid_load_is_loud_and_pins_nothing(
    deployment: Deployment, tmp_path: pathlib.Path
) -> None:
    """A returned ``RegistrationRefusal`` must never become an ``ArtifactPin`` version.

    ``register_versioned`` **returns** its D-05 refusals rather than raising them
    (the GateRefusal discipline), so a bare assignment in ``load_and_boot``
    would put a ``RefuseUnbumpedChange`` *object* into ``ArtifactPin.version``
    and record a refusal as a pin — a refusal entering Decision Replay dimension
    2 as though it were a binding.

    The second boot shares the first's registry, because the bump history lives
    there: changed content under an unbumped ``artifact_version`` is the
    two-boot shape, not a one-boot one.

    **Fails before the source change, passes after**: before it there was no
    manifest path to ``register_versioned`` for this class at all, so nothing
    reached the bump check and the second boot succeeded.
    """
    key = "fixture/prompt-artifact"
    registry = ControlPlaneRegistry()
    first = _boot(
        deployment,
        tmp_path,
        registry=registry,
        name="first.sqlite3",
        manifest=_with_extra_entry(
            deployment,
            name="bump-first.yaml",
            filename="prompt-first.yaml",
            key=key,
            class_id="ccf.prompt-artifact",
            registration="versioned",
            document=_prompt_artifact(body="the first body"),
        ),
    )
    try:
        assert isinstance(first.pins.version_for(key), str)
    finally:
        first.handle.close()

    # Same declared artifact_version, different content. D-05's second outcome.
    second = _with_extra_entry(
        deployment,
        name="bump-second.yaml",
        filename="prompt-second.yaml",
        key=key,
        class_id="ccf.prompt-artifact",
        registration="versioned",
        document=_prompt_artifact(body="a materially different body"),
    )

    with pytest.raises(ValueError) as raised:
        _boot(
            deployment,
            tmp_path,
            registry=registry,
            name="second.sqlite3",
            manifest=second,
        )
    message = str(raised.value)
    assert key in message
    assert "RefuseUnbumpedChange" in message

    # The load raised, so no pin set was returned at all — which is the strongest
    # form of "no pin carries a refusal". Asserted against the pins the FIRST
    # load did return, so the check is not vacuous: every version there is a
    # string, and a `RegistrationRefusal` could never satisfy that.
    assert all(isinstance(pin.version, str) for pin in first.pins.entries)
    assert first.pins.entries
