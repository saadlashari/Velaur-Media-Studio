"""Reversible public-page SEO patch; current VPS files are authoritative."""
import argparse,hashlib,json,shutil,subprocess,time
from pathlib import Path
from seo_patch import PAGES,patch,bundle_styles
BASE=Path(__file__).resolve().parent
def docker(*args,check=True):
 r=subprocess.run(['docker',*args],capture_output=True,text=True)
 if check and r.returncode:raise RuntimeError(r.stderr[-700:])
 return r
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');parser.add_argument('--no-css-bundle',action='store_true');args=parser.parse_args()
 for name,digest in json.loads((BASE/'MANIFEST.json').read_text()).items():
  if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:raise SystemExit('STOP: checksum mismatch: '+name)
 project=Path.home()/'Velaur-Media-Studio';backup=project/('backup-before-seo-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()));backup.mkdir(mode=0o700);stage=backup/'prepared';stage.mkdir();saved=[];assets={'seo-content-v1.css':(BASE/'seo-content-v1.css').read_text()};report=[]
 def read_asset(name):
  if name in assets:return assets[name]
  if '/' in name or '..' in name:raise ValueError('Unexpected asset path')
  target=backup/('asset-'+name)
  if not target.exists():docker('cp','velaur-api:/app/'+name,str(target))
  return target.read_text(encoding='utf-8-sig')
 for name in PAGES:
  docker('cp','velaur-api:/app/'+name,str(backup/name));saved.append(name)
  original=(backup/name).read_text(encoding='utf-8-sig');changed=patch(original,name)
  if not args.no_css_bundle:
   changed,new,note=bundle_styles(changed,read_asset);assets.update(new);report.append(name+': '+note)
  # Existing handlers/scripts must be preserved exactly.
  import re
  assert re.findall(r'<script\b[^>]*src=[^>]+>',original)==re.findall(r'<script\b[^>]*src=[^>]+>',changed)
  assert re.findall(r'\bid="([^"]+)"',original)==[i for i in re.findall(r'\bid="([^"]+)"',changed) if not i.startswith('seo-workflows')]
  (stage/name).write_text(changed,encoding='utf-8')
 for name,body in assets.items():
  if docker('exec','velaur-api','test','-f','/app/'+name,check=False).returncode==0:
   docker('cp','velaur-api:/app/'+name,str(backup/name));saved.append(name)
  (stage/name).write_text(body,encoding='utf-8')
 (backup/'changes.json').write_text(json.dumps(report,indent=2))
 rollback='import subprocess,shutil\nfrom pathlib import Path\nb=Path(__file__).resolve().parent\nfor n in '+repr(saved)+':\n subprocess.run(["docker","cp",str(b/n),"velaur-api:/app/"+n],check=True)\n shutil.copy2(b/n,b.parent/n)\nprint("Previous public pages restored. Hard-refresh the website.")\n'
 (backup/'rollback.py').write_text(rollback)
 print('\n'.join(report));print('BACKUP:',backup)
 if args.dry_run:print('DRY RUN: prepared files only; no live changes.');return
 try:
  for name in [*assets,*PAGES]:docker('cp',str(stage/name),'velaur-api:/app/'+name)
  verification=docker('exec','velaur-api','python','-c','import urllib.request; s=urllib.request.urlopen("http://127.0.0.1:8000/",timeout=15).read(); assert b"seo-workflows-1:start" in s; p=urllib.request.urlopen("http://127.0.0.1:8000/pricing",timeout=15).read(); assert b\'<h1 id="pricing-title"\' in p; assert urllib.request.urlopen("http://127.0.0.1:8000/static/seo-content-v1.css?v=1",timeout=15).status==200')
  for name in [*assets,*PAGES]:shutil.copy2(stage/name,project/name)
 except BaseException:
  for name in saved:
   docker('cp',str(backup/name),'velaur-api:/app/'+name)
   shutil.copy2(backup/name,project/name)
  print('Automatic rollback restored previous container pages.');raise
 print('INSTALLED: SEO public-page fixes. No restart, auth/media changes, analytics collection or database migration.')
 print('ROLLBACK: python3',backup/'rollback.py')
 print('NEXT: python3',BASE/'verify-live.py')
if __name__=='__main__':main()
