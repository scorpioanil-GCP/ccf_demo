"""`ci-posture` — CI workflows run read-only and on immutable action pins (SEC-015).

A GitHub Actions workflow with no ``permissions:`` block runs with the
repository's default token grant, which may be read-write; an action
referenced by a tag (``actions/checkout@v4``) runs whatever commit that tag
points at *today*, and a tag can be moved. Either is a supply-chain path into
the build that produces the SDK a bank installs. CLAUDE.md §2.2 says *never a
secret in the tree*; this rule is the same commitment for the token CI holds
and for the code CI executes.

Two refusals, over every ``.github/workflows/*.yml`` / ``*.yaml`` under the
base, each file parsed with ``yaml.safe_load``:

1. **Permissions.** The workflow must carry a top-level ``permissions:`` block
   that is *restrictive*: exactly ``{contents: read}``, or an empty mapping
   ``{}`` with every grant enumerated per job. A missing block, a string form
   (``write-all``, ``read-all``), or any other top-level grant is refused —
   a write at the top level reaches every job. A job-level block may grant a
   write by name (``contents: write``); a job-level ``write-all`` is refused,
   because it enumerates nothing.
2. **Pins.** Every ``uses:`` — on a step, or on a job that calls a reusable
   workflow — must name a full 40-hex commit SHA, with a trailing ``# vN``
   comment on the same source line recording the tag the SHA was resolved
   from (the comment is what a reviewer and Dependabot read). A local action
   (``./path``) is in-tree and exempt; a ``docker://`` reference must carry an
   ``@sha256:`` digest. The comment is not in the parsed YAML, so each parsed
   reference is matched against the raw source lines; a reference with no
   matching ``uses: <ref>  # vN`` line is refused rather than assumed.

PyYAML (YAML 1.1) parses the bare key ``on:`` as the boolean ``True``; the rule
never reads that key and never sorts mixed-type keys, so a workflow's trigger
block cannot trip it.

The rule is mechanism, not a deployment value: the row ruled it
(``docs/superpowers/specs/2026-10-05-remaining-rows-exploit-tests.md``, SEC-015,
``D-IMPL-368``, ``D-IMPL-369``). Exit code is the gate signal, as for every rule
in ``tools/lints/__main__.py``; there is no allowlist (D-13). A base with no
``.github/workflows`` directory yields no findings, so the runner's synthetic
trees stay clean; the committed tree is pinned by
``tools/lints/tests/test_ci_posture.py::test_the_lint_reads_exactly_the_committed_workflows``.
"""

from __future__ import annotations

import pathlib
import re
from collections import Counter
from typing import Any, Iterator

import yaml

RULE = "ci-posture"

#: Where the workflows live, relative to the base.
WORKFLOW_DIR = pathlib.Path(".github") / "workflows"

#: A full commit SHA.
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")

#: A docker reference pinned by digest.
DOCKER_DIGEST = re.compile(r"^docker://[^@\s]+@sha256:[0-9a-f]{64}$")

#: A raw ``uses:`` source line: the reference, then an optional comment.
_RAW_USES = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<q>['\"]?)(?P<ref>[^\s'\"#]+)(?P=q)\s*(?:#\s*(?P<comment>.*?))?\s*$"
)

#: The trailing tag comment: ``# v4`` or ``# v4.2.2``.
_TAG_COMMENT = re.compile(r"^v\d+(?:\.\d+)*\b")

#: The only restrictive non-empty top-level grant.
_TOP_LEVEL_READ_ONLY: dict[str, str] = {"contents": "read"}


def workflow_paths(base: pathlib.Path) -> list[pathlib.Path]:
    """Every workflow file under ``base``, sorted, ``.yml`` and ``.yaml``."""
    root = base / WORKFLOW_DIR
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_file() and p.suffix in {".yml", ".yaml"})


def _uses_sites(doc: dict[Any, Any]) -> Iterator[tuple[str, str]]:
    """``(where, ref)`` for every ``uses:`` on a job or a step."""
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            continue
        if "uses" in job:
            yield f"jobs.{job_id}", str(job["uses"])
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for index, step in enumerate(steps):
            if isinstance(step, dict) and "uses" in step:
                yield f"jobs.{job_id}.steps[{index}]", str(step["uses"])


def _raw_uses_lines(text: str) -> list[tuple[int, str, str | None]]:
    """``(lineno, ref, comment)`` for every raw ``uses:`` source line."""
    found: list[tuple[int, str, str | None]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = _RAW_USES.match(line)
        if match is not None:
            found.append((lineno, match.group("ref"), match.group("comment")))
    return found


def _permission_findings(doc: dict[Any, Any], path: str) -> list[str]:
    findings: list[str] = []
    if "permissions" not in doc:
        findings.append(
            f"{path}:1 {RULE} no top-level `permissions:` block; the token takes"
            " the repository default, which may be read-write — declare"
            " `permissions: {contents: read}`"
        )
    else:
        top = doc["permissions"]
        if not isinstance(top, dict):
            findings.append(
                f"{path}:1 {RULE} top-level `permissions: {top!r}` is not"
                " restrictive; declare `permissions: {contents: read}`"
            )
        elif top and top != _TOP_LEVEL_READ_ONLY:
            findings.append(
                f"{path}:1 {RULE} top-level `permissions:` grants"
                f" {dict(top)!r}; the top level may grant `contents: read` only"
                " — enumerate any write on the job that needs it"
            )
    jobs = doc.get("jobs")
    if isinstance(jobs, dict):
        for job_id, job in jobs.items():
            if isinstance(job, dict) and isinstance(job.get("permissions"), str):
                if job["permissions"] != "read-all":
                    findings.append(
                        f"{path}:1 {RULE} jobs.{job_id} `permissions:"
                        f" {job['permissions']}` enumerates nothing; name each"
                        " grant the job needs"
                    )
    return findings


def _pin_findings(doc: dict[Any, Any], text: str, path: str) -> list[str]:
    findings: list[str] = []
    raw = _raw_uses_lines(text)
    commented: Counter[str] = Counter(
        ref for _, ref, comment in raw if comment is not None and _TAG_COMMENT.match(comment)
    )
    line_of: dict[str, int] = {}
    for lineno, ref, _ in raw:
        line_of.setdefault(ref, lineno)
    for where, ref in _uses_sites(doc):
        lineno = line_of.get(ref, 1)
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DOCKER_DIGEST.match(ref):
                findings.append(
                    f"{path}:{lineno} {RULE} {where} `uses: {ref}` is not pinned"
                    " by `@sha256:` digest"
                )
            continue
        _, at, version = ref.rpartition("@")
        if not at or not FULL_SHA.match(version):
            findings.append(
                f"{path}:{lineno} {RULE} {where} `uses: {ref}` is on a mutable"
                " ref; pin the full 40-hex commit SHA with a trailing `# vN`"
            )
            continue
        if commented[ref] <= 0:
            findings.append(
                f"{path}:{lineno} {RULE} {where} `uses: {ref}` has no trailing"
                " `# vN` comment on its source line naming the tag it pins"
            )
            continue
        commented[ref] -= 1
    return findings


def check_source(text: str, path: str) -> list[str]:
    """Findings for one workflow's text, as ``path:line rule message``."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"{path}:1 {RULE} workflow does not parse as YAML: {exc}"]
    if not isinstance(doc, dict):
        return [f"{path}:1 {RULE} workflow is not a mapping"]
    return _permission_findings(doc, path) + _pin_findings(doc, text, path)


def check_tree(base: pathlib.Path) -> list[str]:
    """Whole-tree entry point for ``python -m tools.lints``."""
    findings: list[str] = []
    for path in workflow_paths(base):
        rel = path.relative_to(base).as_posix()
        findings.extend(check_source(path.read_text(encoding="utf-8"), rel))
    return findings
