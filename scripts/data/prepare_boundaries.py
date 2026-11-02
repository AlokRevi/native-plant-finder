"""Prepare the two preserved LIO archives for the central builder using GDAL."""
from pathlib import Path
import shutil,subprocess,zipfile

def main():
 root=Path(__file__).resolve().parents[2];outer=root.parent
 ogr=shutil.which('ogr2ogr')
 if not ogr:
  fallback=Path(r'C:\Program Files\QGIS 3.40.15\bin\ogr2ogr.exe')
  if fallback.exists():ogr=str(fallback)
 if not ogr:raise SystemExit('GDAL ogr2ogr is required for this step; use a QGIS/GDAL environment.')
 work=outer/'work/boundaries';work.mkdir(parents=True,exist_ok=True)
 for archive,output in [('CAADMIN','authority'),('ECODISTR','ecodistrict')]:
  target=work/archive;target.mkdir(exist_ok=True)
  with zipfile.ZipFile(outer/'dependencies/source-data/boundaries'/(archive+'.zip')) as z:
   for n in z.namelist():
    if not (target/n).resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe ZIP path')
   z.extractall(target)
  shape=next(target.rglob('*.shp'));temp=work/(output+'.building.geojson');final=work/(output+'.geojson')
  subprocess.run([ogr,'-overwrite','-f','GeoJSON','-t_srs','EPSG:4326',str(temp),str(shape)],check=True)
  temp.replace(final);print('Prepared '+output)
if __name__=='__main__':main()
