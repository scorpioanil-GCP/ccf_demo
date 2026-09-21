# CP-17 `S-01` reproduction against `main @ 5996dddb`

**Tested SHA:** `5996dddb` — `main` with `D-IMPL-345` merged (`D-GATE-345` at
`fd4205d4`, candidate `3f7778e3`). Working tree clean at the measurement.

**Subject under test:** the **frozen** CP-17 product, `examples/cp-17-mnpi-wall-enforcement`
at `f5e22e6b`, unchanged. No CP-17 file was modified, and none appears in the
merge. The measurement runs the product's own HTTP door — `server/serve.py`'s
`http_app` over one opened product, the same store and the same recorder — on
the live `.76` estate, with the same four credentials the close panel used:
`PRIN-COV-001` (coverage banker), `PRIN-RES-002` (research analyst),
`PRIN-TRD-003` (trader), `PRIN-KYC-004` (recognized, granted nothing).

**Verdict: all three attacks are closed.** Nothing was repaired during this
pass; this document is measurement only.

---

## 0 · The one refusal, measured five ways

Before the attacks one by one, the property they all turn on. Five different
asks — a record that exists and belongs to someone else, an address that is
nothing, a non-record blob, the store's naming index by name, and a caller's
own withheld shell's reference — produce **one** body, one status and one
header set:

```
404  {"kind": "subject-unavailable",
      "refusal_type": "SubjectUnavailableRefusal",
      "refusal": {"detail": "the requested subject is not available to this principal under this product",
                  "disclosure": "minimal",
                  "fields": {"cause": "\"undisclosed\"", "error_code": "\"undisclosed\""},
                  "key": null, "kind": "subject-unavailable",
                  "pre_assembly_lineage": null, "reason": "subject-unavailable",
                  "request": {"parameters": {"reference": "<the caller's own ask>"},
                              "product_id": "ccf.evidence-dereference",
                              "product_version": null, "temporal_boundary": null},
                  "replay_reference": "<this refusal's own record>"}}
```

Measured: status codes equal across all five, header sets equal across all
five, and the bodies byte-identical once each response's own
`replay_reference` is removed and its own echoed ask is normalized. The two
members that vary are the two that are the caller's own: the reference it
asked for, echoed back, and the address of the record **this** refusal
produced.

| leg | what was asked | echoed ask |
|---|---|---|
| cross-principal record (exists, not yours) | the banker's record address | `025b3620…` |
| nonexistent address | a fabricated 64-hex string | `eeee…` |
| non-record blob | a graph-query pin's address | `5b4be65b…` |
| the naming index by name | `.artifact-names.json` | `.artifact-names.json` |
| own withheld shell's reference | the KYC refusal's URI | `ccf-artifact://cp-17-demo/…` |

---

## 1 · Attack 1 — the minimal shell's own reference

**Credential:** `PRIN-KYC-004`, the recognized-but-ungranted principal.

**Steps.** Ask the product over HTTP; take the `replay_reference` the governed
minimal 404 shell carries; present it back to the same door at
`GET /replay/resolutions`.

| | original `S-01` (on `f5e22e6b`, 2026-09-20) | post-345 (`5996dddb`) |
|---|---|---|
| product ask | `404`, minimal shell, `cause`/`error_code` `"undisclosed"` | unchanged: `404`, minimal shell, both `"undisclosed"` |
| dereference | **`200`** — the whole five-dimension record | **`404`** — the governed shell of §0 |
| internal cause | **visible**: `cause: unauthorized` | withheld |
| typed code | **visible**: `principal-not-entitled` | withheld |
| detail | **visible**: *"no entitlement entry for principal `PRIN-KYC-004` under tenant `cp-17-demo`"* | withheld |

**Disclosure comparison, measured on the returned body.** Searched for, and
absent: the typed code `principal-not-entitled`; the string `unauthorized`;
the internal detail sentence; the principal id `PRIN-KYC-004`; the product
class `cib.mnpi-wall`; the subject LEI `0IDE18EMH1CUKQCUYE69`; the
`assembly_refusal` block; `touched_entities`. All eight: **not present**.

**The internal truth is retained**, as `D-IMPL-253` Q27 requires — read
in-process from the store by an examiner, the record behind the new refusal
still carries `cause: unauthorized` and `error_code: principal-not-entitled`.
What changed is who may read it over a door.

**On the tenant string.** `cp-17-demo` does appear in the response — inside
the `replay_reference` URI of the record **this** refusal just wrote, which is
the same shape of string the caller already held from step 1. It is not newly
visible and it is not a signal about the target: the identical string appears
in the refusal for a fabricated address that names nothing (§0), and strip
each response's own reference and the tenant is absent from both bodies.

---

## 2 · Attack 2 — the banker's record address in the analyst's hands

**Credentials:** `PRIN-COV-001` produces the record; `PRIN-RES-002` attempts
the read.

**Setup, measured.** The banker's governed serve returns `200` at product
address `fdf5752d…`; its replay record is at `025b3620…` and carries **47**
touched entities (the deal-engagement and interaction URIs the wall exists to
keep from the analyst).

| attempt | original `S-01` | post-345 |
|---|---|---|
| `GET /replay/decisions?content_address=025b3620…` | **`200`**, the banker's record | **`404`**, the §0 shell |
| `GET /replay/resolutions?uri=<the banker's ref>` | **`200`** | **`404`**, the §0 shell |
| `GET /artifact/025b3620…` | **`200`**, raw record bytes | **`404`**, the §0 shell |

**Disclosure comparison, on each of the three bodies.** Searched for, and
absent from all three: the banker's principal id `PRIN-COV-001`; the subject
LEI; the product class; the first touched entity URI; the substrings
`deal_engagement` and `interaction`. The only match anywhere is the tenant,
inside each response's own reference URI, which §1 and §0 dispose of.

**Refused as `unauthorized` under the approved posture.** The internal
determination behind the analyst's refusal records `cause: unauthorized` with
the typed code `evidence-principal-mismatch` — hold 1, the retained record
principal. On the wire, under CP-17's `minimal` disclosure posture, that
refusal is indistinguishable from a nonexistent address (§0), which is the
stronger of the two outcomes `R-4` permits.

### 2.1 Can the banker still retrieve its own record?

**On CP-17 as it stands: no, and that is the ruled behavior, not a leak.**
CP-17's own entitlement policy (`policy_version` at `90e5cfc5…`) declares
`disclosure_level: minimal` at the tenant and **no per-principal override** —
measured: all three entitled principals carry `null`. Under `R-2` a governed
record crosses a door only at `full`, so on this product **no** principal's
record crosses, its own owner included. CP-17 therefore sits at the strictest
end of the contract rather than at an exception to it.

**The authorized read was measured on a deliberately perturbed policy**, so
the question Dave asked is answered rather than deferred. Registering a `full`
override for `PRIN-COV-001` in the opened product's own Control Plane — a
runtime registration of the kind `serve.entitle` itself performs, changing no
CP-17 file — and repeating the read:

| | result |
|---|---|
| banker reads its own record | `200` |
| bytes returned | equal to the store's, byte for byte |
| `X-CCF-Content-Address` | equals the address asked for |
| record's dimension 4 | `PRIN-COV-001` |
| analyst, same record, same instant | still `404` |

The last row is the point: raising the **banker's** disclosure level does not
open the banker's record to the analyst. Hold 1 is per-principal and hold 3 is
read for the caller, not for the record's owner.

---

## 3 · Attack 3 — artifact and index reachability

**Credential:** `PRIN-RES-002` (an authenticated, entitled bearer); the
non-record blob was also attempted as `PRIN-COV-001`, the principal whose own
serve produced it.

| attempt | original `S-01` / `S-02` | post-345 |
|---|---|---|
| `GET /artifact/.artifact-names.json` | **`200`** with the store's entire naming index — every `tenant/class/name → address` it holds | **`404`**, the §0 shell |
| `GET /artifact/<graph-query pin>` | **`200`** with the pinned traversal query (`seeds`, `allowed_entities`) | **`404`**, the §0 shell, for the analyst **and** for the banker whose serve produced it |
| store-level traversal (`S-02`) | in-process, `FileArtifactStore.get` returned the host's `/etc/hostname` | refused before filesystem access by the content-address invariant merged with 345 |

**Disclosure comparison.** The index exists on disk during the measurement and
its first key is
`cp-17-demo/ccf.graph-query/5b4be65b75b6e12ebb6dd37d626e9170d64efcd60b5f5557156639eddc3c52f8`.
Measured on the response: the index's contents are absent, and **no key from
it appears at all**. The pin's own bytes begin
`{"allowed_entities":null,"as_of":"2026-08-17T00:00:00.000000Z","classi…` —
absent from the response, as is the subject LEI. No filesystem or path
information appears: the body is the §0 shell and nothing else.

The URL-encoded traversal (`/artifact/..%2F..%2F..%2F..%2Fetc%2Fhostname`)
answers `404` at the router with FastAPI's own `{"detail":"Not Found"}`, which
is the same answer it gave before 345 — the route never matched. The
substantive traversal evidence is the store-level one retained from the 345
close: the address invariant refuses `..` traversal, absolute paths, the index
filename, wrong lengths and wrong case before the substrate is touched, which
is why HTTP, the MCP artifact resources and in-process callers all inherit it.
Not expanded further here.

**PUT was not tested and not touched.** It remains outside `D-IMPL-345`.

---

## 4 · Positive-path sanity

Not a new test phase — evidence that closing the three attacks cost CP-17
nothing.

| path | result |
|---|---|
| entitled governed serve, coverage banker | `200`, role `coverage-banker`, 47 entities, address `fdf5752d…` |
| entitled governed serve, research analyst | `200`, role `research-analyst`, 4 entities, address `e7a8970b…` |
| entitled governed serve, trader | `200`, role `trader`, 2 entities, address `b580d4fa…` |
| HTTP requested role outside the grant (analyst asks `coverage-banker`) | `404` governed refusal, minimal shell, typed code not on the wire — no silent downgrade |
| HTTP requested role within the grant (banker asks `coverage-banker`) | `200`, served at `coverage-banker` |
| same-principal authorized record dereference at `full` | `200`, bytes equal, address header matches (§2.1) |

The three product addresses are the ones `CP-SPEC-017` §A.2 records for the
frozen build, so the products are byte-identical to what CP-17 shipped.

**CP-17's own gate suite on `5996dddb`, estate live:** `tests/examples/test_cp_17_wall.py`,
`test_cp_17_doors.py`, `test_cp_17_replay.py`, `test_cp_17_sabotage.py` →
**21 passed, 3 xfailed**. The three expected failures are unchanged and are the
recorded SDK findings `CP17-F-08`, `CP17-F-09` and `CP17-F-10`, which this pass
did not touch.

---

## 5 · What this does and does not establish

**Establishes.** The three attacks that produced `S-01` are closed on the
frozen CP-17 product running on merged `main`, with no CP-17 change; the
internal truth of each determination is still retained for an examiner; and
CP-17's positive paths — three governed serves, the role-request behavior the
HTTP door exists to prove, and an authorized same-principal record read where
policy permits one — all still operate.

**Does not establish, and is not claimed.** Nothing here rules on
`D-GATE-cp-17`, which is a separate decision. Nothing here touches artifact
PUT governance, non-record reachability, CLI bearer support, or
`CP17-F-08`/`F-09` — all carried residuals of `D-GATE-345`. The `full`-level
read of §2.1 was measured on a policy perturbed at runtime for the
measurement and says nothing about what CP-17's shipped policy should declare.
