# Plant-to-VASCAN identity crosswalk

Reviewed 100 original records / 96 distinct scientific names: {'verified': 89, 'needs review': 3, 'unmatched': 8}.

Verified means a name-level match in the downloaded VASCAN snapshot. It does not establish Ontario native status or growing suitability. Original database was read only.

## Method

Matched species-rank canonical names exactly after removing the declared authorship from VASCAN scientific names. Did not use fuzzy matches or common names to assign identities. Excluded hybrid/infraspecific names from species matching. Followed acceptedNameUsageID and validated accepted targets. Reviewed ambiguous, synonym, duplicate-target and unmatched cases against archive records. Unresolved IDs remain NULL.

VASCAN publication: 2026-08-04. DOI: https://doi.org/10.5886/zw3aqw. CC0 1.0. Full candidate evidence is in the JSON file.

## Review findings

- ID 39, Penstemon laevigatus: **needs review**. Only narrower infraspecific names match. A broad species cannot be equated automatically with a subspecies or variety. VASCAN lists calycosus subspecies/variety as synonyms of Penstemon calycosus (24968); do not replace Penstemon laevigatus without confirming intent.
- ID 45, Sisyrinchium angustifolium: **needs review**. Accepted name 6197 exists, but the same authorless name also has a misapplied usage (16676) resolving to 6208, 6210, or 6212. Confirm intended identity before assigning an ID.
- ID 54, Desmodium glutinosum: **verified**. Accepted: Hylodesmum glutinosum (27746). Verified name-level identity in downloaded VASCAN; not verification of a specimen, native status, or garden suitability. Original name is a VASCAN synonym of the accepted name.
- ID 55, Parthenium integrifolium: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 57, Coreopsis palmata: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 62, Ruellia humilis: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 70, Heuchera villosa: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 72, Phlox glaberrima: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 82, Eryngium yuccifolium: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 85, Brickellia eupatorioides: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.
- ID 87, Anemone canadensis: **verified**. Accepted: Anemonastrum canadense (30375). Verified name-level identity in downloaded VASCAN; not verification of a specimen, native status, or garden suitability. Original name is a VASCAN synonym of the accepted name.
- ID 89, Anemone patens: **needs review**. Only narrower infraspecific names match. A broad species cannot be equated automatically with a subspecies or variety. VASCAN lists multifida/nutttalliana usages under Pulsatilla nuttalliana (30377); confirm intended taxon. Original common name is insufficient.
- ID 97, Scutellaria elliptica: **unmatched**. No exact species-level canonical name in this VASCAN snapshot; this does not establish absence from Canada.

## Duplicate names retained

- Heliopsis helianthoides: original IDs [42, 56]; separate original records retained.
- Elymus canadensis: original IDs [66, 68]; separate original records retained.
- Baptisia australis: original IDs [76, 91]; separate original records retained.
- Campanulastrum americanum: original IDs [79, 81]; separate original records retained.

## All original records

| Plant ID | Original scientific name | Accepted VASCAN name | VASCAN ID | Status |
|---|---|---|---|---|
| 1 | Asclepias tuberosa | Asclepias tuberosa | 2713 | verified |
| 2 | Asclepias syriaca | Asclepias syriaca | 2711 | verified |
| 3 | Asclepias incarnata | Asclepias incarnata | 2704 | verified |
| 4 | Monarda fistulosa | Monarda fistulosa | 6417 | verified |
| 5 | Rudbeckia hirta | Rudbeckia hirta | 3388 | verified |
| 6 | Symphyotrichum novae-angliae | Symphyotrichum novae-angliae | 3561 | verified |
| 7 | Iris versicolor | Iris versicolor | 6188 | verified |
| 8 | Lobelia cardinalis | Lobelia cardinalis | 4182 | verified |
| 9 | Veronicastrum virginicum | Veronicastrum virginicum | 7348 | verified |
| 10 | Schizachyrium scoparium | Schizachyrium scoparium | 7944 | verified |
| 11 | Aquilegia canadensis | Aquilegia canadensis | 8444 | verified |
| 12 | Echinacea purpurea | Echinacea purpurea | 3060 | verified |
| 13 | Ratibida pinnata | Ratibida pinnata | 3382 | verified |
| 14 | Symphyotrichum laeve | Symphyotrichum laeve | 3545 | verified |
| 15 | Solidago speciosa | Solidago speciosa | 9884 | verified |
| 16 | Solidago canadensis | Solidago canadensis | 3445 | verified |
| 17 | Verbena hastata | Verbena hastata | 9462 | verified |
| 18 | Eutrochium purpureum | Eutrochium purpureum | 3167 | verified |
| 19 | Eupatorium perfoliatum | Eupatorium perfoliatum | 3144 | verified |
| 20 | Lobelia siphilitica | Lobelia siphilitica | 4186 | verified |
| 21 | Lupinus perennis | Lupinus perennis | 5817 | verified |
| 22 | Geum triflorum | Geum triflorum | 8775 | verified |
| 23 | Silphium perfoliatum | Silphium perfoliatum | 3431 | verified |
| 24 | Silphium laciniatum | Silphium laciniatum | 3429 | verified |
| 25 | Silphium terebinthinaceum | Silphium terebinthinaceum | 3433 | verified |
| 26 | Geranium maculatum | Geranium maculatum | 6042 | verified |
| 27 | Tiarella cordifolia | Tiarella cordifolia | 9311 | verified |
| 28 | Asarum canadense | Asarum canadense | 2698 | verified |
| 29 | Maianthemum racemosum | Maianthemum racemosum | 2738 | verified |
| 30 | Polygonatum biflorum | Polygonatum biflorum | 2745 | verified |
| 31 | Monarda punctata | Monarda punctata | 6421 | verified |
| 32 | Penstemon digitalis | Penstemon digitalis | 7273 | verified |
| 33 | Penstemon hirsutus | Penstemon hirsutus | 7282 | verified |
| 34 | Oenothera biennis | Oenothera biennis | 6808 | verified |
| 35 | Liatris spicata | Liatris spicata | 3290 | verified |
| 36 | Liatris cylindracea | Liatris cylindracea | 3283 | verified |
| 37 | Senna hebecarpa | Senna hebecarpa | 5901 | verified |
| 38 | Ceanothus americanus | Ceanothus americanus | 8587 | verified |
| 39 | Penstemon laevigatus |  |  | needs review |
| 40 | Agastache foeniculum | Agastache foeniculum | 6351 | verified |
| 41 | Achillea millefolium | Achillea millefolium | 2768 | verified |
| 42 | Heliopsis helianthoides | Heliopsis helianthoides | 3210 | verified |
| 43 | Helenium autumnale | Helenium autumnale | 3185 | verified |
| 44 | Liatris aspera | Liatris aspera | 3282 | verified |
| 45 | Sisyrinchium angustifolium |  |  | needs review |
| 46 | Fragaria virginiana | Fragaria virginiana | 8758 | verified |
| 47 | Caltha palustris | Caltha palustris | 8452 | verified |
| 48 | Oenothera fruticosa | Oenothera fruticosa | 6815 | verified |
| 49 | Angelica atropurpurea | Angelica atropurpurea | 2535 | verified |
| 50 | Chelone glabra | Chelone glabra | 7220 | verified |
| 51 | Liatris pycnostachya | Liatris pycnostachya | 3288 | verified |
| 52 | Lespedeza capitata | Lespedeza capitata | 5763 | verified |
| 53 | Desmodium canadense | Desmodium canadense | 5717 | verified |
| 54 | Desmodium glutinosum | Hylodesmum glutinosum | 27746 | verified |
| 55 | Parthenium integrifolium |  |  | unmatched |
| 56 | Heliopsis helianthoides | Heliopsis helianthoides | 3210 | verified |
| 57 | Coreopsis palmata |  |  | unmatched |
| 58 | Coreopsis lanceolata | Coreopsis lanceolata | 3013 | verified |
| 59 | Conoclinium coelestinum | Conoclinium coelestinum | 3009 | verified |
| 60 | Eupatorium serotinum | Eupatorium serotinum | 3145 | verified |
| 61 | Eutrochium fistulosum | Eutrochium fistulosum | 3161 | verified |
| 62 | Ruellia humilis |  |  | unmatched |
| 63 | Deschampsia cespitosa | Deschampsia cespitosa | 7531 | verified |
| 64 | Bouteloua curtipendula | Bouteloua curtipendula | 7441 | verified |
| 65 | Bouteloua gracilis | Bouteloua gracilis | 7442 | verified |
| 66 | Elymus canadensis | Elymus canadensis | 7588 | verified |
| 67 | Elymus hystrix | Elymus hystrix | 7735 | verified |
| 68 | Elymus canadensis | Elymus canadensis | 7588 | verified |
| 69 | Heuchera richardsonii | Heuchera richardsonii | 9241 | verified |
| 70 | Heuchera villosa |  |  | unmatched |
| 71 | Phlox divaricata | Phlox divaricata | 8060 | verified |
| 72 | Phlox glaberrima |  |  | unmatched |
| 73 | Phlox maculata | Phlox maculata | 8064 | verified |
| 74 | Gentiana andrewsii | Gentiana andrewsii | 5994 | verified |
| 75 | Gentiana clausa | Gentiana clausa | 5996 | verified |
| 76 | Baptisia australis | Baptisia australis | 5697 | verified |
| 77 | Baptisia tinctoria | Baptisia tinctoria | 5698 | verified |
| 78 | Agastache scrophulariifolia | Agastache scrophulariifolia | 6353 | verified |
| 79 | Campanulastrum americanum | Campanulastrum americanum | 14091 | verified |
| 80 | Campanula rotundifolia | Campanula rotundifolia | 4171 | verified |
| 81 | Campanulastrum americanum | Campanulastrum americanum | 14091 | verified |
| 82 | Eryngium yuccifolium |  |  | unmatched |
| 83 | Dalea purpurea | Dalea purpurea | 5714 | verified |
| 84 | Dalea candida | Dalea candida | 5711 | verified |
| 85 | Brickellia eupatorioides |  |  | unmatched |
| 86 | Clinopodium vulgare | Clinopodium vulgare | 6368 | verified |
| 87 | Anemone canadensis | Anemonastrum canadense | 30375 | verified |
| 88 | Anemone virginiana | Anemone virginiana | 8440 | verified |
| 89 | Anemone patens |  |  | needs review |
| 90 | Geranium bicknellii | Geranium bicknellii | 6037 | verified |
| 91 | Baptisia australis | Baptisia australis | 5697 | verified |
| 92 | Thalictrum dasycarpum | Thalictrum dasycarpum | 8572 | verified |
| 93 | Thalictrum dioicum | Thalictrum dioicum | 8573 | verified |
| 94 | Aralia racemosa | Aralia racemosa | 2686 | verified |
| 95 | Prunella vulgaris | Prunella vulgaris | 6437 | verified |
| 96 | Scutellaria galericulata | Scutellaria galericulata | 6455 | verified |
| 97 | Scutellaria elliptica |  |  | unmatched |
| 98 | Scrophularia marilandica | Scrophularia marilandica | 9321 | verified |
| 99 | Nuttallanthus canadensis | Nuttallanthus canadensis | 7263 | verified |
| 100 | Physostegia virginiana | Physostegia virginiana | 9888 | verified |
