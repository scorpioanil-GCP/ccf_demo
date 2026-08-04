# HTTP API

The specification below is the committed OpenAPI baseline, regenerated from `create_app()` and
checked for drift by an always-on test — if the running application's routes, models or
responses change without the baseline being regenerated, the suite fails. Regenerate with
`make openapi` and commit the diff; the reviewable diff is the point, and it is why the
baseline is stored rather than produced at documentation build time.

Because this page includes that same committed file whole, the published contract is the
committed contract by construction. There is no transcription step in which the two could
diverge.

```json
--8<-- "openapi.json"
```
