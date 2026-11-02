"""Build a normalized central catalogue and a PostgreSQL/PostGIS import.

Standard library only. Source snapshots are read-only. The SQLite build is a
portable inspection/staging copy; PostgreSQL is the spatial operational database.
"""
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
from datetime import date
import argparse,collections,csv,hashlib,io,json,re,sqlite3,zipfile,os

TABLES={
 'sources': [('source_id','TEXT PRIMARY KEY'),('title','TEXT NOT NULL'),('publisher','TEXT'),('url','TEXT'),('edition','TEXT'),('retrieved_on','TEXT'),('license','TEXT'),('sha256','TEXT'),('scope_notes','TEXT')],
 'plants': [('plant_id','TEXT PRIMARY KEY'),('accepted_scientific_name','TEXT NOT NULL'),('scientific_name_author','TEXT'),('preferred_common_name','TEXT'),('family','TEXT'),('taxon_rank','TEXT NOT NULL'),('parent_plant_id','TEXT REFERENCES plants(plant_id) DEFERRABLE INITIALLY DEFERRED'),('plant_form','TEXT'),('lifecycle','TEXT'),('description','TEXT'),('taxonomy_source_id','TEXT REFERENCES sources(source_id)'),('identity_review_status',"TEXT NOT NULL CHECK(identity_review_status IN ('verified','needs_review'))")],
 'source_records': [('source_record_id','TEXT PRIMARY KEY'),('source_id','TEXT NOT NULL REFERENCES sources(source_id)'),('original_record_id','TEXT NOT NULL'),('source_page','INTEGER'),('source_row','INTEGER'),('subset_status',"TEXT CHECK(subset_status IN ('native','review','excluded','original'))"),('original_json','TEXT NOT NULL')],
 'plant_source_links': [('source_record_id','TEXT PRIMARY KEY REFERENCES source_records(source_record_id)'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('match_status',"TEXT NOT NULL CHECK(match_status IN ('verified','needs_review'))"),('match_method','TEXT NOT NULL'),('notes','TEXT')],
 'plant_names': [('name_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('name','TEXT NOT NULL'),('name_type','TEXT NOT NULL'),('source_id','TEXT NOT NULL REFERENCES sources(source_id)')],
 'external_identifiers': [('identifier_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('authority','TEXT NOT NULL'),('external_taxon_id','TEXT NOT NULL'),('source_id','TEXT REFERENCES sources(source_id)')],
 'regions': [('region_id','TEXT PRIMARY KEY'),('region_name','TEXT NOT NULL'),('region_type','TEXT NOT NULL'),('external_region_code','TEXT'),('boundary_source_id','TEXT REFERENCES sources(source_id)'),('boundary_version','TEXT'),('coverage_precision',"TEXT NOT NULL CHECK(coverage_precision IN ('confirmed','approximate','pending'))"),('geometry_geojson','TEXT'),('notes','TEXT')],
 'source_coverage': [('coverage_id','TEXT PRIMARY KEY'),('source_id','TEXT NOT NULL REFERENCES sources(source_id)'),('region_id','TEXT NOT NULL REFERENCES regions(region_id)'),('coverage_role','TEXT NOT NULL'),('coverage_status','TEXT NOT NULL'),('notes','TEXT')],
 'regional_evidence': [('evidence_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('region_id','TEXT NOT NULL REFERENCES regions(region_id)'),('evidence_type',"TEXT NOT NULL CHECK(evidence_type IN ('native_classification','occurrence','planting_guidance'))"),('native_status',"TEXT CHECK(native_status IN ('native','introduced','mixed','uncertain'))"),('occurrence_status',"TEXT CHECK(occurrence_status IN ('present','historical','extirpated','uncertain'))"),('planting_status','TEXT'),('source_status_code','TEXT'),('source_record_id','TEXT NOT NULL REFERENCES source_records(source_record_id)'),('evidence_date','TEXT'),('review_status','TEXT NOT NULL'),('notes','TEXT')],
 'trait_claims': [('claim_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('field_name','TEXT NOT NULL'),('value_json','TEXT NOT NULL'),('original_value','TEXT'),('source_record_id','TEXT NOT NULL REFERENCES source_records(source_record_id)'),('review_status','TEXT NOT NULL'),('qualification_notes','TEXT')],
 'growing_conditions': [('plant_id','TEXT PRIMARY KEY REFERENCES plants(plant_id)'),('soil_ph_min','REAL'),('soil_ph_max','REAL'),('height_min_cm','REAL'),('height_max_cm','REAL'),('spread_min_cm','REAL'),('spread_max_cm','REAL'),('bloom_start_month','INTEGER'),('bloom_end_month','INTEGER'),('drought_tolerance','TEXT'),('maintenance_level','TEXT'),('spreading_behavior','TEXT'),('selection_provenance_json','TEXT NOT NULL')],
 'condition_values': [('condition_value_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('field_name',"TEXT NOT NULL CHECK(field_name IN ('sunlight','soil_texture','soil_moisture','drainage','flower_color'))"),('value','TEXT NOT NULL'),('source_record_id','TEXT NOT NULL REFERENCES source_records(source_record_id)'),('is_preferred','INTEGER NOT NULL CHECK(is_preferred IN (0,1))'),('review_status','TEXT NOT NULL')],
 'original_plant_links': [('original_plant_id','INTEGER PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('source_record_id','TEXT NOT NULL REFERENCES source_records(source_record_id)'),('review_status','TEXT NOT NULL'),('notes','TEXT')],
 'import_issues': [('issue_id','TEXT PRIMARY KEY'),('source_record_id','TEXT REFERENCES source_records(source_record_id)'),('issue_type','TEXT NOT NULL'),('detail','TEXT NOT NULL')],
 'evidence_conflicts': [('conflict_id','TEXT PRIMARY KEY'),('plant_id','TEXT NOT NULL REFERENCES plants(plant_id)'),('region_id','TEXT REFERENCES regions(region_id)'),('field_name','TEXT NOT NULL'),('source_record_ids_json','TEXT NOT NULL'),('detail','TEXT NOT NULL')]
}
JSON_FIELDS={'original_json','value_json','selection_provenance_json','source_record_ids_json'}
def uid(s):return str(uuid5(NAMESPACE_URL,'native-plant-finder:'+s))
def norm(s):return re.sub(r'\s+',' ',s.replace('ssp.','subsp.').replace(' × ',' x ')).strip().casefold()
def read(p):return json.loads(p.read_text(encoding='utf8'))
def js(x):return json.dumps(x,ensure_ascii=True,separators=(',',':'))
def canon(t):
    n,a=t['scientificName'],t['scientificNameAuthorship']
    return re.sub(r'\s+',' ',n.replace(' '+a,'',1)).strip() if a else n
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);args=ap.parse_args()
    root=args.root.resolve();outer=root.parent;dest=root/'data/central';dest.mkdir(parents=True,exist_ok=True)
    database=root/'data/database/native-plants-central.sqlite';tmp=database.with_suffix('.building.sqlite')
    if tmp.exists():raise RuntimeError('A previous build staging file exists; inspect it before rebuilding.')
    c=sqlite3.connect(tmp);c.execute('PRAGMA foreign_keys=ON');c.execute('BEGIN')
    def put(table,**values):
        cols=[n for n,t in TABLES[table]];c.execute('INSERT OR IGNORE INTO '+table+' ('+','.join(cols)+') VALUES ('+','.join('?' for _ in cols)+')',[values.get(n) for n in cols])
    def issue(rid,kind,detail):put('import_issues',issue_id=uid(str(rid)+kind+detail),source_record_id=rid,issue_type=kind,detail=detail)
    for table,fields in TABLES.items():c.execute('CREATE TABLE '+table+' ('+','.join(n+' '+t for n,t in fields)+')')
    manifests=read(root/'data/native-only/manifest.json')['sources'];regional_meta={s['source_id']:s for s in read(root/'data/regional/sources.json')}
    publishers={'vascan_ontario':'Universite de Montreal / Canadensys','kew_researched':'Royal Botanic Gardens, Kew','trca_2025':'Toronto and Region Conservation Authority','cvc_2021':'Credit Valley Conservation','halton_2018':'Conservation Halton','toronto_2020':'Marc Cadotte / University of Toronto'}
    for m in manifests:
        sid=m['source_id'];put('sources',source_id=sid,title=regional_meta.get(sid,{}).get('title',sid),publisher=publishers[sid],url=m['source_url'],edition=m['edition'],retrieved_on='2026-10-30',license='CC0 1.0' if sid in ['vascan_ontario','toronto_2020'] else 'CC BY 3.0 (Kew backbone)' if sid=='kew_researched' else 'Not verified; publisher terms apply',sha256=m['input_sha256'],scope_notes=m['scope']+' '+m['notes'])
    rawdb=outer/'dependencies/source-data/original/plants.db'
    put('sources',source_id='original_catalogue',title='Original 100-plant SQLite catalogue',publisher='Project input',url=None,edition='Local snapshot 2026-10-30',retrieved_on='2026-10-30',license='Not established',sha256=sha(rawdb),scope_notes='Original traits are unverified source claims, not independently validated horticultural facts.')
    for sid,file,edition in [('authority_boundaries','CAADMIN.zip','Archive LIO-2019-09-26; feature dates retained'),('ecodistrict_boundaries','ECODISTR.zip','Archive LIO-2025-02-13; feature dates retained')]:
        put('sources',source_id=sid,title=file,publisher='Land Information Ontario',url='https://data.ontario.ca/',edition=edition,retrieved_on='2026-10-30',license='Open Government Licence - Ontario; confirm archive terms',sha256=sha(outer/'dependencies/source-data/boundaries'/file),scope_notes='Downloaded snapshot; not claimed to be the latest boundary. Transformation notes are retained in region metadata.')
    with zipfile.ZipFile(outer/'dependencies/source-data/vascan/vascan-identity-reference.zip') as z:
        taxa=list(csv.DictReader(io.StringIO(z.read('taxon.txt').decode('utf8')),delimiter='\t'))
        common=list(csv.DictReader(io.StringIO(z.read('vernacularname.txt').decode('utf8')),delimiter='\t'))
        descriptions=list(csv.DictReader(io.StringIO(z.read('description.txt').decode('utf8')),delimiter='\t'))
    byid={t['id']:t for t in taxa};accepted=collections.defaultdict(set);aliases=collections.defaultdict(set)
    habits={r['id']:r['description'].split(',') for r in descriptions if r.get('type')=='habit'}
    for t in taxa:
        key=norm(canon(t));targets=t['acceptedNameUsageID'].split('|')
        if t['taxonomicStatus']=='accepted':accepted[key].add(t['id'])
        elif 'auct.' not in t['scientificNameAuthorship'] and len(targets)==1:aliases[key].add(targets[0])
    english={}
    for r in common:
        if r.get('language') in ['en','eng'] and r.get('isPreferredName') in ['true','True','1']:english[r['id']]=r['vernacularName']
    kew=read(root/'data/identity/plant-kew-crosswalk.json');kbyid={r['original_plant_id']:r for r in kew};kindex={}
    for r in kew:
        for n in [r['original_scientific_name'],r['accepted_canonical_name']]:kindex[norm(n)]=r
    def name(pid,n,kind,sid):
        if n:put('plant_names',name_id=uid(pid+n+kind+sid),plant_id=pid,name=n,name_type=kind,source_id=sid)
    def identifier(pid,authority,key,sid):put('external_identifiers',identifier_id=uid(authority+str(key)),plant_id=pid,authority=authority,external_taxon_id=str(key),source_id=sid)
    def vplant(tid):
        t=byid[tid];pid=uid('vascan:'+tid)
        if c.execute('SELECT 1 FROM plants WHERE plant_id=?',(pid,)).fetchone():return pid
        parent=t['parentNameUsageID'];parent_id=None
        if t['taxonRank'] in ['subspecies','variety','form'] and parent in byid and byid[parent]['taxonRank'] in ['species','subspecies','variety']:parent_id=vplant(parent)
        put('plants',plant_id=pid,accepted_scientific_name=canon(t),scientific_name_author=t['scientificNameAuthorship'],preferred_common_name=english.get(tid),family=t['family'] or None,taxon_rank=t['taxonRank'],parent_plant_id=parent_id,taxonomy_source_id='vascan_ontario',identity_review_status='verified')
        identifier(pid,'VASCAN',tid,'vascan_ontario');name(pid,canon(t),'accepted','vascan_ontario');return pid
    def resolve(n,common_name=None,forced_v=None,forced_k=None):
        if forced_v:return vplant(str(forced_v)),'verified','verified_vascan_crosswalk'
        key=norm(n);vs=accepted.get(key) or aliases.get(key)
        if vs and len(vs)==1:
            target=next(iter(vs))
            if target in byid and byid[target]['taxonomicStatus']=='accepted':return vplant(target),'verified','exact_accepted_name' if accepted.get(key) else 'unique_vascan_synonym'
        k=forced_k or kindex.get(key)
        if k:
            v=accepted.get(norm(k['accepted_canonical_name']))
            pid=vplant(next(iter(v))) if v and len(v)==1 else uid('kew:'+k['kew_taxon_id'])
            put('plants',plant_id=pid,accepted_scientific_name=k['accepted_canonical_name'],scientific_name_author=k['accepted_scientific_name'][len(k['accepted_canonical_name']):].strip(),preferred_common_name=common_name,taxon_rank='species',taxonomy_source_id='kew_researched',identity_review_status='verified')
            identifier(pid,'Kew POWO',k['kew_taxon_id'],'kew_researched');name(pid,k['accepted_canonical_name'],'accepted','kew_researched');name(pid,k['original_scientific_name'],'synonym' if k['match_method']=='synonym_resolved' else 'accepted','kew_researched');return pid,'verified','verified_kew_name'
        pid=uid('unresolved:'+key)
        put('plants',plant_id=pid,accepted_scientific_name=n,preferred_common_name=common_name,taxon_rank='unresolved',identity_review_status='needs_review')
        return pid,'needs_review','unresolved_exact_name'
    def region(rid,title,kind,code=None,sid=None,geometry=None,precision='pending',version=None,notes=None):put('regions',region_id=rid,region_name=title,region_type=kind,external_region_code=code,boundary_source_id=sid,boundary_version=version,coverage_precision=precision,geometry_geojson=js(geometry) if geometry else None,notes=notes)
    region('ontario','Ontario','province','CA-ON',notes='Province polygon not supplied in the existing boundary archives.')
    region('halton_inventory','Halton inventory area','study_area',notes='Original inventory extent requires verification; municipality/jurisdiction boundaries are not assumed equivalent.')
    region('hamilton_inventory','Hamilton inventory area','study_area',notes='Original inventory extent requires verification.')
    region('toronto_study','Toronto checklist study area','study_area',notes='Metropolitan study scope is not assumed to equal Toronto municipal limits.')
    authority_lookup={}
    for file,sid,kind in [('authority','authority_boundaries','conservation_authority'),('ecodistrict','ecodistrict_boundaries','ecodistrict')]:
        p=outer/'work/boundaries'/(file+'.geojson')
        for f in read(p)['features']:
            props=f['properties'];code=str(props['CA_ID']) if file=='authority' else props['DIST_CODE'];rid=file+':'+code
            title=props['COM_NAME'] if file=='authority' else props['DIST_NAME']
            region(rid,title,kind,code,sid,f['geometry'],'confirmed',props.get('EFF_DATE'),js(dict(original_properties=props,transform='OGR EPSG:4326; input NAD83. OGR reported multiple coordinate operations; small transformation differences possible. Coverage is source boundary snapshot, not plant range.')))
            if file=='authority':authority_lookup[title]=rid
    trca=next(v for k,v in authority_lookup.items() if 'Toronto' in k)
    cvc=next(v for k,v in authority_lookup.items() if 'Credit' in k)
    halton=next(v for k,v in authority_lookup.items() if k=='Conservation Halton')
    covers={'vascan_ontario':['ontario'],'kew_researched':['ontario'],'trca_2025':[trca],'cvc_2021':[cvc],'halton_2018':['halton_inventory','hamilton_inventory',halton],'toronto_2020':['toronto_study']}
    for sid,rids in covers.items():
        for rid in rids:
            context=sid=='halton_2018' and rid==halton
            put('source_coverage',coverage_id=uid(sid+rid),source_id=sid,region_id=rid,coverage_role='context_only' if context else 'assertion_scope',coverage_status='approximate' if context else 'pending_extent' if rid in ['halton_inventory','hamilton_inventory','toronto_study'] else 'documented_scope',notes='No plant claims should be extended from a named study area to an administrative polygon without verifying scope.')
    def record(sid,key,raw,status='original',page=None,row=None):
        rid=uid('record:'+sid+':'+str(key));put('source_records',source_record_id=rid,source_id=sid,original_record_id=str(key),source_page=page,source_row=row,subset_status=status,original_json=js(raw));return rid
    def link(rid,pid,status,method,notes=None):put('plant_source_links',source_record_id=rid,plant_id=pid,match_status=status,match_method=method,notes=notes)
    def evidence(pid,rid,region_id,kind,native=None,occurrence=None,planting=None,code=None,when=None,review='accepted_source_assertion',notes=None):
        put('regional_evidence',evidence_id=uid(rid+region_id+kind),plant_id=pid,region_id=region_id,evidence_type=kind,native_status=native,occurrence_status=occurrence,planting_status=planting,source_status_code=code,source_record_id=rid,evidence_date=when,review_status=review,notes=notes)
    def trait(pid,rid,field,value,raw=None,review='source_unverified',notes=None):
        put('trait_claims',claim_id=uid(rid+field),plant_id=pid,field_name=field,value_json=js(value),original_value=raw,source_record_id=rid,review_status=review,qualification_notes=notes)
    def condition(pid,rid,field,values,preferred,review):
        if preferred and c.execute('SELECT 1 FROM condition_values WHERE plant_id=? AND field_name=? AND is_preferred=1 AND source_record_id<>?',(pid,field,rid)).fetchone():preferred=False
        for value in values:put('condition_values',condition_value_id=uid(rid+field+value),plant_id=pid,field_name=field,value=value,source_record_id=rid,is_preferred=int(preferred),review_status=review)
    # Import subsets while retaining their native/review classifications.
    for m in manifests:
        sid=m['source_id']
        for state in ['native','review']:
            for sub in read(root/'data/native-only'/sid/(state+'.json')):
                raw=sub['source_record'];n=sub['scientific_name'];common_name=raw.get('common_name') or raw.get('ENGLISH_COMMON_NAME')
                pid,match,method=resolve(n,common_name,raw['id'] if sid=='vascan_ontario' else None,raw if sid=='kew_researched' else None)
                if sid=='kew_researched' and raw['original_plant_id']==89:match='needs_review'
                rid=record(sid,sub['subset_record_id'],raw,state,raw.get('source_pdf_page'),raw.get('source_csv_row') or raw.get('source_table_row'))
                link(rid,pid,match,method,sub['decision_reason']);name(pid,n,'source_usage',sid)
                if common_name:name(pid,common_name,'common',sid)
                if match=='needs_review':issue(rid,'identity_review',sub['decision_reason']+'; '+method)
                review='accepted_source_assertion' if state=='native' and match=='verified' else 'needs_review'
                native='native' if state=='native' else 'uncertain';occ='present' if state=='native' else 'uncertain'
                if sid=='vascan_ontario':
                    d=raw['ontario_distribution'];occ={'present':'present','absent':'historical','doubtful':'uncertain'}.get(d['occurrenceStatus'],'uncertain')
                    evidence(pid,rid,'ontario','native_classification',native,occ,code=d['occurrenceStatus']+'/'+d['establishmentMeans'],when=m['edition'],review=review,notes=d['source']+' '+d['occurrenceRemarks'])
                    if raw['id'] in habits:
                        h=habits[raw['id']];trait(pid,rid,'plant_form',h,','.join(h),'source_reported')
                        if len(h)==1:c.execute('UPDATE plants SET plant_form=COALESCE(plant_form,?) WHERE plant_id=?',(h[0],pid))
                elif sid=='kew_researched':
                    evidence(pid,rid,'ontario','native_classification','native' if state=='native' else 'uncertain',None,when=raw['reviewed_on'],review=review,notes=raw['distribution_note'])
                elif sid=='trca_2025':
                    rank=raw['local_rank'];occ='extirpated' if rank=='LX' else 'uncertain' if rank.startswith('LU') else 'present'
                    evidence(pid,rid,trca,'native_classification','native' if rank in ['L1','L2','L3','L4','L5','LX'] else 'uncertain',occ,code=rank,when='2025-05',review=review)
                elif sid=='cvc_2021':
                    ns=raw['native_status_as_published'];native='native' if ns=='native' else 'mixed' if ns.startswith('Native and') else 'uncertain'
                    evidence(pid,rid,cvc,'native_classification',native,'present',code=ns,when=raw['last_year_observed'],review=review,notes='Source regional classification; occurrence alone is not native-range geometry.')
                elif sid=='toronto_2020':
                    occ='extirpated' if raw['S_RANK']=='SX' else 'historical' if raw['S_RANK']=='SH' else 'uncertain' if state=='review' else 'present'
                    evidence(pid,rid,'toronto_study','native_classification','native' if raw['EXOTIC_NATIVE']=='N' else 'uncertain',occ,code=raw['EXOTIC_NATIVE']+'/'+raw['S_RANK'],when='2020',review=review,notes='Study extent is pending; a provincial S-rank must not be represented as precise local presence.')
                    if raw.get('source_encoding_review'):issue(rid,'source_encoding','Original author text contains mixed encoding; original bytes retained in archive.')
                    form={'Herbaceous':'herb','Tree':'tree','Shrub':'shrub','Vine':'vine','Graminoid':'graminoid','Fern':'fern'}.get(raw.get('Growth_form'))
                    if form:trait(pid,rid,'plant_form',form,raw['Growth_form'],'source_reported');c.execute('UPDATE plants SET plant_form=COALESCE(plant_form,?) WHERE plant_id=?',(form,pid))
                elif sid=='halton_2018':
                    for reg,field,yr in [('halton_inventory','halton_status_2006','2006'),('hamilton_inventory','hamilton_status_2014','2014')]:
                        code=raw[field]
                        if code in ['C','U','R']:
                            evidence(pid,rid,reg,'occurrence',None,'present',code=code,when=yr,review='accepted_source_assertion' if match=='verified' else 'needs_review')
                            evidence(pid,rid,reg,'planting_guidance',None,None,'restricted' if code=='R' else 'recommended',code,yr,'source_context_only','Retain PDF colour restrictions; guidance concerns regulated-area planting plans, not all gardens.')
                            if state=='native':evidence(pid,rid,reg,'native_classification','native',None,code=code,when='2018-08',review='inferred_needs_review',notes='Native-list context plus provincial corroboration, not an explicit independent local-native boolean.')
                        elif code=='I':evidence(pid,rid,reg,'native_classification','introduced',None,code=code,when=yr,review='accepted_source_assertion')
                        elif code=='H?':evidence(pid,rid,reg,'occurrence',None,'uncertain',code=code,when=yr,review='needs_review')
                    shade=raw['shade_tolerance'];sun={'S':['full_sun'],'P':['partial_shade'],'D':['shade'],'S-P':['full_sun','partial_shade'],'P-D':['partial_shade','shade'],'S-D':['full_sun','partial_shade','shade']}.get(shade)
                    if sun:
                        trait(pid,rid,'sunlight',sun,shade,'source_reported','Halton hour definitions retained in original PDF; shade category boundaries differ among sources.')
                        condition(pid,rid,'sunlight',sun,match=='verified','source_reported')
                    for f in ['drought_tolerance','salt_tolerance','coefficient_of_wetness','root_type','rooting_ability']:
                        if raw[f]:trait(pid,rid,f,raw[f],raw[f],'source_reported')
                if state=='review':issue(rid,'subset_review',sub['decision_reason'])
    # Preserve original plants and their verified authority links, including non-native original entries.
    vlookup={r['original_plant_id']:r for r in read(root/'data/identity/plant-vascan-crosswalk.json')['crosswalk']}
    original=sqlite3.connect(rawdb.as_uri()+'?mode=ro',uri=True);original.row_factory=sqlite3.Row
    for row in original.execute('SELECT * FROM plantlist ORDER BY plant_id'):
        raw=dict(row);old=raw['plant_id'];v=vlookup[old];k=kbyid.get(old)
        pid,match,method=resolve(raw['scientific_name'],raw['common_name'],v['vascan_taxon_id'],k)
        if old==89:match='needs_review'
        rid=record('original_catalogue',old,raw);link(rid,pid,match,method,'Original catalogue identity retained; no native status inferred from membership.')
        put('original_plant_links',original_plant_id=old,plant_id=pid,source_record_id=rid,review_status=match,notes='Intended identity requires confirmation' if old==89 else None)
        name(pid,raw['common_name'],'common','original_catalogue');name(pid,raw['scientific_name'],'source_usage','original_catalogue')
        c.execute('UPDATE plants SET preferred_common_name=COALESCE(preferred_common_name,?) WHERE plant_id=?',(raw['common_name'],pid))
        sun=raw['sun'].split('/');soil=[{'sandy':'sand'}.get(x,x) for x in raw['soil'].split('/')];moisture=[{'medium':'average'}.get(x,x) for x in raw['moisture'].split('/')]
        for field,vals in [('sunlight',sun),('soil_texture',soil),('soil_moisture',moisture),('flower_color',[raw['color'].lower()])]:
            trait(pid,rid,field,vals,review='source_unverified',notes='Original catalogue values; horticultural source not established.')
            has_preferred=c.execute('SELECT 1 FROM condition_values WHERE plant_id=? AND field_name=? AND is_preferred=1',(pid,field)).fetchone()
            condition(pid,rid,field,vals,not has_preferred and match=='verified','source_unverified')
        for field,value in [('height_max_cm',raw['max_height_cm']),('pollinator_score',raw['pollinator_score']),('bloom_month_original',raw['bloom_month']),('bloom_season_original',raw['bloom_season'])]:trait(pid,rid,field,value,review='source_unverified')
        if match=='verified':
            put('growing_conditions',plant_id=pid,height_max_cm=raw['max_height_cm'],selection_provenance_json=js({'height_max_cm':{'source_record_id':rid,'review_status':'source_unverified'}}))
        if match=='needs_review':issue(rid,'identity_review','Original plant 89 is not confirmed as the Canadian plant; do not use its garden traits as verified.')
    original.close()
    # Link synonyms with a single accepted target in the archive; retain separate ranks.
    for t in taxa:
        target=t['acceptedNameUsageID'];pid=uid('vascan:'+target)
        if t['taxonomicStatus']=='synonym' and '|' not in target and 'auct.' not in t['scientificNameAuthorship'] and c.execute('SELECT 1 FROM plants WHERE plant_id=?',(pid,)).fetchone():name(pid,canon(t),'synonym','vascan_ontario')
    # Preserve all Kew crosswalk identifiers even for original plants outside the native subset.
    for k in kew:
        pid,match,method=resolve(k['accepted_canonical_name'],forced_k=k)
        identifier(pid,'Kew POWO',k['kew_taxon_id'],'kew_researched')
    # Preserve excluded rows as raw evidence, and attach explicit introduced
    # assertions when their identities already exist in the native/original master.
    # Retain unmatched excluded rows without creating additional taxon identities.
    for m in manifests:
        sid=m['source_id'];excluded=outer/'work/native-subsets/excluded'/(sid+'.json')
        if not excluded.exists():raise RuntimeError('Missing exclusion audit: '+str(excluded))
        for sub in read(excluded):
            raw=sub['source_record'];n=sub['scientific_name']
            rid=record(sid,sub['subset_record_id'],raw,'excluded',raw.get('source_pdf_page'),raw.get('source_csv_row') or raw.get('source_table_row'))
            key=norm(n);targets=accepted.get(key) or aliases.get(key);pid=None
            if targets and len(targets)==1:pid=uid('vascan:'+next(iter(targets)))
            if sid=='kew_researched':
                k=raw;vs=accepted.get(norm(k['accepted_canonical_name']))
                pid=uid('vascan:'+next(iter(vs))) if vs and len(vs)==1 else uid('kew:'+k['kew_taxon_id'])
            if not pid or not c.execute('SELECT 1 FROM plants WHERE plant_id=?',(pid,)).fetchone():continue
            link(rid,pid,'verified','exact_existing_identity','Excluded raw source evidence retained; no new non-native master identity created.')
            if sid=='vascan_ontario':
                d=raw['ontario_distribution']
                if d['establishmentMeans']=='introduced':evidence(pid,rid,'ontario','native_classification','introduced','present' if d['occurrenceStatus']=='present' else 'uncertain',code=d['occurrenceStatus']+'/'+d['establishmentMeans'],when=m['edition'])
                elif d['occurrenceStatus']=='excluded':evidence(pid,rid,'ontario','occurrence',None,'uncertain',code='excluded',when=m['edition'],review='needs_review',notes=d['occurrenceRemarks'])
            elif sid=='trca_2025':evidence(pid,rid,trca,'native_classification','introduced','present',code=raw['local_rank'],when='2025-05')
            elif sid=='cvc_2021':evidence(pid,rid,cvc,'native_classification','introduced','present',code=raw['native_status_as_published'],when=raw['last_year_observed'])
            elif sid=='toronto_2020':evidence(pid,rid,'toronto_study','native_classification','introduced',None,code=raw['EXOTIC_NATIVE'],when='2020',notes='Source exotic classification; no wild presence inferred for cultivated records.')
            elif sid=='halton_2018':
                for reg,field,yr in [('halton_inventory','halton_status_2006','2006'),('hamilton_inventory','hamilton_status_2014','2014')]:
                    if raw[field]=='I':evidence(pid,rid,reg,'native_classification','introduced',None,code='I',when=yr)
            # Kew's lack of an Ontario range entry is not an introduced assertion.
    for row in c.execute('SELECT plant_id FROM plants').fetchall():put('growing_conditions',plant_id=row[0],selection_provenance_json='{}')
    # Record conflicting growing-condition claims from different sources.
    groups=collections.defaultdict(list)
    for pid,reg,ns,rid in c.execute("SELECT plant_id,region_id,native_status,source_record_id FROM regional_evidence WHERE native_status IS NOT NULL"):
        groups[(pid,reg)].append((ns,rid))
    for (pid,reg),items in groups.items():
        if {'native','introduced'}.issubset({n for n,r in items}):put('evidence_conflicts',conflict_id=uid(pid+reg+'native_status'),plant_id=pid,region_id=reg,field_name='native_status',source_record_ids_json=js(sorted({r for n,r in items})),detail='Native and introduced statements coexist; resolve before recommendation.')
    for pid in [r[0] for r in c.execute('SELECT plant_id FROM plants')]:
        for field in ['sunlight','soil_texture','soil_moisture']:
            claims=c.execute('SELECT source_record_id,value_json FROM trait_claims WHERE plant_id=? AND field_name=?',(pid,field)).fetchall()
            if len({v for r,v in claims})>1:put('evidence_conflicts',conflict_id=uid(pid+field),plant_id=pid,field_name=field,source_record_ids_json=js([r for r,v in claims]),detail='Source growing-condition claims differ; preferred values are a documented selection, not a guarantee.')
    views={
      'native_candidates':"SELECT DISTINCT p.* FROM plants p JOIN regional_evidence e ON e.plant_id=p.plant_id JOIN plant_source_links l ON l.source_record_id=e.source_record_id WHERE p.identity_review_status='verified' AND l.match_status='verified' AND e.native_status='native' AND e.occurrence_status='present' AND e.review_status='accepted_source_assertion' AND NOT EXISTS (SELECT 1 FROM evidence_conflicts f WHERE f.plant_id=p.plant_id AND f.region_id=e.region_id AND f.field_name='native_status')",
      'plant_profile':"SELECT p.*,g.height_min_cm,g.height_max_cm,g.soil_ph_min,g.soil_ph_max,g.spread_min_cm,g.spread_max_cm,g.bloom_start_month,g.bloom_end_month,g.drought_tolerance,g.maintenance_level,g.spreading_behavior,g.selection_provenance_json FROM plants p JOIN growing_conditions g ON g.plant_id=p.plant_id",
      'identity_review_queue':"SELECT s.source_record_id,s.source_id,l.plant_id,l.match_method,l.notes FROM source_records s JOIN plant_source_links l ON l.source_record_id=s.source_record_id WHERE l.match_status='needs_review'",
      'preferred_conditions':"SELECT * FROM condition_values WHERE is_preferred=1"}
    for n,q in views.items():c.execute('CREATE VIEW '+n+' AS '+q)
    for table,cols in [('plant_source_links','plant_id'),('regional_evidence','plant_id,region_id'),('condition_values','plant_id,field_name'),('plant_names','name'),('source_records','source_id')]:c.execute('CREATE INDEX idx_'+table+' ON '+table+'('+cols+')')
    c.commit();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert c.execute('SELECT count(*) FROM original_plant_links').fetchone()[0]==100
    assert c.execute('SELECT review_status FROM original_plant_links WHERE original_plant_id=89').fetchone()[0]=='needs_review'
    # Export the PostgreSQL schema with JSONB fields and PostGIS geometry.
    schema=['CREATE EXTENSION IF NOT EXISTS postgis;','CREATE SCHEMA IF NOT EXISTS native_plants;','SET search_path=native_plants,public;']
    for table,fields in TABLES.items():
        definition=[]
        for n,t in fields:
            if n in JSON_FIELDS:t=t.replace('TEXT','JSONB',1)
            if n=='geometry_geojson':n='geom';t='geometry(MultiPolygon,4326)'
            definition.append(n+' '+t)
        schema.append('CREATE TABLE IF NOT EXISTS '+table+'('+','.join(definition)+');')
    schema+=['CREATE INDEX IF NOT EXISTS regions_geom_gist ON regions USING GIST(geom);','CREATE INDEX IF NOT EXISTS evidence_plant_region ON regional_evidence(plant_id,region_id);','CREATE INDEX IF NOT EXISTS names_lower_idx ON plant_names(lower(name));']
    for n,q in views.items():schema.append('CREATE OR REPLACE VIEW '+n+' AS '+q+';')
    (dest/'schema.postgresql.sql').write_text('\n'.join(schema)+'\n',encoding='utf8')
    def literal(v,n):
        if v is None:return 'NULL'
        if isinstance(v,(int,float)):return str(v)
        s="'"+v.replace("'","''")+"'"
        if n=='geometry_geojson':return 'ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON('+s+'),4326)),3))'
        return s+'::jsonb' if n in JSON_FIELDS else s
    with (dest/'load-data.postgresql.sql').open('w',encoding='utf8') as out:
        out.write('BEGIN;\nSET search_path=native_plants,public;\nSET CONSTRAINTS ALL DEFERRED;\n')
        for table,fields in TABLES.items():
            names=[n for n,t in fields];pgcols=['geom' if n=='geometry_geojson' else n for n in names]
            for row in c.execute('SELECT '+','.join(names)+' FROM '+table):
                out.write('INSERT INTO '+table+'('+','.join(pgcols)+') VALUES ('+','.join(literal(v,n) for n,v in zip(names,row))+') ON CONFLICT ('+pgcols[0]+') DO UPDATE SET '+','.join(n+'=EXCLUDED.'+n for n in pgcols[1:])+';\n')
        out.write('COMMIT;\nANALYZE;\n')
    report={'built_on':date.today().isoformat(),'tables':{table:c.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in TABLES},'native_candidates':c.execute('SELECT count(*) FROM native_candidates').fetchone()[0],'regions_with_geometry':c.execute('SELECT count(*) FROM regions WHERE geometry_geojson IS NOT NULL').fetchone()[0],'identity_review_links':c.execute("SELECT count(*) FROM plant_source_links WHERE match_status='needs_review'").fetchone()[0],'unlinked_excluded_audit_records':c.execute("SELECT count(*) FROM source_records s WHERE s.subset_status='excluded' AND NOT EXISTS (SELECT 1 FROM plant_source_links l WHERE l.source_record_id=s.source_record_id)").fetchone()[0],'source_hashes_verified':all(sha(outer/m['input_file'])==m['input_sha256'] for m in manifests),'limitations':['Not all source records are taxonomically resolved.','Original growing conditions are unverified; they retain their provenance.','Halton and Toronto study polygons are pending; no ecological-district nativity is inferred.','Native candidates are provincially/regionally supported, not guaranteed garden matches.']}
    (dest/'build-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    c.close()
    if database.exists():
        backup=outer/'work/backups';backup.mkdir(parents=True,exist_ok=True);database.replace(backup/('central-before-'+date.today().isoformat()+'.sqlite'))
    tmp.replace(database)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
