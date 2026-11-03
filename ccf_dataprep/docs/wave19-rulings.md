# Wave 19 — rulings made during execution

Every decision taken on Dave's behalf while executing `docs/wave19-plan.md`,
in the order made. Copied out of the SDD ledger, which is git-ignored scratch
that `git clean -fdx` destroys — the same reason Wave 18's deferred findings
were copied into `docs/wave18-deferred-findings.md`.

Each ruling states what was decided, why, and what it costs if wrong. Nine of
them correct the controller's own instructions rather than an implementer's
work; four correct the design or plan documents.

---

### R01

no git worktree — work in the primary checkout on the branch — because data/departmental.sqlite is git-ignored and resolved from REPO_ROOT, so a worktree would hand every SQLite loader a different, empty file: the five tables earlier waves put there would silently vanish and every SQLite check would still pass against fresh empty tables. Cost if wrong: less filesystem isolation from main, mitigated by being on a branch with a clean tree.

### R02

P1 — Task 8 CREATES loaders/load_policy_fluree.py (insider designations) and Task 9 EXTENDS it (limit envelope, regime versions), rather than Task 8 modifying a file Task 9 has not yet created. Chosen over reordering the tasks because Task 9 depends on Task 4's passage ids and Task 8 does not, so 8-before-9 is the correct dependency order. Cost if wrong: none material — the file's final contents are identical either way.

### R03

P2 — the insider guard keys on person_key, not person_id. Verified live: ccf_v2.person and ccf_v2.psc_person both key on person_key, and person.provenance takes only 'public' and 'synthetic — engineered', so the 'public' test is the right discriminator. Cost if wrong: the guard raises UndefinedColumn on first run — loud, not silent.

### R04

P3 — the debt-tolerance floor reads ccf_v2.memo_context_debt .aggregate_debt keyed by lei, NOT ccf_v2.context_debt. Verified live: context_debt is a RECORD table (debt_id, reason, subject_kind, subject_key) with no numeric score and 133 of 304 rows keyed to a person rather than an entity; memo_context_debt carries the float, and validators/memo_debt.py already exposes policy_tolerance(cur) as the tolerance source. One obligor already sits at aggregate_debt 0.4875 against a 0.2 bound, so the condition may need verification rather than invention — Task 14 must MEASURE before it engineers anything. Cost if wrong: Task 15's debt floor would aggregate a column that does not exist, failing loudly on first run.

### R05

P4 — Task 1 expects 7 passed, not 6: two tests are parametrised over two tables. Cost if wrong: an implementer reports a mismatch against a wrong number and wastes a round.

### R06

P5 — FIBO declares fibo-fbc-fct-fse:Bank, BankHoldingCompany, DepositoryInstitution, FinancialInstitution and fibo-fbc-fct-usfse:NationalBank in subject position, verified 2026-08-27. Task 3 adds NationalBank to KNOWN_PRESENT and Task 5 types the reporting bank with it — "National Association" is precisely what that term models, and BankHoldingCompany is right for RSSD 1039502. Cost if wrong: a less precise but still valid type.

### R07

Task 1 Step 5 no longer runs an UPDATE on the live estate inside a rollback. assert_capital_magnitudes takes a cursor, so a stub cursor gives the same proof with zero connection to shared servers; a missed rollback would have divided real capital by 1,000. A positive control was added alongside the negative one, because a test that only proves rejection also passes for an assertion that rejects every input. Cost if wrong: the floor is exercised against a fabricated population rather than the real one -- mitigated because the real population is separately asserted by the other seven tests.

### R08

the reviewer raised a ⚠️ Cannot-verify asking whether the design doc's "17" should be escalated to Dave rather than silently fixed. Ruled: fix it, do not escalate. It is a factual error with a measured correct value (28 rows across 16 institutions, tables overlapping on RSSD 852218), not a judgment call — escalating a wrong number as if it were a decision would spend Dave's attention on arithmetic. Corrected in docs/wave19-design.md and docs/wave19-plan.md at

### R09

the fix COUNTS both figures from the tables rather than substituting the literal 28 for the literal 17. A hard-coded total is a claim nobody re-checks, and this exact number has now been wrong in three files; the tables overlap, so the arithmetic that produced "17" will keep looking right to anyone who does not query them. Cost if wrong: two extra COUNT queries per loader run.

### R10

INTERFACE CHANGE for Task 5. Its brief says produce

### R11

Task 4 does NOT refuse to write a passage lacking an embedding, which is what the plan told it to do. That instruction contradicts this estate's documented architecture:

### R12

the implementer REFUSED the brief's field names and it was right. The brief said doc_id/char_start/char_end; the estate uses document_id/start_offset/end_offset, confirmed live against a pre-Wave-19 passage. The brief's names match a retired alias pair and would have orphaned 513 passages from validators/partition.py's anchor check — a silent disconnection, not an error. This is the "plan verbatim tests become defects" failure the repo has hit three times in one wave before; the implementer copied from the live thing instead. Deviation ACCEPTED and the plan is the document that was wrong. Cost if wrong: none — the estate's own convention is by definition the one partition.py checks.

### R13

this is a real estate finding, not a Task 4 defect — Task 4's own 513 passages are all embedded and it did not add to either population. It goes to Task 17 for docs/known-issues.md §38/§42, which currently records 84 and understates by ~170x. Cost if wrong: a corpus-wide similarity search silently returns nothing from 37.7% of the corpus while the documentation says 0.2%.

### R14

MY OWN Task 4 constraint was measured with a blind query. I wrote "84 before, 84 after" using {'embedding': {'$exists': False}}, which cannot see a passage whose embedding is explicitly null. Had Task 4 written null on all 513, my guard would have reported "84, unchanged" and passed it. The correct question is "how many passages have a USABLE vector", and every later task in this wave that touches passages must ask it that way. Same defect class this wave keeps finding: a check that cannot see what it claims to verify.

### R15

the plan's node URI scheme

### R16

46 dissolved predecessor institutions EXCLUDED from the graph; only the 2 active ones load. FDIC's RSSDHCR:1039502 roster has 48 entries, 46 of them long-dissolved (Texas Commerce, Chemical Bank, Manufacturers Hanover). The loader hard-asserts the 48/2 split against the live source, so the exclusion is checked rather than assumed. Cost if wrong: an as-of reconstruction reaching before a dissolution would miss those entities — acceptable, since no §F condition asks for historical bank structure and the capital base only goes back 12 quarters.

### R17

MY DEFECT, not the implementer's. My Task 5 dispatch explicitly listed

### R18

FIX BY REMOVING ex:rssd from the three Fluree bank nodes, NOT by exempting rssd in partition.py. The estate contains a real tension — §C for this product names RSSD a correlation key for the bank hierarchy, and FABRIC_CORRELATION_KEYS (partition.py:696) lists it alongside lei — but CLAUDE.md settles it: "Fluree nodes carry

### R19

PLAN ORDERING GAP in Task 7, closed in its dispatch. Task 7 must produce ">= 1 dependency edge that CHANGES THE BINDING LIMIT", but the limits do not exist until Task 9. Ruled: Task 7 computes group exposures, selects merges by the arithmetic, and WRITES DOWN the threshold each merge would have to sit against; Task 9 then sets the internal appetite so the intended merge actually bites; Task 15 recomputes the claim from the stores and is the only thing that certifies it. No task asserts the property from a stored flag. Cost if wrong: Task 15 finds the property unsatisfied and it costs a fix round in Task 9 rather than a redesign, because the arithmetic will already be recorded.

### R20

ACCEPT the implementer's deviation — ONE dual-hatted insider (director + executive officer) rather than the brief's literal two invented people. 12 CFR 215.4(b)(2) aggregates "that person, and all related interests" into a single ceiling, so one insider with one related interest is what the rule actually tests; §F asks for ">= 1 Regulation O related-party case", which one case satisfies. A second invented person would add a row and demonstrate nothing. Flagged by the implementer as a judgement call rather than slipped through, which is the behaviour I want. Cost if wrong: trivially reversible — add a second person and a second designation.

### R21

Task 9's internal appetite should be 5.0% of tier 1, subject to the implementer re-deriving it. Two conditions must hold simultaneously and one value satisfies both: the design requires the largest CONTROL group (5.41%, $16.01bn) to breach house policy, and Task 7 requires an appetite inside (4.936%, 7.602%] for the Vertiv/TransDigm dependency edge to change which limit binds. 5.0% is above 4.936%, below 5.41%, and below 7.602%. Cost if wrong: the band is recorded in Task 7's report, so a miss costs one fix round rather than a redesign.

### R22

the PRA regime version must cite CRR Article 395(1) as the provision that ESTABLISHES its 25% limit, keep LE 2.4 as the instrument that applies and modifies it, and stop citing LE 2.3 as a limit source. A limit citing a notification duty asserts the limit comes from there; it does not. §D's regime-anchoring gate exists for exactly this, and the product's stated audience is an examiner. Fixing rather than deleting the PRA version, because the 2022-01-01 boundary is real and is what makes as_of reconstruction differ from the live answer. Cost if wrong: an over-cautious citation set naming two provisions where one would do.

### R23

the DESIGN DOC was wrong about the mechanism and is corrected in place (commit follows). It said the UK "moved large exposures out of assimilated CRR and into the PRA Rulebook". The articles were indeed omitted from the assimilated CRR on 2022-01-01, but the PRA Part APPLIES Article 395(1) rather than restating it. Corrected because the wave's own data disproved my prose, and the true mechanism is the more interesting one.

### R24

CONTROLLER PROCESS ERROR, corrected. I found the LE 2.3 problem in my own verification and dispatched a fix WITHOUT first dispatching the Task 9 review — skipping the gate the skill requires. Recovery: the full task review is now dispatched over the whole range d29d3e6..HEAD, covering the original work and the fix together, rather than a scoped re-review that would only have seen the fix. Cost if wrong: none to the artifact; the range reviewed is strictly larger than either gate alone would have covered.

### R25

BATCH Tasks 11 and 12 into one implementer dispatch. Both are small, independent, single-store row loads (SQLite workbook; Postgres ProjectionPlan rows), they share no file, and neither needs the other's output. The skill's batching guidance covers exactly this shape. Reviewed as one unit. Cost if wrong: one review covers two deliverables, so a finding on either sends both back — acceptable at this size.

### R26

fix by citing BOTH provisions — the limb that applies the limit and the provision that establishes the figure — rather than swapping one for the other. Each citation then carries a claim its own text supports. Cost if wrong: two citations where a purist might want one.

### R27

ACCEPT the table rename. The brief named

### R28

BATCH Tasks 13 and 14 into one dispatch. Task 14 EXTENDS generators/generate_proposals.py, which Task 13 creates — same file, strictly sequential, so two dispatches would mean a second implementer reading in a file the first just wrote. One implementer, two commits, reviewed as one unit. Cost if wrong: a finding on either sends both back.

### R29

resize the BREACHES proposal to breach NET of mitigation (gross must clear $73.9395bn + $12.5849bn collateral), leaving FITS_AFTER_MITIGATION untouched as the sole flip case; and tighten Task 15's floor 4 to assert the breach net of mitigation rather than gross, so a gross-only breach fails it. Neither floor was individually wrong — floor 4 measured gross, floor 5 measured the flip — which is why passing floors did not reveal it. Cost if wrong: a larger hypothetical proposal, still never booked.

### R30

ACCEPT the implementer's pushback — the jurisdiction shortfall is NOT added to spec_coverage.py, and MY INSTRUCTION WAS WRONG. That file's own docstring says it "walks the §C Data Catalog of every registered product": it maps §C catalog ROWS. The ~15-groups-spanning-3-jurisdictions figure is a §F condition about a POPULATION, not a §C element, so there is no row to attach it to and forcing one would mean inventing a §C row the vault spec does not contain — fabrication of exactly the kind this project guards against. The divergence IS recorded: in conditions.py's

### R31

widen both checks rather than accept a narrower claim, and fix the false positive by EXCLUDING the known column by full name rather than by narrowing the search term. An exclusion list is visible to the next reader; a narrow pattern is not. Cost if wrong: a future table legitimately containing "group" in its name trips W19-2 and needs adding to the exclusion list — a loud, cheap failure.

### R32

CONTROLLER CLAIM CORRECTED. I told Dave repeatedly that the vault mirror was stale by four, then five, six, seven uncollected bundles and that the custodian had drained none. That was FALSE. It came from docs/HANDOFF.md, written before the custodian drained them, and I repeated it without ever listing the directory. Verified now: all six Wave 18 bundles are in _archive/sent/; the outbox holds only Wave 19's new bundle. Task 17 caught it and corrected HANDOFF.md rather than repeating it. Cost of the error: I attributed inaction to the custodian, in writing, several times, on no evidence. Recorded here because the correction is owed to Dave in the final message, not just to the file.

### R33

FIX Important 1, 2, 3 and Minor 4, 5 in one fix wave; DEFER Minor 6 and 7 with rulings. 1-3 are all the same failure: a guard whose stated scope exceeds what it inspects (bank_tokens missing the short name; Fluree free text never read at all; a methodology claiming bitemporal structure the ledger does not carry). Minor 4 matters more than its severity — a retrieval date stored as

### R34

Minor 6 (W19-2 scans table names only) DEFERRED. It is accurate to its own label; widening it to columns, SQLite and sources/ is a partition.py redesign that belongs to whoever owns that file, not to a fix wave closing this branch. Recorded in the deferred findings.

### R35

Minor 7 (floor 6 sums a 0-1 debt score across members, so ten pristine members could "breach") DEFERRED. Not live — the passing group contains a member at 0.4143 alone, so the aggregation contributes nothing today. But the reviewer is right that the arithmetic is wrong in principle, and it should be recorded rather than silently carried. Cost if wrong: a future group could pass floor 6 with no genuinely-indebted member.

### R36

the D04 deferred finding TEXT is corrected before merge. The reviewer found sources/screening/wave19_proposals.json also carries

### R37

MY CONSTRAINT WAS WRONG and is withdrawn for Important 3. I told the fix wave to write nothing to any store; it complied, so load_regime_mongo.py was not re-run and the corrected sentence never reached the estate. Verified: the source no longer asserts the false bitemporal claim (grep count 0) while the LIVE Mongo passage still does. The finding was that the ESTATE contains a methodology document claiming structure the ledger lacks — a corrected source with stale data live is arguably worse than no fix, because the next reader of the source believes it is done. Re-run dispatched. Cost if wrong: one write to an idempotent loader whose re-run stability both Task 4 and Task 10 verified.
