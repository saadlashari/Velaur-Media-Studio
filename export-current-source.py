"""Export allowlisted application source from velaur-api, never its database/env/cookies."""
import subprocess,sys
from pathlib import Path
SCRIPT=r'''
import ast,io,re,sys,zipfile
from pathlib import Path
root=Path('/app')
extensions={'.py','.html','.js','.css','.svg','.webp','.png','.jpg','.jpeg','.ico','.woff','.woff2'}
files=[p for p in root.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() in extensions and '.before' not in p.name and not p.name.startswith('.')]
for directory in ['static','assets']:
 d=root/directory
 if d.is_dir() and not d.is_symlink():
  files += [p for p in d.rglob('*') if p.is_file() and not p.is_symlink() and not any(x.startswith('.') for x in p.relative_to(root).parts) and p.suffix.lower() in extensions]
files=[p for p in files if not any(word in p.name.lower() for word in ['cookie','credential','backup','private-key'])]
if not any(p.name=='main.py' for p in files):raise SystemExit('STOP: main.py not found')
if sum(p.stat().st_size for p in files)>40*1024*1024:raise SystemExit('STOP: source exceeds 40 MB; review the allowlist')
for p in files:
 if p.suffix.lower() not in {'.py','.js','.html','.css'}:continue
 text=p.read_text(encoding='utf-8-sig')
 if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',text):raise SystemExit('STOP: possible private key in '+p.name)
 if p.suffix=='.py':
  tree=ast.parse(text)
  for node in ast.walk(tree):
   if isinstance(node,(ast.Assign,ast.AnnAssign)):
    targets=node.targets if isinstance(node,ast.Assign) else [node.target]
    value=node.value
    for target in targets:
     if isinstance(target,ast.Name) and re.search(r'(?:password|client_secret|session_secret|database_url|api_key)$',target.id,re.I) and isinstance(value,ast.Constant) and isinstance(value.value,str) and value.value and value.value not in {'changeme','placeholder'}:
      raise SystemExit('STOP: review hard-coded credential assignment in '+p.name+' before exporting')
 if re.search(r'(?:client_secret|api_key|database_url|password)\s*[:=]\s*[\"\x27](?![\"\x27])[^\"\x27]{12,}[\"\x27]',text,re.I):
  raise SystemExit('STOP: review possible embedded credential in '+p.name)
buffer=io.BytesIO()
with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
 for p in sorted(files):archive.writestr('app/'+str(p.relative_to(root)),p.read_bytes())
sys.stdout.buffer.write(buffer.getvalue())
'''
def main():
 output=Path.home()/'Velaur-Media-Studio'/'Velaur-current-source-safe.zip'
 if output.exists():raise SystemExit('STOP: archive already exists. Rename it first to preserve the previous export.')
 result=subprocess.run(['docker','exec','-i','velaur-api','python','-c',SCRIPT],capture_output=True)
 if result.returncode:
  print(result.stderr.decode(errors='replace')[-800:],file=sys.stderr);raise SystemExit(result.returncode)
 if not result.stdout.startswith(b'PK'):raise SystemExit('STOP: no valid ZIP returned')
 output.write_bytes(result.stdout)
 print('EXPORTED:',output)
 print('Application source/assets only. No .env, databases, downloads, sessions or cookie files. Review before sharing; automated checks are not a guarantee of secret detection.')
if __name__=='__main__':main()
