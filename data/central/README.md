# Central database artifacts

See ../../docs/CENTRAL_DATABASE.md for connection details, schema, management and limitations.

- schema.postgresql.sql: normalized PostgreSQL/PostGIS schema and views.
- load-data.postgresql.sql: generated source-data and geometry import (Git ignored; rebuild locally).
- build-report.json: staging import counts and checks.
- live-validation.json: actual PostgreSQL/PostGIS, spatial and backup-restore checks.
- runtime-sources.json: exact runtime download URLs and checksums; no credentials.

The operational server database is native_plants at 127.0.0.1:55432, schema native_plants. The local SQLite staging snapshot is ../database/native-plants-central.sqlite. These are distinct from the earlier ../database/plant-project.db working database, which remains preserved.
