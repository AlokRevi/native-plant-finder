"""Install a portable PostgreSQL/PostGIS runtime in the outer project folder.

Windows-only, no service registration or administrator install. Existing cluster
data and credentials are preserved. Downloads are pinned to the tested versions.
"""
from pathlib import Path
import hashlib,json,os,secrets,subprocess,urllib.request,zipfile

URLS={
 'postgresql.zip':'https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip',
 'postgis.zip':'https://download.osgeo.org/postgis/windows/pg17/postgis-bundle-pg17-3.6.2x64.zip'
}
# Pinned SHA-256 values for the reviewed runtime snapshots.
SHA256={
 'postgresql.zip':'4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf',
 'postgis.zip':'7ba180ee2a352987b9a2f194673652c59483b55852295ccf401dceccd8765425'
}

def verify_archive(path, expected):
 digest=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
 if digest.hexdigest()!=expected:
  raise RuntimeError('Runtime archive SHA-256 mismatch: '+path.name)
 return digest.hexdigest()

def prepare_runtime_archive(archive,name,runtime,deps):
 digest=verify_archive(archive,SHA256[name])
 with zipfile.ZipFile(archive) as z:
  if z.testzip():raise RuntimeError('Archive integrity failed: '+name)
  required=runtime/('bin/postgres.exe' if name=='postgresql.zip' else 'share/extension/postgis.control')
  if not required.exists():extract(z,deps/'postgresql' if name=='postgresql.zip' else runtime,strip=name=='postgis.zip')
 return digest

def extract(z,target,strip=False):
 for entry in z.infolist():
  parts=Path(entry.filename).parts;relative=Path(*parts[1:]) if strip else Path(*parts)
  if not relative.parts:continue
  dest=target/relative
  if not dest.resolve().is_relative_to(target.resolve()):raise ValueError('Unsafe archive path')
  if entry.is_dir():dest.mkdir(parents=True,exist_ok=True)
  else:dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(entry.filename))
def main():
 if os.name!='nt':raise SystemExit('This helper is for Windows; use PostgreSQL + PostGIS packages on other platforms.')
 root=Path(__file__).resolve().parents[2];outer=root.parent;deps=outer/'dependencies';downloads=deps/'downloads';downloads.mkdir(parents=True,exist_ok=True)
 runtime=deps/'postgresql/pgsql';settings=outer/'local';settings.mkdir(exist_ok=True);(outer/'work').mkdir(exist_ok=True)
 records=[]
 for name,url in URLS.items():
  archive=downloads/name
  if not archive.exists():
   print('Downloading '+name,flush=True)
   temporary=archive.with_suffix('.zip.part')
   try:
    with urllib.request.urlopen(url,timeout=60) as response,temporary.open('wb') as f:
     while chunk:=response.read(1024*1024):f.write(chunk)
    verify_archive(temporary,SHA256[name])
    temporary.replace(archive)
   finally:temporary.unlink(missing_ok=True)
  digest=prepare_runtime_archive(archive,name,runtime,deps)
  records.append(dict(file=name,url=url,sha256=digest))
 (downloads/'runtime-downloads.json').write_text(json.dumps(records,indent=2))
 config_path=settings/'database.json'
 config=json.loads(config_path.read_text()) if config_path.exists() else dict(host='127.0.0.1',port=55432,database='native_plants',user='nativeplant_owner',password=secrets.token_urlsafe(32),runtime=str(runtime),data_dir=str(deps/'postgresql-data'))
 config_path.write_text(json.dumps(config,indent=2));data=Path(config['data_dir']);bin=Path(config['runtime'])/'bin';flags=subprocess.CREATE_NO_WINDOW
 (settings/'pgpass.conf').write_text(f"127.0.0.1:{config['port']}:*:{config['user']}:{config['password']}\n")
 env=dict(os.environ,PGPASSFILE=str(settings/'pgpass.conf'),PGCONNECT_TIMEOUT='5')
 if not (data/'PG_VERSION').exists():
  pw=settings/'init-password.txt';pw.write_text(config['password']+'\n')
  try:subprocess.run([str(bin/'initdb.exe'),'-D',str(data),'-U',config['user'],'--pwfile='+str(pw),'--auth=scram-sha-256','--locale=C','--encoding=UTF8'],check=True,creationflags=flags)
  finally:pw.unlink(missing_ok=True)
  with (data/'postgresql.conf').open('a') as f:f.write("\nlisten_addresses='127.0.0.1'\nport="+str(config['port'])+"\ntimezone='America/Toronto'\n")
 running=subprocess.run([str(bin/'pg_ctl.exe'),'-D',str(data),'status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags).returncode==0
 if not running:subprocess.run([str(bin/'pg_ctl.exe'),'-D',str(data),'-l',str(outer/'work/postgresql.log'),'-w','start'],check=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
 base=[str(bin/'psql.exe'),'-h',config['host'],'-p',str(config['port']),'-U',config['user'],'-v','ON_ERROR_STOP=1','-A','-t']
 exists=subprocess.run(base+['-d','postgres','-c',"SELECT 1 FROM pg_database WHERE datname='native_plants'"],env=env,capture_output=True,text=True,check=True,creationflags=flags).stdout.strip()
 if exists!='1':subprocess.run([str(bin/'createdb.exe'),'-h',config['host'],'-p',str(config['port']),'-U',config['user'],config['database']],env=env,check=True,creationflags=flags)
 subprocess.run(base+['-d',config['database'],'-c','CREATE EXTENSION IF NOT EXISTS postgis'],env=env,check=True,creationflags=flags)
 # Reader credentials are retained when rebuilding an existing workspace.
 if config.get('reader_user'):
  with (settings/'pgpass.conf').open('a') as f:f.write(f"127.0.0.1:{config['port']}:*:{config['reader_user']}:{config['reader_password']}\n")
 print('Local PostgreSQL/PostGIS ready on loopback. Credentials saved outside Git under local/.')
if __name__=='__main__':main()
