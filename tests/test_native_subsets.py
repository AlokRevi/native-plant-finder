"""Check native-only outputs against source classifications and original snapshots."""
import hashlib,json,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/native-only'
def load(sid,state):return json.loads((DATA/sid/(state+'.json')).read_text(encoding='utf8'))
class NativeSubsetTests(unittest.TestCase):
 def test_every_source_is_partitioned_and_inputs_unchanged(self):
  manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf8'))
  self.assertEqual(len(manifest['sources']),6)
  for source in manifest['sources']:
   self.assertEqual(sum(source['counts'].values()),source['input_records_considered'])
   for state in ['native','review']:
    records=load(source['source_id'],state)
    self.assertEqual(len(records),source['counts'][state])
    self.assertEqual(len({r['subset_record_id'] for r in records}),len(records))
   p=ROOT.parent/source['input_file']
   if p.exists():self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),source['input_sha256'])
 def test_vascan_requires_explicit_ontario_native_evidence(self):
  for r in load('vascan_ontario','native'):
   source=r['source_record'];d=source['ontario_distribution']
   self.assertEqual(source['taxonomicStatus'],'accepted')
   self.assertEqual((d['locationID'],d['occurrenceStatus'],d['establishmentMeans']),('ISO3166-2:CA-ON','present','native'))
 def test_regional_uncertainty_and_extirpation_are_not_native(self):
  self.assertEqual({r['source_record']['local_rank'] for r in load('trca_2025','native')},{'L1','L2','L3','L4','L5'})
  self.assertTrue(all(r['source_record']['native_status_as_published']=='native' for r in load('cvc_2021','native')))
  for r in load('toronto_2020','native'):
   s=r['source_record'];self.assertEqual(s['EXOTIC_NATIVE'],'N')
   self.assertNotIn(s['S_RANK'],['SX','SH']);self.assertFalse(s['Cultivated'].strip())
 def test_kew_keeps_scope_and_identity_flag(self):
  self.assertEqual([r['source_record']['original_plant_id'] for r in load('kew_researched','native')],[45])
  self.assertEqual([r['source_record']['original_plant_id'] for r in load('kew_researched','review')],[89])
 def test_halton_keeps_region_qualification_and_corroboration(self):
  for r in load('halton_2018','native'):
   s=r['source_record'];self.assertEqual(len(s['supporting_vascan_accepted_ids']),1)
   self.assertTrue(r['native_regions'])
   for name,key in [('Halton inventory area','halton_status_2006'),('Hamilton inventory area','hamilton_status_2014')]:
    self.assertEqual(name in r['native_regions'],s[key] in ['C','U','R'])
    self.assertNotIn(s[key],['I','H?'])
 def test_database_contains_all_six_subsets_without_expanding_original_list(self):
  p=ROOT/'data/database/plant-project.db'
  if not p.exists():self.skipTest('Local database excluded from Git')
  m=json.loads((DATA/'manifest.json').read_text())
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as c:
   self.assertEqual(c.execute('select count(*) from native_subset_sources').fetchone()[0],6)
   self.assertEqual(c.execute("select count(*) from native_subset_records where subset_status='native'").fetchone()[0],m['native_total'])
   self.assertEqual(c.execute('select count(*) from plantlist').fetchone()[0],100)
   self.assertEqual(c.execute('select identity_match_status from plant_taxonomy where plant_id=89').fetchone()[0],'needs review')
   self.assertEqual(c.execute('pragma foreign_key_check').fetchall(),[])
if __name__=='__main__':unittest.main()
