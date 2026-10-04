"""The CINV-06 base roster: every defaulted ``CCFContract`` field at ``13bd250``.

``D-IMPL-243`` amendment 2 (Dave: *"New-since-13bd250 only. Do not allowlist
115 names. Lint: field absent at 13bd250 → must declare ``ccf_hash_transparent``.
Older fields are D-IMPL-89 by construction. … Base roster is a committed file
measured at ``13bd250``, not a comment."*); whitepaper §7.10; CLAUDE.md §7.4.
SDK-defined enforcement, not whitepaper-derived.

What this module is
-------------------
The generator of :data:`ROSTER_PATH` — ``tools/lints/hash_transparent_base_roster.json``
— and its drift check. The roster lists, model-qualified as
``module.Class.field`` and sorted, every field on a ``CCFContract`` subclass
under ``src/`` and ``runtime/`` that carried a default (a plain ``= value``,
``Field(default=…)``, ``Field(default_factory=…)`` or a positional default)
in the tree at :data:`BASE_COMMIT`, the Phase 24.5 base. The CINV-06 lint
(``tools/lints/hash_transparent_key.py``) reads that file and names a
defaulted field that is NOT in it and declares no key: a field that existed
with a default before the phase is the ``D-IMPL-89`` lineage by construction
and is never named; a field added since must say what its sentinel means.

The roster is **measured, never typed**: it is produced by exporting the base
tree with ``git archive`` and walking it with the same AST instrument the lint
walks HEAD with (:func:`tools.lints.hash_transparent_key.defaulted_fields`),
so the two sides of the "new since base" question are answered by one
walker. Regenerating by hand, or editing the file, is not a supported path —
the ``--check`` mode below is what makes a hand edit visible.

Why JSON and not YAML
---------------------
Three reasons, each sufficient. The lint reads the roster at every ``make
lint``, and the lint package's rule is stdlib-only checkers (``D-06``) —
``json`` is stdlib, PyYAML is not. The file is compared BYTE-for-byte by
``--check``, and ``json.dumps(sort_keys=True, indent=2)`` is a deterministic
rendering, which lets the check be a byte equality rather than a
parse-and-compare that could pass over a reordered or re-commented file. And
a roster is one name per line either way; YAML's one advantage — comments —
is carried instead by the header keys (``base_commit``, ``generator``,
``rule``), which say where the file came from in a form a reader of the
file and a test can both check.

Usage::

    python -m tools.lints.base_roster          # (re)write the roster
    python -m tools.lints.base_roster --check  # regenerate into memory; diff; exit 1 on drift

``--check`` needs :data:`BASE_COMMIT` in the clone (``fetch-depth: 0`` in a
CI checkout); it fails loudly, never silently, when the commit is absent —
a check that cannot read its subject must not report a clean result.
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterable, Sequence

from tools.lints import hash_transparent_key

#: The Phase 24.5 base (``phase-24.5-base``), in full: the tree every field
#: in the roster is measured against.
BASE_COMMIT = "13bd250e7a9d9ea12daf596ef86597557aad702f"

#: The committed roster the lint reads.
ROSTER_PATH = pathlib.Path(__file__).with_name("hash_transparent_base_roster.json")

#: Base-roster names a RULING retired: fields the roster measured at
#: :data:`BASE_COMMIT` that a later decision removed from the tree outright.
#: The roster file itself is never edited (it is a measurement, see above);
#: a retirement is absorbed only here, by name and by the decision that made
#: it, and ``tools/lints/tests/test_base_roster.py`` asserts each entry is
#: both in the roster AND absent at HEAD — so a stale entry (a field that
#: came back) is as red as an unexplained removal.
RETIRED_BY_RULING: dict[str, str] = {
    # `D-IMPL-363` E1 / C8 (SEC-005): `signed_binding` is REPLACED, not
    # deprecated, by `attestation` (a `SignedHitlAction`), and Dave ruled the
    # rename over keeping the stale name when the two collided (2026-10-03).
    "ccf.hitl.transport.HitlActionSubmission.signed_binding": "D-IMPL-363",
}

#: The trees exported from the base commit — the lint's own scope, so the
#: roster covers exactly the universe the lint walks.
EXPORTED_TREES: tuple[str, ...] = hash_transparent_key.SCOPE_TREES

#: How the roster names itself, so a reader of the JSON can see which commit,
#: which tool and which rule it serves without opening this module.
HEADER = {
    "base_commit": BASE_COMMIT,
    "generator": "tools/lints/base_roster.py",
    "rule": hash_transparent_key.RULE_HASH_TRANSPARENT_KEY,
}


class BaseCommitUnavailable(RuntimeError):
    """``git archive`` could not read :data:`BASE_COMMIT` from this clone."""


def measure(base: pathlib.Path) -> list[str]:
    """Every defaulted contract field under ``base``, model-qualified and sorted."""
    names = {
        hash_transparent_key.module_qualified(field, base)
        for field in hash_transparent_key.defaulted_fields(base)
    }
    return sorted(names)


def export_base_tree(repo: pathlib.Path, dest: pathlib.Path) -> None:
    """Extract ``src/`` and ``runtime/`` at :data:`BASE_COMMIT` into ``dest``."""
    completed = subprocess.run(
        ["git", "-C", str(repo), "archive", BASE_COMMIT, *EXPORTED_TREES],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise BaseCommitUnavailable(
            f"git archive {BASE_COMMIT[:8]} failed (exit {completed.returncode}):"
            f" {completed.stderr.decode('utf-8', 'replace').strip()} — the base"
            " commit must be in the clone (fetch-depth: 0)"
        )
    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        archive.extractall(dest, filter="data")


def measure_base(repo: pathlib.Path) -> list[str]:
    """The roster as the base commit says it, measured fresh."""
    with tempfile.TemporaryDirectory(prefix="ccf-base-roster-") as scratch:
        dest = pathlib.Path(scratch)
        export_base_tree(repo, dest)
        return measure(dest)


def render(names: Iterable[str]) -> str:
    """The roster's one canonical text: header, then the sorted names."""
    document = dict(HEADER)
    document["fields"] = sorted(set(names))
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def load(path: pathlib.Path = ROSTER_PATH) -> frozenset[str]:
    """The names in a committed roster, after checking it says what it is."""
    document = json.loads(path.read_text(encoding="utf-8"))
    for key, value in HEADER.items():
        if document.get(key) != value:
            raise ValueError(
                f"{path} does not describe itself as this roster:"
                f" {key}={document.get(key)!r}, expected {value!r}"
            )
    fields = document["fields"]
    if fields != sorted(set(fields)):
        raise ValueError(f"{path} is not sorted and unique; regenerate it")
    return frozenset(fields)


def check(repo: pathlib.Path, path: pathlib.Path = ROSTER_PATH) -> list[str]:
    """Unified-diff lines between the committed roster and a fresh measurement.

    Empty means the file is byte-identical to what the generator would write.
    """
    committed = path.read_text(encoding="utf-8")
    fresh = render(measure_base(repo))
    if committed == fresh:
        return []
    return list(
        difflib.unified_diff(
            committed.splitlines(keepends=True),
            fresh.splitlines(keepends=True),
            fromfile=str(path),
            tofile=f"measured at {BASE_COMMIT[:8]}",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.lints.base_roster",
        description=(
            "Generate, or check, the CINV-06 base roster: every defaulted"
            f" CCFContract field at {BASE_COMMIT[:8]} (D-IMPL-243 amendment 2)."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate into memory from git archive and diff; exit 1 on drift",
    )
    parser.add_argument(
        "--repo",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[2],
        help="repository root (default: this file's repository)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            drift = check(args.repo)
            if drift:
                sys.stdout.writelines(drift)
                print(
                    f"\n{ROSTER_PATH} has drifted from the {BASE_COMMIT[:8]} tree;"
                    " run python -m tools.lints.base_roster to regenerate it",
                    file=sys.stderr,
                )
                return 1
            print(f"{ROSTER_PATH}: identical to the {BASE_COMMIT[:8]} measurement")
            return 0
        names = measure_base(args.repo)
        ROSTER_PATH.write_text(render(names), encoding="utf-8")
        print(f"{ROSTER_PATH}: {len(names)} fields at {BASE_COMMIT[:8]}")
        return 0
    except BaseCommitUnavailable as unavailable:
        print(f"error: {unavailable}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
