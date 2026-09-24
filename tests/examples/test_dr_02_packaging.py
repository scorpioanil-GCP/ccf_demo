"""`dr-02` — Assembly Mode 2, and the gate that keeps the packaging honest.

Every test here runs against the SHIPPED upstream: `cp-06-canonical`'s own
door, booted as its own process by `run.py --door`, reached over loopback MCP
with a bearer credential. Nothing is stubbed on the substrate side — the whole
claim of Mode 2 is that it packages an *already-governed* product, and a test
that handed the packager a dictionary would be testing a different thing.

**The model IS stubbed, and by ruling** (`DR-SPEC-002` R4): CI never reaches a
provider. The stub is fail-loud — it answers only the headings the prompt
artifact declares — so prose nobody wrote cannot reach the smoothing gate.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import pytest

from ccf.products.refusal import RefusalEnvelope

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DR02 = REPO_ROOT / "examples" / "dr-02-package-a-context-product"
UPSTREAM = REPO_ROOT / "examples" / "cp-06-canonical-collateral-and-setoff-coverage"

#: The upstream's own demonstration facility and borrower, passed through.
FACILITY = "FAC-5B8418"
SCOPE = "2549001IGRCG4F0RLD36"
INSTANT = datetime.fromisoformat("2026-09-07T12:00:00+00:00")
INTENT = "credit-memo-drafting"
FRESHNESS = "as-filed"
DEV_TOKEN = "dr-02-development-token"

#: The upstream needs its own estate names; this rung reads no store itself.
ESTATE_VARIABLES = (
    "CCF_CP_06C_POSTGRES_DSN",
    "CCF_CP_06C_POSTGRES_SCHEMA",
    "CCF_CP_06C_FLUREE_URL",
    "CCF_CP_06C_FLUREE_LEDGER",
)


@pytest.fixture(scope="module")
def estate() -> None:
    missing = [name for name in ESTATE_VARIABLES if not os.environ.get(name)]
    if missing:
        message = (
            "the live estate is not configured:"
            f" {', '.join(missing)} unset (CLAUDE.md §9)"
        )
        if os.environ.get("CCF_REQUIRE_ESTATE"):
            pytest.fail(message)
        pytest.skip(message)


@contextmanager
def _upstream_door() -> Iterator[str]:
    """The upstream product's own door, in its own process."""
    environ = {
        **os.environ,
        "CCF_CP_06C_DOOR_TOKEN": DEV_TOKEN,
        "CCF_CP_06C_DOOR_ISSUER_URL": "https://issuer.invalid",
        "CCF_CP_06C_DOOR_RESOURCE_URL": "https://rs.invalid",
    }
    process = subprocess.Popen(
        [sys.executable, str(UPSTREAM / "run.py"), "--door"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environ,
    )
    try:
        assert process.stdout is not None
        announcement = process.stdout.readline().strip()
        if not announcement.startswith("READY "):
            _, stderr = process.communicate(timeout=15)
            raise AssertionError(
                f"the upstream door did not announce readiness"
                f" ({announcement!r}); stderr:\n{stderr[-2000:]}"
            )
        yield f"http://127.0.0.1:{int(announcement.split()[1])}/mcp"
    finally:
        process.terminate()
        process.wait(timeout=15)


def _environ(url: str) -> dict[str, str]:
    return {
        **os.environ,
        "CCF_DR_02_UPSTREAM_URL": url,
        "CCF_DR_02_UPSTREAM_TOKEN": DEV_TOKEN,
        "CCF_DR_02_DOOR_TOKEN": DEV_TOKEN,
        "CCF_DR_02_DOOR_ISSUER_URL": "https://issuer.invalid",
        "CCF_DR_02_DOOR_RESOURCE_URL": "https://rs.invalid",
    }


@contextmanager
def _asked(
    url: str, *, audience: tuple[str, ...] = ("credit-officer",)
) -> Iterator[tuple[Any, Any, Any]]:
    """One question, answered, with its record — the opened product held open."""
    sys.path.insert(0, str(DR02))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as scratch:
            with produce.product(pathlib.Path(scratch), environ=_environ(url)) as opened:
                question = opened.question(
                    subject=FACILITY, asked_at=INSTANT, intent=INTENT,
                    freshness=FRESHNESS,
                    parameters={
                        deployment.FACILITY: FACILITY,
                        deployment.BORROWER_SCOPE: [SCOPE],
                        deployment.AUDIENCE: list(audience),
                    },
                )
                outcome = opened.answer(question)
                yield opened, outcome, opened.record_of(outcome)
    finally:
        sys.path.remove(str(DR02))


@pytest.fixture(scope="module")
def served(estate: None) -> Iterator[tuple[Any, Any, Any]]:
    """One served memo, reused — the door boot is the expensive part."""
    with _upstream_door() as url, _asked(url) as answered:
        yield answered


def _payload(outcome: Any) -> dict[str, Any]:
    assert not isinstance(outcome, RefusalEnvelope), outcome
    return dict(outcome.product.payload)


# ===========================================================================
# PKG-G01 / PKG-G02 — the mode, and what the mode obliges
# ===========================================================================


def test_the_record_carries_the_declared_assembly_mode(
    served: tuple[Any, Any, Any],
) -> None:
    """Declared product gate `PKG-G01` (`DR-SPEC-002` §0.2 (1)).

    Both halves. The class declaring `llm_packaged` and the record carrying it
    are separately falsifiable, and a config string nobody checks is a claim
    rather than a demonstration.
    """
    import yaml

    _opened, outcome, record = served
    assert not isinstance(outcome, RefusalEnvelope), outcome
    declared = yaml.safe_load((DR02 / "ccf_config.yaml").read_text(encoding="utf-8"))
    assert declared["product_class"]["assembly_mode"] == "llm_packaged"
    assert record.model_version.assembly_mode == "llm_packaged", (
        "the class declares Mode 2 and the record does not carry it;"
        f" dimension 3 says {record.model_version.assembly_mode!r}"
    )


def test_the_four_rendering_primitives_are_pinned(
    served: tuple[Any, Any, Any],
) -> None:
    """Declared product gate `PKG-G02` (`DR-SPEC-002` §0.2 (2)).

    Whitepaper §7.10.4 names four: model version, temperature, prompt template
    and output hash. An examiner reads them off the product without
    dereferencing the agent definition, which is why `D-IMPL-346` pinned them
    rather than leaving three reachable and one unreachable.
    """
    _opened, outcome, _record = served
    packaged_by = _payload(outcome)["packaged_by"]
    for field in (
        "model", "temperature", "prompt_artifact_uri", "prompt_artifact_hash"
    ):
        value = packaged_by.get(field)
        assert value, (field, packaged_by)
        assert value != "no-packaging", (
            f"{field} is the positive no-packaging sentinel on a product that"
            " WAS packaged; the pin is absent, not merely unreported"
        )
    # The output hash is the served product's own address — the substrate's
    # stays on `packaged_from`, and holding both is what lets an examiner ask
    # whether the packaging moved the conclusion.
    assert _payload(outcome)["packaged_from"]["content_address"]


def test_the_prompt_hash_resolves_to_the_bytes_used(
    served: tuple[Any, Any, Any],
) -> None:
    """Declared product gate `PKG-G03` (`DR-SPEC-002` §D.1 (2)).

    The No-Hardcoding Rule makes the prompt an artifact; this makes the pin
    mean something. A hash that did not resolve would name a prompt nobody
    could read back, which is the same as no pin at all.
    """
    from ccf.contracts.canonical import content_hash

    _opened, outcome, _record = served
    on_product = _payload(outcome)["packaged_by"]["prompt_artifact_hash"]
    on_disk = content_hash(
        (DR02 / "artifacts" / "memo-prompt.yaml").read_text(encoding="utf-8")
    )
    assert on_product == on_disk, (
        "the hash the product carries does not resolve to the prompt artifact"
        " it names"
    )


# ===========================================================================
# PKG-G04 — THE SMOOTHING GATE. The point of this rung.
# ===========================================================================


def test_an_invented_figure_refuses_the_serve(estate: None) -> None:
    """Declared product gate `PKG-G04` (`DR-SPEC-002` §D.4).

    **The sabotage is carried inside the test, and it runs BOTH directions.** A
    packager that states one figure the substrate does not carry must refuse;
    the same packager without it must serve. Only the pair proves the gate
    discriminates — a gate that refused everything would pass the first
    assertion alone, which is exactly how a sabotage comes back green.

    This gate caught its own author on the rung's first honest run: the shipped
    packager wrote *"3 asset(s) secure this facility"*, a COMPUTED count the
    substrate never carried, and the serve refused (`PKG-F-01`).
    """
    sys.path.insert(0, str(DR02))
    try:
        import deployment  # noqa: PLC0415
        import memo_packaging as packaging_module  # noqa: PLC0415

        # PATCHED WHERE IT IS USED, not where it is defined. `deployment` binds
        # the class by `from`-import at module load, so rebinding the source
        # module leaves the deployment holding whatever it captured first —
        # which is how this sabotage first "passed" while its own positive
        # control failed. The control is why that was caught.
        honest = deployment.DeterministicPackager

        class _Liar(honest):  # type: ignore[misc, valid-type]
            """States one figure the substrate does not carry, and nothing else."""

            def package(self, *, product: Any, headings: Any) -> Any:
                rendered = super().package(product=product, headings=headings)
                first = rendered[0]
                return (
                    packaging_module.PackagedSection(
                        heading=first.heading,
                        audience=first.audience,
                        # 4242424242 appears nowhere in a coverage product.
                        prose=first.prose + " Total exposure is 4242424242.",
                        figures_cited=first.figures_cited,
                    ),
                    *rendered[1:],
                )

        with _upstream_door() as url:
            deployment.DeterministicPackager = _Liar  # type: ignore[misc]
            try:
                with _asked(url) as (_opened, refused, record):
                    assert isinstance(refused, RefusalEnvelope), (
                        "a memo stating a figure the substrate does not carry"
                        " was SERVED"
                    )
                    assert refused.reason == "packaging.did-not-move-the-conclusion"
                    block = str(record.content_generation_path.assembly_refusal)
                    assert "4242424242" in block, block
            finally:
                deployment.DeterministicPackager = honest  # type: ignore[misc]

            # THE POSITIVE CONTROL, same door, same question, honest packager.
            with _asked(url) as (_opened, served_again, _record):
                assert not isinstance(served_again, RefusalEnvelope), (
                    "the honest packager was refused too; the gate is not"
                    " discriminating, it is refusing everything"
                )
    finally:
        sys.path.remove(str(DR02))


# ===========================================================================
# PKG-G05..G08 — entitlement, upstream refusal, expiry, determinism
# ===========================================================================


def test_a_section_outside_the_audience_never_materializes(estate: None) -> None:
    """Declared product gate `PKG-G05` (`DR-SPEC-002` §B.2).

    The Policy operator admits before materialization, so an excluded section
    is absent from the view rather than filtered from a payload. Asserted as a
    DIFFERENCE against the same question at the shipped audience, because
    "no sections" is also what a broken walk produces.
    """
    with _upstream_door() as url:
        with _asked(url, audience=("credit-officer",)) as (_o, wide, _r):
            admitted = {s["heading"] for s in _payload(wide)["sections"]}
        with _asked(url, audience=("nobody-holds-this",)) as (_o, narrow, _r):
            if isinstance(narrow, RefusalEnvelope):
                # REFUSED, and the reason is the SDK's own gate 3 rather than
                # this product's gate 4. Measured 2026-09-23: with no section
                # admitted there is no observation to anchor an
                # evidence-anchored TTL on, so `ttl-anchor-unresolvable` fires
                # FIRST. Both are correct refusals of an empty memo and the
                # ordering is the SDK's, not this product's — asserted as
                # either rather than pinned to one, because pinning would make
                # this test fail if the SDK ever reordered two gates that
                # both say no.
                assert narrow.reason in {
                    "ttl-anchor-unresolvable",
                    "packaging.did-not-move-the-conclusion",
                }, narrow.reason
            else:
                assert not _payload(narrow)["sections"]
    assert admitted, "the wide audience admitted nothing; the control is vacuous"


def test_an_upstream_refusal_becomes_this_products_refusal(estate: None) -> None:
    """Declared product gate `PKG-G06` (`DR-SPEC-002` §D.1 (1)).

    `dr-02` resolves no subject of its own. If the substrate will not answer
    there is nothing to package, and a memo assembled anyway would be a memo
    about nothing — so the refusal is raised at the acquisition seam, where a
    deployment's governed refusal becomes data rather than a traceback.
    """
    sys.path.insert(0, str(DR02))
    try:
        import deployment  # noqa: PLC0415
        import produce  # noqa: PLC0415

        unreachable = "http://127.0.0.1:1/mcp"
        with tempfile.TemporaryDirectory() as scratch:
            with produce.product(
                pathlib.Path(scratch), environ=_environ(unreachable)
            ) as opened:
                question = opened.question(
                    subject=FACILITY, asked_at=INSTANT, intent=INTENT,
                    freshness=FRESHNESS,
                    parameters={
                        deployment.FACILITY: FACILITY,
                        deployment.BORROWER_SCOPE: [SCOPE],
                        deployment.AUDIENCE: ["credit-officer"],
                    },
                )
                with pytest.raises(Exception) as unreached:
                    opened.answer(question)
                # An unreachable door is a DEFECT, not a determination — the
                # upstream did not refuse, it did not answer. `D-IMPL-347` B2
                # is what would convert this by declaration, and this class
                # declares no `seam_refusals`, so it propagates. Recorded as
                # `PKG-F-03` rather than converted here.
                assert "did not complete" in str(unreached.value) or "Unreachable" in type(
                    unreached.value
                ).__name__
    finally:
        sys.path.remove(str(DR02))


def test_the_expiry_follows_the_substrate_not_the_request(
    served: tuple[Any, Any, Any],
) -> None:
    """Declared product gate `PKG-G07` (`DR-SPEC-002` §B.1 (3)).

    A rendering cannot be fresher than what it renders. The class anchors on
    entity freshness, so the served expiry is derived from the packaged
    claims' own instants and not from `asked_at` — which a decision anchor
    would have made it, silently.
    """
    _opened, outcome, _record = served
    assert not isinstance(outcome, RefusalEnvelope), outcome
    assert outcome.product.ttl_anchor == "from_entity_freshness"
    assert outcome.product.ttl_anchor_at is not None, (
        "an evidence-anchored product served with no anchor instant"
    )


def test_the_same_question_reaches_the_same_address_twice(estate: None) -> None:
    """Declared product gate `PKG-G08` (`DR-SPEC-002` §D.2).

    Mode 2 is deterministic GIVEN its pins, which is what makes recording the
    four of them worth doing. Two identical questions against one door reach
    one address.
    """
    sys.path.insert(0, str(DR02))
    try:
        import deployment  # noqa: PLC0415

        def _address(record: Any) -> str:
            return str(record.content_generation_path.product_content_address)

        with _upstream_door() as url:
            addresses = []
            for _ in range(2):
                with _asked(url) as (_opened, outcome, record):
                    assert not isinstance(outcome, RefusalEnvelope), outcome
                    addresses.append(_address(record))
            assert addresses[0] == addresses[1], addresses

            # THE OTHER LIMB, and the gate claims both. Without it,
            # "deterministic GIVEN its pins" is half asserted: a pin that can
            # change while the address stands still is not part of the
            # identity it claims to be, and `PKG-G02` would still pass because
            # the field would be POPULATED and simply not load-bearing.
            #
            # `deployment.packager` is the binding the deployment actually
            # calls -- `acquisition` receives the model as an argument and
            # binds nothing of its own. Patching the module global is what
            # `PKG-F-04` says to verify rather than assume.
            honest = deployment.packager

            def _warmer(declaration: Any) -> Any:
                return deployment.DeterministicPackager(temperature="0.7")

            deployment.packager = _warmer  # type: ignore[assignment]
            try:
                with _asked(url) as (_opened, warmer, warm_record):
                    assert not isinstance(warmer, RefusalEnvelope), warmer
                    moved = _address(warm_record)
                    assert dict(warmer.product.payload)["packaged_by"][
                        "temperature"
                    ] == "0.7", "the sabotage did not reach the served payload"
            finally:
                deployment.packager = honest  # type: ignore[assignment]

            assert moved != addresses[0], (
                "the temperature pin moved and the product's content address"
                f" did not ({moved}); the pin is RECORDED but is not part of"
                " the identity §7.10.4 asks it to pin"
            )
    finally:
        sys.path.remove(str(DR02))


# ===========================================================================
# PKG-G09 — the RETAINED record, not the served payload
# ===========================================================================


def test_the_retained_record_carries_the_real_packaging_trace(estate: None) -> None:
    """Declared product gate `PKG-G09` (`DR-SPEC-002` §D.2).

    §7.10.4 pins Mode 2's rendering primitives so an examiner reads the
    packaging off replay **dimension 3** without dereferencing anything. This
    reads the bytes the store retained, because the payload passing is not
    evidence about the record: measured 2026-09-23, `dr-02` served real pins
    on the payload while every field of dimension 3 read `no-packaging`, and
    all eight gates were green (`PKG-F-08`).
    """
    sys.path.insert(0, str(DR02))
    try:
        import acquisition  # noqa: PLC0415
        import deployment  # noqa: PLC0415
        from ccf.replay.record import NO_PACKAGING  # noqa: PLC0415
        from ccf.replay.record import DecisionReplayRecord  # noqa: PLC0415

        with _upstream_door() as url:
            with _asked(url) as (opened, outcome, _record):
                assert not isinstance(outcome, RefusalEnvelope), outcome
                retained = DecisionReplayRecord.model_validate_json(
                    opened.artifact_store.get(
                        content_address=outcome.replay_ref.content_address
                    )
                )
                trace = retained.model_version.packaging_trace
                assert retained.model_version.assembly_mode == "llm_packaged"

                # All five, named individually so a failure says WHICH pin.
                for pin in (
                    "model_version",
                    "temperature",
                    "prompt_artifact_uri",
                    "prompt_artifact_hash",
                    "output_hash",
                ):
                    assert getattr(trace, pin) != NO_PACKAGING, (
                        f"dimension 3's `{pin}` is the no-packaging sentinel on"
                        " a product a model wrote; an examiner reading this"
                        " record would be told no packaging happened"
                    )

                # The record and the memo agree, so a reader holding either
                # reaches the same four pins.
                payload = dict(outcome.product.payload)
                pins = payload["packaged_by"]
                assert trace.model_version == pins["model"]
                assert trace.temperature == pins["temperature"]
                assert trace.prompt_artifact_uri == pins["prompt_artifact_uri"]
                assert trace.prompt_artifact_hash == pins["prompt_artifact_hash"]
                assert trace.output_hash == pins["output_hash"]

                # THE REPLAY CONTRACT. `output_hash` is re-derivable from the
                # served memo alone, which is what makes it checkable by
                # someone holding the record and the product and nothing else.
                assert trace.output_hash == acquisition.output_hash(
                    payload["sections"]
                )

                # DETECTION, carried inside the test: move one word of the
                # prose and the re-derivation stops matching the pin. Without
                # this the equality above would hold for ANY hash function,
                # including one that ignored its input.
                tampered = [dict(section) for section in payload["sections"]]
                tampered[0]["prose"] = str(tampered[0]["prose"]) + " (altered)"
                assert acquisition.output_hash(tampered) != trace.output_hash, (
                    "the packaged prose was altered and the output hash did"
                    " not move; the pin cannot detect a rewritten memo"
                )

            # THE SABOTAGE. A deployment that supplies no trace serves the
            # same payload pins and records the sentinel — exactly the state
            # this gate exists to refuse, and the one `dr-02` shipped in.
            honest = deployment.packaging_trace
            deployment.packaging_trace = None  # type: ignore[assignment]
            try:
                with _asked(url) as (opened, dark, _record):
                    assert not isinstance(dark, RefusalEnvelope), dark
                    unrecorded = DecisionReplayRecord.model_validate_json(
                        opened.artifact_store.get(
                            content_address=dark.replay_ref.content_address
                        )
                    )
                    sentinel = unrecorded.model_version.packaging_trace
                    assert sentinel.model_version == NO_PACKAGING
                    assert sentinel.output_hash == NO_PACKAGING
                    # ...while the memo still carries real pins. The payload
                    # is why this was invisible for a whole rung.
                    assert (
                        dict(dark.product.payload)["packaged_by"]["model"]
                        != NO_PACKAGING
                    )
            finally:
                deployment.packaging_trace = honest  # type: ignore[assignment]
    finally:
        sys.path.remove(str(DR02))
