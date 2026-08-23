# Phase 22: The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack - Pattern Map

**Mapped:** 2026-08-23
**Files analyzed:** 4 (2 new, 2 modified)
**Analogs found:** 4 / 4 (2 exact, 2 role-match)

Every measurement in this document was taken against the tree at
`acbe632` by running the command shown beside it. Where CONTEXT.md
asserted a figure, it was re-run rather than copied; each is marked
**verified** or **corrected**.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `public/concepts/<planner's-name>.md` (NEW) | published Concepts page (docs) | read-only render; `--8<--` literal include + prose citation | `public/tutorial/adopters-guide.md` (include-and-name-the-test pattern) + `public/concepts/invariants.md` (Concepts heading shape) | role-match (see §"No Analog Found" — no Concepts page currently includes source code) |
| `tools/docs_tests/<planner's-name>.py` (NEW) | prose gate / test module | batch scan over `public/**/*.md`, paragraph-scoped, plus tmp-dir mutation controls | `tools/docs_tests/test_gate_two_wording.py` | **exact** — named in CONTEXT.md `D-04` as "the shape `D-04` copies" |
| `mkdocs.yml` (EDIT) | config | declarative nav | its own `Concepts:` block, lines shown in §"`mkdocs.yml`" | **exact** |
| `.planning/REQUIREMENTS.md` (EDIT) | ledger (hand-edited) | two-channel row edit | the `DOCS-16` row (checkbox line 41 + table line 335) | **exact** |

---

## Pattern Assignments

### 1. `tools/docs_tests/<wording-gate>.py` (prose gate, batch scan)

**Analog:** `tools/docs_tests/test_gate_two_wording.py` (304 lines) — copy its
structure wholesale. Second analog for the mutate-a-copy controls:
`tools/docs_tests/test_advisory_discharge.py` (533 lines).

**Registration is free.** No wiring is needed beyond dropping the file into
`tools/docs_tests/`. `Makefile:188-190`:

```make
gate-tools: ## Run the tools/ suites CI runs that `testpaths` excludes from `make test`
	$(ENV_DOCS) $(PYTHON) -m pytest tools/lints/tests -q
	$(ENV_DOCS) $(PYTHON) -m pytest tools/publish_scan_tests tools/docs_tests -q
```

and `Makefile:138` / `:172` — `ci-core: lint typecheck test gate-tools`,
`ci: ci-core examples docs-strict gate-tools`. The CI `docs` job runs the same
two directories directly.

#### 1a. Imports pattern (`test_gate_two_wording.py:46-54`)

```python
from __future__ import annotations

import pathlib
import re
import shutil

import pytest

from tools.docs_tests import _prose
```

`_prose` is the shared paragraph reader (`tools/docs_tests/_prose.py`, 262
lines). **Do not hand-roll a line-scoped `grep -rn` over `public/`.** Its own
docstring (`_prose.py:33-36`) names that as the defect:

> **The warning sign.** A plan step spelled ``grep -rn "<phrase>" public/`` is
> the thing this module exists to remove. If a new gate reaches for a
> line-scoped regex over an unjoined file, it has reintroduced the defect that
> cost Phase 15.1 six sweeps.

The API the new gate needs, all from `_prose`:

| Symbol | Signature / meaning |
|---|---|
| `_prose.PUBLIC_DIR` | `REPO_ROOT / "public"` — resolved from `__file__`, never the CWD |
| `_prose.published_pages(root=None)` | `sorted(base.rglob("*.md"))` |
| `_prose.iter_paragraphs(pages, *, prose_only=True)` | yields `(page, Paragraph)`; `prose_only=True` skips fenced blocks — what a *wording* gate wants |
| `_prose.Paragraph` | `NamedTuple(text, lineno, raw, fenced, info)`. `text` = markup-stripped, code spans removed, casing preserved. `raw` = nothing stripped, code spans survive. |
| `_prose.sentence_at(text, offset)` | the sentence containing `offset` — this is the sentence scoping |
| `_prose.relative(path)` | repo-relative POSIX, or absolute if off-root (tmp-dir controls) |

**Which field to match against.** `text` for wording (code spans are noise);
`raw` only if the gate must see a path or symbol an author wrote as an inline
code span. `test_no_stale_example_paths.py` is the one gate that wants `raw`
and says so at `test_no_stale_example_paths.py:50-56`.

#### 1b. Vocabulary constants — module-level, `#:`-documented, regex

`test_gate_two_wording.py:56-86`:

```python
#: The subject. ``Gate 2`` is included alongside the invariant id and the long
#: name because published prose uses all three interchangeably, and a gate that
#: reads only the formal id is defeated by an author writing English.
GATE_TWO = re.compile(
    r"INV-CH7-47|lineage strict equality|\bGate 2\b",
    re.IGNORECASE,
)

#: The correction that must be present when Gate 2's job is described.
CORRECTION = re.compile(r"assembly-path integrity", re.IGNORECASE)

#: Verbs that turn a *mention* of Gate 2 into a *characterization* of it. A
#: paragraph containing one of these is making a claim about what the gate
#: establishes, and therefore owes the reader the correction.
CHARACTERIZES = re.compile(
    r"\b(?:verif(?:y|ies|ying)|establish(?:es|ing)?|prove[sd]?|proving"
    r"|witness(?:es|ing)?|confirm(?:s|ing)?|guarantee(?:s|ing)?"
    r"|attest(?:s|ing)?|demonstrat(?:e|es|ing))\b",
    re.IGNORECASE,
)

#: The claim being guarded against.
INDEPENDENCE = re.compile(r"\bindependent(?:ly)?\b", re.IGNORECASE)

#: Tokens that turn an independence mention into a denial of one. Word-bounded
#: on purpose: an unbounded ``not`` matches "nothing", "note" and "another",
#: which would exonerate every paragraph in the tree.
NEGATION = re.compile(
    r"\b(?:not|never|cannot|rather than|instead of|no)\b",
    re.IGNORECASE,
)
```

The four-part decomposition transfers directly to obligation 1 of `D-04`:
**SUBJECT** (which external approaches the sentence is about — RAG, vector
store, semantic layer, prompt template, hand-rolled assembly) × **LIMIT VERB**
(the `X can't Y` shape: `cannot`, `can't`, `unable to`, `lacks`, `fails to`,
`has no`, `does not support`, `is incapable of`) × **GROUNDING** (what
exonerates: an adjacent `--8<--` include, a question-fact recast, an explicit
`D-03` pairing marker) × **NEGATION/scope** (the boundary from the other side).

#### 1c. Sentence scoping — the mechanism, quoted (`:109-134`)

```python
def _denies_independence(text: str) -> bool:
    """Whether every ``independent`` in `text` sits in a negating sentence."""
    matches = list(INDEPENDENCE.finditer(text))
    if not matches:
        return False
    return all(
        NEGATION.search(_prose.sentence_at(text, match.start())) is not None
        for match in matches
    )


def paragraphs_asserting_independence(
    pages: list[pathlib.Path],
) -> list[str]:
    """`page:line — sentence` for every affirmative independence claim."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages):
        if not GATE_TWO.search(paragraph.text):
            continue
        for match in INDEPENDENCE.finditer(paragraph.text):
            sentence = _prose.sentence_at(paragraph.text, match.start())
            if NEGATION.search(sentence) is None:
                offenders.append(
                    f"{_prose.relative(page)}:{paragraph.lineno} — {sentence.strip()}"
                )
    return offenders
```

Note the two-level shape: **paragraph** is the unit of *candidacy* (does this
paragraph talk about the subject at all), **sentence** is the unit of
*judgement*. Offenders are reported as `page:line — sentence`, openable.

The `continue` with an inline comment at `:101-104` is the pattern for "this
is a legitimate way to be right":

```python
        if INDEPENDENCE.search(paragraph.text) and _denies_independence(paragraph.text):
            # The paragraph makes the point in the negative rather than by
            # naming the correction. That is a legitimate way to be right.
            continue
```

#### 1d. Non-vacuity floors — three of them (`:137-182`)

```python
# --------------------------------------------------------------------------
# Preconditions — a vacuous pass is the failure this module exists to prevent.
# WR-04: a CWD-relative walk scanned zero files and the gate passed over
# nothing.
# `tools/publish_scan_tests/test_docstring_leaks.py::test_the_walk_does_not_depend_on_the_process_cwd`
# is the model.
# --------------------------------------------------------------------------


def test_the_published_tree_is_populated() -> None:
    assert _prose.PUBLIC_DIR.is_dir(), f"missing published tree: {_prose.PUBLIC_DIR}"
    pages = _prose.published_pages()
    assert pages, f"no markdown pages under {_prose.PUBLIC_DIR}"
    assert any(
        GATE_TWO.search(paragraph.text)
        for _, paragraph in _prose.iter_paragraphs(pages)
    ), "no published paragraph mentions Gate 2 — this gate is scanning nothing"


def test_the_positive_assertion_has_something_to_assert_over() -> None:
    """At least one published paragraph *characterizes* Gate 2.

    The positive assertion below is a filter, and a filter that matches nothing
    passes forever. Two paragraphs trigger it today —
    ``public/reference/artifacts/product-registration.md`` and
    ``public/tutorial/adopters-guide.md`` — and both carry the correction. If
    this ever fails, the assertion has stopped scanning and the "green" it
    reports means nothing.
    """
    triggered = [
        f"{_prose.relative(page)}:{paragraph.lineno}"
        for page, paragraph in _prose.iter_paragraphs(_prose.published_pages())
        if GATE_TWO.search(paragraph.text) and CHARACTERIZES.search(paragraph.text)
    ]
    assert triggered, (
        "no published paragraph characterizes what Gate 2 verifies, so the "
        "positive assertion is passing over an empty set"
    )


def test_the_walk_does_not_depend_on_the_process_cwd(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _prose.published_pages(), "the walk resolved against the CWD, not the repo"
```

**Planner-critical:** the *corpus floor* shape above ("some real paragraph
triggers this filter") is available for obligation 1 only after the new page
ships, and only if the page actually names the three alternatives — which
`D-02` and `D-12` push it to do sparingly. It is **not available at all** for
obligation 2. See §"Measured facts" #6.

The alternative floor shape, for the case where a corpus floor would demand
padding, is stated in the `DOCS-16` ledger row (`.planning/REQUIREMENTS.md:41`)
and implemented in `test_advisory_discharge.py`:

> each advisory assertion is paired with a control that mutates a copy of the
> real page and asserts refusal, so **non-vacuity is proven by watching the
> gate fail rather than by a corpus floor**

and its module docstring states the same for A-3:

> **Measured at this plan's HEAD: zero published pages carry a ``boot(``
> invocation with arguments**, so the assertion currently passes over an empty
> set on purpose […] Non-vacuity is therefore proven by a control that injects
> a stale signature rather than by a floor on the corpus, because a floor here
> would demand a page write a call it has no reason to write.

#### 1e. The shipped assertions (`:185-206`)

```python
def test_every_characterization_of_gate_two_carries_the_correction() -> None:
    offenders = paragraphs_missing_the_correction(_prose.published_pages())
    assert not offenders, (
        "published paragraphs describe what Gate 2 verifies without saying it "
        "verifies assembly-path integrity — see D-IMPL-86 and its correction "
        "of 2026-08-05, and copy the canonical sentence from "
        "src/ccf/deployment/__init__.py:72-79: " + ", ".join(offenders)
    )
```

The failure message names *the ruling*, *where the canonical wording lives*,
and *the offenders*. Copy that three-part shape: a `D-04` failure should say
which obligation broke, what `D-02` requires instead, and the `page:line —
sentence`.

#### 1f. Injected-violation controls — the full set (`:209-305`)

```python
# --------------------------------------------------------------------------
# Controls — a gate nobody has watched fail is a gate that may scan nothing.
# Each injects a violation into a COPY of a real page and asserts refusal.
# --------------------------------------------------------------------------


def _copied_tree(tmp_path: pathlib.Path, extra: str) -> list[pathlib.Path]:
    """A copy of a real published page with `extra` appended."""
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / source.name
    shutil.copy(source, target)
    with target.open("a", encoding="utf-8") as handle:
        handle.write("\n\n" + extra + "\n")
    return [target]
```

The five controls, each with the property it holds:

| Control | Property held |
|---|---|
| `test_the_gate_refuses_an_injected_affirmative_independence_claim` | obligation 1 fires on the direct violation |
| `test_the_gate_refuses_a_characterization_missing_the_correction` | obligation 2 fires on the *subtle* violation — and asserts the **other** obligation does **not** fire: *"this control must be caught by the positive assertion alone; if the negative one also fires, the two are not testing different things"* |
| `test_the_unmodified_copy_passes_both_assertions` | the baseline — *"Without this, a control that 'refuses' proves nothing — the refusal could be coming from the page rather than from the injected paragraph."* |
| `test_a_negation_in_a_different_sentence_does_not_exonerate` | **sentence scoping proven rather than asserted** — injects `"Gate 2 is not optional. It is an independent witness that the operator set was right."` |
| `test_a_bare_enumeration_is_not_an_offender` | **the false-positive control** — injects `"The three validation gates are the empty-operator guard, lineage strict equality, and the TTL bound."` and asserts `== []`. Its docstring: *"If this ever fails, the gate has started demanding padding in correct prose."* |

Quoted in full, the two that are hardest to reconstruct:

```python
def test_the_unmodified_copy_passes_both_assertions(tmp_path: pathlib.Path) -> None:
    """The control's own baseline: the copy is clean before injection.

    Without this, a control that "refuses" proves nothing — the refusal could
    be coming from the page rather than from the injected paragraph.
    """
    source = _prose.PUBLIC_DIR / "tutorial" / "adopters-guide.md"
    target = tmp_path / source.name
    shutil.copy(source, target)
    assert paragraphs_missing_the_correction([target]) == []
    assert paragraphs_asserting_independence([target]) == []


def test_a_bare_enumeration_is_not_an_offender(tmp_path: pathlib.Path) -> None:
    """The trigger boundary, held from the other side.

    Naming lineage strict equality in a list of the three validation gates
    asserts nothing about independence. If this ever fails, the gate has
    started demanding padding in correct prose.
    """
    pages = _copied_tree(
        tmp_path,
        "The three validation gates are the empty-operator guard, lineage "
        "strict equality, and the TTL bound.",
    )
    assert paragraphs_missing_the_correction(pages) == []
```

**`_copied_tree` appends to a copy in `tmp_path`. The working tree is never
touched.** `test_advisory_discharge.py:412-417` is the same helper without the
append, when the mutation is a substitution rather than an addition:

```python
def _copy(tmp_path: pathlib.Path, relative: str) -> pathlib.Path:
    source = _prose.PUBLIC_DIR / relative
    assert source.is_file(), f"control fixture source missing: {source}"
    target = tmp_path / pathlib.Path(relative).name
    shutil.copy(source, target)
    return target
```

and `test_advisory_discharge.py:428-438` shows the substitution mutation plus a
**fixture-integrity assertion**, which is the piece `_copied_tree` does not
have:

```python
def test_the_a8_gate_refuses_a_page_that_states_only_reachability(
    tmp_path: pathlib.Path,
) -> None:
    """Strip the absence claim; the reachability sentence survives intact."""
    page = _copy(tmp_path, A8_PAGE)
    text = page.read_text(encoding="utf-8").replace("absent from", "reachable from")
    page.write_text(text, encoding="utf-8")
    assert A8_REACHABILITY in text, "the fixture removed the wrong half"
    offenders = a8_offenders(page)
    assert offenders, "the gate admitted a page stating only the reachable half"
```

**The control-fixture source page.** Both existing gates use
`public/tutorial/adopters-guide.md`. The new gate should use **the page this
phase ships** as its control fixture — an injected `X cannot Y` appended to
the adoption page proves the gate guards the page it exists for, and the
unmodified-copy baseline then also proves the shipped page is clean.

#### 1g. `D-06` — the stretch symbol-resolver test

If it lands, `test_requirement_ledger.py` shows how to reuse the citation lint
rather than reimplement it (`test_requirement_ledger.py:60`):

```python
from tools.lints.citations import CITATION, CITED_SUFFIXES, NODE_ID, repo_index
```

If it does not land, `D-06` requires it be **named as owed**, not skipped.

---

### 2. `public/concepts/<page>.md` (published Concepts page)

**Analogs, three of them, each for a different property:**

| Property | Analog |
|---|---|
| Concepts heading + prose shape | `public/concepts/invariants.md` (175 lines) |
| The result-citation pattern (`--8<--` the artifact, then name the test) | `public/tutorial/adopters-guide.md` (447 lines), `public/tutorial/demo-walkthrough.md` |
| What a Concepts page may embed | all 11 non-example includes under `public/concepts/` are `.mmd` diagrams |

#### 2a. Heading convention — `public/concepts/invariants.md:1-30`

No YAML frontmatter anywhere in `public/`. The page opens with a single `#`
title, an orientation paragraph, then `##` sections. Each invariant section
uses the same three bolded lead-ins:

```markdown
# Architectural invariants

CCF makes a small number of structural promises. Each one is what some
downstream guarantee — replay determinism, auditability, portability — actually
rests on, and each is enforced by a mechanism that fails the build or the call
rather than by a convention someone is expected to remember.

This page names all seven, says why the architecture forces each, and names the
specific thing that enforces it. An invariant with no named enforcement is an
aspiration, and the SDK does not ship those.

## Single writer to the graph

**The promise.** Exactly one component holds a write handle to the Context
Graph: L2 Context Assembly. Nothing else can write, under any circumstance.

**Why the architecture forces it.** ...

**How it is enforced.** ...
```

That last sentence of the orientation paragraph — *"An invariant with no named
enforcement is an aspiration, and the SDK does not ship those"* — is the house
voice for exactly the claim this phase's page makes. A parallel triple for the
adoption page reads naturally as **The question.** / **What the question
demands.** / **What the deployment does, and where to look.**

#### 2b. Include syntax inside a Concepts page — `invariants.md:30-33`

```markdown
The write path, and the two paths that look like exceptions but are not:

```mermaid
--8<-- "public/diagrams/seq-single-writer-write-path.mmd"
```
```

Include paths are repo-root-relative (`base_path: ["."]`, `mkdocs.yml:90`), so
an include of the spine is written `--8<-- "examples/s1-01-hello-context-product/spine.py:boot"`.

#### 2c. The result-citation pattern — quoted, three instances

The established pattern is: **include the declared output artifact, then name
the test that asserts it, in the same breath as the include.**

`public/tutorial/demo-walkthrough.md:79-85`:

```markdown
The run opens with two stages of banners (all console output is
deterministic and byte-compared in CI against
`artifacts/expected_output.txt` by `tests/examples/test_e2e_demo_output.py`
— the full expected transcript is in §8 below).
```

`public/tutorial/demo-walkthrough.md:292-302`:

```markdown
```
--8<-- "examples/08-e2e-demo/artifacts/expected_output.txt"
```

And the thin, generic driver that produced it — six labeled stages of
loading and mapping, opening with a single `load_and_boot` call over the
manifest above; deleting the artifacts would leave it nothing to run
(§6.4). It checks nothing itself: the driver returns its state and
`tests/examples/test_e2e_demo_output.py` holds every assertion,
including the byte-comparison, where a test runner can fail a build:

```python
--8<-- "examples/08-e2e-demo/run.py"
```
```

`public/tutorial/adopters-guide.md:198-206`:

```markdown
Each of the six axes resolves observably — the context contract admits the
served product, the perspective conditions the view and the record, the policy
regime excludes what it excludes, and the referenced artifacts resolve at
pinned versions or construction refuses. Two of those axes are visible in the
spine itself; `tests/examples/test_agent_basics_output.py` checks all six, one
test per axis. The [agent Protocol surface](../reference/protocols/agents.md)
names the methods used here:

```py
--8<-- "examples/01-agent-basics/run.py:specialization-axes"
```
```

`public/tutorial/adopters-guide.md:329-336`:

```markdown
Every failure mode fails closed and typed — unauthenticated, expired,
unsigned, and tampered are four distinct refusals, and none of them reaches
the authority path. The spine drives all four; that each is the *right* typed
refusal is asserted in `tests/examples/test_workflow_hitl_output.py`:

```py
--8<-- "examples/05-workflow-hitl/run.py:hitl-refusals"
```
```

`public/tutorial/adopters-guide.md:362-372`:

```markdown
Replay is the payoff for everything above. From a record address alone, the
engine resolves the graph snapshot, the policy bundle version, the agent
version, the skill-set in force, and the prompt artifact version — each at its
exact recorded version, never at "latest" — and reproduces the product
byte-for-byte through the canonical serializer. The byte-equality assertion
itself lives in `tests/examples/test_decision_replay_output.py`, where a runner
can fail on it; the spine is the call it asserts about:

```py
--8<-- "examples/06-decision-replay/run.py:replay-reproduce"
```
```

**The invariant across all four instances:** the test is named as a
`tests/examples/…py` path in an inline code span in the *prose immediately
preceding* the include, with an explicit statement of what a runner would go
red on. Note the prose is a path (`tests/examples/x.py`), not a `::symbol`
node id — both are gated by `tools/lints/citations.py`, and the path form is
what the published tree uses.

#### 2d. The subject: `examples/s1-01-hello-context-product`

**Seven spine snippet regions** in `examples/s1-01-hello-context-product/spine.py`
(617 lines), with exact marker lines and body sizes — measured, not copied:

| Marker | `[start:]` line | `[end:]` line | Body lines | Include target string |
|---|---|---|---|---|
| `boot` | 297 | 308 | 10 | `examples/s1-01-hello-context-product/spine.py:boot` |
| `ingest` | 333 | 340 | 6 | `…/spine.py:ingest` |
| `operators` | 342 | 361 | 18 | `…/spine.py:operators` |
| `project` | 363 | 397 | 33 | `…/spine.py:project` |
| `gate` | 399 | 549 | **149** | `…/spine.py:gate` |
| `record` | 551 | 577 | 25 | `…/spine.py:record` |
| `serve` | 579 | 605 | 25 | `…/spine.py:serve` |

**`gate` is 149 lines — six times the next largest.** A page that includes it
whole ships a wall. Pick deliberately; `operators` (18) and `project` (33) are
the two that carry the "sum over ownership paths" argument at readable size,
and `serve` (25) carries the callable-not-configurable point.

**The twenty artifacts** under `examples/s1-01-hello-context-product/artifacts/`,
with the six the argument needs sized:

`backends.yaml`, `debt-profile.yaml` (85), `events.yaml` (**502**),
`expected.yaml` (195), `half-life-table.yaml`, `manifest.yaml`,
`operator-parameters-policy.yaml`, `operator-parameters-similarity.yaml`,
`operator-parameters-temporal.yaml`, `operator-parameters-traversal.yaml`,
`perspective.yaml`, `policy-bundle.yaml`, `product-class.yaml`,
`product-governance.yaml`, `projection-requirements.yaml`, `questions.yaml`
(89), `request-contract.yaml`, `resolution-spec.yaml`,
`source-estate.yaml` (**576**), `ubo-question.yaml` (56).

**No artifact carries a snippet marker** — verified: the only `--8<--` string
anywhere under `examples/s1-01-hello-context-product/` outside `spine.py` is a
prose mention in `run.py:32`. So **every artifact include is whole-file.**
`events.yaml` (502) and `source-estate.yaml` (576) are not includable at
readable size; `ubo-question.yaml` (56), `debt-profile.yaml` (85) and
`questions.yaml` (89) are. `expected.yaml` (195) is borderline.

**The two artifact headers the argument rests on**, both quotable in prose
without an include:

`artifacts/ubo-question.yaml:5-19` — the *callable, not configurable* point
that separates CCF from a semantic layer plus prompt templates:

```yaml
# *"Who ultimately owns this company?"* is a question with a VOCABULARY, and
# every term of it is here rather than in `../deployment.py`: which class counts
# as a natural person, which class carries an ownership interest, and which
# attribute of that class carries the owner, the target and the percentage. The
# projection is an interpreter of this document. Delete it and there is nothing
# left for the projection to compute.
#
# THE SUBJECT IS NOT HERE, AND ITS ABSENCE IS THE POINT (plan 15.5-13).
# `subject_entity_ref` used to sit under `declaration:` below, which made this
# product *configurable* rather than *callable*: one class, one company, one
# frozen answer. Which company is being asked about is the caller's question,
# not the fabric's configuration — it arrives as `ProductRequest.subject`,
# validated at the door against the class's declared request contract
# (`request-contract.yaml`, D-IMPL-98).
```

`artifacts/debt-profile.yaml:18-26` — the staleness claim, in the artifact's
own words:

```yaml
# **The bands are calibrated so the demonstration crosses one, and that is
# stated rather than hidden.** `artifacts/questions.yaml`'s third question asks
# the same thing six weeks later against the same graph; the measured freshness
# falls from 0.995 to 0.803 and D_c rises from ~0.035 to ~0.221, which is above
# `forced_llm_threshold` and below `fail_closed_threshold`. The delivered
# product therefore carries `signal: forced_llm` — the CAR routing state doing
# its job on real measurement rather than being described in a comment. Move
# this number and the demonstration changes with it, which is the correct
# relationship between a calibration and an outcome.
```

**The sentence the page is the published expansion of**,
`examples/s1-01-hello-context-product/README.md:48-53`:

> It answers a question a vector store over chunked documents structurally
> cannot. Jane Doe holds 12.0% of Acme directly and 60.0% of a holding
> company that itself holds 30.0%. Her real interest is 30.0%, it crosses the
> regime's 25.0% threshold, and **no document in any source system states
> that number**. It is a sum over ownership paths, which is what a graph is a
> substrate for — and it is a *different* sum depending on which company you
> ask about and when.

Note: the README's own first sentence is a naked *"a vector store … structurally
cannot"* — precisely the shape `D-02` bars from the **published** page. The
README is not under `public/` and is out of the gate's `D-05` scope; the page
must recast it. The second half of that quote (*"no document in any source
system states that number"*) is already in `D-02`-conforming form and is the
sentence to build on.

#### 2e. Test functions that hold the numbers — cite these by name

In `tests/examples/test_s1_01_output.py` (1105 lines):

| Claim on the page | Test that asserts it |
|---|---|
| Jane's aggregate 30.0% matches the declared answer | `tests/examples/test_s1_01_output.py::test_the_aggregate_ownership_answer_matches_the_declared_expectation` (line 398) |
| The answer is a **sum over paths**, not a single hop — the load-bearing one for the RAG contrast | `…::test_the_answer_is_a_sum_over_paths_not_a_single_hop` (line 422) |
| The declared absences really are absent (each operator's witness) | `…::test_every_declared_absence_really_is_absent` (line 455) |
| The product answers the question the caller asked | `…::test_the_product_answers_the_question_the_caller_asked` (line 485) |
| A different company gets a different answer | `…::test_a_different_company_gets_a_different_answer` (line 680) |
| The same company at a later instant gets a different answer (Marcus Vale) | `…::test_the_same_company_at_a_later_instant_gets_a_different_answer` (line 707) |
| Debt rides the delivered product | `…::test_the_delivered_product_carries_its_debt` (line 811) |
| Debt is **measured, not constant**; `ok` → `forced_llm` band crossing driven by freshness | `…::test_the_debt_figure_is_measured_and_not_constant` (line 830) |
| The routing state carries the deployment's obligation | `…::test_the_routing_state_carries_what_this_deployment_says_it_obliges` (line 869) |
| The obligation in force is pinned into the replay record | `…::test_the_obligation_in_force_is_pinned_into_the_replay_record` (line 919) |

**A correction the planner must carry.** CONTEXT.md `D-15` names the band as
"0.035 `ok` → 0.221 `forced_llm`". Verified against the tree: **the test does
not assert either number.** `test_the_debt_figure_is_measured_and_not_constant`
asserts only a monotonic relation plus the band names:

```python
    fresh, stale = answers[0].product.debt, answers[2].product.debt

    assert stale.debt > fresh.debt, (
        f"the later question measured no more debt ({stale.debt}) than the"
        f" earlier one ({fresh.debt}); the figure is not measured"
    )
    assert fresh.signal.value == expected[EXPECTED_DEBT_SIGNAL_FIRST]
    assert stale.signal.value == expected[EXPECTED_DEBT_SIGNAL_THIRD]

    weak = expected[EXPECTED_DEBT_WEAK_FACTOR]
    assert getattr(stale.factors, weak) < getattr(fresh.factors, weak)
```

and `expected.yaml:170-176` says so deliberately:

```yaml
  # D_c rides the product (D-IMPL-100). These are the CAR routing states the
  # measured figures land in under `debt-profile.yaml`'s bands, not the figures
  # themselves: the numbers are a decay computation over the assembled view and
  # restating them here would be authoring the answer.
  debt_signal_first_question: "ok"
  debt_signal_third_question: "forced_llm"
```

**Consequence for the page.** `ok` → `forced_llm`, *freshness is the factor
that moves*, and *completeness and semantic consistency do not* are all
test-asserted and safe to state with a named test. The literal figures `0.035`
and `0.221` appear only in `examples/s1-01-hello-context-product/README.md:18-20`
and `artifacts/debt-profile.yaml:21` — neither is a test. If the page prints
them it should say they are the artifact's stated calibration example, not a
gated assertion; `D-15`'s *"if `s1-01`'s measurement will not carry the claim,
the claim is narrowed"* applies exactly here.

#### 2f. `expected.yaml` excerpts — the checkable question-facts (`D-02`)

`expected.yaml:62-75`:

```yaml
  ownership_percent_by_party:
    "http://example.org/fibo/JaneDoe": "30.000"
    "http://example.org/fibo/JohnSmith": "45.000"
    "http://example.org/fibo/SarahChen": "1.125"

  # Those at or above the regime's 25.0% threshold. Jane Doe is here ONLY
  # because 12.0% direct and 60.0% x 30.0% indirect were added together; no
  # record in any source system states her real figure.
  beneficial_owners:
    - party_ref: "http://example.org/fibo/JaneDoe"
      aggregate_ownership_percent: "30.000"
```

That comment — *"no record in any source system states her real figure"* —
is `D-02` already written: a checkable fact about the question, not a claim
about a rival.

#### 2f-i. The honesty caveat — original wording

`.planning/phases/16-…/abandoned/16-13-PLAN.md:241-245`:

> On `L`, carry the honesty caveat: the `passage_anchor` **contract** ships and
> is populated on `LineageEntry`, but Pattern 5 / `src/ccf/unstructured/` was
> never built, so there is **no shipped ingestion pipeline that produces
> passage anchors from documents**. The page may say the lineage contract
> anchors a claim to the passage it came from; it must not say CCF extracts
> passage anchors from your documents today.

and its gate shape at `:275`:

> The lineage section states the `passage_anchor` caveat; `grep -ci "extracts
> passage anchors\|passage anchors from your documents" public/` returns 0.

That grep is the line-scoped shape `_prose.py:33-36` bars. `D-04` obligation 2
is its paragraph-scoped replacement.

---

### 3. `mkdocs.yml` (EDIT — one `nav:` entry)

**The Concepts block, verbatim** (`nav:` begins at `mkdocs.yml:113`):

```yaml
  - Concepts:
      - Pillars:
          - Data and Context Layer: concepts/pillars/data-context.md
          - Orchestration Layer: concepts/pillars/orchestration.md
          - Core Agent Types: concepts/pillars/agent-types.md
          - Human in the Loop and Control: concepts/pillars/hitl.md
          - Experience Layer: concepts/pillars/experience.md
      - Invariants: concepts/invariants.md
      - Replay anatomy: concepts/replay-anatomy.md
      - Whitepaper cross-reference: concepts/whitepaper-index.md
```

Paths are relative to `docs_dir` (`public/`), so the new entry is
`concepts/<name>.md`, four-space-indented under `- Concepts:` at the same level
as `- Invariants:`.

**Placement is the planner's (`D-13`).** Two of the existing entries carry an
inline `# D-17 placement:` comment stating the reason for their position
(How-to lead, Reference tail) — that convention is available if placement needs
a stated reason.

**The strict-mode settings that make an include fail loudly** (`mkdocs.yml:84-100`,
plus `strict: true` at `:22`):

```yaml
  - pymdownx.snippets:
      # 14-RESEARCH Pitfall 2: resolved against the process CWD (repo root
      # under make), NOT this file's directory. ...
      base_path: ["."]
      # 14-RESEARCH Pitfall 1: at the default `false` BOTH a missing file and a
      # missing named section build clean at exit 0 with an empty block, and
      # `--strict` cannot help because nothing is emitted to warn about.
      # This one line is D-08 in its entirety.
      check_paths: true
      # Blocks `../` escapes above base_path. Never turn this off.
      restrict_base_path: true
      # Snippet regions taken from inside function bodies render flush-left
      # instead of as an accidental code block.
      dedent_subsections: true
```

`dedent_subsections: true` is why the seven `s1-01` spine regions — all of
which sit inside function bodies — render flush-left.

**Nav is authoritative and globless** (`mkdocs.yml:110-112`):

> Every path enumerated explicitly — no globs. The nav is authoritative: it
> lists 42 pages, and `charter.md` is the single `not_in_nav` page, for the 43
> markdown files under `public/`.

**That count moves.** Adding one page makes it 43 nav pages / 44 markdown
files, and the comment must be updated with it or it becomes a false statement
in the config. `--strict` fails a page absent from nav
(`validation.nav.omitted_files`), and `test_advisory_discharge.py` parses the
nav block independently — the `NAV_BLOCK` / `NAV_PAGE` regexes at
`test_advisory_discharge.py:126-128`.

---

### 4. `.planning/REQUIREMENTS.md` (EDIT — hand-edited, two channels)

**Two channels, both must be edited, and a gate asserts they agree.**

- Channel 1 — checkbox list. `DOCS-15` is line 40, currently `- [ ]`.
- Channel 2 — traceability table (header at line 301, `| Requirement | Phase | Status |`). `DOCS-15` is line 334.

`tools/docs_tests/test_requirement_ledger.py` (7428 lines) holds the gate. Its
docstring states what it enforces:

> the citation form a status cell may carry, the agreement between the two
> channels, the verdict vocabulary, and one verdict per cell.

**The verdict vocabulary is fixed** (`test_requirement_ledger.py:1554-1566`):

```python
COMPLETE_FAMILY = frozenset(
    {"Complete", "Complete as ruled", "Complete over the ruled scope"}
)
VERDICT_VOCABULARY: frozenset[str] = COMPLETE_FAMILY | frozenset(
    {"Partial", "Not built", "Orphaned", "Pending"}
)
```

**Row shape to copy — `DOCS-16`, which is the closest analog** because it is
the row whose evidence is a `tools/docs_tests/` gate with mutate-a-copy
controls. `.planning/REQUIREMENTS.md:41` (identical text at table line 335):

```markdown
- [x] **DOCS-16**: Carried advisories A-1, A-2, A-3 and A-8 are discharged in the published tree with positive per-advisory evidence rather than a green build — **Complete** (`tools/docs_tests/test_advisory_discharge.py::test_a1_the_preferred_day_one_import_is_documented`, `tools/docs_tests/test_advisory_discharge.py::test_a2_the_maintainer_page_is_published_and_names_its_subject`, `tools/docs_tests/test_advisory_discharge.py::test_a3_no_documented_boot_signature_disagrees_with_the_code`, `tools/docs_tests/test_advisory_discharge.py::test_a8_both_halves_are_stated_in_one_paragraph`, `tools/docs_tests/test_advisory_discharge.py::test_the_a8_gate_refuses_a_page_that_states_only_reachability`) — one named assertion per advisory, and the *positive evidence rather than a green build* clause is what the module is built around: each advisory assertion is paired with a control that mutates a copy of the real page and asserts refusal, so non-vacuity is proven by watching the gate fail rather than by a corpus floor, and a failure reports by advisory id — "A-8 is undischarged", not "assertion failed". A-3's gate is the strongest of the four: it compares a documented boot signature against `inspect.signature()` at run time rather than against a transcription
```

Structure: `- [x] **ID**: <requirement restated> — **Verdict** (`node::id`, `node::id`, …) — <prose stating what each limb rests on and naming any absence>`. Note the citations are **`file.py::symbol` node ids**, and that at least one of the cited assertions is a *control* rather than a shipped assertion — the row is making the non-vacuity claim, so it cites the proof of non-vacuity.

**Every cited node id must resolve** — `cite03-node-id` in the citation lint,
plus the ledger gate's own stricter requirement that the cited path exist
exactly as written (`test_requirement_ledger.py:41-45`).

**CONTEXT.md sequencing:** rows this phase mints are minted in wave 1 and
verdicted **before** the close panel reads the tree, on the `RECON-` / `VAC-`
precedent.

---

## Shared Patterns

### The `public/` never-publish rule — constrains every sentence on the page

**Source:** `public/charter.md:11-17`
**Apply to:** the new Concepts page, absolutely

```markdown
The internal deliverable tree adjacent to this one holds the canonical
specification `CCF_Whitepaper_1-2.md` together with `DECISIONS.md`,
`SPEC_INVENTORY.md`, `DESIGN.md`, `FEASIBILITY.md`, `ROADMAP.md`, the
`PHASE_I*_GATE.md` records and `09-ruling-batch-minicycle.md`. **Nothing
under `public/` may reference any of them.** No link. No `--8<--` snippet
include. No symlink. No transitive path that resolves into that tree.
```

Enforced with **no allowlist** (D-20) by the post-build site scan in
`make docs-strict` (`Makefile:517-521`):

```make
docs-strict:
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py --pre-build
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py docs/schemas
	$(ENV_DOCS) $(PYTHON) -m mkdocs build --strict
	$(ENV_DOCS) $(PYTHON) tools/publish_scan.py site
```

**What this means concretely for the honesty caveat.** The caveat's authority
is `D-IMPL-46` in `docs/DECISIONS.md` — the page may **not** name that path.
Measured across `public/`: bare `D-IMPL-NN` ids are used (`adopters-guide.md`
carries 2, the `.mmd` diagram sources carry 25 between them) and prose
whitepaper section refs are used (`demo-walkthrough.md:164` — "whitepaper
§7.4"), while the only occurrence of `DECISIONS.md` anywhere under `public/`
is `charter.md:13` stating the rule. **So: cite `D-IMPL-46` as a bare id and
`whitepaper §7.10.3` as prose; never as a path.**

### The citation lint — `public` is gated

**Source:** `tools/lints/citations.py:153-164`
**Apply to:** every prose path and every `::symbol` on the new page, and every
citation in the new `REQUIREMENTS.md` cell.

```python
#: Trees walked by the gate. Measured, not assumed: every top-level tracked
#: directory was scanned for citations before this tuple was written. The two
#: absent from it — ``references`` and the repo-root files — were scanned and
#: carry none; they are excluded to keep the walk honest about what it covers
#: rather than because nobody looked.
GATED_TREES: tuple[str, ...] = (
    "src",
    "runtime",
    "tools",
    "tests",
    "examples",
    "public",
    "docs",
    "perf",
    ".planning",
    ".github",
)
```

The two forms it checks (`citations.py:244-253`):

```python
#: A line citation: ``path/to/file.py:12``, ``file.py:12-34``, ``x.py:12,34``.
CITATION = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.(?:" + _SUFFIX_ALT + r"))"
    r":(?P<lines>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)(?![\w-])"
)

#: A symbol citation — the rot-resistant form, checked rather than trusted.
NODE_ID = re.compile(
    r"(?P<path>[A-Za-z0-9_][A-Za-z0-9_./+-]*\.py)::(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)"
)
```

`CITED_SUFFIXES` = `py, md, yaml, yml, json, toml, txt, cfg, ini, sh`
(`citations.py:206-217`) — a `Makefile:NNN` citation is invisible to the lint
by construction, which is why `DOCS-08`'s row states the `ci` composition in
prose rather than citing it.

**Three rules, and what each buys** (`citations.py:14-38`): `cite01-resolves`
(the file exists and the line is inside it), `cite02-anchor` (a backticked span
immediately before the citation must actually live at those lines),
`cite03-node-id` (`file.py::symbol` resolves to a `def`, `class` or
module-level binding).

**A hard prohibition already in force on published pages.** `16-13-PLAN.md:275`
records the acceptance criterion `grep -rEc "[a-z_]+\.py:[0-9]+" public/`
returns 0 — i.e. **published prose does not use `file.py:NNN` line citations
at all.** Use the `tests/examples/x.py` bare-path form the four
result-citation instances above use, or a `::symbol` node id.

### The stale-path gate — what counts as a "prose path reference"

**Source:** `tools/docs_tests/test_no_stale_example_paths.py:73-119`
**Apply to:** every `examples/…` or `tests/examples/…` token the new page writes.

```python
#: An `examples/…` or `tests/examples/…` path token.
#:
#: The trailing character class excludes ``.``, ``,`` and ``)`` so a path at the
#: end of a sentence does not absorb the punctuation. The lookbehind stops the
#: inner ``examples`` of ``tests/examples/x`` from being re-matched as a bare
#: ``examples/x`` that does not exist ...
PATH_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:tests/examples|examples)/[A-Za-z0-9_./-]*[A-Za-z0-9_/]"
)


def prose_path_offenders(pages: list[pathlib.Path]) -> list[str]:
    """`page:line -> missing path` for every unresolvable prose path token."""
    offenders: list[str] = []
    for page, paragraph in _prose.iter_paragraphs(pages, prose_only=False):
        for token in PATH_TOKEN.findall(paragraph.raw):
            if not _resolves(token):
                offenders.append(
                    f"{_prose.relative(page)}:{paragraph.lineno} -> {token}"
                )
    return offenders
```

Two things transfer: `prose_only=False` (fenced blocks are scanned too — *"A
stale path inside a ```sh``` block is exactly as rotten as one in a
sentence"*), and reading `paragraph.raw` rather than `.text` because a path in
prose is almost always an inline code span, which `.text` strips.

Its stated blind spot, worth knowing: a path broken **mid-token** across a
line break is invisible to this and every line-scoped gate, because the join
inserts a space.

### The snippet gate — read this before assuming an include is safe

**Source:** `tools/docs_tests/test_snippet_gate.py:1-28` — module docstring, in
full, as CONTEXT.md `D-01` requires:

```
"""D-08 — the snippet drift gate, proven live rather than assumed.

`check_paths: true` in `mkdocs.yml` is the entirety of D-08. At the
extension's default (`false`) BOTH a missing snippet file and a missing named
section build clean at exit 0, emitting an EMPTY code block onto the published
page — and `--strict` cannot help, because nothing is emitted to warn about. A
guide whose every code block is an include would then ship silently blank the
moment a marker was renamed.

This module is the negative control for that setting. It builds throwaway
mkdocs projects in a temporary directory and asserts the build FAILS for each
failure mode, and succeeds for the clean control.

Both violating cases are exercised separately on purpose: `pymdownx.snippets`
guards them at two different call sites — one when opening the file, one when
locating the named section inside it — so a config regression could plausibly
restore one guard without the other. A single combined case would pass while
half the gate was dead.

`base_path` resolves against the PROCESS CWD, not against the config file's
directory. Every subprocess below therefore runs with `cwd` set to the
throwaway project root and `base_path: ["."]`, which is the same relationship
the real build has (`mkdocs.yml` at the repo root, `make` run from the repo
root). Getting this wrong makes the clean case fail for the wrong reason.

The working tree is never modified: sources are COPIED into the temporary
directory before being mutated.
"""
```

**A live coupling the planner should know about**, `test_snippet_gate.py:38-53`:

```python
#: These two constants are a COUPLING to a real file in the tree, not a fixture
#: this module owns: both the clean control and the deleted-marker case read
#: `SNIPPET_SOURCE` from disk and assert `[start:SECTION]` is present. ...
#:
#: Plan 16-18 repoints BOTH constants again at the Section-1 spine when
#: `examples/00-quickstart` retires. Recorded here so the terminal plan does not
#: have to rediscover the coupling from a failing assertion.
SNIPPET_SOURCE = REPO_ROOT / "examples" / "00-quickstart" / "run.py"
SECTION = "boot"
```

This is a `DOCS-17` obligation, **not this phase's** — `D-08` bars touching the
`00`–`08` trees. Noted so the planner does not repoint it opportunistically.

### The retirement-coupling regeneration — LAST, with `.venv/bin/python`

**Source:** `tools/retirement_sweep.py:1425` — `public/` is one of three swept trees:

```python
SWEPT_TREES: tuple[str, ...] = ("examples/", "tests/examples/", "public/")
```

so the new page's `s1-01` references become coupling rows in
`docs/surface/examples/RETIREMENT-COUPLINGS.md` owned by `17-08`, mechanically
(`D-09`). Regenerate **last**, after every `.planning/` or `public/` write:

```
PYTHONPATH=.:src:runtime .venv/bin/python tools/retirement_sweep.py --report
```

**Never the system `python3`.** CONTEXT.md records the live trap: the sweep
imports test modules and executes their scan functions, swallowing failure at
four sites (`:789`, `:973`, `:982`, `:1111`/`:1124`); under the system
interpreter `joserfc` is missing, three modules fail to import, six coupling
rows vanish silently, and the tool prints a confident `238 coupling rows` at
exit 0. Fixing it is out of scope (`CLNT-17` / `DOCS-17`).

---

## Measured Facts — CONTEXT.md's claims, re-run against the tree

Every one of these was re-measured rather than copied.

**1. `hw1` carries zero snippet section markers — VERIFIED.**
`grep -rn -- "--8<--" examples/hw1-companies-over-revenue/ examples/hw1-harness-clients/` returns **0**.
(A naive `grep "start:\|end:"` returns 2 hits, both false: a prose comment and
a `backend:` key in `examples/hw1-companies-over-revenue/deployment/ccf_config.yaml`.)

**2. `hw1` line counts — VERIFIED, exactly as CONTEXT.md `D-10` states:**

| File | Lines |
|---|---|
| `examples/hw1-companies-over-revenue/consume.py` | 79 |
| `examples/hw1-harness-clients/client_adk.py` | 186 |
| `examples/hw1-harness-clients/client_anthropic.py` | 288 |
| `examples/hw1-harness-clients/client_langgraph.py` | 237 |

An include against any of these would be whole-file. Prose citation of
`src/ccf/client/…` symbols is the `D-10` route, and it is gated (`public` ∈
`GATED_TREES`).

**3. The condemned trees' current load — VERIFIED, all three figures:**

| Measurement | Count |
|---|---|
| References (prose + include) to `examples/0[0-8]` or `examples/external/00` across `public/` | **111** |
| …of which are `--8<--` snippet includes | **102** |
| Distinct published pages carrying them | **15** |
| Total `--8<--` includes anywhere in `public/` | **116** |

The 14 non-condemned includes: 11 `.mmd` diagrams under `public/concepts/`,
`public/reference/http-api.md:14` (`openapi.json`),
`public/reference/performance.md:20` (`perf/baselines/local.json`), and one
prose mention in `charter.md:16`. **This phase adds `s1-01` includes and zero
against `00`–`08` — the first published citation of the `s1-*` trees.**

**4. Zero published pages mention `s1-00` or `s1-01` — VERIFIED.**
`grep -rn "s1-00\|s1-01" public/` returns **0**. Independently corroborated by
the `DOCS-12` ledger row: *"no page under `public/` names `s1-00` or `s1-01` —
the grep across the published tree returns zero."*

**5. The `DOCS-15` `Not built` basis — VERIFIED.** No page under `public/`
names RAG, a vector store, hand-rolled context assembly or a semantic layer,
and no page carries the UBO question. Both greps return zero.

**6. Passage-anchor vocabulary in `public/` — MEASURED, and this changes the
gate design.** The whole published tree contains **3** occurrences of
"passage", of which **2** are the phrase "passage-level lineage":

- `public/how-to/compose-a-workflow-with-hitl.md:157` — "review queue holds
  generated content, with its passage-level lineage attached,"
- `public/concepts/pillars/hitl.md:33` — "integrated with passage-level lineage
  so a reviewer can see what each claim…"

Both are correct: they describe lineage *attachment*, not document
*extraction*. **Consequence for `D-04` obligation 2:** a corpus non-vacuity
floor of the form *"some published paragraph triggers the extraction-claim
predicate"* is **unsatisfiable at HEAD and would be red on a correct tree.**
The floor must be the `test_advisory_discharge.py` A-3 shape — non-vacuity
proven by an injected control — optionally plus a weaker corpus floor
asserting the *subject vocabulary* ("passage", "lineage") appears at all,
which the two paragraphs above do satisfy. The new page will itself add
occurrences, since it must carry the caveat.

**7. `s1-01` spine and artifacts — MEASURED.** Seven marker regions with the
line ranges in §2d; twenty artifacts, none carrying a marker; `gate` is 149
body lines and `events.yaml`/`source-estate.yaml` are 502/576 lines.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| the persuasion-shaped Concepts page | published Concepts page | source-code `--8<--` include inside a Concepts page | **No Concepts page in the tree currently includes source code.** All 11 includes under `public/concepts/` are `.mmd` diagram sources. The result-citation pattern the page must use lives entirely in `public/tutorial/` (`adopters-guide.md`, `demo-walkthrough.md`), which is a different Diátaxis mode. The planner is composing two analogs: Concepts heading/voice from `invariants.md`, code-citation mechanics from `adopters-guide.md`. |
| the *contrast* structure itself (`D-02`/`D-03`) | prose | — | Strict Diátaxis means **none of the four modes is a home for persuasion**, and nothing in `public/` currently makes a comparative argument. There is no in-tree prose analog for "state a checkable fact about the question and let the reader draw the inference." The closest thing to a model is the *voice* of `invariants.md`'s orientation paragraph and of `expected.yaml`'s `absent_by_policy` comments — each of which states a witness rather than a claim. |
| a non-vacuity floor for `D-04` obligation 2 | test | — | Measured fact 6: zero offending paragraphs exist, by design. Use `test_advisory_discharge.py`'s injected-control non-vacuity instead of a corpus floor, and say so in the module docstring the way A-3's does. |

---

## Metadata

**Analog search scope:** `tools/docs_tests/` (all 13 modules listed and sized),
`tools/lints/citations.py`, `public/` (all 43 markdown files walked for
includes, path tokens, decision ids and passage vocabulary), `mkdocs.yml`,
`Makefile`, `examples/s1-01-hello-context-product/` (spine, all 20 artifacts,
README), `examples/hw1-companies-over-revenue/`,
`examples/hw1-harness-clients/`, `tests/examples/test_s1_01_output.py`,
`.planning/REQUIREMENTS.md`, `.planning/phases/16-…/abandoned/16-13-PLAN.md`.

**Files read in full:** `tools/docs_tests/test_gate_two_wording.py`,
`tools/docs_tests/test_snippet_gate.py`, `tools/docs_tests/_prose.py`.
**Files read in targeted non-overlapping ranges:**
`tools/docs_tests/test_advisory_discharge.py`,
`tools/docs_tests/test_no_stale_example_paths.py`,
`tools/docs_tests/test_documented_commands_exist.py`,
`tools/lints/citations.py`, `tools/docs_tests/test_requirement_ledger.py`,
`tests/examples/test_s1_01_output.py`, `public/concepts/invariants.md`,
`public/tutorial/adopters-guide.md`, `public/tutorial/demo-walkthrough.md`,
`public/charter.md`, `mkdocs.yml`, `Makefile`, `.planning/REQUIREMENTS.md`.

**Pattern extraction date:** 2026-08-23 (tree at `acbe632`)

**Read-only:** no source file was modified. This document is the only file written.
