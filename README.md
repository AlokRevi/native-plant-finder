# Native Plant Finder

A map-based search tool for Ontario native plants, built with Python, PostgreSQL/PostGIS and Leaflet. Search by address, then filter by sunlight, soil, moisture and other garden conditions. Results include source links and the geographic scope of the native-status evidence.

## Local setup

Tested with Python 3.12. The repository contains application code, database schema and processing scripts. Plant records, database files and source archives are stored locally and excluded from Git. See [Setup](docs/SETUP.md) for required inputs, database loading and read-only account configuration.

For an existing configured workspace:

```powershell
python -m pip install --require-hashes -r requirements-web.lock
python scripts/database/manage_database.py start
$env:PORT="8002"
python app.py
```

Open http://127.0.0.1:8002. Without PORT, the server uses port 8000. The Windows management helper requires the portable PostgreSQL runtime and the outer local/database.json file. Other PostgreSQL installations can be configured directly.

Copy database.example.json to database.local.json and enter the read-only account credentials. Set NATIVE_PLANT_DB_CONFIG to its absolute path, or provide NATIVE_PLANT_DATABASE_URL through the environment. The application does not load .env files. Database access uses the reader account; there is no JSON or SQLite fallback.

## Search rules

1. Convert the submitted address to coordinates and identify the province. The Oakville example uses a fixed approximate location.
2. Find the regional boundaries covering the location. Mapped TRCA and CVC checklist coverage supports local native-status results. Introduced, mixed, historical or extirpated evidence excludes a candidate within the selected scope.
3. Where local checklist coverage is unavailable, use explicit Ontario-native records and label results "Ontario native; local status unverified." Ecological districts provide geographic context, not proof of nativity. Halton jurisdiction boundaries do not substitute for inventory extents.
4. Apply every selected garden condition. A plant with missing information for a selected condition is excluded. Some original garden values remain unverified; recorded compatibility does not establish survival at a site.
5. Return results in pages of 50. Records include species, subspecies and varieties.

The current snapshot contains 2,442 records with explicit Ontario-native evidence for provincial fallback searches. Local searches can return different counts. These are taxon records, not a count of distinct species.

## Project structure

| Path | Purpose |
|---|---|
| app.py | HTTP routes, address lookup, input validation and pagination |
| plant_database.py | Read-only PostgreSQL queries, regional selection and condition matching |
| index.html, assets/ | Browser interface and decorative illustrations |
| data/plant-art.json | Scientific-name lookup for illustrations |
| data/central/ | PostgreSQL schema and validation reports |
| data/regional/, data/native-only/, data/identity/ | Source registries, processing rules and local record files |
| scripts/data/ | Extraction, identity integration and database-building scripts |
| scripts/database/ | Local PostgreSQL setup and management |
| docs/ | Setup, database model, pipeline and verification notes |

The legacy data/plants.json catalogue is retained locally as an input and is no longer used for recommendations. PostgreSQL runtime files, credentials, source archives and backups sit outside the repository. SQLite snapshots and generated bulk SQL are Git-ignored.

## Data and images

Twelve plants have decorative SVG illustrations matched by scientific name. Other records display a flower symbol labelled "Plant image not available." The illustrations are not suitable for plant identification.

Native-status evidence links to its source. Original catalogue garden values have not been independently verified, and unresolved identities and conflicting claims remain in review tables. Some plant categories are inferred from botanical family, including conifers in the non-flowering filter.

Boundary editions can predate the plant checklists. Halton/Hamilton inventory extents and the Toronto study extent remain unverified. A regional native-status record does not establish occurrence at every location within its boundary. Missing records do not establish absence.

Source attribution and publication exclusions are listed in [DATA_SOURCES.md](DATA_SOURCES.md). Some reuse permissions remain unresolved, so source-derived records are excluded from the default Git upload. [LICENSE.md](LICENSE.md) records the current code-licensing status.

## Tests

With the local datasets prepared and PostgreSQL running:

```powershell
python -m unittest discover -s tests -v
```

All 52 tests passed on 2026-11-01. Tests cover source reconciliation, identity matching, regional selection, garden filters, pagination, input validation and HTTP errors. JavaScript syntax was checked separately. See [Release checks](docs/RELEASE_CHECK.md) for the verification scope.

## Map and address services

Leaflet, OpenStreetMap tiles and Nominatim require internet access. Submitted addresses are sent to Nominatim and are not saved to disk. City or region searches are sufficient when an exact address is unnecessary.

Address lookup uses POST JSON on submission. Access logs contain fixed route names and status codes, without addresses, queries or request bodies. Results are cached in memory for up to 15 minutes, with a limit of 256 entries. The server allows 16 concurrent connections, a queue of 32 pending connections, 15-second socket inactivity timeouts, and 120 connections per client per minute. Busy geocoding requests receive HTTP 429 instead of waiting in a queue. Set NATIVE_PLANT_USER_AGENT to identify the deployment. Follow the [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/) and [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/).

The Python HTTP server supports local demonstrations. Public hosting requires a separate deployment setup; GitHub Pages cannot run the Python/PostGIS backend.

See [Security and deployment](docs/SECURITY.md) for request limits, dependency locks and proxy logging configuration. The lockfiles target Windows x64 with Python 3.12; other platforms need a separately resolved and audited lockfile.
