# 378-43 — three small SDK corrections: a declined MCP write is a decline, the SQLite lease's key stated truly, and a `never` class's declaration requirement stated where the field is

`D-IMPL-378`, lane `378f-small2`: three issues surfaced by the 2026-10-08 lanes, remediated under CLAUDE.md §9's
three-issue cap. **No SEC row changes here**: SEC-009, SEC-013 and SEC-020 stay as they were, and SEC-020 stays OPEN.

**1. `McpArtifactStore.put` reported a declined write as an outage.** It judged the server's answer inside the session
operation, and the session runner (`ccf.mcp.client.run_with_session`) reports anything an operation raises that is not
an `McpClientError` as `McpServerUnreachable`. So a write the server declined (the call completed, and the server
answered it as an error) reached the caller as unreachability, the same type a dead server raises, which invites a
retry of a write that will be declined again. `put` now judges the answer after the session closes, as
`McpArtifactStore.match_subject` already did. Measured red before and green after by
`tests/mcp/test_mcp_store_put_decline.py::test_a_write_the_server_declines_is_an_artifact_store_error_not_an_outage`,
which runs the session runner as shipped, unpatched, over real streamable HTTP to the conformance child server, whose
store declines a client-lane write to its replay-record class; and by
`tests/mcp/test_mcp_store_put_decline.py::test_each_answer_put_judges_keeps_its_own_type_through_the_session_runner`
(the runner as shipped, with its transport and session replaced). The other methods were swept. None of their
session operations raises an error of its own. A refusal of a resource read (`get`, `exists`, `names_at`,
`resolve_uri`) reaches the client as the MCP library's protocol error, which this store deliberately does not parse,
so it stays `McpServerUnreachable` as documented. `match_subject` already answers `ArtifactStoreError`.

**2. `SqliteWriterLease`'s docstring said the lease is "keyed on the inode".** It is keyed on the resolved path. A
relative spelling or a symbolic link resolves to one sidecar, but another name for the same file does not: a hard link
resolves to itself, and a live file moved to a new name leaves its old name's sidecar behind. So a writer booted
through the other name in a second process is not refused while the first process's writer is live. SQLite names its
write-ahead log after the path too, so a second name reads another log and misses what the first committed. The
docstring now says all of this and tells the operator to give a live database file one name and not to move it under
a writer. The new module `tests/graph/test_sqlite_writer_lease_hard_link.py` measures each statement as it stands
(`test_a_second_process_boots_a_writer_through_a_hard_link_to_a_held_graph`,
`test_a_second_process_boots_a_writer_through_the_new_name_of_a_moved_live_file`,
`test_the_lease_taken_through_a_hard_link_is_another_lock`, and
`test_sqlite_keeps_a_write_ahead_log_per_name_so_a_second_name_misses_what_the_first_committed`), so the docstring
cannot drift from it unnoticed. Documentation only: the lease's behavior is unchanged. Keying the lease on the file's
identity is a proposal for Dave, because the direct way, locking the database file itself, drops the record locks
SQLite holds in the same process when that descriptor closes.

**3. `ProductClassDeclaration`'s `subject_withholding` description did not state E2 (ii) (d)'s requirement.** It now
says that a class affirming `never` is built only over a plan factory implementing
`ccf.products.resolver.NonWithholdingPlanFactoryProtocol` whose `withholds_no_subject()` returns exactly `True`. It says
that silence or any other value is refused at construction with `NeverWithholdingNeedsAPositiveDeclaration`, and that a
factory declaring it withholds is refused first, with `NeverWithholdingProjectionCanWithhold`. It says that the
declaration is trusted deployment code, an assumption limited to code no caller can influence, and that a false
declaration still meets only the serve-time defense, `NeverWithholdingContradicted`, which tells the withheld subject
from one nothing holds. Documentation only; `docs/schemas/ccf.product-class.json`, whose description is the class
docstring, is regenerated. The statements are measured by `tests/products/test_sec020_never_capability.py` and
`tests/products/test_sec020_e2ii_trusted_declaration.py`, unchanged and passing on this tree.

The manifest `make surface` writes is unchanged by all three, because it records signatures rather than docstring
text, and no signature changed.

## ccf.artifacts.mcp_store.McpArtifactStore

- Surface: ccf.artifacts.mcp_store.McpArtifactStore
- Public surface: true
- Change type: behavior
- Before: `put` raised `McpServerUnreachable` for a write the server declined (a tool answer with `isError`, or one with no structured reference), because the decline was raised inside the session operation and the session runner reports what an operation raises as unreachability; an answer that was not an artifact reference was also `McpServerUnreachable`.
- After: `put` judges the answer after the session closes. A decline raises `ArtifactStoreError` (exactly that type, "the artifact server declined to store '<name>'"), including a refusal by the server's tenant guard or authorizer, which reaches the client as a tool error. An answer that is not an artifact reference still raises `McpServerUnreachable`, because it says nothing about whether the write happened. Transport, handshake and credential failures are unchanged (a rejected bearer token is still `McpServerUnreachable`).
- Why: `put`'s own docstring promised `ArtifactStoreError` for a declined write; a decline is an answer, not an outage to retry.
- Migration: code that caught `McpServerUnreachable` around `put` to handle a server's refusal catches `ArtifactStoreError` instead.
