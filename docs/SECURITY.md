# Security and deployment

## Address handling

The browser sends an address in a JSON POST body to /api/geocode. GET geocoding requests return 405. Application access logs contain a fixed route label, method and status code. Request bodies, query strings, arbitrary paths and exception details are omitted.

Addresses are forwarded to Nominatim. The geocoder cache holds at most 256 results for 15 minutes. Cache keys are hashed; result display names can still contain addresses. Expired entries are removed during requests and regular server housekeeping. No application code writes this cache to disk.

Proxy, platform, CDN and monitoring logs require separate configuration. Disable body capture and use the supplied nginx example, or equivalent settings. This repository does not configure an external hosting account. Existing logs may still contain past queries; review their retention separately.

## Resource limits

The built-in server binds to loopback and uses these limits:

| Resource | Limit |
|---|---|
| Worker connections | 16 active; excess connections receive 503 |
| TCP listen backlog | 32 pending connections |
| Socket inactivity | 15 seconds |
| Per-client connections | 120 per 60 seconds; excess receives 429 |
| Rate-limit records | 2,048 clients, expired after the window; full tables reject new clients |
| Geocoding | One active lookup; concurrent uncached lookups receive 429 |
| Upstream geocoding | At least 1.1 seconds between requests; 12-second upstream socket timeout |
| Geocoding request body | 2,048 bytes; 3–180 address characters |
| Geocoding cache | 256 results, 15-minute TTL |

Limits are per process. The client key uses the actual peer address; forwarded headers are not trusted. Behind a proxy, backend clients share that proxy's limit. Apply per-client limits at the proxy too. Use one geocoding process or shared upstream coordination when scaling. Socket timeouts measure inactivity, not total request duration; a public deployment also needs proxy-side timeouts and connection limits.

## Dependency locks

requirements-web.lock and requirements-data.lock pin the resolved Windows x64 / CPython 3.12 dependencies and wheel hashes. The data lock includes the web dependencies. Install using --require-hashes. requirements.txt and requirements-data.txt retain the direct dependency constraints for resolving other platforms.

pypdf is pinned to 6.21.4. The 13-package locked data environment was installed in an isolated environment, exercised against the three source PDFs and checked against OSV. No known advisories were returned at the time of the check. Repeat dependency checks when updating; this is not a guarantee against undisclosed vulnerabilities.

## Runtime downloads

The Windows database installer checks pinned SHA-256 values before extracting new or cached archives. Downloads use temporary .part files and are renamed only after validation. ZIP integrity checks are additional corruption checks. A digest mismatch stops setup before extraction or execution.

The pinned digests identify the reviewed PostgreSQL/PostGIS snapshots recorded in data/central/runtime-sources.json. They are project-pinned values, not a publisher signature. Version updates require separately reviewing the source and digest, updating both the registry and installer, and rerunning tests. Existing installed executables remain local trusted inputs; archive verification is not an audit of an already installed runtime.

## Git author privacy

Repository-local Git configuration uses the GitHub noreply address. Both author and committer metadata must use that address. Rewriting the original commit removes its personal email from the active branch history, but does not guarantee removal from old clones, cached commit pages or unreachable GitHub objects. GitHub Support may be needed to remove retained server-side copies before making the repository public.
