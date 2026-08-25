"""Fixture-diff utility — makes regeneration a reviewable event (D-04/D-10).

Stdlib only. Compares two directories of model-API fixtures (the checked-in
set vs a fresh live recording, or any two snapshots) file by file and prints
a unified diff of their canonically re-serialized JSON
(``json.dumps(..., indent=2, sort_keys=True)``), so key order and
whitespace never masquerade as change.

Files are gathered by the same convention ``replay_server._load_fixtures``
uses: sorted glob over ``<prefix>-*.json`` per known prefix, with request
(``*-request.json``) and response fixtures paired by filename ordinal.
Files present in only one directory are reported as added/removed.

Exit status: 0 when the sets are identical, 1 when any difference exists —
suitable for gating a commit on a human having actually looked.

Usage:
    python diff_fixtures.py <old_dir> <new_dir>
"""

from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

#: Fixture filename prefixes, mirroring replay_server.SUFFIXES.
PREFIXES: tuple[str, ...] = ("anthropic", "gemini")


def _fixture_names(directory: Path) -> list[str]:
    """Sorted fixture filenames (requests and responses) in a directory."""
    names: list[str] = []
    for prefix in PREFIXES:
        names.extend(
            path.name for path in sorted(directory.glob(f"{prefix}-*.json"))
        )
    return names


def _canonical(path: Path) -> list[str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(document, indent=2, sort_keys=True).splitlines(
        keepends=True
    )


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    old_dir, new_dir = Path(argv[1]), Path(argv[2])
    for directory in (old_dir, new_dir):
        if not directory.is_dir():
            print(f"not a directory: {directory}", file=sys.stderr)
            return 2

    old_names = _fixture_names(old_dir)
    new_names = _fixture_names(new_dir)
    differences = 0

    for name in sorted(set(old_names) | set(new_names)):
        if name not in old_names:
            print(f"ADDED: {name} (only in {new_dir})")
            differences += 1
            continue
        if name not in new_names:
            print(f"REMOVED: {name} (only in {old_dir})")
            differences += 1
            continue
        diff = list(
            difflib.unified_diff(
                _canonical(old_dir / name),
                _canonical(new_dir / name),
                fromfile=str(old_dir / name),
                tofile=str(new_dir / name),
            )
        )
        if diff:
            sys.stdout.writelines(diff)
            print()
            differences += 1

    if differences:
        print(f"{differences} fixture file(s) differ")
        return 1
    print("fixtures identical")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
