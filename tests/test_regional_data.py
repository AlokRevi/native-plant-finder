"""Published-source reconciliation and preservation checks; no network calls."""
import collections,json,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(source):return json.loads((ROOT/'data/regional'/f'{source}.json').read_text(encoding='utf8'))
class RegionalDataTests(unittest.TestCase):
 def test_trca_reconciles_to_printed_summary(self):
  data=rows('trca_2025');ranks=collections.Counter(r['local_rank'] for r in data)
  self.assertEqual(len(data),1977)
  self.assertEqual(sum(ranks[r] for r in ['L1','L2','L3','L4','L5']),956)
  self.assertEqual(ranks['L+']+ranks['L+?'],915)
  self.assertEqual(ranks['LX'],94)
  self.assertEqual(ranks['LU']+ranks['LU+'],12)
 def test_cvc_uncertainty_is_not_lost(self):
  data=rows('cvc_2021');states=collections.Counter(r['native_status_as_published'] for r in data)
  self.assertEqual(states,{'native':782,'non-native':340,'unknown':3,'Native and non-native (depends on subspecies)':3})
  raspberry=next(r for r in data if r['scientific_name']=='Rubus idaeus')
  self.assertEqual(raspberry['source_continuation_pages'],[51])
 def test_halton_colours_and_multiline_names_survive(self):
  data=rows('halton_2018')
  tree=next(r for r in data if r['scientific_name']=='Celtis occidentalis')
  self.assertEqual(tree['halton_status_2006'],'R')
  self.assertIn(0.753,tree['cell_styles']['halton_status_2006']['background_colors'])
  grass=next(r for r in data if r['scientific_name']=='Agrostis stolonifera')
  self.assertEqual(grass['plant_group'],'Grasses')
  self.assertEqual(grass['common_name'],'Creeping Bent Grass')
  self.assertTrue(any(r['scientific_name']=='Helianthus annuus ssp. annuus' for r in data))
 def test_all_records_have_unique_ids_and_page_provenance(self):
  allrows=sum([rows(s) for s in ['trca_2025','cvc_2021','halton_2018']],[])
  self.assertEqual(len(allrows),len({r['record_id'] for r in allrows}))
  self.assertTrue(all(r['source_pdf_page']>0 and r['scientific_name'] and r['source_cells'] for r in allrows))
 def test_working_database_preserves_catalogue_and_evidence(self):
  p=ROOT/'data/database/plant-project.db'
  if not p.exists():self.skipTest('Local database is intentionally excluded from Git')
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as c:
   self.assertEqual(c.execute('select count(*) from plantlist').fetchone()[0],100)
   self.assertEqual(c.execute('select count(*) from regional_plant_records').fetchone()[0],3758)
   self.assertEqual(c.execute('select identity_match_status from plant_taxonomy where plant_id=89').fetchone()[0],'needs review')
   self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok')
   self.assertEqual(c.execute('pragma foreign_key_check').fetchall(),[])
if __name__=='__main__':unittest.main()
