# Delivering a Context Product example — recipe for SDK Claude

> Companion to [How a spec is generated](spec_generation.md). That document ends
> when the specification is written and approved. **This one covers everything
> after**: building the example, making it runnable by somebody who has just
> cloned the repository, documenting it for two different audiences, and
> validating it before calling it done.
>
> Read both. Neither is optional, and the sequencing between them is a rule
> rather than a preference — see §1.

---

## 0 · What this document is

`spec_generation.md` governs **the specification**. This document governs
**the example that surrounds it**: the Makefile target, the venv, the README,
the documentation page, the banker-facing summary, and the validation that
proves all of them agree with the program.

Everything here was learned by shipping `cp-00` and `cp-01` and then watching a
reader — Dave — try to run them cold. **Most of these rules exist because
something failed in exactly the way the rule now prevents**, and where that is
true the failure is named, because a rule whose reason is invisible gets
optimized away by the next person.

**Scope note.** This document does not restate the specification recipe, the
ladder order, or the Gate 1/Gate 2 protocol. Those are `spec_generation.md` §2
and §3, and they still bind.

---

## 1 · The sequencing

```
spec authored  →  GATE 1 (Dave approves)  →  build  →  run against the estate
      →  document  →  validate every documented command  →  PAUSE for Dave
      →  GATE 2 / close
```

Two rules inside that line are absolute:

- **No implementation code before Gate 1.** `spec_generation.md` §2 owns this.
- **Pause after the build, before any close panel, `D-GATE`, or completion
  mark.** Dave evaluates the built product himself. He validates that the
  example *runs and produces the expected output* — which means the example has
  to be runnable by him, from a cold shell, without you in the loop. Sections
  3–5 exist entirely to make that true.

---

## 2 · The example layout

**This section is authoritative and supersedes the diagram in
`spec_generation.md` §7.2**, which predates the page and the summary.

```
examples/cp-NN-<slug>/
├── spec/CP-SPEC-NNN_<Product_Name>.md   ← written first; everything below derives from it
├── artifacts/
│   ├── assembly-recipe.yaml   ← §D.2 as data, with a WITNESS per step
│   ├── expected.yaml          ← what the served product should contain; derives nothing from a run
│   ├── question.yaml          ← the caller's vocabulary, read-side, and the asked_at pin
│   └── ttl.yaml               ← the class TTL and its ceiling
├── backends.yaml              ← the env-var NAME only; no host, no port, no credential
├── ccf_config.yaml            ← the Control Plane document
├── deployment.py              ← the interpreter
├── produce.py                 ← the spine
├── assembler.py               ← the governed seam
├── run.py                     ← the client
├── page/
│   ├── build_page.py          ← committed
│   ├── template.html          ← committed
│   └── run-transcript.txt     ← committed; the pinned run the page reproduces
├── README.md                  ← seven headings, gated (§4)
└── summary_explanations.md    ← the three-reader document (§6)
```

Plus, outside the example directory:

```
tests/examples/test_cp_01_output.py  ← one per example; the gates, marked for a substrate leg (§3)
```

The rendered `page/*.html` is **not** committed — `.gitignore` excludes
`examples/*/page/*.html` and re-includes `template.html`. The generator
reproduces the page from the tree.

---

## 3 · The Makefile target

**Every Context Product example gets an `example-cp-NN` target.** Without
one, the only way to run the example is a raw script invocation, and a reader
who has just cloned has no way to discover it.

Mirror `example-cp-00` / `example-cp-01`:

```makefile
example-cp-NN: ## Run examples/cp-NN-<slug> (PARAM… optional; needs CCF_CP_NN_<STORE>_DSN)
	$(ENV) $(PYTHON) examples/cp-NN-<slug>/run.py \
		$(if $(PARAM),--param $(PARAM))
```

Four rules, each with its reason:

- **Add the target to `.PHONY`.** Beside the other `example-*` names.
- **Every request parameter is OPTIONAL.** A threshold, an anchor, a principal
  and an as-of date are **request parameters, not deployment configuration, and
  a build tool is not a request channel.** Omitted, `run.py` asks the
  demonstration question declared in `artifacts/question.yaml`.
- **Do NOT add it to the `examples:` aggregate** when the example declares a
  networked substrate. It reads a real estate through an environment variable
  and there is no in-tree fixture it can fall back onto. A red check nobody can
  make green is worse than no check.
- **Its code path is still covered in CI, and by a different mechanism.** The
  test module sets `pytestmark = pytest.mark.<substrate>`, seeds a service
  container **itself** from `tests/examples/fixtures/`, and runs the example's
  own modules against it. The `leg-<substrate>` target then selects those tests **by
  marker**, so CI reaches them without the Makefile naming them. *The target
  runs the program; the leg proves the program.*

> **Learned the hard way.** A handoff recorded that cp-01's thirteen tests "run
> nowhere automatically." They ran in CI the whole time — the leg selects by
> marker over the entire `tests` tree. **Check the Makefile before recording an
> absence.** What was genuinely missing was the target, which is a smaller and
> different job.

---

## 4 · The venv, and the README run block

**Never write a bare `python` in a document.** This repository has no `python`
on `PATH`; `Makefile`'s `PYTHON := .venv/bin/python` is a path, and until `make
venv` existed nothing created it. A fresh clone's first `make` died on *"No such
file or directory"* naming an interpreter — which tells a new reader nothing.

Every example README's **Run it** section carries, in this order:

1. **`make venv`** — the first command in a fresh clone.
2. **The environment variable to export**, with what the role needs and what it
   must not have. Read-only, and say why: *nothing this example runs writes to
   the store it reads, and a role that could write would make that a promise
   rather than a guarantee.*
3. **The `example-cp-NN` target** — the one documented command.
4. **`make -s example-cp-NN`** — and say what `-s` is for: it suppresses make's
   echo of the recipe, which is the only thing that differs between the target's
   output and the transcript published on the documentation page.
5. **The no-make path**, spelling `.venv/bin/python` explicitly.
6. **The variations worth trying**, each of which changes the answer rather
   than the formatting, expressed as `make` invocations now that they are real.
7. **Which variations exit non-zero, and that this is correct.** Promoting a
   refusal to a `make` command makes `make: *** Error 1` visible, and an
   undocumented `Error 1` reads as a broken target. *A refusal is not a crash,
   but it is also not a success.*

**Connection strings.** `backends.yaml` holds the variable's NAME and nothing
else. Both libpq spellings work and neither is preferred — a
`host=… user=… password=…` keyword string and a `postgresql://…` URI. Say so,
because a reader who hits a quoting problem with one will assume the example is
broken. Note also that libpq reads `PGHOST`/`PGPORT`/`PGUSER`/`PGPASSWORD` from
the environment on its own, so the variable's contents can be as short as
`dbname=<database>`.

**The seven README headings are gated** by
`tests/examples/test_cp_readme_template.py`. Do not invent an eighth or rename
one.

---

## 5 · The documentation page

Governed by `EXAM-06` (`D-IMPL-217`, `D-IMPL-218`) for its **content** — the
spine, the build order, the collapsibles, the named snapshot. This section
covers only its **mechanics**.

- **Commit the generator and the template; never the render.** `build_page.py`
  substitutes each source file into `template.html` at build time, so the page
  cannot drift from the tree. `.gitignore` enforces the split.
- **Prefer a FULL generator to a partial one.** cp-00's is partial — five whole
  files placeholdered, ten hand-cut excerpts, eight authored blocks — and the
  excerpts can still drift. cp-01's places every source file behind a
  placeholder. Do it cp-01's way.
- **Commit `run-transcript.txt`** — the pinned run the page reproduces — and
  prove the generator's output matches the published page rather than assuming
  it.
- **Name the snapshot in one sentence**, in the *what would fail* section:
  the commit, the `asked_at` pin, and the content address. `D-IMPL-218`.
- **Republish after any change to a file the page reproduces.** Editing a README
  makes the published artifact stale. This is easy to forget, and the page is
  what Dave shows people.

---

## 6 · `summary_explanations.md` — the three-reader document

**Every Context Product example ships one, beside the README.** Dave presents
from it directly.

**Its audience is THREE readers at once — corrected 2026-08-29 by Dave, and the
correction is worth keeping visible because this document caused the error.**
An earlier revision of this section said *"bankers, not engineers"*, and both
`cp-00` and `cp-01`'s summaries were written to it. Dave: *"Technical product
managers, engineers and banker subject matter experts are the audience... More
tech than bankers."* A document pitched at one of those three is wrong for the
other two, and the failure is asymmetric — a subject-matter expert can skip a
mechanism paragraph, while an engineer given only consequence has no way to
check whether any of it is true.

**Do not write a third document.** The README explains the example to somebody
building one; this explains the product to somebody deciding whether to fund it,
and to somebody who has to believe it. Those are the same document with a
mechanism layer, not two.

### The shape that serves all three

**One section per run, three parts, in this order:**

1. **The output** — the command, and the program's exact text (§7).
2. **What you'd have missed** — the business consequence, framed as a
   consequence rather than a property.
3. **How it works** — the operator, the artifact and the gate. Name the file. A
   reader who wants to check a claim should not have to search for where it
   lives.

**Two more sections carry the technical half**, and both belong near the end
rather than the front, so the consequence is read first:

- **A vocabulary table with a third column** — what the term means to a reader,
  AND what it is in the system. `Content address` is *a tamper-evident seal on
  one answer* and it is *`sha256` over the canonical bytes of the served
  product*. Both, in one row.
- **"Where each claim is enforced"** — every claim mapped to its mechanism and
  the gate that fails if it stops being true. This is the section that answers
  *"what stops this from regressing?"*, and it is the one a product manager
  reads to tell a demonstration from a guarantee.

### What it must carry

- **The argument in one paragraph**, up front. *A report tells you what the data
  says; a Context Product tells you what you may rely on, who may rely on it,
  how long it stays good, how complete it is, and refuses rather than guessing.*
  Follow it with **the one-line version of what is new at this rung**, because a
  reader who knows the catalog wants the delta, not the pitch.
- **A vocabulary table, two readings per term** (see above).
- **The pipeline in three rows** — Resolve, Policy, contract assembly, with what
  each does and which layer it is. Every difference between the runs comes from
  one of the three, and naming them once up front stops each run's mechanism
  block from re-explaining the fabric.
- **One section per run**, with the command, the real output, and — the part
  that carries the document — **"what you'd have missed."**
- **The lift, named per run, as a business consequence.** Not that the fabric is
  clever: that the ordinary tool quietly returns a wrong-looking-right answer.
  A duplicate client file. A stale identity in a credit memo. A silently ignored
  as-of date that makes today's data wear last quarter's label. **Frame every
  figure as a consequence, not as a property.**
- **A "why you can trust these numbers" section** naming the snapshot, exactly
  as the page does.
- **A section on what the runs do NOT show.** An audience of this kind trusts a
  document more, not less, for naming its limits.

### Discipline

- **Regulatory framing stays general** — say *"trade reporting regimes that
  require an active LEI"*, not a cited rule number, unless the citation has been
  verified. A wrong citation in front of this audience costs more than the
  point was worth.
- **Every figure comes from a real run.** Banking readers discount unverifiable
  numbers hard, and the reproduction instructions are what make them checkable.
- **US English** — see §8.

---

## 7 · Verbatim-output discipline

**This applies to the page, the summary and the README alike, and it is the rule
most likely to be broken by good intentions.**

> **Every code fence that looks like program output must be the program's exact
> text, or be explicitly labeled an excerpt.**

The failure mode is specific: making output *readable* by relabelling it. Print
`completeness` where the program prints `context debt D_c`, or `seal` where it
prints `content address`, and a reader running the example during a presentation
sees different text from the handout. **A documentation defect that presents as
a fabric defect** — the reader debugs the wrong system.

The right shape is **the verbatim block, with the plain-English reading in a
table beside it**, never replacing it.

Three concrete rules:

- **Excerpts are labeled.** *"Two of the fields in the record it returns"*,
  *"three lines lifted from the summary block"*. A fence implies contiguity;
  say when it is not.
- **Elisions are marked.** Dropping two fields from the middle of an error
  message without a marker is an unsigned edit to the program's own words.
- **Prose in a fence is prose, not output.** If you wrote it, do not fence it.

### How to verify it

Not by re-reading. **Check every fenced block against captured run output, then
check the survivors line by line, with a control.**

```
1. Capture each documented command's output to a file.
2. Extract every non-bash fenced block from the document.
3. Normalize whitespace, and test each block for containment in the captured runs.
4. For blocks that fail — the legitimate excerpts — test each LINE individually.
5. Run a control: a plausible string that must NOT be found. If it is, the
   instrument is broken and the greens mean nothing.
```

> **Learned the hard way, twice in one document.** The first pass checked
> sixteen strings *already suspected* and passed. Re-reading found four more
> blocks that were not the program's text at all — including two the author had
> written and fenced. **Checking what you suspect is not checking.** The second
> pass enumerated every block and found them immediately.

---

## 8 · US English

`CLAUDE.md` carries the rule; it binds every artifact this project produces.
US spelling and usage throughout — *behavior*, *catalog*, *analyze*, *-ize*,
*center*, *artifact*.

**With one carve-out that matters here:** identifiers, quoted source, and
verbatim program output are **exempt**. If the program prints a British
spelling, the document reproduces it exactly as printed. A blanket sweep would
otherwise make documents disagree with the code they document — which is §7's
failure mode arriving through a different door.

---

## 9 · Validate before you call it done

**Run every command the documentation names, and confirm the behavior matches
what the documentation claims.** Not the happy path — every one.

- **The default run must reproduce the published transcript byte-for-byte.**
  Diff it, and prove the diff is not blind by planting a change and watching it
  fail.
- **Every variation must do what its line says it does.** A variation described
  as changing the answer must change the content address; one described as
  refusing must refuse, with the reason the document quotes.
- **Every refusal's exit code must match what the README claims.**
- **The content address is the single check worth running.** It is a hash over
  the whole answer, so it only reproduces if every input did — the resolved
  entity, the entitlements, the debt figure, the TTL window, the operator plan.
  One drifted value anywhere and the hash differs.

---

## 10 · Housekeeping that bites

- **The generated retirement-coupling report under `docs/surface/` records
  Makefile line numbers.** Adding a target shifts them and turns
  `test_the_committed_report_is_current` red. Regenerate with
  `python tools/retirement_sweep.py --report`.
- **Two docs gates read this recipe as if it were instructions to a reader,
  because it is one.** `test_documented_commands_exist.py` scans every code
  span and fence on a published page for a `make <target>` invocation and fails
  if the Makefile has no such target — so a placeholder like `example-cp-NN` is
  named as *a target* here rather than spelled as a runnable command, since `NN`
  is not a target and the page would be telling a reader to run something that
  does not exist. `test_no_stale_example_paths.py` does the same for `examples/`
  paths, exempting tokens containing `<…>`, `{…}` or a standalone `NN` — which
  is why placeholder paths here are written `test_cp_<NN>_output.py` rather than
  `test_cp_NN_output.py`, where the underscores stop the word-boundary match.
  Its path matcher also starts at a bare `examples/` even mid-path, so a real
  file whose directory happens to contain that segment cannot be cited in full.
- **A new page under `public/` must be added to the `mkdocs.yml` nav.** The nav
  is enumerated explicitly and `--strict` fails an omitted file.
- **Attribute a red before fixing it.** Revert to a clean `HEAD`, re-run, and
  see whether it passes there. A failure you assumed was inherited and a failure
  you caused need different responses.
- **Diff `.planning/STATE.md` before staging anything.** It has been silently
  truncated at least once, and `git add -A` swept the damage into a commit.
- **Verify a push against the remote**, not against the local ref.
  `git ls-remote origin main` is the check; `git rev-parse origin/main` only
  reports what the last fetch believed.

---

## 11 · Definition of done — delivery

`spec_generation.md` §8 lists the specification's conditions. These are the
example's, and both must hold.

- **The `example-cp-NN` target exists**, is in `.PHONY`, appears in `make help`, and
  every request parameter is optional
- **`make -s example-cp-NN` reproduces the published transcript byte-for-byte**,
  proven with a diff whose blindness was tested
- **The README's Run-it section names `make venv` and `.venv/bin/python`**, and
  no document in the example writes a bare `python`
- **Seven README headings, unchanged**, passing
  `tests/examples/test_cp_readme_template.py`
- **The test module is marked for a substrate leg**, seeds its own fixture, and
  is selected by the `leg-<substrate>` target — confirmed by running that leg, not by
  reading the marker
- **Every product gate has been made to fail deliberately at least once**, and
  a gate asserting a shipped defect is written so that **it turns red when the
  defect is fixed**
- **`page/build_page.py` and `template.html` are committed, the render is not**,
  and the generator's output has been proven to match the published page
- **The page names its snapshot in one sentence** (`D-IMPL-218`)
- **`summary_explanations.md` exists**, is written for all three readers (§6), and
  names the lift per run
- **Every fenced block in every document is the program's exact text or a
  labeled excerpt**, verified block-then-line against captured output with a
  control
- **Every documented command has been run**, and its behavior matches its
  description
- **US English throughout**, output excepted
- **`make lint` rc=0 and the docs gates pass**, with
  `RETIREMENT-COUPLINGS.md` regenerated if the Makefile changed
- **Findings are raised, not resolved.** An SDK-surface problem found while
  building is recorded in the spec's §F.4 and taken to Dave. `CLAUDE.md` §11 —
  an executor surfaces gaps; it does not close them.
- **Then stop.** Dave evaluates the built product before any close panel,
  `D-GATE` or completion mark.

---

## 12 · Summary

The specification is half the deliverable. The other half is an example a
stranger can clone, run, and understand — and two documents that explain it to
two different readers without either of them disagreeing with the program.

**The recurring defect across everything above is the same one**: a claim that
was true when written and went false without anything going red. A layout
diagram that predates two new files. A handoff recording tests as uncovered
when a marker already selected them. A transcript relabelled for readability. A
line-number reference in a generated report.

**None of those is caught by re-reading.** They are caught by running the
command, diffing the output, and keeping a control beside every check that is
supposed to come back green.
