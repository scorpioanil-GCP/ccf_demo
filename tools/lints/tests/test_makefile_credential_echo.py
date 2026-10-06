"""SEC-026 behavioral exploit test — ``make`` must never print a credential.

``make`` echoes every recipe line it runs unless that LOGICAL line (backslash
continuations joined) begins with ``@``. A recipe line that expands a
credential-bearing variable therefore writes the credential to the terminal
and to the CI log. The control is behavioral, not textual: each
credential-bearing target is run for real with ``SHELL=/bin/true``, which turns
every recipe into a no-op while ``make`` still echoes the command line it would
have handed the shell, and the canary must be absent from stdout and stderr.

Why this shape rather than ``make -n``: ``make -n`` prints ``@`` lines too, so a
dry run can never prove the echo is gone (D-IMPL-368 PRE-RUN panel, finding P8,
``docs/D-IMPL-368-PRERUN-REVIEWS.md``). ``SHELL=/bin/true`` also guarantees no
recipe reaches any server, curated or otherwise.

The row: ``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``
section SEC-026. Secret hygiene is CLAUDE.md §11 (typed boundaries, nothing
secret in the tree) and §2.2 (never a secret in the tree).
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

CANARY = "CANARY"

#: One credential-shaped value per credential-bearing variable the Makefile
#: reads. Each carries userinfo so a leak is the realistic one.
CANARY_ENV: dict[str, str] = {
    "CCF_TEST_POSTGRES_DSN": f"postgresql://u:{CANARY}@h/db",
    "CCF_TEST_NEO4J_URI": f"neo4j://u:{CANARY}@h:7687",
    "CCF_TEST_MONGO_URI": f"mongodb://u:{CANARY}@h:27017/db",
    "CCF_TEST_FLUREE_URL": f"http://u:{CANARY}@h:8090",
}

#: Every target whose recipe expands one of the variables above. The two
#: Fluree recipe lines of ``example-s1-01`` (the estate fence and the run) are
#: one target.
CREDENTIAL_TARGETS = (
    "leg-postgres",
    "leg-neo4j",
    "leg-mongo",
    "leg-fluree",
    "example-s1-01",
    "example-s1-00",
)

#: Variables inherited from an enclosing ``make`` (``make gate-tools``) that
#: could silence or dry-run the child and make this test vacuous.
_MAKE_INHERITED = ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEOVERRIDES", "GNUMAKEFLAGS")


def _env(**overrides: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _MAKE_INHERITED}
    for name in CANARY_ENV:
        env.pop(name, None)
    env.update(overrides)
    return env


def _make(*args: str, cwd: pathlib.Path = REPO_ROOT, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "--no-print-directory", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_the_harness_sees_an_echo_when_there_is_one(tmp_path: pathlib.Path) -> None:
    """Positive control: the same invocation shape DOES surface a non-``@``
    echo, so a green result below is evidence rather than a blind harness."""
    (tmp_path / "Makefile").write_text(
        "leak:\n\tcmd CCF_TEST_POSTGRES_DSN=$(CCF_TEST_POSTGRES_DSN) \\\n\t\trest\n",
        encoding="utf-8",
    )
    result = _make("leak", "SHELL=/bin/true", cwd=tmp_path, env=_env(**CANARY_ENV))
    assert result.returncode == 0, result.stdout + result.stderr
    assert CANARY in result.stdout + result.stderr


@pytest.mark.parametrize("target", CREDENTIAL_TARGETS)
def test_no_credential_bearing_target_prints_its_credential(target: str) -> None:
    result = _make(target, "SHELL=/bin/true", env=_env(**CANARY_ENV))
    output = result.stdout + result.stderr
    # The recipe must actually have run (as a no-op): a target that failed
    # before reaching its recipe would hide the echo and prove nothing.
    assert result.returncode == 0, output
    echoed = [line for line in output.splitlines() if CANARY in line]
    assert not echoed, f"make {target} echoed a credential:\n" + "\n".join(echoed)


def test_leg_neo4j_refuses_by_name_when_the_uri_is_unset() -> None:
    """No baked default: an unset ``CCF_TEST_NEO4J_URI`` is refused, by name,
    at expansion time — so even ``make -n`` exits non-zero."""
    result = _make("-n", "leg-neo4j", "SHELL=/bin/true", env=_env())
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "CCF_TEST_NEO4J_URI" in output, output
    assert "ccf_test_password" not in output, output


def test_leg_neo4j_still_receives_the_uri_when_set() -> None:
    """CI is unchanged: with the URI set, the recipe still carries it.
    ``make -n`` prints ``@`` lines, which is what makes this visible."""
    result = _make("-n", "leg-neo4j", "SHELL=/bin/true", env=_env(**CANARY_ENV))
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert f"CCF_TEST_NEO4J_URI={CANARY_ENV['CCF_TEST_NEO4J_URI']}" in output, output
