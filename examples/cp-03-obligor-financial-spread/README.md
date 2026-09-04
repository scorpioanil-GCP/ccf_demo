# cp-03 — Obligor Financial Spread

**Rung 03 of the vault's Context Product ladder, and the last of Tier 1.**
One obligor's standardized financial spread, where every figure names the period
it describes, the filing that asserted it, and whether a later filing changed it.

Specification: [`spec/CP-SPEC-003_Obligor_Financial_Spread.md`](spec/CP-SPEC-003_Obligor_Financial_Spread.md).

> **The anchor was chosen for RESTATEMENT, not for a complete spread block.**
> Digital Turbine files no depreciation, so EBITDA and its three dependents are
> permanently `NOT_EVALUABLE` in the default run, and it is one of the 20
> obligors with no peer cohort at all. Two variations below supply what it
> cannot. No obligor in this estate carries everything, and picking one that
> looked complete would have meant giving up the restatement this rung exists to
> teach.

## What this demonstrates

**Attribute-level temporal validity — one freshness per product stops being
enough.** Rungs 01 and 02 each carry a single expiry for the whole answer. A
spread cannot: it is stitched from many filings, and a payload holding last
week's quarter beside a four-year-old annual is not uniformly fresh. Every
figure here carries its own `period_end`, `filed_date` and `accession`, and the
product's expiry is anchored on the *latest* filing in the payload rather than
on the question's date.

**`basis` — the catalog's first parameter where both settings are correct and
the decision picks.** `as-reported` is what the obligor said at the time.
`latest-restated` is what it says now. Neither is the truth; the decision
selects. For an obligor carrying a restatement the two produce different
content addresses, so a cache can never serve one for the other.

**A contrast with rung 02 that neither rung teaches alone.** Both anchor their
expiry on an entity date. Rung 02 anchors on a credit agreement's effective
date, which can never advance, so its 50 refusals of 60 are permanent. This rung
anchors on `filed_date`, which moves every quarter, so its 27 refusals of 50
clear as filers file. Same primitive, opposite behavior, and the difference is
entirely whether the anchored field is re-observed.

**One store and one operator.** PostgreSQL — schema `ccf_v2` in the
operator-supplied database. The Policy operator is the only one in the plan, and
an empty plan fails the SDK's empty-operator guard, so the product cannot serve
without it.

## Run it

**1 · Create the virtual environment.** This repository has no `python` on
`PATH`; the `Makefile` uses `.venv/bin/python`, and nothing creates it for you.

```
make venv
```

**2 · Export the connection string.** `backends.yaml` holds the variable's
*name* and nothing else — no host, no port, no credential ever enters the tree.

```
export CCF_CP_03_POSTGRES_DSN='host=… port=5432 dbname=… user=… password=…'
```

**The role must be read-only.** Nothing this example runs writes to the store it
reads, and a role that *could* write would make that a promise rather than a
guarantee. Both libpq spellings work and neither is preferred — the keyword
string above, or a `postgresql://user:pass@host:5432/dbname` URI. libpq also
reads `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` from the environment on its
own, so the variable's contents can be as short as `dbname=<database>`.

**3 · Run the demonstration question.**

```
make -s example-cp-03
```

`-s` suppresses make's echo of the recipe. That echo is the only difference
between this target's output and the transcript published on the documentation
page.

**4 · Without make**, spelling the interpreter explicitly:

```
.venv/bin/python examples/cp-03-obligor-financial-spread/run.py
```

**5 · Variations worth trying.** Every request parameter is optional — omitted, the run asks the question
declared in `artifacts/question.yaml`.

| Command | What changes |
|---|---|
| `make -s example-cp-03 BASIS=latest-restated` | the same obligor read the other way. Content address moves from `e2a0224f…` to `9fe28bb1…`, because two figures genuinely differ |
| `make -s example-cp-03 LEI=549300FHJQTDPPN41627` | Celanese — the **full derived ratio block**, which the anchor cannot show, and restatement across five spread lines |
| `make -s example-cp-03 LEI=529900VKCYZW8GZ4WW58` | Sabre — the **only way the peer block is visible at all**, since neither the anchor nor Celanese has a cohort |
| `make -s example-cp-03 PERIODS=1` | one period instead of eight. Context debt falls from `0.8782` to `0.494` — the debt figure is driven by the width of the history window, not by the obligor |
| `make -s example-cp-03 PRINCIPAL=PRIN-RES-002` | asked as a principal entitled to 49 of the 50 obligors rather than 47. **The content address does not move** — both principals can see this obligor, so the answer is the same answer; only the replay record differs. Entitlement changes what you *can* see, not what the answer *is* once you can |

**6 · Two variations exit non-zero, and that is correct.** A refusal is not a
crash, but it is also not a success, so `make` reports `Error 1`:

```
make -s example-cp-03 AS_OF=2026-03-31
```

```
refused: not-supported-at-tier — as_of
   as_of: 400 not_supported_at_tier — reconstructing the spread as it stood on a past date requires ledger time-travel and arrives at Tier 3 with covenant-in-force-as-of. This tier serves the spread as it stands, with every figure naming the filing that asserted it.
```

The first line is the SDK's verdict, returned as data by the tier step of
`refuse_request` before the product's own code runs; the second is the detail
the class declaration carries for the parameter, printed beneath it. Both lines
are stdout, and the program exits 1.

```
make -s example-cp-03 PRINCIPAL=PRIN-KYC-004
```

```
assembly refused: obligor '549300D0WZR1VI2QGB24' is not available (404); §D.2 fails closed rather than returning an empty payload. A spread with no lines would read as 'this company reported no financials', which is a claim about the world rather than about the request
```

The second is the interesting one. `PRIN-KYC-004` holds nine jurisdiction
grants; none of them reaches any obligor in this estate. It receives **exactly
what it would receive for an obligor that does not exist** — because a refusal
that said *"you are not permitted to see this"* would tell an unentitled caller
that the obligor is real.

## The story

A credit analyst asks for one obligor's spread. What comes back is not a table
of numbers.

**Every figure names its own filing.** Two lines in one column routinely carry
different `accession` values, because a spread is stitched from filings rather
than taken from one. The default run returns **8 period ends as 16 columns** — a
non-December filer carries two columns at one period end, an annual cell and a
quarterly cell.

**Two lines were restated.** `equity` and `interest_expense` changed value
across filings on the estate's own fact-identity key. The obligor also filed an
Item 4.02 non-reliance notice, so `formally_restated` reads `True` — but that
filing is **corroboration and never the detector**. Twenty-eight of the 37
restated obligors here filed no 4.02 at all, and two obligors filed one without
moving a single figure.

**The answer expires on 2026-09-04**, thirty days after `2026-08-05`, the latest
filing in the payload. Ask the same question an hour later and the expiry does
not move. An expiry that tracked the question would make every product
permanently fresh.

**Context debt reads `0.8782` → `fail_closed`, and the spread is served
anyway.** That is deliberate and it is recorded: the signal is advisory at every
rung of this ladder, and the figure is driven by the width of the history window
rather than by anything wrong with the obligor. Ask for one period instead of
eight and the same obligor reads `0.494` → `ok`. A spread exists to carry old
periods, so a freshness measure that composes across all of them will always
read poorly.

## Artifact-by-artifact

| File | What it carries |
|---|---|
| `artifacts/question.yaml` | the demonstration question — the anchor LEI, the parameters and the `asked_at` pin. **Nothing in any module names an LEI**; changing the subject here re-asks the same question of another obligor |
| `artifacts/spread-lines.yaml` | the spread's line vocabulary and each line's declared kind and source tags |
| `artifacts/restatement.yaml` | **the two credit-policy judgments**: what makes two rows the same fact, and which corrections are material. Both are values wearing numeric clothing, so neither is a constant in code |
| `artifacts/ttl.yaml` | the expiry anchor and window |
| `artifacts/assembly-recipe.yaml` | the steps, in order, with what each reads |
| `artifacts/expected.yaml` | what the served product must contain, **declared rather than derived from a run**, plus the witnesses the gates address by name |
| `backends.yaml` | the store binding — the environment variable's name and nothing else |
| `ccf_config.yaml` | the product class, request contract and Control Plane bindings |
| `deployment.py` | everything domain-specific: tables, columns, SQL, the estate's vocabulary. Makes no fabric call |
| `produce.py` | the fabric's call spine. Names no table, no column and no domain word |
| `assembler.py` | the client seam — routes the run through `ContextAssemblerProtocol` |
| `run.py` | the command-line driver |

## Whitepaper / CLAUDE.md sections exercised

| Section | How |
|---|---|
| Whitepaper §7.4 — Context Operators | the Policy operator, the only one in the plan; an empty plan fails the empty-operator guard |
| Whitepaper §7.5 — Context Projection | `FinancialSpreadProjection`, structural typing through `required_operators()` and `invoke()` |
| Whitepaper §7.6 — Context Product Contract | the three validation gates, one of which refuses 27 of 50 obligors on TTL bounds |
| Whitepaper §7.7 — Half-life and Context Debt | **two decay classes in one payload** — annual and quarterly columns decay at different rates, which a single product-level `λ_c` could not express |
| Whitepaper §7.10 — Decision Replay | the replay record, addressed at `ad70fa4b…` |
| `CLAUDE.md` §6.4 — the No-Hardcoding Rule | no prompt, no threshold, no LEI and no routing value in any module |
| `CLAUDE.md` §10 — single-writer | this example is read-only; nothing it runs holds a write handle |

## What to change first

**Point it at your own estate.** `backends.yaml` names the environment
variable; `deployment.py` names the tables and columns. Those two files are the
whole adaptation surface for a different store.

**Then change the question.** `artifacts/question.yaml` carries the anchor and
the parameters. Nothing in any module names an LEI, so a different obligor is an
artifact edit rather than a code change.

**Then change the policy.** `artifacts/restatement.yaml` decides what counts as
the same fact and which corrections are material. Both are judgments your credit
policy owns, not ours — and `OFS-G13` proves the product reads them rather than
agreeing with them by coincidence.

## What would fail

**Fourteen gates, and every one has been made to fail deliberately** — the
sabotage applied to each and the observed result are recorded at
`CP-SPEC-003` §G.2. A gate that has never been observed red is not evidence that
it runs.

Three of them **passed their first sabotage**, all for the same reason, and the
finding is more useful than the gates: each was reading a token that appears
whether the product is right or wrong. `OFS-G01` counted the declared kind of a
line the obligor never filed as evidence of a real fact. `OFS-G02` matched the
word "crosswalk" in the function's own docstring. `OFS-G11` watched a content
address that always changes, because the payload echoes the basis it was read
under. **A check that reads a token present in both the compliant and the
violating case is measuring vocabulary, not content.**

**The snapshot.** The transcript published on the documentation page is the
default run at `asked_at 2026-08-29T12:00:00+00:00`, serving content address
`e2a0224fa5c9ecf4cbf7c0e6ef4ae89a4bccb85d85ebf20f7e206f73b1372edc`. It
reproduces byte-for-byte because the question is pinned; every figure in it came
from that run.

**One conflict was raised and is now ruled** (`D-IMPL-222`, Dave, 2026-08-31).
§D.4 required identical content addresses for an obligor with no restatement,
read under both bases. It does not hold as built — and measuring showed the
first explanation was incomplete. It is not merely that the payload echoes
`basis_applied`: the two bases genuinely **read different filings** for 20 of 75
cells, reporting the same number from each. **Not one served figure moves**, but
the documents differ in provenance, and the address seals the document.

Making the addresses match would have meant suppressing `accession` and
`filed_date` wherever the value agreed — deleting a true fact to make a hash
match, at the rung whose whole subject is which filing asserted which figure.
The criterion is amended instead: for an unrestated obligor the two bases must
change no figure, which is what `OFS-G11` asserts.
