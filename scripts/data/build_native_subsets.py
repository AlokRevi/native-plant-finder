"""Build conservative native-only JSON subsets; retain all original source inputs.

No third-party dependencies. Runs against the local project source snapshots.
Native status is source evidence, not proof of garden suitability.
"""
from pathlib import Path
import argparse,collections,csv,hashlib,io,json,re,sqlite3,zipfile
from datetime import date

def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(s):return re.sub(r'\s+',' ',s.replace('ssp.','subsp.')).strip().casefold()
def canonical(t):
    name,author=t['scientificName'],t['scientificNameAuthorship']
    return name[:-len(author)].strip() if author and name.endswith(author) else name

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);args=ap.parse_args()
    root=args.root.resolve();outer=root.parent;raw=outer/'dependencies/source-data'
    dest=root/'data/native-only';audit=outer/'work/native-subsets';audit.mkdir(parents=True,exist_ok=True)
    manifests=[];partitions={}
    def emit(sid,records,input_path,scope,rule,source_url,edition,notes=''):
        buckets={k:[] for k in ['native','review','excluded']}
        for record,state,reason,regions in records:
            name=record.get('scientific_name') or record.get('scientificName') or record.get('SCIENTIFIC_NAME') or record.get('accepted_canonical_name')
            rid=record.get('record_id') or record.get('id') or str(record.get('original_plant_id'))
            buckets[state].append(dict(subset_record_id=sid+':'+str(rid),source_id=sid,scientific_name=name,
                subset_status=state,decision_reason=reason,native_regions=regions,source_record=record))
        assert sum(map(len,buckets.values()))==len(records)
        assert len({r['subset_record_id'] for b in buckets.values() for r in b})==len(records)
        write_json(dest/sid/'native.json',buckets['native'])
        write_json(dest/sid/'review.json',buckets['review'])
        write_json(audit/'excluded'/(sid+'.json'),buckets['excluded'])
        manifest=dict(source_id=sid,input_file=str(input_path.relative_to(outer)),input_sha256=sha(input_path),
            scope=scope,edition=edition,source_url=source_url,rule=rule,notes=notes,processed_on=date.today().isoformat(),
            counts={k:len(v) for k,v in buckets.items()},input_records_considered=len(records))
        manifests.append(manifest);partitions[sid]=buckets

    vp=raw/'vascan/vascan-identity-reference.zip'
    with zipfile.ZipFile(vp) as z:
        taxa=list(csv.DictReader(io.StringIO(z.read('taxon.txt').decode('utf-8-sig')),delimiter='\t'))
        distribution=list(csv.DictReader(io.StringIO(z.read('distribution.txt').decode('utf-8-sig')),delimiter='\t'))
    byid={t['id']:t for t in taxa};on={d['id']:d for d in distribution if d['locationID']=='ISO3166-2:CA-ON'}
    vrecords=[]
    for taxid,d in on.items():
        t=byid[taxid];record=dict(t,ontario_distribution=d)
        if t['taxonomicStatus']!='accepted':state,reason='review','Taxonomic status is not accepted'
        elif d['occurrenceStatus']=='present' and d['establishmentMeans']=='native':state,reason='native','Explicit present/native Ontario assertion'
        elif d['occurrenceStatus'] in ['doubtful','absent']:
            state,reason='review','Doubtful or absent/historical Ontario assertion; not accepted as current native evidence'
        else:state,reason='excluded','Not a present/native Ontario assertion; original status preserved'
        vrecords.append((record,state,reason,['Ontario'] if state=='native' else []))
    emit('vascan_ontario',vrecords,vp,'Ontario assertions only; all explicitly listed accepted species/subspecies/varieties retained separately',
        "Ontario occurrenceStatus='present' AND establishmentMeans='native', accepted identity. No parent-species propagation.",
        'https://data.canadensys.net/ipt/resource?r=vascan','2026-08-04',
        'Counts are taxon records, not unique species. Taxa without an Ontario assertion are outside this subset scope. Synonyms remain in the original archive.')

    kp=root/'data/identity/plant-kew-crosswalk.json';kr=read_json(kp);krecords=[]
    for r in kr:
        pid=r['original_plant_id']
        if pid==45:state,reason,regions='native','Verified POWO record explicitly lists Ontario as native',['Ontario']
        elif pid==89:state,reason,regions='review','Literal name resolves to Eurasian Pulsatilla patens; intended Canadian plant identity remains unresolved',[]
        else:state,reason,regions='excluded','Ontario is not listed in the native range checked for this POWO accepted taxon',[]
        krecords.append((r,state,reason,regions))
    emit('kew_researched',krecords,kp,'Only the 11 Kew identities researched for the original 100 plants, not the complete Kew flora',
        'Keep explicit Ontario-native evidence; retain original plant 89 for identity review.',
        'https://powo.science.kew.org/','Records checked 2026-10-30',
        'Ontario evidence for 440925-1: https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:440925-1 . Other ranges and citations are retained in original distribution_note fields. Global intended-identity review is not cleared.')

    tp=root/'data/regional/trca_2025.json';tr=[]
    for r in read_json(tp):
        rank=r['local_rank']
        if rank in ['L1','L2','L3','L4','L5']:state,reason='native','Extant native local rank '+rank
        elif rank=='L+':state,reason='excluded','Explicit introduced/non-native local rank'
        else:state,reason='review','Locally extinct, uncertain native status or unproven occurrence: '+rank
        tr.append((r,state,reason,['TRCA jurisdiction'] if state=='native' else []))
    emit('trca_2025',tr,tp,'TRCA jurisdiction','Keep L1-L5. Review LX, L+?, LU and LU+. Exclude L+.',
        'https://trca.ca/conservation/terrestrial-ecosystems/ranks-and-scores/','2025-05')

    cp=root/'data/regional/cvc_2021.json';cr=[]
    for r in read_json(cp):
        status=r['native_status_as_published']
        if status=='native':state,reason='native','Explicit native label in regional source'
        elif status=='non-native':state,reason='excluded','Explicit non-native label in regional source'
        else:state,reason='review','Unknown or subspecies-dependent native status: '+status
        cr.append((r,state,reason,['CVC jurisdiction'] if state=='native' else []))
    emit('cvc_2021',cr,cp,'CVC jurisdiction',"Keep native_status_as_published='native'; review unknown and mixed statuses.",
        'https://cvc.ca/document/credit-river-watershed-plant-species-list/','2022-02; 2021 update',
        'Source classification is retained as published. It is not a species range polygon or a guarantee of indigenous origin at every site.')

    # Resolve historical Halton names against VASCAN without fuzzy or lower-rank matching.
    vindex=collections.defaultdict(set)
    for t in taxa:
        vindex[norm(canonical(t))].update(t['acceptedNameUsageID'].split('|'))
    hp=root/'data/regional/halton_2018.json';hr=[]
    for original in read_json(hp):
        r=dict(original);codes=[r['halton_status_2006'],r['hamilton_status_2014']]
        regions=[region for region,code in zip(['Halton inventory area','Hamilton inventory area'],codes) if code in ['C','U','R']]
        colors=[color for style in r['cell_styles'].values() for color in style['background_colors']]
        nurse=any(isinstance(col,list) and len(col)==3 and col[1]>col[0] and col[1]>col[2] and col[0]>.4 for col in colors)
        ids=vindex.get(norm(r['scientific_name']),set());r['supporting_vascan_accepted_ids']=sorted(ids)
        statuses=[(on[i]['occurrenceStatus'],on[i]['establishmentMeans']) for i in ids if i in on]
        if all(x=='I' or x=='-' for x in codes) and 'I' in codes:
            state,reason='excluded','Introduced in all source regions with a determined occurrence'
        elif 'I' in codes:
            state,reason='review','Regional statuses conflict: introduced in at least one region'
        elif 'H?' in codes:
            state,reason='review','Source explicitly requires further review'
        elif nurse:
            state,reason='review','Green nurse-crop highlighting; title alone is insufficient native-status evidence'
        elif not regions:
            state,reason='review','No positive C/U/R local occurrence context'
        elif len(ids)!=1:
            state,reason='review','Historical name lacks a unique exact VASCAN accepted-target match'
        elif statuses!=[('present','native')]:
            state,reason='review','Ontario-native status not corroborated by an exact VASCAN assertion'
        else:
            state,reason='native','C/U/R in native-list context, no nurse-crop or uncertain/introduced flags, corroborated by VASCAN Ontario-native assertion'
        r['rare_in_source_region']='R' in codes
        hr.append((r,state,reason,regions if state=='native' else []))
    emit('halton_2018',hr,hp,'Separate Halton and Hamilton inventory-area evidence; never assign both if one has no positive status',
        'Conservative native-list-context filter: positive C/U/R; no I/H?/green nurse-crop flag; unique exact VASCAN Ontario-native corroboration. Rare records retained as native, not approved for planting.',
        'https://haltonmastergardeners.com/wp-content/uploads/2019/02/native_species_list_aug2018.pdf','2018-08',
        'C/U/R are abundance codes, not an explicit native boolean. This subset is a documented inference using the native-list context plus provincial corroboration; independent local indigenous status may still require inventory review. VASCAN infraspecific-to-species propagation is not used.')

    zp=raw/'toronto/doi_10_5061_dryad_1ns1rn8sg__v20201124.zip'
    with zipfile.ZipFile(zp) as z:
        fn=next(n for n in z.namelist() if n.endswith('.csv'));rawbytes=z.read(fn)
    try:text=rawbytes.decode('utf-8-sig');encoding='UTF-8'
    except UnicodeDecodeError:text=rawbytes.decode('latin1');encoding='Latin-1 byte-preserving fallback (source has mixed/garbled author encoding)'
    tor=[]
    for number,original in enumerate(csv.DictReader(io.StringIO(text)),2):
        r=dict(original,record_id=f'csv-row-{number}',source_csv_row=number)
        r['source_encoding_review']=any(127<=ord(ch)<=159 for v in original.values() for ch in v)
        status=r['EXOTIC_NATIVE'].strip();rank=r['S_RANK'].strip();cult=r['Cultivated'].strip()
        if status=='E':state,reason='excluded','Explicit exotic/non-native classification'
        elif status!='N':state,reason='review','Native classification is unknown'
        elif rank in ['SX','SH','SX?','SH?']:state,reason='review','Extirpated or historical provincial rank; do not treat as currently established native'
        elif cult:state,reason='review','Native-labelled but cultivation flagged; local wild-origin evidence needs review'
        else:state,reason='native','Explicit N native classification, without historical/extirpated or cultivation flags'
        tor.append((r,state,reason,['Toronto study area'] if state=='native' else []))
    emit('toronto_2020',tor,zp,'Toronto compilation study area, subject to verified study extent',
        'Keep EXOTIC_NATIVE=N; review unknown, SX/SH and cultivation flags; exclude E. Conservation rarity/uncertainty does not by itself negate a clear N status.',
        'https://datadryad.org/dataset/doi:10.5061/dryad.1ns1rn8sg','2020-11-24 release; July 2020 file',
        encoding+'. Original source bytes remain in the ZIP; author-text encoding issues are flagged, not guessed or used to change native status.')

    write_json(dest/'manifest.json',dict(sources=manifests,policy='Ontario-native for VASCAN/Kew; local source status for regional lists; uncertainty separated; sources preserved.',native_total=sum(m['counts']['native'] for m in manifests),review_total=sum(m['counts']['review'] for m in manifests)))
    write_json(dest/'validation.json',dict(partitions_complete=True,counts={m['source_id']:m['counts'] for m in manifests},warnings=['Kew covers only 11 researched records.','Halton native determination uses a conservative documented inference; C/U/R alone is not native status.','Native-only records are not a deduplicated master list or a planting approval.']))
    # Store only native and review records as additional tables. Original inputs remain unchanged.
    db=root/'data/database/plant-project.db'
    if db.exists():
        c=sqlite3.connect(db)
        c.executescript('''CREATE TABLE IF NOT EXISTS native_subset_sources (source_id TEXT PRIMARY KEY, metadata_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS native_subset_records (subset_record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES native_subset_sources(source_id), scientific_name TEXT NOT NULL, subset_status TEXT NOT NULL CHECK(subset_status IN ('native','review')), record_json TEXT NOT NULL);''')
        c.execute('PRAGMA foreign_keys=ON')
        with c:
            for m in manifests:
                sid=m['source_id'];c.execute('DELETE FROM native_subset_records WHERE source_id=?',(sid,))
                c.execute('INSERT OR REPLACE INTO native_subset_sources VALUES (?,?)',(sid,json.dumps(m)))
                for state in ['native','review']:
                    for r in partitions[sid][state]:c.execute('INSERT INTO native_subset_records VALUES (?,?,?,?,?)',(r['subset_record_id'],sid,r['scientific_name'],state,json.dumps(r)))
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('SELECT count(*) FROM plantlist').fetchone()[0]==100
        c.close()
    print(json.dumps({m['source_id']:m['counts'] for m in manifests},indent=2))

if __name__=='__main__':main()
