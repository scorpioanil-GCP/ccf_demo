# examples/cp-02-facility-terms-snapshot — an expiry that belongs to the instrument, not to the question

Rung 02 of the vault's 21-product ladder, and the first product on it that
**anchors on something that is not a legal entity**. A credit facility is an
instrument: its identifier is internal, no external registry stands behind it,
and its terms do not decay on a clock — they are valid until the agreement is
amended.

That makes it the right place to make one primitive concrete.
`ttl_anchor: from_entity_freshness` means **`expires_at` is a function of the
facility, never of the request**. Ask the same facility twice, a fortnight
apart, and the expiry does not move. Rung 01 introduced the anchor; this is
where getting it wrong becomes visible, and where getting it right costs
something.

Specification: [`spec/CP-SPEC-002_Facility_Terms_Snapshot.md`](spec/CP-SPEC-002_Facility_Terms_Snapshot.md).
Gate 1 approved 2026-08-29.

## What this demonstrates

- **An expiry derived from a filed date.** `contract.expires_at` is the EX-10
  credit agreement's own *"dated as of"* clause plus 90 days. `asked_at` appears
  nowhere in the computation, and the payload carries `ttl_basis` so a consumer
  can check the arithmetic without reading the specification.
- **A policy step with two conditions**, where only one of them would have
  passed the obvious test. Facility-level need-to-know is a property of the
  *principal*; jurisdiction visibility is a property of the *borrower*. Three of
  the four principals in the estate see nothing at all.
- **A refusal you cannot probe.** A facility withheld by policy and a facility
  that does not exist produce byte-identical refusals. The distinction survives
  only in the replay record.
- **Three data traps, each served honestly rather than repaired**: four
  facilities whose maturity date precedes their effective date, seven with no
  maturity date at all, and 43 carrying an amendment count that the estate has
  no amendment *date* to go with.
- **A shipped finding, asserted by a gate that goes red when it is fixed.**
  50 of the 60 facilities are refused on `ttl-bounds` at the pinned instant.

## Run it

```bash
# 1. A fresh clone has no interpreter yet. This creates .venv/.
make venv

# 2. The read-only connection string for the facility estate.
#    The role needs SELECT and nothing else: nothing this example runs writes to
#    the store it reads, and a role that could write would make that a promise
#    rather than a guarantee.
#
#    Both libpq spellings work and neither is preferred:
#      export CCF_CP_02_POSTGRES_DSN='host=… port=… dbname=… user=… password=…'
#      export CCF_CP_02_POSTGRES_DSN='postgresql://user:pass@host:5432/dbname'
#    libpq also reads PGHOST/PGPORT/PGUSER/PGPASSWORD from the environment on
#    its own, so the variable's contents can be as short as `dbname=<database>`.
export CCF_CP_02_POSTGRES_DSN='dbname=<database>'

# 3. The one documented command. `-s` suppresses make's echo of the recipe,
#    which is the only thing that differs between this output and the
#    transcript published on the documentation page.
make -s example-cp-02
```

Without `make`, spelling the interpreter explicitly:

```bash
.venv/bin/python examples/cp-02-facility-terms-snapshot/run.py
```

**Variations that change the answer, not the formatting.** Each is a `make`
invocation because each is a request parameter, and a request parameter belongs
on the command line rather than in configuration:

```bash
# The same facility asked seventeen days later. `expires at` MUST NOT MOVE.
# This is the whole product in one comparison.
make -s example-cp-02 ASKED_AT=2026-09-15T23:45:00+00:00

# A maturity date 196 days BEFORE the effective date. Serves, and refuses to
# compute a tenor. Its borrower is cp-01's own demonstration anchor.
make -s example-cp-02 FACILITY=FAC-66B83D

# No maturity date at all.
make -s example-cp-02 FACILITY=FAC-517638

# Drop the pricing grid. Changes the payload's SHAPE, so the content address
# changes with it.
make -s example-cp-02 NO_PRICING_GRID=1
```

**Variations that exit non-zero, and that is correct.** A refusal is not a
crash, but it is also not a success, so `make` reports `Error 1` and the shell
sees a non-zero status:

```bash
# ELEVEN amendments, effective 2026-05-29 — outside the 90-day window.
# Refused on `ttl-bounds`. This is 50 of the 60 facilities in the estate.
make -s example-cp-02 FACILITY=FAC-1FF50C

# A principal granted every jurisdiction in the estate and NO facility-level
# need-to-know. Refused, indistinguishably from a facility that does not exist.
make -s example-cp-02 PRINCIPAL=PRIN-RES-002

# A parameter this tier declares and always refuses.
make -s example-cp-02 AS_OF=2026-01-01T00:00:00+00:00
```

## The story

A credit officer opens a drawdown request. They need the facility's terms — the
commitment, the currency, the maturity, the pricing grid — as a typed object
rather than a PDF.

A loan-system screen returns all of that. What it cannot return is **a statement
of when believing it stops being safe.** So the officer reads terms that were
filed in 2021, and nothing on the screen says whether the agreement has been
amended eleven times since.

This product returns the same terms **plus** an `expires_at` derived from the
agreement's own date, a `ttl_basis` naming which date that was, a `context_debt`
score on the answer, and a refusal when the terms are older than the window
allows. The default run:

```
   asked as of        2026-08-29T12:00:00+00:00
   ttl basis          2026-07-29   (effective_date, the agreement's own date)
   expires at         2026-10-27T00:00:00+00:00   (ttl_anchor from_entity_freshness)
   ...which does NOT move when `asked as of` moves — that is the anchor
   context debt D_c   0.0396  ->  ok
```

*Three lines lifted from the summary block of the default run; the full
transcript is in `page/run-transcript.txt`.* Its last line is `assembled by`:

The `assembled by` line names the assembler implementation that produced this run (`cp-02.facility-terms-snapshot@1.0.1`) — transcript evidence, read off the program's own stdout.

Replay carriage of that identity is a Phase 24.6 ledger row (`D-IMPL-245` amendment 1); the transcript is the evidence the example can carry today.

**What changed in this example on 2026-09-03.** The assembler's unreachable
compatibility branch — kept for a refusal the SDK could not, at the time, return
as data — was removed after the SDK gained the tier refusal (`24.5-L-12`/`L-13`),
so the implementation identity moved to `1.0.1` while the product stayed `1.0.0`,
because the served bytes and the contract did not change (`D-IMPL-245` (1)).

**The uncomfortable half is the point.** At the pinned instant, 50 of the 60
facilities in this estate are **refused** — their agreements are older than 90
days and the fabric will not vouch for terms whose currency it cannot establish.
The 43 that carry an amendment history are all in that 50. That is recorded as a
finding and taken back to the vault, not smoothed away: the specification's
§E.5 sets out both candidate anchor bases with the measurement that separates
them, and the one that would make every facility serve turns out to have a
single distinct value across all 60 rows — which is a product-level TTL wearing
a per-entity label.

## Artifact-by-artifact

| File | | What it carries |
|---|---|---|
| `spec/CP-SPEC-002_…md` | `[READ FIRST]` | The specification. Gate 1 approved; everything below derives from it |
| `ccf_config.yaml` | `[ADAPT]` | The Control Plane document — product class, the operator's parameters, the resolution rules, four λ_c classes, the debt bands, the policy regime and the default perspective |
| `backends.yaml` | `[ADAPT]` | How the graph's settings are composed and how the system of record is reached. A variable **name**, never a value |
| `artifacts/question.yaml` | `[ADAPT]` | The caller's vocabulary — anchor, intent, freshness, debt tolerance, and the pinned `asked_at` |
| `artifacts/ttl.yaml` | `[ADAPT]` | The 90-day window and its ceiling, with the measurement that constrains them |
| `artifacts/assembly-recipe.yaml` | `[ADAPT]` | §D.2's operator table **as data**, with a witness per step. A step nothing executes is red |
| `artifacts/expected.yaml` | `[ADAPT]` | What the served product must contain. Derives nothing from a run |
| `deployment.py` | `[ADAPT]` | The interpreter. Reads the documents above and answers what the spine asks |
| `produce.py` | `[MECHANISM]` | The spine — the fabric's call path, carrying the seven canonical regions |
| `assembler.py` | `[ADAPT]` | The governed seam, conforming to `ContextAssemblerProtocol` |
| `run.py` | `[ADAPT]` | The client |
| `summary_explanations.md` | | The same product explained to a banker rather than an engineer |

## Whitepaper / CLAUDE.md sections exercised

- **Whitepaper §7.6** — the Context Product Contract and its TTL anchor; §7.7
  half-life and Context Debt; §7.10 Decision Replay.
- **CLAUDE.md §6.4** — the No-Hardcoding Rule. Delete `artifacts/` and
  `ccf_config.yaml` and this example has nothing left to run.
- **CLAUDE.md §10** — single-writer: `booted.handle.worker` is the only write
  handle to L3 in the process, and the source estate is unreachable from it.
- **Standard §2.4** — the declared-but-inert parameter; §6.4 Temporal
  Validation, which is why §E.3's materialization posture needs a carve-out.

## What to change first

Point it at your own store. `backends.yaml` names one environment variable and
`ccf_config.yaml`'s `resolution:` block names the columns; between them they are
the whole binding. Then:

1. **Change the anchor** in `artifacts/question.yaml` to a facility of yours.
2. **Change the TTL** in `artifacts/ttl.yaml` — and read the note at the bottom
   of that file first, because the window and the *basis* are separate decisions
   and conflating them is how a cache collapses.
3. **Change the policy attribute** in `ccf_config.yaml` if your facilities carry
   their own jurisdiction rather than inheriting the borrower's.
4. **Add a signal class** to `half_life:` if your payload mixes cadences the way
   this one does — 540 days beside 1 day, in the same record.

## What would fail

**The published transcript reproduces against a named snapshot.** The default
run above was produced at commit `HEAD` of this example against the estate as
loaded on `2026-08-25`, asking as of the pinned
`asked_at: 2026-08-29T12:00:00+00:00`, and its content address is
`708a4a3f1a8486b125fdcbcbb848c3a43ae7cda81066ad3ee832aafe749d8b0c`. A reader
whose address differs has re-derived rather than replayed.

Things that would break, and how you would know:

- **Asking as of "now."** Every facility whose agreement is more than 90 days
  old refuses on `ttl-bounds`. That is 50 of 60 today and it grows. It is the
  fabric working, not a broken example.
- **Anchoring the TTL on `retrieved_at`** to make that go away. Every facility
  would then expire at the same instant, because that column carries **one**
  distinct value across all 60 rows. The gates would pass and the primitive
  would be gone.
- **Flattening the pricing grid** to a headline margin. Nothing fails loudly: a
  margin comes back, and the leverage tiers it depends on are simply absent.
  `FTS-G07` is what catches it.
- **Naming entitlement in a refusal.** `"you are not entitled to see it"`
  discloses that the facility exists. `FTS-G04` compares the two refusals for
  byte equality.
- **Reading `source_offsets`.** They are populated on 60 of 60 rows and sit in
  the same row as the terms. A T1 example that reaches into a document has
  silently become a T4 example.
