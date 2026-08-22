# Deferred items — phase 21

Out-of-scope discoveries logged rather than fixed, per the executor's scope
boundary and per `D-11`: **this phase FINDS and RECORDS; an executor that
closes a gap it discovers has turned an audit into an unplanned implementation
phase.** Plan `21-05` carries these to Dave with the work list.

## From plan `21-01`

**1. `Makefile`'s `gate-tools` comment cites `.github/workflows/ci.yml:314`,
which is not the command it claims to quote.** The comment says *"The two
commands are `.github/workflows/ci.yml:35` and `:314` verbatim"*. `:35` is
correct — it is the lint job's `pytest tools/lints/tests -q`. `:314` is not:
at plan `21-01`'s pinned base it pointed at the `docs` job's bare `steps:`
line, and the command it means (`pytest tools/publish_scan_tests
tools/docs_tests -q`) sat sixteen lines further down.

- **Pre-existing, not caused by this phase.** Measured against
  `21-BASE-COMMIT.txt`'s parent: the citation was already off before plan
  `21-01`'s `fetch-depth: 0` edit. That edit moved the true target further
  (the command is now lower in the file still), but the pointer never
  addressed it.
- **Why nothing caught it.** The citation lint reads `.py`, `.md`, `.yaml`
  and `.yml`. A `Makefile` has no suffix and is never scanned, so a line
  citation inside one is unchecked by construction. This is the same shape as
  `D-IMPL-174`'s second counter — a pointer nothing in the toolchain can
  verify.
- **Not fixed here.** The `Makefile` is not among plan `21-01`'s
  `files_modified`, and correcting a stale pointer is a repair, not a finding.
  Reported.

**2. `gsd-sdk query audit-uat` filters on frontmatter `status:`.** Named, not
fixed, by `D-20` — tooling repair inside an audit phase, on the same reasoning
as `D-07` for the citation lint. It reports twenty-four items across nine
files; the files carry twenty-seven across eleven. The eleven-member roster in
`tools/docs_tests/test_requirement_ledger.py` is re-derived by parsing the
records rather than by asking the query.

**3. The citation lint's two silent-drop holes stay open.** A citation whose
basename is ambiguous, and a citation to a path that does not exist at all,
are both dropped without a finding. `D-07` holds `tools/lints/citations.py`
byte-identical for this phase, and plan `21-01` pins that mechanically. The
ledger check dodges both from the outside by requiring a cited path to exist
exactly as written; the repo-wide surface is unchanged and stays named.
