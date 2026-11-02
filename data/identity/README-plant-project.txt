Identity preparation notes
Runtime setup: ../../docs/SETUP.md.
These notes describe the SQLite identity preparation stage.

Plant project working database
Created: 2026-10-30

plant-project.db is a SQLite working copy of the original plants.db, with original tables and plant IDs preserved.
The operational database uses PostgreSQL/PostGIS; plant-project.db is a separate SQLite working copy.

Added tables:
- plant_vascan_crosswalk: all 100 original records, with 89 verified VASCAN identities, 3 requiring review, 8 unmatched in VASCAN.
- plant_kew_crosswalk: the 8 VASCAN-unmatched plants verified against Kew POWO. Kew IDs are full IPNI LSIDs used by POWO, not VASCAN IDs.
- plant_taxonomy view: combined identity information for all 100 records, including 97 verified and 3 requiring review.

Coreopsis palmata is retained as the original name; its Kew accepted name is Anacis palmata.
The VASCAN unmatched statuses remain unchanged because Kew matches do not create VASCAN matches.
Native-region polygons and garden suitability are not established by these identity links.

PostgreSQL import:
Import the original plantlist table first. Run plant-vascan-crosswalk.sql, then plant-kew-crosswalk.sql once in the destination database. These scripts create new tables and will stop if the tables already exist.
Each Kew row includes its source URL and review date. Kew POWO credits the IPNI and World Checklist of Vascular Plants 2026; its name/backbone data pages specify CC BY 3.0.

Update: three additional Kew links added (39,45,89), bringing Kew links to 11 and name links to all 100 records. Combined identity status is 99 verified / 1 needs review. plant_identity_review retains ID 89 for intended-identity review despite its verified literal name link. The plant_taxonomy view exposes this flag. VASCAN review statuses are unchanged. Apply plant-kew-additional-three.sql after the initial 8-row Kew SQL for PostgreSQL. JSON now contains all 11 Kew links.
