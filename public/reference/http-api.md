# HTTP API

The specification below is the committed OpenAPI baseline, regenerated from `create_app()` and
checked for drift by an always-on test — if the running application's routes, models or
responses change without the baseline being regenerated, the suite fails. Regenerate with
`make openapi` and commit the diff; the reviewable diff is the point, and it is why the
baseline is stored rather than produced at documentation build time.

Because this page includes that same committed file whole, the published contract is the
committed contract by construction. There is no transcription step in which the two could
diverge.

Apart from the `422` validation error the framework generates, refusal statuses are not
modeled in this OpenAPI document. A request with no credential the auth hook recognizes is
answered `401 unauthenticated`. The gate's other refusals are `403`, except an allow it cannot
mint a capability from, which is `503 decision-unmintable`. On
`GET /product/{tenant}/{product_class}/{version}`, a deny by the deployment's scope mapping is
answered `404 subject-unavailable` (dated 2026-10-12, R5-CP17-F01). At the minimal (default)
and reasoned disclosure levels, that is the reply an unentitled caller gets for a real class;
at the full disclosure level, the body names the internal cause. Every other route answers
that deny `403 request-unauthorized`. See [security and deployment, §4.2](../how-to/security-and-deployment.md#42-choose-the-authorization-posture).

```json
--8<-- "openapi.json"
```
