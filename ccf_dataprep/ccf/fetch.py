"""Rate-limited fetch harness with provenance manifests.

Every public source this project touches is fetched through here, so that
retrieval date, URL, and checksum are recorded without anyone remembering to.
`.gitignore` commits `sources/**/manifest.json` and excludes the payloads.

SEC enforces 10 requests/second and blocks IPs that ignore it. The limiter is
built in rather than left to the caller.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import requests

from ccf.config import REPO_ROOT, SEC_USER_AGENT

SOURCES_ROOT = REPO_ROOT / "sources"


class RateLimiter:
    """Simple thread-safe minimum-interval limiter."""

    def __init__(self, per_second: float) -> None:
        self._min_interval = 1.0 / per_second
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last = time.monotonic()


#: SEC publishes a 10 req/s ceiling. 8 leaves headroom for clock skew.
SEC_LIMITER = RateLimiter(per_second=8.0)

#: GLEIF is more permissive but there is no reason to hammer it.
DEFAULT_LIMITER = RateLimiter(per_second=5.0)

#: Transient network errors worth retrying — weather, not data. An HTTP
#: status error (e.g. 404 via `raise_for_status()`) is deliberately excluded:
#: it is a fact about the resource, not a fact about the network, and
#: retrying it three times only burns rate-limit budget for nothing.
_TRANSIENT_ERRORS = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
)
_MAX_ATTEMPTS = 3
#: Seconds to wait before attempt 2 and attempt 3, respectively.
_RETRY_BACKOFF = (2, 8)


@dataclass
class FetchRecord:
    """One retrieval, as recorded in a source manifest."""

    url: str
    path: str
    retrieved_at: str
    sha256: str
    bytes: int
    http_status: int
    content_type: str = ""
    notes: str = ""


@dataclass
class SourceManifest:
    """Provenance record for one public source directory."""

    source: str
    description: str
    licence: str
    fetches: list[FetchRecord] = field(default_factory=list)

    @property
    def directory(self) -> Path:
        return SOURCES_ROOT / self.source

    @property
    def manifest_path(self) -> Path:
        return self.directory / "manifest.json"

    def load(self) -> SourceManifest:
        if self.manifest_path.exists():
            raw = json.loads(self.manifest_path.read_text())
            self.fetches = [FetchRecord(**f) for f in raw.get("fetches", [])]
        return self

    def save(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": self.source,
            "description": self.description,
            "licence": self.licence,
            "fetches": [vars(f) for f in self.fetches],
        }
        self.manifest_path.write_text(json.dumps(payload, indent=2) + "\n")

    def already_fetched(self, url: str) -> FetchRecord | None:
        """Return the prior fetch of `url`, if its payload still exists.

        Checks the RECORDED path directly, not `directory / basename`. The
        previous version reconstructed the path from the manifest's own
        directory plus only the record's basename, which silently missed any
        payload written a subdirectory deeper (e.g. `<slug>/<month>.xml`) --
        every such fetch always looked uncached, defeating idempotency for
        exactly the layout Wave 14 introduced. `_record_path` already wrote
        the correct location (repo-relative, or the `[outside repo] ...`
        marker for a `dest_dir` payload); this reads that back instead of
        re-deriving it.
        """
        for rec in self.fetches:
            if rec.url != url:
                continue
            marker = "[outside repo] "
            target = (Path(rec.path[len(marker):]) if rec.path.startswith(marker)
                       else REPO_ROOT / rec.path)
            if target.exists():
                return rec
        return None


def _record_path(target: Path) -> str:
    """How a payload's location is written into the manifest.

    Repo-relative when the file is inside the repo. For a `dest_dir` payload
    living outside it, `relative_to` would raise, so the absolute path is
    recorded and marked — a reader must be able to tell "this file is not in
    the repository, and deliberately so" from "this path is broken".
    """
    try:
        return str(target.relative_to(REPO_ROOT))
    except ValueError:
        return f"[outside repo] {target}"


def sec_headers() -> dict[str, str]:
    if not SEC_USER_AGENT:
        raise RuntimeError(
            "SEC_USER_AGENT is unset. SEC returns 403 without a descriptive "
            "User-Agent carrying a contact email."
        )
    return {"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def fetch(
    url: str,
    manifest: SourceManifest,
    filename: str,
    *,
    is_sec: bool = False,
    force: bool = False,
    timeout: int = 60,
    headers: dict[str, str] | None = None,
    dest_dir: Path | None = None,
) -> Path:
    """Fetch `url` into the manifest's directory, recording provenance.

    Idempotent: a previously-fetched URL whose file still exists is skipped
    unless `force`.

    `dest_dir` puts the PAYLOAD somewhere else while provenance still lands in
    the manifest. It exists for one reason: UK Companies House PSC data
    concerns real living people, and Wave 13b's rule is that no such payload
    touches a path this repository tracks — *including* intermediate state
    (`docs/wave13b-design.md` §2.1). The manifest keeps URL, retrieval date,
    sha256 and byte count, which name the snapshot without carrying anyone's
    identity.
    """
    manifest.load()
    target = (dest_dir / filename) if dest_dir else (manifest.directory / filename)

    if not force:
        prior = manifest.already_fetched(url)
        if prior:
            print(f"  [cached] {filename}  ({prior.retrieved_at})")
            return target

    limiter = SEC_LIMITER if is_sec else DEFAULT_LIMITER

    request_headers = dict(headers or {})
    if is_sec:
        request_headers.update(sec_headers())

    resp = None
    digest = hashlib.sha256()
    size = 0
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        limiter.wait()
        digest = hashlib.sha256()
        size = 0
        try:
            resp = requests.get(url, headers=request_headers, timeout=timeout, stream=True)
            resp.raise_for_status()

            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            break
        except _TRANSIENT_ERRORS as exc:
            if attempt == _MAX_ATTEMPTS:
                raise
            wait_s = _RETRY_BACKOFF[attempt - 1]
            print(f"  [retry {attempt}/{_MAX_ATTEMPTS - 1}] {filename}: "
                  f"{type(exc).__name__} — retrying in {wait_s}s")
            time.sleep(wait_s)

    # A zero-byte body served with a 200 is not a successful fetch, but it
    # satisfies every other check here: status ok, file written, digest
    # computed (of the empty string, sha256 e3b0c442...). Recording it would
    # put a provenance entry for nothing into the manifest and hand the
    # caller a file that fails to parse three functions later. OFAC's
    # CONS.XML does exactly this. Nothing this project fetches is legitimately
    # empty, so the guard is unconditional.
    if size == 0:
        target.unlink(missing_ok=True)
        raise RuntimeError(
            f"Empty payload from {url} (HTTP {resp.status_code}, "
            f"content-type {resp.headers.get('Content-Type', '?')}). "
            f"A 200 with zero bytes is a broken endpoint, not a fetch. "
            f"Nothing was recorded in {manifest.manifest_path.name}."
        )

    record = FetchRecord(
        url=url,
        path=_record_path(target),
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        sha256=digest.hexdigest(),
        bytes=size,
        http_status=resp.status_code,
        content_type=resp.headers.get("Content-Type", ""),
    )
    manifest.fetches = [f for f in manifest.fetches if f.url != url] + [record]
    manifest.save()

    print(f"  [fetched] {filename}  {size:,} bytes  sha256:{record.sha256[:12]}…")
    return target


def get(url: str, *, is_sec: bool = False, timeout: int = 30,
        headers: dict[str, str] | None = None) -> requests.Response:
    """One-off GET through the limiter, with no manifest entry.

    For screening and probing — anything that lands in the dataset must go
    through `fetch()` so its provenance is recorded.

    `headers` are merged under the SEC headers when `is_sec`, so a caller can
    add e.g. a `Range` request without losing the User-Agent SEC requires.

    Same bounded, transient-only retry as `fetch()`: 3 attempts, exponential
    backoff, only for `_TRANSIENT_ERRORS`. An HTTP status error still raises
    immediately, unretried. Shared here rather than reimplemented per-caller —
    every probing call gets the retry for free instead of each one carrying
    its own copy that can drift or be dropped.
    """
    limiter = SEC_LIMITER if is_sec else DEFAULT_LIMITER
    request_headers = dict(headers or {})
    if is_sec:
        request_headers.update(sec_headers())
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        limiter.wait()
        try:
            resp = requests.get(url, headers=request_headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except _TRANSIENT_ERRORS as exc:
            if attempt == _MAX_ATTEMPTS:
                raise
            wait_s = _RETRY_BACKOFF[attempt - 1]
            print(f"  [retry {attempt}/{_MAX_ATTEMPTS - 1}] {url}: "
                  f"{type(exc).__name__} — retrying in {wait_s}s")
            time.sleep(wait_s)


def get_json(url: str, *, is_sec: bool = False, timeout: int = 30):
    """One-off JSON GET — see `get()`. No manifest entry."""
    return get(url, is_sec=is_sec, timeout=timeout).json()
