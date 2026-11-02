"""Extract published regional PDF tables without changing their botanical claims.

Run from anywhere. Defaults to source PDFs outside the Git repository.
Requires pdfplumber and pypdf; the web application does not require these.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, re, sqlite3, tempfile
from pathlib import Path
import pdfplumber
from pypdf import PdfReader, PdfWriter

SOURCES = {
 'trca_2025': dict(file='2025_Flora_Rank_Scores.pdf', title='TRCA Flora Species Ranks and Scores', edition='2025-05',
   url='https://trcaca.s3.ca-central-1.amazonaws.com/app/uploads/2025/05/26121544/2025_Flora_Rank_Scores.pdf',
   coverage='TRCA jurisdiction', boundary_key='conservation_authority:TRCA',
   notes='Local ranks are source codes, not a garden suitability score. L+ is non-native, LX locally extinct; uncertain suffixes must be retained. Occurrence grid interval 2010-2024.'),
 'cvc_2021': dict(file='Credit-River-Watershed-Plant-Species-List-2021-Update_na.pdf',title='Credit River Watershed Plant Species List',edition='2022-02',data_edition='2021',
   url='https://files.cvc.ca/cvc/uploads/2022/07/Credit-River-Watershed-Plant-Species-List-2021-Update_na.pdf',
   coverage='CVC jurisdiction: Credit River watershed and small Mississauga creeks draining directly into Lake Ontario',boundary_key='conservation_authority:CVC',
   notes='Current natural/naturalized vascular flora observed 2001-2021. Native/non-native status is copied as published. Includes non-native plants; not a planting shortlist.'),
 'halton_2018': dict(file='native_species_list_aug2018.pdf',title='Conservation Halton Native Species List',edition='2018-08',
   url='https://haltonmastergardeners.com/wp-content/uploads/2019/02/native_species_list_aug2018.pdf',
   coverage='Conservation Halton guidance, with separate Halton 2006 and Hamilton 2014 status columns',boundary_key='conservation_authority:CH; municipal:Halton; municipal:Hamilton',
   notes='Planting guidance for regulated areas; not blanket local nativity. Codes, colours and regional columns are retained. C/U acceptable per document; R, I, H?, absence and coloured cells need interpretation. Use inventory references for discrepancies. Colour extraction is evidence, not automated planting approval.')
}

def clean(v): return re.sub(r'\s+', ' ', v or '').strip()
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj): p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def visual_style(page, box):
    x0,y0,x1,y1=box; x=(x0+x1)/2; y=(y0+y1)/2
    backgrounds=[]
    for r in page.rects:
        if r['x0']<=x<=r['x1'] and r['top']<=y<=r['bottom'] and r['width']>3 and r['height']>3:
            color=r.get('non_stroking_color')
            if color is not None and color not in backgrounds: backgrounds.append(color)
    return dict(background_colors=backgrounds)

def halton_rows(table):
    """Merge PDF drawing fragments into the eleven visible table columns."""
    borders=[72.26,171.25,277.62,327.15,391.01,433.62,490.26,539.82,596.61,660.45,717.09,759.59]
    sections={'Trees','Shrubs','Woody Groundcover','Vines','Clubmosses, Ferns and Horsetails','Grasses','Rushes','Sedges','Emergent Vegetation','Submergent Vegetation','Floating Aquatics','Herbaceous'}
    prepared=[]
    for row_no,(raw,geometry) in enumerate(zip(table.extract(),table.rows),1):
        if row_no<=2:continue
        values=['']*11
        present=[b for b in geometry.cells if b is not None]
        if not present:continue
        top=min(b[1] for b in present);bottom=max(b[3] for b in present)
        for v,b in zip(raw,geometry.cells):
            v=clean(v)
            if not v or b is None:continue
            if v in sections:
                values=[v]+['']*10;break
            x=(b[0]+b[2])/2
            j=next((k for k in range(11) if borders[k]<=x<borders[k+1]),None)
            if j is not None:values[j]=clean(values[j]+' '+v)
        # Text split over drawing fragments is still one printed plant row.
        continuation=not values[2] and not values[3] and values[0] not in sections
        if continuation and prepared and prepared[-1][1][0] not in sections:
            prev_no,prev,prev_boxes=prepared[-1]
            for j,v in enumerate(values):prev[j]=clean(prev[j]+' '+v)
            prepared[-1]=(prev_no,prev,[(b[0],b[1],b[2],bottom) for b in prev_boxes])
        else:
            prepared.append((row_no,values,[(borders[k],top,borders[k+1],bottom) for k in range(11)]))
    return prepared

def extract(source_id, path, temp, qa):
    rows=[]; pages=[]; rejected=[]; section=None
    source=SOURCES[source_id]
    if source_id=='halton_2018':
        reader=PdfReader(path); writer=PdfWriter()
        for i,p in enumerate(reader.pages):
            if i>=3:p.rotate(-90)
            writer.add_page(p)
        path2=temp/'halton-upright.pdf'
        with path2.open('wb') as f:writer.write(f)
    else:path2=path
    with pdfplumber.open(path2) as pdf:
        for page_no,page in enumerate(pdf.pages,1):
            page_text=page.extract_text() or ''
            pages.append(dict(pdf_page=page_no,text=page_text))
            first=1 if source_id=='trca_2025' else 8 if source_id=='cvc_2021' else 4
            if page_no<first:continue
            tables=page.find_tables()
            if not tables:raise ValueError(f'{source_id} page {page_no}: missing table')
            table=max(tables,key=lambda t:len(t.cells))
            count=0
            if source_id=='halton_2018':
                prepared=halton_rows(table)
            else:
                prepared=[(n,raw,g.cells) for n,(raw,g) in enumerate(zip(table.extract(),table.rows),1)]
            for row_no,raw,boxes in prepared:
                cells=[(clean(v),b) for v,b in zip(raw,boxes) if b is not None]
                values=[v for v,b in cells]
                nonempty=[v for v in values if v]
                if not nonempty:continue
                if source_id=='halton_2018':
                    if len(nonempty)==1:
                        section=nonempty[0];continue
                    if any('Scientific Name' in v or 'Environmental Tolerance' in v for v in values):continue
                    fields=['scientific_name','common_name','halton_status_2006','hamilton_status_2014','coefficient_of_wetness','drought_tolerance','salt_tolerance','shade_tolerance','root_type','rooting_ability','stormwater_pond']
                    # Empty geometric fragments are not genuine columns.
                    if len(values)!=11:
                        cells=[(v,b) for v,b in cells if v or b[2]-b[0]>10]
                        values=[v for v,b in cells]
                    record=dict(zip(fields,values));record['plant_group']=section
                    record['cell_styles']={k:visual_style(page,b) for k,(v,b) in zip(fields,cells)}
                    valid=len(values)==11 and bool(re.match(r'^[A-Z][a-z]+\s',record.get('scientific_name','')))
                elif source_id=='cvc_2021':
                    if len(values)==5 and values[:4]==['']*4 and values[-1]=='(depends on subspecies)':
                        assert rows and rows[-1]['scientific_name']=='Rubus idaeus'
                        rows[-1]['native_status_as_published']+=' '+values[-1]
                        rows[-1]['source_continuation_pages']=[page_no]
                        continue
                    if not (len(values)==5 and values[-1] in ['native','non-native','unknown','Native and non-native','Native and non-native (depends on subspecies)']):
                        if any('Scientific Name' in v or v in ['native','Status','Native/non-'] for v in values):continue
                        rejected.append(dict(source_id=source_id,pdf_page=page_no,row=row_no,cells=values));continue
                    fields=['plant_group','scientific_name','common_name','last_year_observed','native_status_as_published']
                    record=dict(zip(fields,values));valid=bool(re.fullmatch(r'\d{4}',values[3]))
                else:
                    if 'Family' in values and 'Sp_code' in values:continue
                    if page_no==42 and row_no>=11:continue  # printed legend and summary, retained in page text
                    fields=['family','species_code','scientific_name','common_name','grid_count_2010_2024','local_occurrence_score_2025','population_trend_score','habitat_dependence_score','sensitivity_to_development_score','total_score','local_rank','score_date']
                    record=dict(zip(fields,values))
                    valid=len(values)==12 and bool(record.get('species_code')) and record.get('local_rank','').startswith('L')
                if not valid:
                    rejected.append(dict(source_id=source_id,pdf_page=page_no,row=row_no,cells=values));continue
                count+=1
                record.update(record_id=f'{source_id}:p{page_no}:r{row_no}',source_id=source_id,source_pdf_page=page_no,source_table_row=row_no,source_cells=values)
                rows.append(record)
            qa.append(dict(source_id=source_id,pdf_page=page_no,extracted_rows=count))
            if count==0:raise ValueError(f'{source_id} page {page_no}: no records')
    return rows,pages,rejected

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);parser.add_argument('--source-dir',type=Path);parser.add_argument('--qa-dir',type=Path)
    args=parser.parse_args();root=args.root.resolve();source_dir=args.source_dir or root.parent/'dependencies/source-data/regional';qa_dir=args.qa_dir or root.parent/'work/data-qa'
    dest=root/'data/regional';dest.mkdir(parents=True,exist_ok=True);qa_dir.mkdir(parents=True,exist_ok=True)
    allrows=[];manifest=[];qa=[];rejects=[]
    with tempfile.TemporaryDirectory() as td:
        for sid,meta in SOURCES.items():
            path=source_dir/meta['file']
            records,pages,rejected=extract(sid,path,Path(td),qa)
            allrows.extend(records);rejects.extend(rejected)
            entry=dict(source_id=sid,**meta,sha256=digest(path),extracted_rows=len(records),processed_on='2026-10-30',raw_file_relative_to_outer_folder='dependencies/source-data/regional/'+meta['file'],license='Not verified; original publisher terms apply. Do not infer a licence from public availability.')
            manifest.append(entry);dump(dest/(sid+'.json'),records);dump(qa_dir/(sid+'-pages.json'),pages)
    dump(dest/'sources.json',manifest);dump(qa_dir/'page-counts.json',qa);dump(qa_dir/'rejected-rows.json',rejects)
    # Stop extraction if any table rows remain unclassified.
    if rejects:raise ValueError(f'{len(rejects)} table rows require review; see {qa_dir}/rejected-rows.json')
    for sid in SOURCES:
        selected=[r for r in allrows if r['source_id']==sid]
        dup=[(n,k) for n,k in collections.Counter(r['scientific_name'] for r in selected).items() if k>1]
        dump(qa_dir/(sid+'-duplicate-names.json'),dup)
    dbpath=root/'data/database/plant-project.db'
    if dbpath.exists():
        c=sqlite3.connect(dbpath)
        c.executescript('''CREATE TABLE IF NOT EXISTS regional_sources(source_id TEXT PRIMARY KEY, metadata_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS regional_plant_records(record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES regional_sources(source_id), scientific_name TEXT NOT NULL, common_name TEXT, source_pdf_page INTEGER NOT NULL, record_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plant_regional_links(plant_id INTEGER NOT NULL REFERENCES plantlist(plant_id), record_id TEXT NOT NULL REFERENCES regional_plant_records(record_id), match_method TEXT NOT NULL, PRIMARY KEY(plant_id,record_id));''')
        c.execute('PRAGMA foreign_keys=ON')
        with c:
            for m in manifest:
                c.execute('DELETE FROM plant_regional_links WHERE record_id IN (SELECT record_id FROM regional_plant_records WHERE source_id=?)',(m['source_id'],))
                c.execute('DELETE FROM regional_plant_records WHERE source_id=?',(m['source_id'],))
                c.execute('INSERT OR REPLACE INTO regional_sources VALUES (?,?)',(m['source_id'],json.dumps(m,ensure_ascii=False)))
            names=collections.defaultdict(set)
            for pid,n in c.execute('SELECT plant_id,scientific_name FROM plantlist'):names[clean(n).casefold()].add(pid)
            for pid,n in c.execute('SELECT plant_id,accepted_canonical_name FROM plant_taxonomy'):
                if n:names[clean(n).casefold()].add(pid)
            for r in allrows:
                c.execute('INSERT INTO regional_plant_records VALUES (?,?,?,?,?,?)',(r['record_id'],r['source_id'],r['scientific_name'],r.get('common_name'),r['source_pdf_page'],json.dumps(r,ensure_ascii=False)))
                for pid in names.get(r['scientific_name'].casefold(),[]):
                    c.execute('INSERT INTO plant_regional_links VALUES (?,?,?)',(pid,r['record_id'],'exact_original_or_accepted_name'))
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('SELECT count(*) FROM plantlist').fetchone()[0]==100
        links=c.execute('SELECT count(*) FROM plant_regional_links').fetchone()[0]
        c.close()
    else:links=None
    # SQL uses PostgreSQL JSONB and is independent of the SQLite working copy.
    def lit(s):return "'"+str(s).replace("'","''")+"'"
    sql=['-- Source records only; does not assign native polygons or garden approval.','BEGIN;',
      'CREATE TABLE IF NOT EXISTS regional_sources (source_id TEXT PRIMARY KEY, metadata_json JSONB NOT NULL);',
      'CREATE TABLE IF NOT EXISTS regional_plant_records (record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES regional_sources(source_id), scientific_name TEXT NOT NULL, common_name TEXT, source_pdf_page INTEGER NOT NULL, record_json JSONB NOT NULL);']
    for m in manifest:sql.append('INSERT INTO regional_sources VALUES ('+lit(m['source_id'])+','+lit(json.dumps(m,ensure_ascii=False))+'::jsonb) ON CONFLICT (source_id) DO UPDATE SET metadata_json=EXCLUDED.metadata_json;')
    for r in allrows:
        sql.append('INSERT INTO regional_plant_records VALUES ('+','.join([lit(r['record_id']),lit(r['source_id']),lit(r['scientific_name']),lit(r.get('common_name','')),str(r['source_pdf_page']),lit(json.dumps(r,ensure_ascii=False))+'::jsonb'])+') ON CONFLICT (record_id) DO UPDATE SET scientific_name=EXCLUDED.scientific_name,common_name=EXCLUDED.common_name,source_pdf_page=EXCLUDED.source_pdf_page,record_json=EXCLUDED.record_json;')
    sql.append('COMMIT;');(dest/'regional-datasets.postgresql.sql').write_text('\n'.join(sql)+'\n',encoding='utf8')
    summary=dict(record_counts={m['source_id']:m['extracted_rows'] for m in manifest},total_records=len(allrows),original_plant_links=links,rejected_rows=len(rejects),pages_checked=len(qa))
    dump(dest/'validation.json',summary);print(json.dumps(summary))

if __name__=='__main__':main()
