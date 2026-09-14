# D-IMPL-336 — close-time cross-AI panel

**Subject: the SHIPPED CODE at candidate `e4d53346`**, per CLAUDE.md §3.1:
*"When execution has already happened, the panel reviews the shipped code, not
the plans… Write the close-time panel to a distinct file so the pre-execution
plan review survives."* The earlier records —
`docs/D-IMPL-336-PANEL-REVIEW.md` (the design panel) and
`docs/D-IMPL-336-REMEDIATION-DISPOSITION.md` — are untouched.

**Result: 9 confirmed, 1 partial, 14 rejected, across 30 agents.** Every
finding was adversarially verified against the tree before being recorded, and
every confirmed finding was then re-measured by the orchestrator before it
reached Dave. Remediation is at `1edc8fe7`.

---

## 1 · The panel, and whether each reviewer actually read anything

CLAUDE.md §3.1: *"Before counting any reviewer as having reviewed, check that
the symbols and line numbers in its output actually resolve against the tree —
and record any reviewer that failed that test as failed, rather than as a
reviewer."*

| Reviewer | Build | Read-proof | Findings |
| --- | --- | --- | --- |
| **codex** | codex-cli 0.137.0, gpt-5.5, `model_reasoning_effort=high` | **Conclusive** — all six cited line numbers resolved exactly | 6 |
| **cursor** | cursor 3.19.13 | **Strong** — quoted `_touched_entities`' signature verbatim | 6 |
| **gemini** | gemini CLI 0.35.3, default model | **Strong** — cited the R5 fields at their real lines | 4 |
| **ollama** | qwen3.5:397b-cloud | **Strong** — quoted `_ACQUISITION_OF`'s lookup line | 3 |
| **independent deep read** | given the TREE, not the payload | n/a — read the tree directly | 4 |

**Two silent-failure modes were hit and neither emptied the panel.**
`gemini-3-pro` returned **404 at exit code 0** and fell back to the default
model. Codex's `bwrap` sandbox is the known hazard on this host — it can exit 0
having read nothing. The payload was **inlined (141KB, on stdin)** precisely so
a silent sandbox failure cannot look like a clean review, and the read-proof
check is what turns "exit 0" into evidence rather than an assumption.

---

## 2 · Confirmed findings

### CP-F-01 — `F3` REGRESSED. A local child with no execution record was admitted, and the record named an authority that never ran. **HIGH**

Found independently by **codex, cursor, gemini and the deep read**. Re-measured
by the orchestrator before acceptance:

```
touched SUPPLIED -> ChildAdmissionRefusal
touched=None     -> AdmittedChild  basis=local-register
```

on a child whose entity really was superseded.

Amendment 3 closed `F3` by making `touched_entities` always present. **Amendment
5 made it optional** — correctly, so a remote child need not force a read of its
provider's replay store — **and left the local leg admitting `None`**.
`refuse_dependency_invalidation` returns `None` immediately for `None` (the
deliberate pre-`D-IMPL-334` compatibility posture Dave ruled must not change),
so the register was never resolved and the row still recorded `local-register`.

**Reachable without a hostile caller.**
`GrantBoundChildResolver._touched_entities` returns `None` whenever a local
child's `DoorOutcome.replay_ref` is `None`, which the wire contract explicitly
permits for a producer that is not a shipped door.

**Fixed** at `1edc8fe7`: the local leg refuses with
`eligibility-evidence-missing`. A local child is one *this* fabric dispatched,
so its execution record is this fabric's to hold; not holding one is *don't
know*, and don't-know must never read as *pass*. Unlike the `mcp` leg there is
no other authority to name. It refuses as **missing evidence** rather than
`ineligible` — the child may be perfectly eligible; what is absent is the means
to say so.

Proof: `test_f3_REOPENED_a_local_child_with_no_execution_record_REFUSES`, with
the control beside it, and
`test_f3_the_local_leg_is_the_ONLY_one_that_requires_an_execution_record`
holding the boundary Dave's ruling draws.

### CP-F-02 — the acquisition axis was spoofable. **PARTIAL, and it survived verification**

Raised by cursor. The acquisition kind is read off the dispatch result's type,
and **the dispatch result types are ordinary public contracts** — unlike
`ChildInvocation` and `ResolvedProducer`, nothing mints them. A hand-built
`SkillInvocation` naming a genuinely MCP-bound entry yielded
`acquisition="local-dispatch"` **with caller-chosen touched entities**, which
buys the local invalidation register's authority over a decision it never saw.

That is the hazard Dave named by name: *"a local skill fetching a remote product
must not relabel that product as locally produced to bypass its applicable
checks."*

`grep -c skill_type src/ccf/products/composite.py` was **0**. Both available
cross-checks were unused: the granted entry's `skill_type`, and the `skill_type`
the dispatch stamps on its own result.

**Fixed**: three facts are held to each other. **The guard immediately fired on
the project's own test helper**, which had been pairing a `local_callable` entry
with an `McpInvocation` — the defect building itself.

Proof: `test_a_remote_entry_CANNOT_be_relabelled_as_a_local_dispatch`, with the
honest pairing asserted alongside so it is a differential.

### CP-F-03 — the D-15 surface gate was RED on this branch and GREEN on `main`. **MEASUREMENT FAILURE**

Found by the deep read. The only unclaimed names were **the branch's headline
deliverable** — `GrantBoundChildResolver` and `ChildArguments`. Fragments
`336-01`…`336-04` named `ccf.products.composite` and `ccf.peering.eligibility`;
nothing named the new module.

The orchestrator ran `make surface-changes` after adding the module **and never
ran the gate**. Fragment `336-05` written; gate green.

### CP-F-04 — a test promised what no assertion carried. **MEASUREMENT FAILURE**

Found by the deep read. `test_int01a` contained
`assert row.child_asked_at == ASKED_AT` **twice**, the second where the comment
above it promised an assertion about touched entities.

Now carried by `eligibility_basis == "local-register"` — which *only* carries it
because of CP-F-01's fix. Before that fix the basis was recorded whether or not
any entity had been resolved, so the assertion would have been vacuous.

### CP-F-05 — two live docstrings were false. **LOW**

Found by gemini and the deep read. `CompositeAdmissionGate` told the reader its
inputs arrive as `ChildProvenance` — a deleted class — and
`CompositeChildResolverProtocol` still said *"the SDK ships this Protocol and
never an implementation"* with `child_resolver.py` sitting beside it. This
project treats a false docstring as a defect.

Corrected, each with the ruling that changed it.

### CP-F-06 — `mixing.constituent_id` carries a content address where every other refusal carries a class name. **ADVISORY**

Raised by cursor, confirmed, **not fixed**. `ChildAdmissionRefusal.product_class`
is set from `child.verified_content_address` on the mixing path. Carried as a
consistency observation rather than repaired, because changing what the field
holds on one refusal path affects every reader of that field.

---

## 3 · Rejected — 14, and the shape of why they fell

Recorded because CLAUDE.md §3.1 requires it: *"record the ones you reject as
rejected."* Four recurring shapes:

- **The mechanism is real; the consequence is not.** Five findings correctly
  described `_ACQUISITION_OF` as a name lookup rather than an `isinstance`
  check, then inferred a defect that execution disproved. *"The trigger admits
  nothing the documented default path does not already admit."*
- **Unreachable through supported interfaces.** An AST enumeration over `src/`,
  `runtime/` and `examples/` found exactly **one** `AdmittedProduct(...)`
  construction site — the peering gate — so a finding resting on a forged one
  requires the threat model this project explicitly excludes.
- **Already known and disclosed.** One finding restated a limitation printed in
  `docs/D-IMPL-336-COMPLETION.md` at HEAD, in the same words.
- **The code does the opposite.** Gemini's HIGH finding on `composed.lineage`
  asserted the resolver *"skips this check and treats the union as
  definitive"*; the resolver holds the parent's own declaration strictly
  **before** the union. This is the third recorded instance on this project of
  gemini citing text correctly and inverting its meaning.

**Three reviewers agreeing remains not evidence.** Four agreed on CP-F-01 and it
was real; five overlapping claims about `_ACQUISITION_OF` fell to single
measurements. The verification stage is what separates them, not the count.

---

## 4 · What the panel establishes, and what it does not

**Establishes.** The simplification did not drop the controls it claimed to
relocate — every "Removed" row in `docs/D-IMPL-336-COMPLETION.md` §2 was chased
to where its property is enforced now, and one gap was found (CP-F-01) and
closed. The peered and MCP legs behave as ruled. The four composition laws are
reachable and correct.

**Does not establish.** No composite has run against the `.76` estate — that is
CP-14 work by Amendment 5. The MCP demonstration is one logical resource from
one child process. The peered branch selects the first inbound product that
passes admission and matches the class, and does not disambiguate a peer
returning several.
