# Central database field dictionary

PostgreSQL schema: `native_plants`. Original source statuses and partial dates stay as text. JSON fields use JSONB; region geometry uses PostGIS MultiPolygon/EPSG:4326. Empty unknown values are NULL.

| Table | Rows |
|---|---:|
| sources | 9 |
| plants | 3070 |
| source_records | 9687 |
| plant_source_links | 6363 |
| plant_names | 24195 |
| external_identifiers | 2977 |
| regions | 111 |
| source_coverage | 8 |
| regional_evidence | 9100 |
| trait_claims | 5579 |
| growing_conditions | 3070 |
| condition_values | 757 |
| original_plant_links | 100 |
| import_issues | 526 |
| evidence_conflicts | 21 |

## sources

| Field | PostgreSQL type / constraint |
|---|---|
| source_id | TEXT PRIMARY KEY |
| title | TEXT NOT NULL |
| publisher | TEXT |
| url | TEXT |
| edition | TEXT |
| retrieved_on | TEXT |
| license | TEXT |
| sha256 | TEXT |
| scope_notes | TEXT |

## plants

| Field | PostgreSQL type / constraint |
|---|---|
| plant_id | TEXT PRIMARY KEY |
| accepted_scientific_name | TEXT NOT NULL |
| scientific_name_author | TEXT |
| preferred_common_name | TEXT |
| family | TEXT |
| taxon_rank | TEXT NOT NULL |
| parent_plant_id | TEXT REFERENCES plants(plant_id) DEFERRABLE INITIALLY DEFERRED |
| plant_form | TEXT |
| lifecycle | TEXT |
| description | TEXT |
| taxonomy_source_id | TEXT REFERENCES sources(source_id) |
| identity_review_status | TEXT NOT NULL CHECK(identity_review_status IN ('verified','needs_review')) |

## source_records

| Field | PostgreSQL type / constraint |
|---|---|
| source_record_id | TEXT PRIMARY KEY |
| source_id | TEXT NOT NULL REFERENCES sources(source_id) |
| original_record_id | TEXT NOT NULL |
| source_page | INTEGER |
| source_row | INTEGER |
| subset_status | TEXT CHECK(subset_status IN ('native','review','excluded','original')) |
| original_json | JSONB NOT NULL |

## plant_source_links

| Field | PostgreSQL type / constraint |
|---|---|
| source_record_id | TEXT PRIMARY KEY REFERENCES source_records(source_record_id) |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| match_status | TEXT NOT NULL CHECK(match_status IN ('verified','needs_review')) |
| match_method | TEXT NOT NULL |
| notes | TEXT |

## plant_names

| Field | PostgreSQL type / constraint |
|---|---|
| name_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| name | TEXT NOT NULL |
| name_type | TEXT NOT NULL |
| source_id | TEXT NOT NULL REFERENCES sources(source_id) |

## external_identifiers

| Field | PostgreSQL type / constraint |
|---|---|
| identifier_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| authority | TEXT NOT NULL |
| external_taxon_id | TEXT NOT NULL |
| source_id | TEXT REFERENCES sources(source_id) |

## regions

| Field | PostgreSQL type / constraint |
|---|---|
| region_id | TEXT PRIMARY KEY |
| region_name | TEXT NOT NULL |
| region_type | TEXT NOT NULL |
| external_region_code | TEXT |
| boundary_source_id | TEXT REFERENCES sources(source_id) |
| boundary_version | TEXT |
| coverage_precision | TEXT NOT NULL CHECK(coverage_precision IN ('confirmed','approximate','pending')) |
| geom | geometry(MultiPolygon,4326); GiST indexed |
| notes | TEXT |

## source_coverage

| Field | PostgreSQL type / constraint |
|---|---|
| coverage_id | TEXT PRIMARY KEY |
| source_id | TEXT NOT NULL REFERENCES sources(source_id) |
| region_id | TEXT NOT NULL REFERENCES regions(region_id) |
| coverage_role | TEXT NOT NULL |
| coverage_status | TEXT NOT NULL |
| notes | TEXT |

## regional_evidence

| Field | PostgreSQL type / constraint |
|---|---|
| evidence_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| region_id | TEXT NOT NULL REFERENCES regions(region_id) |
| evidence_type | TEXT NOT NULL CHECK(evidence_type IN ('native_classification','occurrence','planting_guidance')) |
| native_status | TEXT CHECK(native_status IN ('native','introduced','mixed','uncertain')) |
| occurrence_status | TEXT CHECK(occurrence_status IN ('present','historical','extirpated','uncertain')) |
| planting_status | TEXT |
| source_status_code | TEXT |
| source_record_id | TEXT NOT NULL REFERENCES source_records(source_record_id) |
| evidence_date | TEXT |
| review_status | TEXT NOT NULL |
| notes | TEXT |

## trait_claims

| Field | PostgreSQL type / constraint |
|---|---|
| claim_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| field_name | TEXT NOT NULL |
| value_json | JSONB NOT NULL |
| original_value | TEXT |
| source_record_id | TEXT NOT NULL REFERENCES source_records(source_record_id) |
| review_status | TEXT NOT NULL |
| qualification_notes | TEXT |

## growing_conditions

| Field | PostgreSQL type / constraint |
|---|---|
| plant_id | TEXT PRIMARY KEY REFERENCES plants(plant_id) |
| soil_ph_min | REAL |
| soil_ph_max | REAL |
| height_min_cm | REAL |
| height_max_cm | REAL |
| spread_min_cm | REAL |
| spread_max_cm | REAL |
| bloom_start_month | INTEGER |
| bloom_end_month | INTEGER |
| drought_tolerance | TEXT |
| maintenance_level | TEXT |
| spreading_behavior | TEXT |
| selection_provenance_json | JSONB NOT NULL |

## condition_values

| Field | PostgreSQL type / constraint |
|---|---|
| condition_value_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| field_name | TEXT NOT NULL CHECK(field_name IN ('sunlight','soil_texture','soil_moisture','drainage','flower_color')) |
| value | TEXT NOT NULL |
| source_record_id | TEXT NOT NULL REFERENCES source_records(source_record_id) |
| is_preferred | INTEGER NOT NULL CHECK(is_preferred IN (0,1)) |
| review_status | TEXT NOT NULL |

## original_plant_links

| Field | PostgreSQL type / constraint |
|---|---|
| original_plant_id | INTEGER PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| source_record_id | TEXT NOT NULL REFERENCES source_records(source_record_id) |
| review_status | TEXT NOT NULL |
| notes | TEXT |

## import_issues

| Field | PostgreSQL type / constraint |
|---|---|
| issue_id | TEXT PRIMARY KEY |
| source_record_id | TEXT REFERENCES source_records(source_record_id) |
| issue_type | TEXT NOT NULL |
| detail | TEXT NOT NULL |

## evidence_conflicts

| Field | PostgreSQL type / constraint |
|---|---|
| conflict_id | TEXT PRIMARY KEY |
| plant_id | TEXT NOT NULL REFERENCES plants(plant_id) |
| region_id | TEXT REFERENCES regions(region_id) |
| field_name | TEXT NOT NULL |
| source_record_ids_json | JSONB NOT NULL |
| detail | TEXT NOT NULL |

## Controlled values

- Identity/link status: verified, needs_review.
- Native status: native, introduced, mixed, uncertain; NULL for evidence that does not assess nativity.
- Occurrence: present, historical, extirpated, uncertain; NULL if not assessed.
- Evidence types: native_classification, occurrence, planting_guidance.
- Condition field names: sunlight, soil_texture, soil_moisture, drainage, flower_color.
- Sunlight values currently normalized to full_sun, partial_shade, shade; source hour definitions remain in the claims.
- Source assertions, inferred statuses and original unverified garden values retain separate review_status strings.
- Plant form may be broad in a taxonomic source. Do not manufacture finer grass/sedge distinctions without evidence.

Excluded raw records outside the native/original master are intentionally allowed to have no plant_source_links row. Native, review and original records all have an identity decision. Explicit introduced classifications for existing master taxa are attached as regional evidence; missing Kew range entries are not converted into introduced assertions.
