# Native-only source subsets

Six separate JSON subsets; original inputs are unchanged. These are source records, not a deduplicated central flora. VASCAN includes species and infraspecific taxa. The same plant can occur in several source files.

| Source | Native records | Review | Excluded |
|---|---:|---:|---:|
| vascan_ontario | 2442 | 45 | 1394 |
| kew_researched | 1 | 1 | 9 |
| trca_2025 | 956 | 148 | 873 |
| cvc_2021 | 782 | 6 | 340 |
| halton_2018 | 477 | 167 | 9 |
| toronto_2020 | 1087 | 28 | 822 |

Each source folder contains native.json and review.json. Each entry keeps its original source record plus decision_reason, native_regions, and a subset_record_id. Excluded records remain in the outer work/native-subsets/excluded directory, with reasons; originals are preserved under dependencies/source-data and data/regional.

## Rules

- VASCAN: accepted taxa with an explicit Ontario present/native distribution assertion. No inheritance from a subspecies to its parent species. Doubtful and absent/historical assertions go to review; introduced and excluded assertions stay out. Taxa without an Ontario assertion are outside the scope considered, not classified as non-native by absence.
- Kew: the 11 researched identities. One explicitly Ontario-native record (Sisyrinchium angustifolium) is retained. Original plant 89 remains under review because its literal name resolves to Eurasian Pulsatilla patens. Other researched taxa have no Ontario native-range entry in the checked Kew records; they are excluded from this subset.
- TRCA: L1-L5 retained. LX, LU, LU+ and L+? go to review. L+ excluded. Native rarity is retained; it does not establish general planting suitability.
- CVC: exact native status retained. Unknown or subspecies-dependent mixed statuses go to review; non-native excluded.
- Halton: abundance codes C/U/R are not a native boolean. Retention uses the native-list context, positive regional occurrence, a unique exact VASCAN Ontario-native match, and no introduced/uncertain/nurse-crop flags. This is a conservative inferred subset, not an independently explicit local-native assertion. Only the regions with positive codes are assigned. Rare plants remain flagged and are not automatically approved for planting. Provincial corroboration cannot prove nativity at every local site. Historical-name and rank mismatches remain in review; no fuzzy matches are used.
- Toronto: EXOTIC_NATIVE=N retained unless cultivation or historical/extirpated S-rank flags require review. U goes to review; E excluded. S? is uncertainty in conservation rank, not automatically uncertainty in native status. The original CSV contains mixed/garbled author encoding; a byte-preserving fallback is recorded and affected records flagged, without guessing repairs.

## Use and rebuild

Run `python scripts/data/build_native_subsets.py` from the repository root. Standard library only. Defaults read original archives outside the repository and existing regional JSON. Input hashes, editions and exact filtering rules are in manifest.json. Checks are in validation.json and tests/test_native_subsets.py.

If the local working SQLite database exists, the script refreshes additional native_subset_sources and native_subset_records tables. Existing plant, source and identity tables are preserved. This step neither creates PostGIS nor changes website recommendations. The subsequent central builder transforms these records into the operational PostgreSQL model; it does not simply copy the legacy subset tables. See ../../docs/SETUP.md.

The six native files contain 5,745 source records, with overlap between sources and taxonomic ranks. Local region boundaries and conflicting source assertions still need review before address-based recommendations.

Original source attribution and reuse terms continue to apply; this filtering does not grant a new licence.

Native/review payloads remain local and are Git-ignored pending reuse review. The public repository retains the manifests and rules.
