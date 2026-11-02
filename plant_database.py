"""Read-only PostgreSQL catalogue queries and regional selection."""
from pathlib import Path
import json,os,sys,threading,time

ROOT=Path(__file__).resolve().parent
packages=ROOT.parent/'dependencies/python-packages'
if packages.exists():sys.path.insert(0,str(packages))

class DatabaseUnavailable(ConnectionError):pass

_lock=threading.Lock()
_cache=None
_cache_time=0.0

def connect():
 try:
  import psycopg
  from psycopg.rows import dict_row
  url=os.environ.get('NATIVE_PLANT_DATABASE_URL')
  if url:return psycopg.connect(url,connect_timeout=4,row_factory=dict_row)
  path=Path(os.environ.get('NATIVE_PLANT_DB_CONFIG',str(ROOT.parent/'local/database.json')))
  cfg=json.loads(path.read_text(encoding='utf8'))
  # Require the reader account from the local configuration.
  return psycopg.connect(host=cfg['host'],port=cfg['port'],dbname=cfg['database'],user=cfg['reader_user'],password=cfg['reader_password'],connect_timeout=4,row_factory=dict_row)
 except Exception as exc:raise DatabaseUnavailable('The plant database is unavailable. Start the local database and try again.') from exc

CATALOGUE_SQL="""
WITH cond AS (
 SELECT plant_id,jsonb_agg(jsonb_build_object('field',field_name,'value',value,'quality',review_status)) AS items
 FROM native_plants.condition_values WHERE is_preferred=1 GROUP BY plant_id
), evidence AS (
 SELECT e.plant_id,jsonb_agg(jsonb_build_object('region_id',e.region_id,'native',e.native_status,'occurrence',e.occurrence_status,'review',e.review_status,'match',l.match_status,'kind',e.evidence_type,'source',s.title,'url',s.url)) AS items
 FROM native_plants.regional_evidence e
 JOIN native_plants.plant_source_links l ON l.source_record_id=e.source_record_id
 JOIN native_plants.source_records sr ON sr.source_record_id=e.source_record_id
 JOIN native_plants.sources s ON s.source_id=sr.source_id GROUP BY e.plant_id
), drought AS (
 SELECT plant_id,jsonb_agg(value_json) AS items FROM native_plants.trait_claims
 WHERE field_name='drought_tolerance' GROUP BY plant_id
)
SELECT p.*,g.height_max_cm,g.drought_tolerance,COALESCE(cond.items,'[]'::jsonb) AS conditions,
 COALESCE(evidence.items,'[]'::jsonb) AS evidence,COALESCE(drought.items,'[]'::jsonb) AS drought_claims
FROM native_plants.native_candidates p
LEFT JOIN native_plants.growing_conditions g ON g.plant_id=p.plant_id
LEFT JOIN cond ON cond.plant_id=p.plant_id LEFT JOIN evidence ON evidence.plant_id=p.plant_id
LEFT JOIN drought ON drought.plant_id=p.plant_id
ORDER BY lower(COALESCE(p.preferred_common_name,p.accepted_scientific_name)),p.plant_id
"""

def catalogue():
 global _cache,_cache_time
 with _lock:
  if _cache is not None and time.monotonic()-_cache_time<30:return _cache
  try:
   with connect() as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    conn.execute("SET LOCAL statement_timeout='10s'")
    data=conn.execute(CATALOGUE_SQL).fetchall()
   _cache=data;_cache_time=time.monotonic();return data
  except DatabaseUnavailable:raise
  except Exception as exc:raise DatabaseUnavailable('Plant records could not be loaded. Check the local database and try again.') from exc

def location_regions(latitude,longitude):
 if latitude is None:return [],set()
 try:
  with connect() as conn:
   conn.execute('SET TRANSACTION READ ONLY')
   conn.execute("SET LOCAL statement_timeout='5s'")
   regions=conn.execute("SELECT region_id,region_name,region_type,external_region_code FROM native_plants.regions WHERE ST_Covers(geom,ST_SetSRID(ST_Point(%s,%s),4326)) ORDER BY region_type,region_name",(longitude,latitude)).fetchall()
   ids=[r['region_id'] for r in regions]
   scopes=conn.execute("SELECT DISTINCT region_id FROM native_plants.source_coverage WHERE region_id=ANY(%s) AND coverage_role='assertion_scope' AND coverage_status='documented_scope'",(ids,)).fetchall() if ids else []
  return regions,{r['region_id'] for r in scopes}
 except DatabaseUnavailable:raise
 except Exception as exc:raise DatabaseUnavailable('Regional plant information could not be loaded. Try again shortly.') from exc

def select_evidence(rows,local_scopes):
 """Prefer explicit mapped local native evidence; otherwise use Ontario evidence.

 Historical/introduced/mixed assertions in the chosen scope block a candidate.
 Halton jurisdiction polygons are excluded as substitutes for inventory extents.
 """
 scope=local_scopes or {'ontario'};selected=[]
 for plant in rows:
  records=[e for e in plant['evidence'] if e['region_id'] in scope and e['match']=='verified']
  blocked=any(e['native'] in ['introduced','mixed'] or e['occurrence'] in ['extirpated','historical'] for e in records)
  positive=[e for e in records if e['kind']=='native_classification' and e['native']=='native' and e['review']=='accepted_source_assertion' and e['occurrence'] in ['present',None]]
  if positive and not blocked:selected.append((plant,positive))
 return selected

def normalized_conditions(row):
 result={f:[] for f in ['sunlight','soil_texture','soil_moisture','flower_color']}
 for value in row['conditions']:
  if value['field'] in result and value['value'] not in result[value['field']]:result[value['field']].append(value['value'])
 return result

def drought_tolerant(row):
 if row.get('drought_tolerance')=='tolerant':return True
 codes=[str(v).upper() for v in row.get('drought_claims',[])]
 return bool(codes) and any(v in ['H','T'] for v in codes) and not any('L' in v or 'M' in v for v in codes)

def matches(row,chosen):
 c=normalized_conditions(row)
 for field,key,mapping in [('sun','sunlight',{'full':['full_sun'],'partial':['partial_shade'],'shade':['shade']}),('soil','soil_texture',{'sandy':['sand'],'loamy':['loam'],'clay':['clay']}),('moisture','soil_moisture',{'dry':['dry'],'average':['average'],'moist':['moist','wet']})]:
  if chosen.get(field) and not set(mapping[chosen[field]])&set(c[key]):return False
 if chosen.get('form') and chosen['form']!=row.get('plant_form'):return False
 if chosen.get('lifecycle') and chosen['lifecycle']!=row.get('lifecycle'):return False
 family=row.get('family') or ''
 flowers='nonflowering' if family in {'Pinaceae','Cupressaceae','Taxaceae','Ginkgoaceae','Sciadopityaceae'} else 'flowering' if c['flower_color'] else None
 if chosen.get('flowers') and chosen['flowers']!=flowers:return False
 if chosen.get('irrigation')=='no' and not drought_tolerant(row):return False
 return True

def card(row,evidence,local):
 c=normalized_conditions(row);sunmap={'full_sun':'full','partial_shade':'partial','shade':'shade'};soilmap={'sand':'sandy','loam':'loamy','clay':'clay'}
 name=row.get('preferred_common_name') or row['accepted_scientific_name']
 uncertain=any(v['quality']=='source_unverified' for v in row['conditions'])
 quality='Some garden conditions come from the original catalogue and still need verification.' if uncertain else 'Missing growing conditions are shown as not recorded.'
 return dict(id=row['plant_id'],common_name=name,scientific_name=row['accepted_scientific_name'],form=row.get('plant_form'),lifecycle=row.get('lifecycle'),
   sun=[sunmap.get(v,v) for v in c['sunlight']],soil=[soilmap.get(v,v) for v in c['soil_texture']],moisture=c['soil_moisture'],drought_tolerant=drought_tolerant(row),height_max_cm=row.get('height_max_cm'),
   summary='Documented as native in this region.' if local else 'Ontario native; local status unverified.',details=quality,source_url=evidence[0]['url'],sources=list({(e['source'],e['url']) for e in evidence}),image=None)
