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
human reviews before merge — never a silent refresh. Regenerate by
running each leg live and capturing the wire traffic:

1. Start the fabric: `python serve.py` (note the `READY <port>` line) and
   export `CCF_MCP_URL=http://127.0.0.1:<port>/mcp` plus `CCF_TOKEN` (the
   active token in `artifacts/tokens.yaml`).
2. **Unset the replay redirects** — `ANTHROPIC_BASE_URL` and
   `GOOGLE_GEMINI_BASE_URL` must not be set.
3. Export real credentials: `ANTHROPIC_API_KEY` (Anthropic leg) and
   `GOOGLE_API_KEY` (ADK leg) — from your environment, never committed.
4. Export the live model names from `artifacts/experience.yaml`
   (`live_mode.anthropic_model` -> `CCF_EXAMPLE_MODEL`,
   `live_mode.gemini_model` -> `CCF_EXAMPLE_GEMINI_MODEL`).
5. Run each leg through a recording proxy (e.g. `mitmproxy`) or with the
   SDKs' HTTP-level logging enabled, and save each POST body as
   `<prefix>-NN-request.json` and each response body as
   `<prefix>-NN.json`, in conversation order, pretty-printed.
6. Re-run the offline harness (serve.py + replay_server.py with the
   base-URL redirects restored) and confirm both legs exit 0 before
   committing.

When recording, replace live model identifiers in the saved responses
with the fixture names the CI harness passes (`claude-fixture`,
`gemini-fixture`) only if you want CI to keep asserting on those names;
otherwise update the harness env accordingly — either way the change is
part of the reviewed diff.
