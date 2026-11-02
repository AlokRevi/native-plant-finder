# Release checks — 2026-11-01

- All 52 local tests passed, including 16 security regressions.
- Address searches use POST JSON; synthetic address markers were absent from access logs.
- Rate-limit exhaustion, worker saturation, worker-slot release, cache expiry and socket timeout configuration were tested.
- Tampered archive hashes were rejected before ZIP processing or extraction. Both cached runtime archives matched the pinned digests.
- The hash-locked 13-package data environment installed successfully in a clean Windows/Python 3.12 environment. OSV returned no known advisories for those versions.
- pypdf 6.21.4 read, rotated and wrote sample pages from all three source PDFs; pdfplumber extracted text from each document.
- Database integration tests ran against the existing local PostgreSQL/PostGIS database.

The repository excludes database files, source payloads and private connection configuration. Code licensing and dataset redistribution terms remain documented separately.

The nginx configuration is an example for a Linux deployment. It has not been applied to a hosting service or validated against an installed nginx instance. Review inherited provider/CDN logging separately.

No public-host load test was performed. The complete source dataset was not rebuilt as part of the dependency update. See SECURITY.md for runtime limits and verification scope.
