# Phase 22: The Adoption Argument — What RAG, Hand-Rolled Assembly and a Semantic Layer Lack - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-23
**Phase:** 22-the-adoption-argument-what-rag-hand-rolled-assembly-and-a-se
**Areas discussed:** Citation standard, Uncited-half rule, Claim gate, Demo subject, Page title
**Order:** set by Dave — *"1. Citation standard 2. Demo subject + CLNT-17 coupling rule 3. Page location 4. Confirm three alternatives"*

---

## Which areas to settle at all

Four were offered: where the page lives, how a claim gets cited, which example it
points at, what the argument covers.

**Dave's ruling:** settle **2, 3, 1 in that order**; **lock 4 to a default.**
Rationale on the record: *"Without this, planning cannot know whether the page is a
doc-only edit or needs new gates."*

---

## Citation standard — what "cited shipped mechanism" means

| Option | Description | Selected |
|--------|-------------|----------|
| Prose that names a symbol | Cheap; rots; *"reviewers will reject as essay"* | |
| Literal snippet include (`--8<--`) | Docs build fails if source moves; matches the adopter's guide | ✓ FLOOR |
| Standing test that each claim resolves | Strongest; more machinery | stretch |

**User's choice:** Snippet includes for every code-backed claim as the **minimum**.
A full per-claim symbol test is a **stretch goal, not the minimum**.

**Notes:** Verified against the tree before locking — `check_paths: true` in
`mkdocs.yml` makes both a missing snippet file and a missing named section fail the
strict build, and `tools/docs_tests/test_snippet_gate.py` is the negative control
exercising each failure mode separately. The floor Dave picked was already proven
live rather than assumed.

---

## The uncited half — claims about what the alternatives lack

Raised by Claude, not offered in the original four: **you can include what CCF does;
you cannot include what RAG lacks.** Half the page's sentences are citable and half
are not, and left unruled the uncitable half reads as assertion — `DCD-02`'s class.

| Option | Description | Selected |
|--------|-------------|----------|
| Recast as facts about the question | Every "lacks" claim rewritten as a checkable property of the UBO question; reader draws the inference | ✓ |
| Label the two halves visibly | Typographic separation of cited mechanism from argued contrast | |
| Pair every contrast with its CCF citation | Adjacency enforced, citation on the CCF half | fallback only |

**User's choice:** **Option 1**, with option 3 as a bounded fallback for residual
contrasts that genuinely cannot be recast — *"each paired and called out — not as the
main style."*

**Notes:** Dave's reasoning, verbatim: *"DOCS-15 asks for claims against cited shipped
mechanism, not for a persuasive essay that asserts what RAG 'can't do.' Uncited
'lacks' sentences are the same defect class as DCD-02: a strong-looking claim with
nothing to open."* And the worked example: *"'No document in any source system states
Jane's 30% ownership' is checkable against `events.yaml` / `source-estate.yaml`."*
Option 2 was rejected as *"honest but still leaves the persuasive half ungated."*

---

## Claim gate — does a standing gate ship with the page?

Re-opened by Claude after the option-1 ruling, because the **price changed**: Dave's
"stretch goal" was priced against a per-claim symbol resolver, but
`tools/docs_tests/test_gate_two_wording.py` is a proven in-repo instrument that
enforces the criterion Dave had just written, at roughly one plan.

| Option | Description | Selected |
|--------|-------------|----------|
| One module, both obligations | Wording gate in the gate-two shape: no ungrounded capability-limit claims + no passage-anchor overclaim | ✓ |
| Stays a stretch goal | Floor is includes plus the two existing gates | |
| Caveat obligation only | Ship the narrow passage-anchor grep, leave the rest to close review | |

**User's choice:** **Option 1 — yes, one module, both obligations.**

**Notes:** Dave's reasoning, verbatim: *"A stretch goal (option 2) means that standard
is enforced only by reviewer diligence — the same pattern that let unevidenced
Completes and vacuous checks ship for years. Phase 22 should not reintroduce it on the
page that exists to model honest citation."* And: *"if the criterion matters, something
can go red when it is violated."* Scope bound stated in the same ruling: `public/`-only,
**not** a repo-wide rhetoric linter; includes remain the floor for mechanism; the
per-claim resolver stays non-blocking. Closing frame: *"Phase 22 is still 'one page +
the gate that keeps it honest,' not a tooling phase."*

---

## Demo subject and the CLNT-17 coupling

| Option | Description | Selected |
|--------|-------------|----------|
| s1-01 plus the client surface | s1-01 for UBO; `ccf.client` + `hw1` for the hand-rolled-assembly contrast, which is about the seam not the graph | ✓ |
| s1-01 only | One subject, one coupling; costs the assembly claim its strongest evidence | |
| Any gated tree except 00–08 | Most evidence, most coupling rows, hardest to re-point | |

**User's choice:** **s1-01 plus the client surface.**

**Notes:** Dave's prior framing carried in: prefer s1-01 *"and record explicitly that
the page is a **CLNT-17 dependency**: s1-01 cannot be removed until this page is
re-pointed or the demo is re-homed. Do **not** add new 00–08 includes."*

Verified before locking: `s1-01/spine.py` already carries the **same seven marker
regions** the adopter's guide includes from `00-quickstart`, plus twenty documented
artifacts and an output test — **the page can be a pure `public/` addition with zero
changes under `examples/`.** Zero published pages cite `s1-00` or `s1-01` today, so
this page is the first, and it starts the replacement direction rather than adding to
`DOCS-17`'s 102-include re-cut burden. The `CLNT-17` dependency also lands
mechanically: `public/` is swept by `tools/retirement_sweep.py`, so the references
become coupling rows owned by `17-08` without anyone having to remember.

**One constraint found and settled by Claude within the ruling:** the `hw1` trees carry
**zero snippet markers** (files are 79 / 186 / 288 / 237 lines), so the client surface
is cited in **prose** — already gated, since `public` is in the citation lint's
`GATED_TREES`. Adding markers to `hw1` is example work and is out of scope; if the
planner concludes an include is necessary, that is a question for Dave.

---

## Page location and title

Location was ruled before the sitting — **Concepts page**, per Dave: *"not a new
top-level section, not folded into a 65-line index, not buried only inside the long
adopter's guide. First-time readers can hit Concepts without finishing the tutorial;
a top-level 'Why CCF' is optional later if the page earns it."*

The title was raised by Claude as a live tension with the option-1 ruling.

| Option | Description | Selected |
|--------|-------------|----------|
| Named for the question, not the rival | e.g. "What a governed answer requires" | ✓ |
| "Why not RAG?" | Direct and searchable, but writes a cheque the body cannot cash | |
| Name all three alternatives | Mirrors the DOCS-15 row; long for a sidebar | |

**User's choice:** **Named for the question, not the rival.**

**Notes:** A title naming RAG would promise exactly the naked assertion the body is
barred from making, and the new wording gate would then be policing a claim the title
had already made.

---

## What the argument covers — locked to a default, not discussed

**Dave's default:** exactly the **three alternatives `DOCS-15` names**. No fourth
unless `DOCS-15` is explicitly expanded — *"Revisit only if discuss surfaces a
must-have fourth that changes the requirement row."* None did.

Staleness / forced-LLM: **use what `s1-01` already measures** (debt crossing the band)
— *"otherwise drop or narrow the staleness claim rather than inventing s1-02 in this
phase."*

---

## Claude's Discretion

- Exact page title within the "name the question" constraint.
- The page's internal section order, and which of `s1-01`'s seven spine regions and
  twenty artifacts are included.
- Placement within the Concepts nav.
- The wording gate's module name and exact pattern vocabulary.

## Deferred Ideas

- **The one-documentation-workstream framing** (`D-IMPL-176` point 4) — `DOCS-12/13/14/15`
  as one surface. Recorded; Dave's point 1 sequences `DOCS-15` first and alone.
- **Snippet markers for the `hw1` trees** — would make the client surface includable.
- **`examples/s1-02-freshness-and-debt`** — `16-08`'s intended λ_c / D_c demonstration,
  never built.
- **A top-level "Why CCF" section** — *"optional later if the page earns it."*
- **The retirement sweep's silent-drop defect** — four failure-swallowing sites; found
  live during this discussion; `CLNT-17` / `DOCS-17` machinery.
- **A per-claim symbol-resolver test** — stretch within this phase; named as owed if it
  does not land.
