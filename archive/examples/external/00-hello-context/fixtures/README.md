# Model-API fixtures (D-09/D-10)

Recorded model-API responses that make the two LLM client legs
(`client_anthropic.py`, `client_adk.py`) deterministic in CI, replayed
verbatim by `../replay_server.py`. The client legs never read these files
and contain zero CI/live branches — the only switch is the SDKs' own
base-URL environment variables.

## Layout

| File | Role |
| --- | --- |
| `anthropic-NN.json` | Anthropic Messages-API response, turn NN |
| `anthropic-NN-request.json` | The request body that produced it (review diffing only; never served) |
| `gemini-NN.json` | Gemini `generateContent` response, turn NN |
| `gemini-NN-request.json` | The request body that produced it (review diffing only; never served) |

The recorded conversation is fixed and two turns long per leg: turn 00 is
a tool call (`tool_use` for Anthropic, `functionCall` for Gemini) invoking
`get_context`; turn 01 is the final text stating the credit decision.

## Matching rule: ordinal per path

`replay_server.py` routes by path suffix (`/v1/messages` -> `anthropic-*`,
`:generateContent` -> `gemini-*`) and serves fixtures ordinal-per-path:
the first matching POST gets index 00, the next 01, and so on, ordered by
filename. A request past the last fixture for its path is answered HTTP
500 naming the exhausted path — a conversation that drifts from the
recording fails loudly rather than looping.

## Regeneration (a reviewed event — D-10)

Fixtures are versioned in git, and regenerating them is a **reviewed
event**: the new request/response pairs land in a commit whose diff a
human reviews before merge — never a silent refresh. The in-tree
recording proxy (`capture_proxy.py`) and diff utility
(`diff_fixtures.py`) make both halves mechanical.

### Capture

1. Start the fabric: `python serve.py` (note the `READY <port>` line) and
   export `CCF_MCP_URL=http://127.0.0.1:<port>/mcp` plus `CCF_TOKEN` (the
   active token in `artifacts/tokens.yaml`).
2. Export real credentials: `ANTHROPIC_API_KEY` (Anthropic leg) and
   `GOOGLE_API_KEY` (ADK leg) — from your environment, never committed.
3. Start the recording proxy: `python fixtures/capture_proxy.py`
   (optionally with an explicit output directory as `argv[1]`). It prints
   three lines: **the output directory**, the secret-bearing base URL to
   export, and `READY <port>`. Note the directory from that first line —
   steps 7 and 8 both refer back to it. With no `argv[1]` it creates a
   private scratch directory via `tempfile.mkdtemp` (mode `0700`, random
   unguessable name) — **never** this committed `fixtures/` directory, so
   promotion is always a deliberate `mv` whose diff you review. The
   directory name is not predictable by design: it holds live vendor
   responses captured against your real key until you promote or delete
   it. The proxy forwards each POST to the real vendor API —
   the key is injected into outbound headers at forward time — and tees
   the request body to `<prefix>-NN-request.json` and the response body
   to `<prefix>-NN.json`. **Bodies only, never headers**, in either
   direction: headers are where key material rides.
4. Point the client legs at the proxy via the same base-URL seam the
   replay server uses, using the URL the proxy printed —
   `ANTHROPIC_BASE_URL=http://127.0.0.1:<proxy-port>/<secret>` and
   `GOOGLE_GEMINI_BASE_URL=http://127.0.0.1:<proxy-port>/<secret>`.
   The one-time secret in that path is what stops any other local process
   from making the proxy spend your API credit or write into the capture
   directory; a request without it is refused `403` and forwards nothing.
5. Export the live model names from `artifacts/experience.yaml`
   (`live_mode.anthropic_model` -> `CCF_EXAMPLE_MODEL`,
   `live_mode.gemini_model` -> `CCF_EXAMPLE_GEMINI_MODEL`).
6. Run each leg (`python client_anthropic.py`, `python client_adk.py`).
   The recordings land in the step-3 scratch directory in conversation
   order.

### Normalize

Working in the step-3 scratch directory (not in `fixtures/` — nothing has
been promoted yet), replace the live model identifiers with the fixture
names the CI harness passes: `claude-fixture` in the Anthropic
request/response `model` fields, `gemini-fixture` for the Gemini leg
(its model rides in the URL path, so only response `modelVersion`-style
fields need touching). The ordinal count is data, not contract — commit
whatever conversation actually happened.

### Diff review (the D-10 reviewed-event mechanism)

7. Render the review diff with the stdlib utility, against **the
   directory the proxy printed on its first line in step 3** — not a
   literal path, since that directory's name is generated per run:

   ```
   python fixtures/diff_fixtures.py fixtures "$CAPTURE_OUT"
   ```

   (Exporting `CAPTURE_OUT=<the step-3 directory>` once keeps steps 7 and
   8 in agreement.) It re-serializes each JSON file canonically and prints
   a unified diff, exiting nonzero when anything differs. A human reads
   this diff before the recordings replace the checked-in fixtures. A
   nonzero exit that reports every file as missing means the path is
   wrong, not that the fixtures drifted.
8. **Move** the reviewed recordings into `fixtures/` — `mv
   "$CAPTURE_OUT"/*.json fixtures/` — rather than copying. A copy leaves
   live-key-derived vendor responses sitting in the scratch directory
   indefinitely; the `mv` is also the deliberate promotion D-10 specifies.
   Then re-run the offline harness (`make example-ext-00`) and confirm all
   assertions pass before committing. Verify no key material:
   `grep -rE "sk-ant|AIza|Authorization" fixtures/*.json` must match
   nothing. Finally remove the now-empty scratch directory
   (`rmdir "$CAPTURE_OUT"`), so no capture artefact outlives the review.
