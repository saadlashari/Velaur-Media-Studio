"""Apply only logo, footer and glass styling to the current live HTML."""
import hashlib,json,re,shutil,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
PAGES=['index.html','pricing.html','studio.html','login.html','dashboard.html','admin.html','privacy.html','terms.html']
ASSETS=['nav-hover-v14.css','nav-hover-v14.js']
def docker(*args,check=True):
    r=subprocess.run(['docker',*args],capture_output=True,text=True)
    if check and r.returncode:raise RuntimeError(r.stderr[-600:])
    return r
def patch(text):
    if text.count('</head>')!=1:raise ValueError('Unexpected HTML structure; no live changes.')
    text=re.sub(r'<link\b[^>]*href="/static/nav-hover-v14\.css[^"<>]*"[^>]*>','',text)
    text=re.sub(r'<script\b[^>]*src="/static/nav-hover-v14\.js[^"<>]*"[^>]*>\s*</script>','',text)
    if text.count('</body>')!=1:raise ValueError('Unexpected body structure; no live changes.')
    text=text.replace('</head>','<link rel="stylesheet" href="/static/nav-hover-v14.css?v=14"></head>')
    return text.replace('</body>','<script src="/static/nav-hover-v14.js?v=14"></script></body>')

def main():
    for name,digest in json.loads((BASE/'MANIFEST.json').read_text()).items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:raise SystemExit('STOP: checksum mismatch: '+name)
    project=Path.home()/'Velaur-Media-Studio'
    backup=project/('backup-before-nav-hover-14-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()))
    backup.mkdir(mode=0o700);stage=backup/'prepared';stage.mkdir();saved=[]
    for name in PAGES:
        docker('cp','velaur-api:/app/'+name,str(backup/name));saved.append(name)
        (stage/name).write_text(patch((backup/name).read_text(encoding='utf-8-sig')),encoding='utf-8')
    for name in ASSETS:
        if docker('exec','velaur-api','test','-f','/app/'+name,check=False).returncode==0:
            docker('cp','velaur-api:/app/'+name,str(backup/name));saved.append(name)
        shutil.copy2(BASE/name,stage/name)
    rollback='import subprocess,shutil\nfrom pathlib import Path\nb=Path(__file__).resolve().parent\nfor n in '+repr(saved)+':\n subprocess.run(["docker","cp",str(b/n),"velaur-api:/app/"+n],check=True)\n shutil.copy2(b/n,b.parent/n)\nprint("Previous UI restored. Reload the browser.")\n'
    (backup/'rollback.py').write_text(rollback)
    try:
        for name in ASSETS+PAGES:docker('cp',str(stage/name),'velaur-api:/app/'+name)
        docker('exec','velaur-api','python','-c','import urllib.request; assert b"nav and hover v1.4" in urllib.request.urlopen("http://127.0.0.1:8000/static/nav-hover-v14.css",timeout=10).read(); assert b"nav-hover-v14.js" in urllib.request.urlopen("http://127.0.0.1:8000/",timeout=10).read()')
        for name in ASSETS+PAGES:shutil.copy2(stage/name,project/name)
    except BaseException:
        for name in saved:docker('cp',str(backup/name),'velaur-api:/app/'+name)
        raise
    print('UPDATED: centered navigation, sign-in icon and balanced hover states. No restart or backend changes.')
    print('BACKUP:',backup);print('ROLLBACK: python3',backup/'rollback.py')
if __name__=='__main__':main()
