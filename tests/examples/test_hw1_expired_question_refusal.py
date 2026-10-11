"""HW-1 refuses an expired question, by name, over both documented transports.

Dave's ruling 1 (2026-10-11 16:23 MST, ``docs/DECISIONS.md`` "Tuesday delivery
— RULED, 15:25 and 16:23"): *"A normal default command must ask a valid question
and reach the example's intended result. [...] Keep an expired-question case as
a normal test that asserts the correct refusal. Do not disable expiry checks,
widen security limits merely to obtain a pass, or relabel old estate data as
freshly observed."*

The default command is the served half, held by
``test_hw1_two_transports.py``: it asks at the pinned ``--as-of`` and is
served at the deployment's labelled development clock
(``demonstration_serve_instant:`` in ``deployment/ccf_config.yaml``). This
module is the other half: the SAME documented commands with only the
``--as-of`` value moved to an instant the deployment's own declarations make
expired, so a reader can see the clock is a demonstration instant and not a
switched-off check. Two expiries, each read off the deployment's own documents
rather than typed here:

* asked further back than ``temporal_boundary.max_past_seconds`` before the
  serve instant — refused ``asked-at-outside-temporal-bound``;
* asked inside that bound, but so long before the serve instant that the
  answer's own lifetime (``product_ttl_seconds`` in ``binding.yaml``) ended
  before it — refused ``ttl-bounds``.

An ordinary passing test, not an expected failure: the refusal IS the correct
behavior. Each leg must exit 1, print exactly the one refusal line naming its
check, and print no content address — a refusal never reaches a caller as a
product.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
from datetime import datetime, timedelta

import pytest
import yaml

from tests.examples.test_client_example_purity import documented_commands
from tests.examples.test_hw1_two_transports import (
    ADDRESS,
    EXAMPLE_ROOT,
    REPO_ROOT,
    TIMEOUT_SECONDS,
    example,  # noqa: F401 — the unseeded copy fixture, re-exported for pytest
    invocation,
    seeded_example,  # noqa: F401 — the seeded copy fixture, re-exported for pytest
)

#: The flag whose VALUE this module moves. Every other token is the README's.
AS_OF_FLAG = "--as-of"


def _document(root: pathlib.Path, name: str) -> dict[str, object]:
    loaded = yaml.safe_load((root / "deployment" / name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), name
    return loaded


def expired_instants(root: pathlib.Path) -> dict[str, datetime]:
    """The two expired ``as_of`` values, keyed by the refusal each must draw."""
    config = _document(root, "ccf_config.yaml")
    binding = _document(root, "binding.yaml")
    declared = config["demonstration_serve_instant"]
    boundary = config["temporal_boundary"]
    assert isinstance(declared, dict) and isinstance(boundary, dict)
    serve_at = datetime.fromisoformat(str(declared["serve_instant"]))
    max_past = timedelta(seconds=int(boundary["max_past_seconds"]))
    lifetime = timedelta(seconds=int(binding["product_ttl_seconds"]))
    assert lifetime < max_past, (
        "the TTL case needs an instant inside the temporal bound whose answer"
        " has already expired; with a lifetime no shorter than the bound there"
        " is none, and this module would be asserting something else"
    )
    return {
        "asked-at-outside-temporal-bound": serve_at - max_past - timedelta(seconds=1),
        "ttl-bounds": serve_at - lifetime - timedelta(seconds=1),
    }


def with_as_of(argv: list[str], instant: datetime) -> list[str]:
    """``argv`` with the documented ``--as-of`` value replaced by ``instant``."""
    assert argv.count(AS_OF_FLAG) == 1, argv
    position = argv.index(AS_OF_FLAG) + 1
    return [*argv[:position], instant.isoformat(), *argv[position + 1 :]]


@pytest.mark.parametrize("reason", ["asked-at-outside-temporal-bound", "ttl-bounds"])
def test_an_expired_question_is_refused_by_name_on_both_transports(
    seeded_example: pathlib.Path,  # noqa: F811
    reason: str,
) -> None:
    """Both documented commands, one moved instant, one named refusal each."""
    instant = expired_instants(seeded_example)[reason]
    commands = documented_commands(EXAMPLE_ROOT)
    assert len(commands) == 2, commands
    for command in commands:
        address, argv = invocation(command, example=seeded_example)
        completed = subprocess.run(
            with_as_of(argv, instant),
            cwd=REPO_ROOT,
            env={**os.environ, "CCF_BINDING": address},
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        assert completed.returncode == 1, (
            f"`{address}` asked at {instant.isoformat()} exited"
            f" {completed.returncode}, not the refusal exit 1\n{completed.stdout}"
            f"\n--- stderr ---\n{completed.stderr}"
        )
        assert completed.stdout.strip() == f"refused: {reason}", (
            f"`{address}` asked at {instant.isoformat()} printed"
            f" {completed.stdout!r}; the deployment's declarations make that"
            f" question refuse `{reason}`"
        )
        assert not ADDRESS.search(completed.stdout), "a refusal printed a content address"
