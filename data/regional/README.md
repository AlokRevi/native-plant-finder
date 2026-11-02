# Regional plant evidence datasets

These JSON tables preserve the three published PDF lists, including their native, introduced and uncertain records. Recommendation queries apply separate native-status rules.

| File | Source edition | Records |
|---|---|---:|
| trca_2025.json | May 2025 TRCA ranks | 1,977 |
| cvc_2021.json | 2021 update, February 2022 report | 1,128 |
| halton_2018.json | August 2018 | 653 |

Halton has 652 distinct scientific-name strings: Chelone glabra occurs in more than one vegetation group and both records are intentionally retained. The other tables have unique scientific-name strings within each source.

## Shared fields

- record_id: stable within this exact PDF edition, using source, PDF page and extracted table-row number. Not a permanent botanical taxon identifier.
- scientific_name/common_name: as printed, with whitespace collapsed. Names retain the published spelling.
- source_id, source_pdf_page: source registry join and one-based physical PDF page for audit.
- source_table_row/source_cells: extraction references and printed cell values.

## Source-specific fields

TRCA: family, species_code, grid_count_2010_2024, local_occurrence_score_2025, population_trend_score, habitat_dependence_score, sensitivity_to_development_score, total_score, local_rank, score_date. Scores stay as source strings, including ns. L1-L3 regional concern; L4 urban concern; L5 no current concern; L+ introduced; L+? likely introduced; LX locally extinct. LU/LU+ occurrences are unproven. No score is a garden success score.

CVC: plant_group, last_year_observed, native_status_as_published. All statuses retained: 782 native, 340 non-native, 3 unknown, 3 mixed depending on subspecies. Rubus idaeus has status text continued onto the next page; source_continuation_pages preserves that reference. The list concerns natural/naturalized occurrence in CVC jurisdiction, not cultivated-only specimens. A source's native label must be interpreted within its methods; it is not a precise natural-range polygon.

Halton: plant_group, halton_status_2006, hamilton_status_2014, coefficient_of_wetness, drought_tolerance, salt_tolerance, shade_tolerance, root_type, rooting_ability, stormwater_pond. C common, U uncommon, R rare, I introduced, H? further review. Empty and dash values are not false or zero. Shade codes: S full sun; P part sun/shade; D full shade; compound codes are ranges. Preserve the document's own hour definitions rather than mixing them with another source's thresholds. cell_styles records background fill colours by column, including grey/brown restrictions and green nurse-crop highlighting; colours have not been converted into unconditional approval. Nursery-crop species can be introduced, even though the title says native species list.

## Registry, database and rebuild

sources.json contains source URLs, editions, SHA-256 hashes, coverage descriptions and boundary keys. Boundary keys link to the central region model. The operational database contains authority and ecodistrict polygons; several inventory/study extents remain unverified. See ../../docs/CENTRAL_DATABASE.md. validation.json contains page and record counts.

regional-datasets.postgresql.sql imports the same evidence into PostgreSQL JSONB tables. It does not require PostGIS until geometries are added. SQL uses upserts; for a changed source edition use a new source_id and retain version history.

The SQLite working database is ../database/plant-project.db. It contains regional_sources, regional_plant_records and plant_regional_links in addition to the original 100 plants and identity crosswalks. The 135 original-plant links use exact original/accepted scientific-name strings only, so missing links do not establish absence. Subspecies are not automatically equated to broad species. Identity-review flags must still be applied before recommendations.

Rebuild with scripts/data/build_regional_datasets.py. See ../../docs/DATA_PIPELINE.md. Extraction supports these three exact PDF layouts; it is not a general PDF table parser.

## Attribution and reuse

Original publishers retain their terms. Public availability is not proof of a redistribution licence. Source licences for these three PDFs have not been verified; no new licence is granted to third-party data here. Retain citations and check the publishers' terms before public redistribution. The original PDFs remain outside the repository.

Source-derived JSON and regional import SQL are excluded from the public Git upload pending reuse review. See ../../DATA_SOURCES.md. Local files are preserved.
