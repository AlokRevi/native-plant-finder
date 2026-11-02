# Setup and reproducibility

## Existing workspace

Use Python 3.12, install requirements-web.lock with --require-hashes, start the configured database with scripts/database/manage_database.py start, then run app.py. Set PORT to choose a port. Full tests: python -m unittest discover -s tests -v.

## Fresh clone with an existing populated database

1. Install PostgreSQL with PostGIS and obtain compatible populated native_plants tables. An empty schema does not supply recommendations.
2. Create an environment and install the web dependencies:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements-web.lock
Copy-Item database.example.json database.local.json
```

3. Fill database.local.json with the database host, port, name and read-only credentials. It is Git-ignored. Set its absolute path in the same terminal:

```powershell
$env:NATIVE_PLANT_DB_CONFIG=(Resolve-Path database.local.json).Path
$env:PORT="8002"
.venv/Scripts/python.exe app.py
```

Open http://127.0.0.1:8002. NATIVE_PLANT_DATABASE_URL is an alternative. Neither setting installs or populates PostgreSQL. There is no .env loader.

## Rebuild the dataset

Rebuilding requires the source archives, original catalogue and reviewed identity input. Keep the repository under an outer workspace. Source URLs and exact filenames are in data/regional/sources.json and data/native-only/manifest.json.

Required outer inputs:

- dependencies/source-data/regional/: the three PDFs named in the regional registry.
- dependencies/source-data/vascan/vascan-identity-reference.zip.
- dependencies/source-data/toronto/doi_10_5061_dryad_1ns1rn8sg__v20201124.zip.
- dependencies/source-data/boundaries/CAADMIN.zip and ECODISTR.zip.
- dependencies/source-data/original/plants.db: original 100-plant catalogue.
- Project data/identity/plant-kew-crosswalk.json: reviewed eleven-identity input. Recover an authorized local copy or independently repeat/document the research. Scripts do not fetch it.

The original catalogue and reviewed identity input are not publicly bundled. A fresh clone alone cannot recreate the full dataset.

With inputs available, activate your environment (`.venv/Scripts/Activate.ps1` in PowerShell), install requirements-data.lock with --require-hashes and GDAL (ogr2ogr on PATH), then run from the project root:

```powershell
python -m pip install --require-hashes -r requirements-data.lock
New-Item -ItemType Directory -Force data/database | Out-Null
python scripts/data/build_regional_datasets.py
python scripts/data/build_native_subsets.py
python scripts/data/prepare_boundaries.py
python scripts/data/build_central_database.py
```

Legacy plant-project.db is optional for these builders; where present they preserve/update its source tables. Boundary preparation and excluded-record audits go outside Git. The central builder backs up an existing staging snapshot; generated load SQL is local-only.

## Initialize and load PostgreSQL

On Windows, setup_local_database.py downloads the pinned portable PostgreSQL/PostGIS runtime and initializes a loopback database outside Git. This downloads executables: review the helper before running. It preserves an existing cluster and does not download plant inputs.

```powershell
python scripts/database/setup_local_database.py
python scripts/database/manage_database.py load
python scripts/database/manage_database.py check
```

For another installation, create a database and enable PostGIS with suitable administrative privileges. Use psql with ON_ERROR_STOP to run data/central/schema.postgresql.sql followed by the locally generated data/central/load-data.postgresql.sql. Inspect the target before loading; do not load into an unrelated database.

## Provision the application reader

The Windows helper creates the owner account but does not automatically create a new reader. After loading, connect using psql as the owner/administrator. For a NEW role, run the following; inspect existing roles instead of recreating them:

```sql
CREATE ROLE nativeplant_reader LOGIN;
\password nativeplant_reader
GRANT CONNECT ON DATABASE native_plants TO nativeplant_reader;
GRANT USAGE ON SCHEMA native_plants TO nativeplant_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA native_plants TO nativeplant_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA native_plants
  GRANT SELECT ON TABLES TO nativeplant_reader;
```

The psql prompt avoids embedding the password in SQL files. Execute default privileges as the role creating future tables. Configure database.local.json with this reader and set NATIVE_PLANT_DB_CONFIG as above. Use the reader account for the website. The original workspace already has a reader and does not need this step repeated.

## Validation and hosting

Run python -m unittest discover -s tests -v after preparation/loading. This is a local integration suite with HTTP and database checks. It is not expected to pass on a bare clone without the inputs. See RELEASE_CHECK.md for the latest preparation results. Counts refer to the source snapshots recorded in the manifests.

The Python HTTP server is for local demonstrations. GitHub Pages cannot execute the backend. Public hosting needs an appropriate deployment setup, database configuration and compliance with map/geocoding policies.

See [Security and deployment](SECURITY.md) for request limits, dependency locks and proxy logging configuration. The lockfiles target Windows x64 with Python 3.12; other platforms need a separately resolved and audited lockfile.
