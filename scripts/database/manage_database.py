"""Manage the project's portable local PostgreSQL server without a system service.

Credentials and runtime files are stored outside the Git repository.
"""
import argparse,json,os,subprocess
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['start','stop','status','load','backup','check']);args=ap.parse_args()
 root=Path(__file__).resolve().parents[2];outer=root.parent;settings=outer/'local/database.json'
 if not settings.exists():raise SystemExit('Local database setup missing. See docs/CENTRAL_DATABASE.md; no credentials are stored in Git.')
 config=json.loads(settings.read_text());bin=Path(config['runtime'])/'bin';flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
 env=dict(os.environ,PGPASSFILE=str(outer/'local/pgpass.conf'),PGCONNECT_TIMEOUT='5')
 base=['-h',config['host'],'-p',str(config['port']),'-U',config['user'],'-d',config['database'],'-v','ON_ERROR_STOP=1']
 def sql(query):
  p=subprocess.run([str(bin/'psql.exe'),*base,'-c',query],env=env,text=True,capture_output=True,creationflags=flags)
  print(p.stdout);print(p.stderr,end='');return p.returncode
 if args.action in ['start','stop','status']:
  probe=subprocess.run([str(bin/'psql.exe'),*base,'-q','-t','-c','SELECT 1'],env=env,capture_output=True,text=True,creationflags=flags)
  if args.action=='status':
   print('Database connection: '+('ready' if probe.returncode==0 else 'unavailable'))
   raise SystemExit(0 if probe.returncode==0 else 1)
  if args.action=='start' and probe.returncode==0:
   print('Database is already running.');return
  command=[str(bin/'pg_ctl.exe'),'-D',config['data_dir']]
  if args.action=='start':command+=['-l',str(outer/'work/postgresql.log'),'-w','start']
  elif args.action=='stop':command+=['-m','fast','-w','stop']
  else:command+=['status']
  # DEVNULL prevents the persistent child server inheriting caller pipes.
  if args.action=='stop':
   p=subprocess.run(command,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,creationflags=flags,timeout=65)
   if p.returncode:print(p.stderr.strip()+'\nIf Windows process-control access is restricted, run this command in a normal PowerShell window as the same Windows user.')
  else:p=subprocess.run(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags,timeout=65)
  print(args.action+': '+('completed' if p.returncode==0 else 'not running or action failed (code '+str(p.returncode)+')'));raise SystemExit(p.returncode)
 if args.action=='load':
  for f in ['schema.postgresql.sql','load-data.postgresql.sql']:
   p=subprocess.run([str(bin/'psql.exe'),*base,'-q','-f',str(root/'data/central'/f)],env=env,capture_output=True,text=True,creationflags=flags)
   if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
   print('Loaded '+f)
 elif args.action=='backup':
  dest=outer/'backups/native-plants-central.dump';dest.parent.mkdir(exist_ok=True)
  p=subprocess.run([str(bin/'pg_dump.exe'),'-h',config['host'],'-p',str(config['port']),'-U',config['user'],'-d',config['database'],'--format=custom','--no-owner','--no-acl','-f',str(dest)],env=env,capture_output=True,text=True,creationflags=flags)
  if p.returncode:print(p.stderr);raise SystemExit(p.returncode)
  print('Saved backup: '+str(dest))
 else:
  raise SystemExit(sql("SET search_path=native_plants,public; SELECT version(); SELECT postgis_full_version(); SELECT count(*) AS plants FROM plants; SELECT count(*) AS valid_spatial_regions FROM regions WHERE geom IS NOT NULL AND ST_IsValid(geom); SELECT region_name,region_type FROM regions WHERE ST_Covers(geom,ST_SetSRID(ST_Point(-79.68,43.45),4326));"))

if __name__=='__main__':main()
