# Central native plant database

The operational central database is PostgreSQL with PostGIS. A separate SQLite staging snapshot makes inspection and repeatable exports possible; it is not the spatial server.

## Connect

| Setting | Value |
|---|---|
| Host | 127.0.0.1 |
| Port | 55432 |
| Database | native_plants |
| Schema | native_plants |
| Read-only account | nativeplant_reader |
| Administrative account | nativeplant_owner |

Passwords are in the outer workspace `local/database.json` and are not included in Git, SQL exports, documentation or this report. Use the reader account for browsing/QGIS and future application reads. The server listens only on loopback and uses password authentication. Runtime files and cluster data live under the outer dependencies folder. No Windows service or startup task was registered; after a reboot, start the server manually.

## What is loaded

- 3,070 central taxon identities (species and infraspecific taxa, plus provisional identities). 2,976 are verified by the matched taxonomy; 94 remain provisional.
- 9,687 source records: all considered native, review and excluded source rows, plus all 100 original plant records. Excluded records whose identities are outside the master remain unlinked audit rows, so they do not create unrelated non-native plants. These counts overlap and are not counts of distinct species.
- 24,195 names/source-name usages and 2,977 authority identifiers, including synonyms and all eleven researched Kew identities.
- 9,100 regional evidence statements, with separate native classification, occurrence and planting guidance.
- 5,579 trait claims. Original catalogue garden traits retain an unverified status.
- 107 valid spatial polygons: 36 conservation-authority jurisdictions and 71 Ontario ecodistricts, using the preserved archive snapshots.
- 2,717 identities currently qualify for the general `native_candidates` view. This view requires a clear matched identity and explicit present/native evidence, without a recorded native/introduced conflict in that same region. It is not an address-specific planting shortlist.
- All original plant IDs remain in `original_plant_links`. Original plant 89 retains its intended-identity review flag.

## Tables and views

`plants` is the central identity table. `plant_names` and `external_identifiers` connect synonyms and authority IDs. `sources`, `source_records` and `plant_source_links` preserve provenance and matching decisions. `regional_evidence` links location-specific statements to `regions`. `source_coverage` records dataset scope separately from plant range. `trait_claims` preserves source-specific growing facts; `growing_conditions` and `condition_values` hold selected values and their provenance. `import_issues` and `evidence_conflicts` retain unresolved questions.

Views: `plant_profile`, `preferred_conditions`, `native_candidates`, `identity_review_queue`.

See DATA_DICTIONARY.md for every field and constraint. PostGIS stores regions as MultiPolygon/EPSG:4326 with a GiST spatial index. Source JSON is JSONB in PostgreSQL. The SQLite staging copy uses JSON text and GeoJSON text instead.

## Query examples

```sql
SET search_path = native_plants, public;

-- Follow original database plant 1 into the central identity.
SELECT o.original_plant_id, p.accepted_scientific_name,
       p.preferred_common_name, o.review_status
FROM original_plant_links o
JOIN plants p ON p.plant_id = o.plant_id
WHERE o.original_plant_id = 1;

-- Show region boundaries covering an approximate Oakville point.
SELECT region_name, region_type, external_region_code
FROM regions
WHERE ST_Covers(geom, ST_SetSRID(ST_Point(-79.68,43.45),4326));

-- Inspect selected conditions with their review status.
SELECT p.accepted_scientific_name, c.field_name, c.value, c.review_status
FROM preferred_conditions c
JOIN plants p ON p.plant_id = c.plant_id
ORDER BY p.accepted_scientific_name, c.field_name;
```

The spatial example returns Conservation Halton and ecodistrict 7E-4, which is named Toronto. That ecodistrict is not Toronto city or the Toronto checklist study extent.

## Local management

From the GitHub project root:

```powershell
python scripts/database/manage_database.py status
python scripts/database/manage_database.py start
python scripts/database/manage_database.py check
python scripts/database/manage_database.py backup
python scripts/database/manage_database.py stop
```

Backups are written to outer `backups/native-plants-central.dump`. The current backup was restored to a temporary database and its plant counts, spatial counts and geometry validity checked. The temporary validation database was then removed.

The status command checks SQL connectivity. Run start and stop from a local PowerShell terminal as the Windows user who owns the database files. SQL connectivity, read-only access, import, backup and restore were verified. A full stop/restart cycle was not verified.

See [SETUP.md](SETUP.md) for fresh-clone prerequisites, publication exclusions and reader provisioning.

## Rebuild / import

```powershell
# If the source JSON is already prepared, no PDF libraries are needed here.
python scripts/data/prepare_boundaries.py
python scripts/data/build_central_database.py
python scripts/database/manage_database.py load
python -m unittest discover -s tests -v
```

Boundary preparation needs GDAL ogr2ogr (available in the installed QGIS). Source archives remain in outer dependencies/source-data. The builder creates a new staging SQLite file, checks its integrity and foreign keys, and preserves a prior central snapshot under outer work/backups. Treat this builder as a source-snapshot rebuild: manual edits to generated selected values should first be recorded in a separate reviewed input, otherwise a rebuild can replace them.

For a fresh Windows workspace, `python scripts/database/setup_local_database.py` downloads the pinned official portable PostgreSQL/PostGIS packages into the outer dependencies folder and initializes a loopback server only if no cluster exists. It does not replace an existing cluster. Original data archives are not redistributed or fetched by this setup helper. Preserve the native-subset exclusion audits in outer work/native-subsets/excluded, or regenerate them with build_native_subsets.py before rebuilding the central catalogue. A new installation must provision a reader before running the website; the app requires reader credentials. See SETUP.md. The original workspace already has a reader.

For another PostgreSQL installation with PostGIS available, create a database and run data/central/schema.postgresql.sql followed by data/central/load-data.postgresql.sql with psql ON_ERROR_STOP enabled. The data load is transactional and uses deterministic keys/upserts. It requires permission to install PostGIS for the initial extension step; use an administrator for that step. Generated load SQL is Git-ignored because it includes large boundary coordinates; schema and rebuild scripts remain in the repository.

## Selection rules and limits

- IDs are deterministic UUIDs keyed to VASCAN, Kew, or an unresolved name. No fuzzy names or common names merge taxa. A species and its variety/subspecies retain separate identities and parent links.
- Original duplicates such as Heliopsis helianthoides map to one taxon while retaining all original IDs and trait claims.
- Review and extinct records remain evidence, not default native candidates. Matching a name does not clear a source's native-status uncertainty.
- Halton abundance codes are retained as occurrence/planting context. Its inferred native classifications remain explicitly `inferred_needs_review`, rather than being counted as explicit local-native assertions.
- Preferred sun values use the first matched Halton claim when supplied, otherwise original catalogue values. One source claim is selected per field; all other claims and detected disagreements remain available. Original preferred values retain source_unverified status. Growth form from VASCAN can be broad (herb) rather than the finer garden category (grass/sedge).
- Missing pH, spread, lifecycle, maintenance, bloom range and other traits remain NULL. Original bloom strings remain source claims; no unsupported numerical range was invented. Pollinator scores remain original, unverified claims.
- The four named regions Ontario, Halton inventory area, Hamilton inventory area and Toronto checklist study area have pending geometries. No approximate study area or province polygon was invented from ecological districts. The conservation-authority layer is the older preserved snapshot; check boundary versions against newer plant sources before production address filtering.
- OGR reported multiple coordinate operations when converting NAD83 source shapes to EPSG:4326. Transformation differences are documented and source coordinates are preserved in the original shapefiles. Imported polygons were validated/repaired with ST_MakeValid and all 107 are valid.
- The website now reads PostgreSQL through a read-only account. Address coordinates select available mapped local checklist scopes, with an explicitly labelled Ontario fallback where local evidence cannot be mapped. See the project README for filter and pagination behaviour.
- Source terms still apply. Licences for the regional PDFs remain unverified; public availability alone is not permission to relicense their content.

## Verification

All 36 tests passed after website integration, including existing application checks, subset checks and seven central-database checks. Live PostgreSQL counts match staging, original IDs and review flags are preserved, foreign keys pass, all polygons are valid with SRID 4326, read-only access was exercised, and a real backup restore was verified. See data/central/build-report.json and live-validation.json.
