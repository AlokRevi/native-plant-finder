# Data sources and publication scope

This repository shares application code, schemas, processing scripts, source registries and documentation. It does not bundle a ready-to-run plant database. Source-derived record files and the original catalogue are excluded from the default Git upload while reuse terms remain unresolved. Existing local copies are preserved.

| Source | Reference | Scope / terms status |
|---|---|---|
| VASCAN | https://data.canadensys.net/ipt/resource?r=vascan | Ontario assertions; local metadata records CC0 1.0; verify the downloaded edition's terms |
| Kew Plants of the World Online | https://powo.science.kew.org/ | Eleven researched identities, not a complete Kew download; distinguish backbone terms from POWO page content |
| Toronto and Region Conservation Authority | https://trca.ca/conservation/terrestrial-ecosystems/ranks-and-scores/ | 2025 flora ranks; redistribution permission not established |
| Credit Valley Conservation | https://cvc.ca/document/credit-river-watershed-plant-species-list/ | 2021 checklist; redistribution permission not established |
| Conservation Halton | https://haltonmastergardeners.com/wp-content/uploads/2019/02/native_species_list_aug2018.pdf | 2018 planting list with separate regional evidence; redistribution permission not established |
| Toronto checklist / Dryad | https://datadryad.org/dataset/doi:10.5061/dryad.1ns1rn8sg | Local metadata records CC0 1.0; verify the exact download and citation |
| Land Information Ontario | https://data.ontario.ca/ | CAADMIN and ECODISTR snapshots; confirm archive-specific Open Government Licence–Ontario terms |
| Original 100-plant catalogue | Locally supplied plants.db | Origin and redistribution permission not established; garden claims remain unverified |

Exact PDF URLs, filenames, editions, hashes and coverage notes are in data/regional/sources.json. Other input filenames, URLs and filtering rules are in data/native-only/manifest.json. The registries describe the downloaded snapshots. Licence labels above are copied from the project metadata and require confirmation against the source terms.

Redistribution of excluded datasets and generated SQL requires confirmation of the source permissions and attribution requirements. The project code licence does not cover third-party data.

The browser uses Leaflet, OpenStreetMap tiles and Nominatim. Retain existing attribution and follow the service policies linked in README.md. Submitted addresses go to Nominatim; the application does not save them to disk.
