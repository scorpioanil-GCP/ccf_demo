"""The CINV-06 base roster and its generator (``D-IMPL-243`` amendment 2).

``tools/lints/base_roster.py`` measures every defaulted ``CCFContract`` field
in the ``13bd250`` tree and writes ``tools/lints/hash_transparent_base_roster.json``;
the lint reads that file as the boundary of its universe. Two things are
proven here. That the committed file IS the measurement — ``--check``
regenerates from ``git archive`` and holds the bytes equal, and a roster with
one name dropped is named in the diff — and that the file says what it is:
the header names the base commit, the generator and the rule; the names are
sorted and unique; a field known to predate the phase is in it and a field
24.5 added is not (a roster is verified by members, never by a count).

The ``--check`` proof needs the base commit in the clone. It FAILS, never
skips, when the commit is absent: a check that cannot read its subject must
not report clean, and the CI lint job checks out with ``fetch-depth: 0`` for
exactly this test.
"""

from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

from tools.lints import base_roster, hash_transparent_key

REPO = pathlib.Path(__file__).resolve().parents[3]


def _committed() -> dict[str, object]:
    return json.loads(base_roster.ROSTER_PATH.read_text(encoding="utf-8"))


# --- the file says what it is -------------------------------------------------


def test_the_roster_names_its_commit_generator_and_rule() -> None:
    document = _committed()
    assert document["base_commit"] == base_roster.BASE_COMMIT
    assert document["base_commit"].startswith("13bd250")
    assert document["generator"] == "tools/lints/base_roster.py"
    assert document["rule"] == hash_transparent_key.RULE_HASH_TRANSPARENT_KEY


def test_the_base_commit_is_the_phase_base_tag() -> None:
    """``phase-24.5-base`` and the roster's commit are one object."""
    resolved = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "phase-24.5-base^{commit}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert resolved == base_roster.BASE_COMMIT


def test_the_names_are_sorted_unique_and_module_qualified() -> None:
    fields = _committed()["fields"]
    assert isinstance(fields, list)
    assert fields == sorted(set(fields))
    for name in fields:
        module, class_name, field_name = name.rsplit(".", 2)
        assert module.startswith(("ccf.", "ccf_runtime.")), name
        assert class_name and field_name, name


def test_positive_controls_a_pre_phase_field_is_in_and_a_phase_field_is_out() -> None:
    """A roster is verified by members: one of the fifteen, one older field, and
    two fields amendment 2 ticks — the last two must be absent, or the lint
    could never have named them."""
    roster = base_roster.load()
    assert "ccf.replay.record.ContentGenerationPath.request" in roster
    assert "ccf.graph.protocols.GraphQuery.traverse" in roster
    assert "ccf.operators.params.TraversalDescendantsParameters.admitted_entity_classes" not in roster
    assert "ccf.controlplane.artifacts.HalfLifeEntry.half_life_seconds" not in roster


def test_every_roster_name_is_still_a_defaulted_field_at_head() -> None:
    """Nothing in the roster has been removed or lost its default since base.

    Measured, not assumed: if a later phase renames or drops one, this names
    it, and the roster is regenerated only by a ruling that moves the base.
    """
    at_head = {
        hash_transparent_key.module_qualified(field, REPO)
        for field in hash_transparent_key.defaulted_fields(REPO)
    }
    assert sorted(base_roster.load() - at_head) == []


# --- the file IS the measurement -----------------------------------------------


def test_check_holds_the_committed_roster_equal_to_a_fresh_measurement() -> None:
    try:
        drift = base_roster.check(REPO)
    except base_roster.BaseCommitUnavailable as unavailable:  # pragma: no cover
        pytest.fail(
            f"the base commit is not in this clone ({unavailable}); deepen the"
            " checkout (fetch-depth: 0) — this test must not skip"
        )
    assert drift == []


def test_a_roster_with_one_name_dropped_is_named_in_the_diff(
    tmp_path: pathlib.Path,
) -> None:
    dropped = "ccf.graph.protocols.GraphQuery.traverse"
    names = sorted(base_roster.load() - {dropped})
    scratch = tmp_path / "roster.json"
    scratch.write_text(base_roster.render(names), encoding="utf-8")
    drift = base_roster.check(REPO, path=scratch)
    assert drift, "a dropped name went unnoticed"
    assert any(line.startswith("+") and dropped in line for line in drift)
    assert not any(line.startswith("-") and line[1:].strip().startswith('"ccf') for line in drift)


def test_render_is_deterministic_and_ends_with_a_newline() -> None:
    once = base_roster.render(["b.B.b", "a.A.a", "a.A.a"])
    assert once == base_roster.render(["a.A.a", "b.B.b"])
    assert once.endswith("\n")
    assert json.loads(once)["fields"] == ["a.A.a", "b.B.b"]


# --- load refuses a file that is not this roster -----------------------------


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(base_commit="0000000"),
        lambda d: d.update(generator="somewhere/else.py"),
        lambda d: d.update(rule="cinv01-no-hardcoding"),
        lambda d: d.update(fields=list(reversed(d["fields"]))),
        lambda d: d.update(fields=d["fields"] + d["fields"][:1]),
    ],
    ids=["commit", "generator", "rule", "unsorted", "duplicate"],
)
def test_load_refuses_a_file_that_is_not_this_roster(
    tmp_path: pathlib.Path, mutation: object
) -> None:
    document = _committed()
    mutation(document)  # type: ignore[operator]
    scratch = tmp_path / "roster.json"
    scratch.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        base_roster.load(scratch)


# --- the CLI ---------------------------------------------------------------------


def test_the_cli_check_mode_exits_zero_on_the_committed_roster(capsys: pytest.CaptureFixture[str]) -> None:
    assert base_roster.main(["--check", "--repo", str(REPO)]) == 0
    assert "identical" in capsys.readouterr().out


def test_module_qualified_derives_the_module_from_the_scope_tree(tmp_path: pathlib.Path) -> None:
    for tree, module in (("src", "ccf.replay.record"), ("runtime", "ccf_runtime.cdc.envelope_map")):
        path = tmp_path / tree / pathlib.Path(*module.split(".")).with_suffix(".py")
        field = hash_transparent_key.DefaultedField(
            path=path, lineno=1, class_name="C", field_name="f", declared=None
        )
        assert hash_transparent_key.module_qualified(field, tmp_path) == f"{module}.C.f"
    package_init = tmp_path / "src" / "ccf" / "__init__.py"
    field = hash_transparent_key.DefaultedField(
        path=package_init, lineno=1, class_name="C", field_name="f", declared=None
    )
    assert hash_transparent_key.module_qualified(field, tmp_path) == "ccf.C.f"
    outside = hash_transparent_key.DefaultedField(
        path=tmp_path / "tests" / "x.py", lineno=1, class_name="C", field_name="f", declared=None
    )
    with pytest.raises(ValueError):
        hash_transparent_key.module_qualified(outside, tmp_path)
