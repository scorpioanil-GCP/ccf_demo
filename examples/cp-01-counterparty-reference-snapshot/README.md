# examples/cp-01-counterparty-reference-snapshot — one anchor, two identity authorities, one entitlement filter

The **first rung of the vault's 21-product ladder** and the product every other
product in that catalog resolves its anchor through. One capability class
(`relational`), three systems of record, Assembly Mode 1.

> **READ THIS BEFORE YOU READ A NUMBER.** These examples teach **method** — how
> to engineer and construct a Context Product with the CCF SDK — not the
> figures. `ccf_v2.legal_entity` is 156 of 156 rows `provenance = 'public'`,
> while `internal_client`, `crosswalk` and `principal_jurisdiction` are
> `synthetic — internal`, invented because no public source can supply a bank's
> internal client master or its entitlement service. **No number here is a fact
> about any real company**, and no principal named below is a real person or a
> real role at any institution.

---

## What this demonstrates

Four things, and the fourth is the one cp-00 could not show.

**1. A TTL anchored on the entity, not the request.** `ttl_anchor:
from_entity_freshness` means `expires_at` is *the source's last observation of
this entity* plus 24 hours. What makes this answer wrong is the vendor speaking
again about this company — not time passing since somebody asked. cp-00 anchors
on a fixed reported quarter end; **two products with different anchors teach the
anchor better than either does alone**, which is why the specification names
this rung's *primitive taught* as the anchor itself.

**2. Two identity authorities behind one `anchor` parameter.** An LEI resolves
through GLEIF reference data with a 24-hour ceiling. An internal client id
resolves through the internal client master with a ceiling of **months**. Which
one answered is carried in the payload as `identity_authority`, because a
consumer must be able to tell a day-old vendor claim from a months-old KYC one
without parsing lineage. The asymmetry is stated **per entity** rather than
averaged into one freshness claim — a single "24 hours" over a mixed population
is the exact error the Standard's per-signal-class rule exists to prevent.

**3. Two labelled addresses, and why that is a finding rather than a field.**
Until 2026-08-28 this estate held **one** address triple with nothing recording
which of the two it was. A missing address returns nothing and the consumer
notices; **an unlabelled one returns Wilmington, Delaware for a company run from
Parsippany, New Jersey.** The demonstration anchor is chosen to make that
visible in the served payload.

**4. A Policy step that is load-bearing at Tier 1.** The same question asked by
four principals is two answers and two refusals:

| Principal | Grant | Sees the anchor? |
|---|---|---|
| `PRIN-COV-001` coverage banker | `US` | yes |
| `PRIN-RES-002` research analyst | `US CA GB` | yes |
| `PRIN-KYC-004` EU KYC analyst | `AT BE DE ES HU IT LU NL SE` | **no** |
| `PRIN-TRD-003` trader | `GB HK JP SG` | **no** |

And the two who cannot see it are **refused, in the words a nonexistent
counterparty gets** — no count, no marker, no notice of what was withheld, and
no name for the principal or the entitlement — because `Policy` substitutes the
permissible subgraph for the full graph *before* anything reads graph state,
rather than filtering afterwards, and the assembler refuses a Policy-removed
record rather than serving it empty (`D-IMPL-245` (4)). A `"1 entity hidden"`
notice is itself a disclosure, and so is a refusal that says *"not entitled"*.

---

## Run it

**Everything here runs on the project venv**, never a bare `python` — this
repository has no `python` on `PATH` and the SDK is installed only into `.venv`.
In a fresh clone, one command creates it:

```bash
make venv
```

**Before you run**, export a **read-only** connection string for the
counterparty estate. `backends.yaml` holds the variable's NAME and nothing
else — no host, no port, no credential enters this tree:

```bash
export CCF_CP_01_POSTGRES_DSN='postgresql://<read-only-role>@<host>/<db>'
```

The role needs `SELECT` and nothing else. **Nothing this example runs writes to
the store it reads** — a role that could write would make that a promise rather
than a guarantee. A `host=… user=… password=…` keyword string works equally
well; both are libpq conninfo and neither is preferred.

```bash
make example-cp-01
```

Use **`make -s example-cp-01`** to suppress make's own echo of the recipe. That
form is what makes the output byte-comparable with the run published on this
example's documentation page — the echoed command is the only thing that
differs otherwise. The run ends with an `assembled by` line:

The `assembled by` line names the assembler implementation that produced this run (`cp-01.counterparty-reference-snapshot@1.0.1`) — transcript evidence, read off the program's own stdout.

Replay carriage of that identity is a Phase 24.6 ledger row (`D-IMPL-245` amendment 1); the transcript is the evidence the example can carry today.

**What changed in this example on 2026-09-03.** The assembler's unreachable
compatibility branch — kept for a refusal the SDK could not, at the time, return
as data — was removed after the SDK gained the tier refusal (`24.5-L-12`/`L-13`),
so the implementation identity moved to `1.0.1` while the product stayed `1.0.0`,
because the served bytes and the contract did not change (`D-IMPL-245` (1)). A principal the Policy step excludes — one whose grant matches no entity
(`CPR-G08`) or one not entitled to this entity (`CPR-G02`, `CPR-G04`) — is now
refused with the same text a missing counterparty receives (`D-IMPL-245` (4)),
never a served answer with `D_c = 1`; the §B.4 lapsed exclusion the caller asks
for is still served with its `excluded` block.

Without make, the same thing. The interpreter is the venv's, and spelling it is
the point rather than clutter:

```bash
.venv/bin/python examples/cp-01-counterparty-reference-snapshot/run.py
```

Then the things worth trying, each of which changes the answer rather than the
formatting:

```bash
# The same question, asked by a principal the Policy step excludes. REFUSED — in
# the words a nonexistent counterparty gets (D-IMPL-245 (4)), never served empty.
make example-cp-01 PRINCIPAL=PRIN-KYC-004

# The other identity authority — a no-LEI borrower. SEE "What would fail".
make example-cp-01 ANCHOR=CLI-000101

# A lapsed registration, excluded by default and returned on request.
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78
make example-cp-01 ANCHOR=549300TRW1LZMDJZAQ78 INCLUDE_LAPSED=1

# A parameter the tier declares and always refuses.
make example-cp-01 AS_OF=2026-01-01T00:00:00+00:00
```

Every one of those is OPTIONAL and none of them is deployment configuration:
they are REQUEST parameters, and omitting them asks the demonstration question
declared in `artifacts/question.yaml`.

**Three of those five exit NON-ZERO, and that is the correct answer rather than
a broken target.** `PRINCIPAL=PRIN-KYC-004` is refused — the Policy step removes
the counterparty from what that principal can see, and the assembler refuses a
Policy-removed record with the same text a nonexistent one gets, so a caller
cannot learn by probing which counterparties this estate covers.
`ANCHOR=CLI-000101` refuses at the `ttl-bounds` gate — the shipped defect this
example documents rather than hides, and the subject of *"What would fail"*
below. `AS_OF=…` is refused before the product's own code runs: the SDK's tier
step returns the verdict as data and the program prints the declaration's detail
beneath it —

```
refused: not-supported-at-tier — as_of
   as_of: 400 not_supported_at_tier — not_supported_at_tier
```

— because the contract declares the parameter so a caller can discover it and
then fails loudly so nobody relies on it in a dispute. **A refusal is not a
crash**, but it is also not a success, so `make` reports it as `Error 1`.

The tests run against a **seeded container**, never the estate:

```bash
.venv/bin/python -m pytest tests/examples/test_cp_01_output.py
```

---

## The story

**The question is `GET /context-products/reference/counterparty/{anchor}`** with
an intent, a debt tolerance and `include_lapsed`. Three steps answer it.

**Step 1 — `Resolve`, at L2.** The anchor is tried against the LEI authority
first and the internal client master second, in the order §C.3's hierarchy
states them. An anchor matching neither resolves to **nothing**, and that is a
`404` returned *as data* — never an empty payload. The distinction is worth
keeping in the type system: *no such entity* and *an entity with nothing in it*
are different answers, and a product returning the second for the first has told
its caller something false about the world.

**Step 2 — `Policy`, at L4.** The calling principal's jurisdiction grant is
read, **expanded**, and handed to `PolicyFilter` as an allowlist. The expansion
matters: a grant is a *prefix* (`US` reaches `US-DE`, `US-MD`, `US-NV`) and the
operator tests exact membership, so a prefix passed through unexpanded matches
nothing and silently empties the view.

**Step 3 — contract assembly, at L6.** Not an operator; the Standard retires
`Compose`. Holding the resulting `ServableProduct` **is** the evidence the three
shipped gates ran, because the type is not constructible outside `run_gates`.

**What the run prints beyond the JSON** is the part a plain `SELECT` cannot give
you: the expiry and its anchor, the context debt and its posture, which
authority answered, that entity's freshness ceiling, how many jurisdictions the
principal sees, the operators actually invoked, and the content address of the
answer.

---

## Artifact-by-artifact

| File | What it carries | Why it is not code |
|---|---|---|
| `spec/CP-SPEC-001_….md` | the specification, authored to Standard v0.3 | it is the contract; the code is its interpreter |
| `ccf_config.yaml` | product class, operator parameters, request contract, resolution rules, λ_c, debt bands, policy regime, perspective | Control Plane state, versioned and registered |
| `backends.yaml` | the graph's per-run recipe and the source's env-var NAME | connection material is deployment environment; a DSN in a content-hashed artifact is a DSN in the audit plane forever |
| `artifacts/question.yaml` | the caller's vocabulary — anchor, intent, tolerance, and the **pinned `asked_at`** | a question is not a permission; it has no business in Control Plane state |
| `artifacts/ttl.yaml` | the declared TTL and its ceiling | registering the ceiling MINTS its pin, so the value cannot live in the document whose pin it becomes |
| `artifacts/assembly-recipe.yaml` | §D.2 as data, with a **witness per step** | a prose table cannot be held against a run |
| `artifacts/expected.yaml` | what the served product should contain | derives nothing from a run — that is the point |

**The code is thin and generic on purpose.** `deployment.py` interprets those
documents, `produce.py` is the spine and names no counterparty, no jurisdiction
and no table, `assembler.py` is the governed seam, `run.py` is a client. An
example whose code would still run meaningfully with its artifacts deleted has
violated the No-Hardcoding Rule.

---

## Whitepaper / CLAUDE.md sections exercised

- **Whitepaper §7.4** — the operator algebra; `Policy` before anything reads graph state.
- **Whitepaper §7.6** — the Context Product contract and its validation gates.
- **Whitepaper §7.7** — `D_c = 1 − (F · C · S)`, measured against what was assembled.
- **Whitepaper §7.10** — the five-dimension replay record, written *before* delivery.
- **`CLAUDE.md` §6.4** — the No-Hardcoding Rule.
- **`CLAUDE.md` §10** — single-writer: `booted.handle.worker` is the only write handle to L3, and the source estate is not reachable from the write path at all.
- **Standard §2.4** — the declared-but-inert parameter.
- **Standard §10.3** — the four composition invariants, three of which hold vacuously here and are labelled as such.

---

## What to change first

**To point it at your own estate:** `backends.yaml`'s variable name, and
`deployment.py`'s five table constants. Nothing else in the code knows a table
name.

**To serve a different entity class:** `ccf_config.yaml`'s `resolution:` block.
Add the attribute to `attribute_keys` and it flows to the payload, to
`C_attributes`, and to the completeness figure — in one edit, because those
three read the same list.

**To change who sees what:** `principal_jurisdiction` in the estate. No code
changes. That is the test of whether entitlement is really Control Plane state.

**To change the expiry:** `artifacts/ttl.yaml`. Read the note in it first — the
24-hour TTL and the months-long KYC ceiling do not currently compose, and the
file says so.

---

## What would fail

**Ask for a no-LEI entity and the product refuses.**

```
run.py --anchor CLI-000101
→ ttl-bounds: expires_at 2026-02-24 is outside (2026-08-16T12:00, 2026-08-17T12:00]
```

This is **not a bug in the fabric and not a defect in the data.** `expires_at`
is that entity's `kyc_last_refresh` — months old by design — plus the declared
24-hour TTL, so it lands in the past and the TTL gate refuses on the first call.
**All 30 no-LEI entities are affected, and 27 of the 30 are live under their own
declared ceiling.** The specification's §B.1 element 3 declares one TTL; §C.3
declares two freshness ceilings; the two do not compose.

It is recorded at **§F.4 finding 8**, asserted by **`CPR-G09`**, and the test
that asserts it is written to go **RED when the declaration is corrected** —
because it is the evidence the deviation gets taken back with, not a
ratification of it.

**Ask "now" instead of the pinned instant and everything refuses.**
`legal_entity.retrieved_at` is a snapshot load date, so at today's clock all 186
entities are past their expiry. That is the fabric working correctly against a
snapshot that is no longer fresh — a fact about the *load*, not about the
assembly — and it is why `question.yaml` pins `asked_at` to `2026-08-16T12:00Z`,
which `EXAM-06` requires of every published run regardless.

**Delete `artifacts/question.yaml`'s `subject` and the example stops working.**
That is the No-Hardcoding Rule holding: the code carries no anchor of its own.
