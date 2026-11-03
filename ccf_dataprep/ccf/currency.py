"""Artifact CURRENCY — is this file still built from the bytes on disk?

`docs/wave11b-design.md` §5 committed to this and Wave 11b shipped without it:

> Where a generator depends on another's artifact, the dependency is enforced
> with an explicit guard that **raises naming the required order** — and,
> unlike Wave 11a's guard, checks that the artifact is *current* rather than
> merely present. `known-issues.md` records that a stale `wave11a_grades.json`
> satisfies the existence check silently; that residual hazard is not repeated
> here.

Every artifact read in the wave was a bare `json.loads`. This module is the
guard, built 2026-08-21.

## The mechanism, in one sentence

A generator records the **sha256 of every artifact it consumed** into its own
output, under `_inputs`; every downstream consumer re-hashes those files on
disk and refuses to proceed if the bytes have changed since.

That converts "the file exists" into "the file is the one this output was
actually built from", which is the whole of the §5 promise. It costs one
`_inputs` dict per generator and one call per consumer.

## What it catches — and what it does NOT, stated plainly

CATCHES — the ordering hazard, which is the one §5 named:

    regenerate `wave11b_gdelt.json`, then load without re-running
    `generate_signals.py`  ->  the loader RAISES, naming the required order,
    instead of writing a signal ledger derived from bytes that no longer
    exist.

DOES NOT CATCH — an input that is *wrong* rather than *stale*. If someone
restores a pre-fix `wave11b_gdelt.json` **and** re-runs `generate_signals.py`
against it, the new ledger records the old file's hash, the hashes agree, and
this guard passes while the estate fills with 1,809 mentions about Bognor
Regis, a wrestler and a vulture (`known-issues.md` §10.1). A content-hash
guard can only ever say *"these are the bytes I was built from"*; it cannot
say *"these were the right bytes"*. The defence against that failure is
`validators/surveillance.py` check 6 (GDELT concentration, which the pre-fix
head would fail) and the sampling record in §10.1 — not this module. Recorded
here rather than left for a reader to discover, because a guard whose limits
are unstated is how "checked" becomes "assumed".
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ccf.config import REPO_ROOT

SCREEN = REPO_ROOT / "sources" / "screening"


class StaleArtifact(RuntimeError):
    """Raised when an artifact's recorded inputs no longer match disk."""


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_inputs(*names: str) -> dict[str, str]:
    """`{artifact name: sha256}` for every artifact a generator consumed.

    Call this in the generator, and put the result in its output under
    `_inputs`. Names are relative to `sources/screening/`, so the record is
    portable and reads as a dependency list rather than as a machine path.
    """
    return {n: sha256_of(SCREEN / n) for n in sorted(names)}


def verify_current(name: str, *, required_order: str = "") -> tuple[dict, str]:
    """Load `sources/screening/<name>` and verify its `_inputs` against disk.

    Returns `(document, one-line verdict)`. Raises `StaleArtifact` — never
    returns a partial answer — if any recorded input's bytes have changed.

    An artifact with no `_inputs` key is reported as such rather than passed
    silently. That is the honest state for a FETCH output: `fetch_8k_items`,
    `fetch_warn` and `fetch_gdelt` read the network, not other artifacts, so
    there is nothing upstream for them to be stale against. The verdict line
    says so on every run, so the coverage of this guard is visible instead of
    inferred.
    """
    doc = json.loads((SCREEN / name).read_text())
    recorded = doc.get("_inputs")
    if recorded is None:
        return doc, (f"{name}: no `_inputs` record — nothing upstream to be "
                     f"stale against (fetch output, or predates 2026-08-21)")

    drifted = []
    for dep, want in sorted(recorded.items()):
        path = SCREEN / dep
        if not path.exists():
            drifted.append(f"{dep} is MISSING")
            continue
        got = sha256_of(path)
        if got != want:
            drifted.append(f"{dep} changed ({want[:12]}… -> {got[:12]}…)")

    if drifted:
        raise StaleArtifact(
            f"{name} is STALE: it was built from inputs that no longer match "
            f"disk — " + "; ".join(drifted) + "."
            + (f" Required order: {required_order}" if required_order else "")
            + " Re-run the generator that produces this artifact, then reload."
        )
    return doc, (f"{name}: current — {len(recorded)} recorded input(s) "
                 f"re-hashed and matching")
