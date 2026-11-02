"""Check normalized identity, provenance, review safeguards and type preservation."""
from pathlib import Path
import json,sqlite3,unittest
ROOT=Path(__file__).resolve().parents[1]
class CentralDatabaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=ROOT/'data/database/native-plants-central.sqlite'
  if not p.exists():raise unittest.SkipTest('Local central snapshot is excluded from Git')
  cls.c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
 @classmethod
 def tearDownClass(cls):cls.c.close()
 def test_all_original_ids_preserved_and_uncertainty_not_cleared(self):
  self.assertEqual(self.c.execute('SELECT count(*) FROM original_plant_links').fetchone()[0],100)
  self.assertEqual(self.c.execute('SELECT review_status FROM original_plant_links WHERE original_plant_id=89').fetchone()[0],'needs_review')
  for ids in [(42,56),(66,68),(79,81),(76,91)]:
   plants=[self.c.execute('SELECT plant_id FROM original_plant_links WHERE original_plant_id=?',(i,)).fetchone()[0] for i in ids]
   self.assertEqual(plants[0],plants[1])
 def test_every_native_review_original_record_is_linked_and_excluded_audit_is_preserved(self):
  self.assertEqual(self.c.execute("SELECT count(*) FROM source_records s WHERE s.subset_status<>'excluded' AND NOT EXISTS (SELECT 1 FROM plant_source_links l WHERE l.source_record_id=s.source_record_id)").fetchone()[0],0)
  self.assertEqual(self.c.execute("SELECT count(*) FROM source_records WHERE subset_status='excluded'").fetchone()[0],3447)
  self.assertEqual(self.c.execute('PRAGMA foreign_key_check').fetchall(),[])
  self.assertEqual(self.c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
 def test_subspecies_are_not_collapsed_into_parent_species(self):
  self.assertGreater(self.c.execute("SELECT count(*) FROM plants WHERE taxon_rank IN ('subspecies','variety') AND parent_plant_id IS NOT NULL").fetchone()[0],0)
  self.assertEqual(self.c.execute('SELECT count(*) FROM plants WHERE plant_id=parent_plant_id').fetchone()[0],0)
 def test_native_candidates_need_clear_identity_and_current_native_evidence(self):
  self.assertEqual(self.c.execute("SELECT count(*) FROM native_candidates WHERE identity_review_status<>'verified'").fetchone()[0],0)
  self.assertEqual(self.c.execute("SELECT count(*) FROM native_candidates p WHERE NOT EXISTS (SELECT 1 FROM regional_evidence e JOIN plant_source_links l ON l.source_record_id=e.source_record_id WHERE e.plant_id=p.plant_id AND e.native_status='native' AND e.occurrence_status='present' AND e.review_status='accepted_source_assertion' AND l.match_status='verified')").fetchone()[0],0)
 def test_spatial_context_is_not_fabricated_for_study_areas(self):
  self.assertEqual(self.c.execute('SELECT count(*) FROM regions WHERE geometry_geojson IS NOT NULL').fetchone()[0],107)
  for rid in ['ontario','toronto_study','halton_inventory','hamilton_inventory']:
   geometry,status=self.c.execute('SELECT geometry_geojson,coverage_precision FROM regions WHERE region_id=?',(rid,)).fetchone()
   self.assertIsNone(geometry);self.assertEqual(status,'pending')
 def test_preferred_condition_values_do_not_union_different_source_claims(self):
  duplicates=self.c.execute('SELECT plant_id,field_name FROM condition_values WHERE is_preferred=1 GROUP BY plant_id,field_name HAVING count(distinct source_record_id)>1').fetchall()
  self.assertEqual(duplicates,[])
 def test_original_traits_remain_labelled_unverified(self):
  self.assertEqual(self.c.execute("SELECT count(*) FROM trait_claims t JOIN source_records s ON s.source_record_id=t.source_record_id WHERE s.source_id='original_catalogue' AND t.review_status<>'source_unverified'").fetchone()[0],0)
  self.assertGreater(self.c.execute('SELECT count(*) FROM evidence_conflicts').fetchone()[0],0)
if __name__=='__main__':unittest.main()
