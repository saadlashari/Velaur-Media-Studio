"""Public HTTP recrawl. Does not sign in, export or change user data."""
import argparse,json,re,time,urllib.request,urllib.error,xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import urljoin,urlsplit
class Tags(HTMLParser):
 def __init__(self):super().__init__();self.tags=[]
 def handle_starttag(self,t,a):self.tags.append((t,dict(a)))
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',default='https://mediastudio.velaurlabs.com');p.add_argument('--output',default='seo-live-verification.json');a=p.parse_args();base=a.base.rstrip('/');rows=[]
 def get(path):
  t=time.monotonic()
  try:r=urllib.request.urlopen(base+path,timeout=30)
  except urllib.error.HTTPError as e:r=e
  return r,r.read().decode('utf-8'),round(time.monotonic()-t,3)
 for path in ['/','/pricing','/privacy','/terms','/login','/studio','/dashboard','/admin','/robots.txt','/sitemap.xml','/seo-audit-missing-page']:
  r,s,seconds=get(path);row={'path':path,'status':r.status,'final_url':r.url,'observed_seconds':seconds};rows.append(row)
  if path in ['/','/pricing','/privacy','/terms']:
   assert r.status==200,(path,r.status);tags=Tags();tags.feed(s)
   assert len([t for t,d in tags.tags if t=='h1'])==1,(path,'H1')
   assert any(t=='link' and d.get('rel')=='canonical' and d.get('href')=='https://mediastudio.velaurlabs.com'+path for t,d in tags.tags),(path,'canonical')
   assert not any(t=='meta' and d.get('name')=='robots' and 'noindex' in d.get('content','') for t,d in tags.tags)
   for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',s,re.S):json.loads(raw)
   styles=[d['href'] for t,d in tags.tags if t=='link' and d.get('rel')=='stylesheet'];row['stylesheets']=len(styles)
   for u in styles:
    asset=urllib.request.urlopen(urljoin(base,u),timeout=30);assert asset.status==200
   assert 'seo-page-schema:start' in s
  if path=='/':assert 'seo-workflows-1:start' in s
  if path in ['/studio','/dashboard','/admin']:
   assert urlsplit(r.url).path=='/login',(path,'guest access changed')
  if path=='/login':assert 'noindex' in s
  if path=='/sitemap.xml':
   root=ET.fromstring(s);urls=[n.text for n in root.iter() if n.tag.endswith('loc')];assert len(urls)==4 and not any('/admin' in u or '/studio' in u for u in urls)
  if path=='/seo-audit-missing-page':assert r.status==404
  print(path,r.status,seconds,'seconds')
 open(a.output,'w').write(json.dumps(rows,indent=2));print('PASS: public metadata/schema, asset serving, sitemap and guest-route checks. CWV and signed-in exports are not tested by this script.')
if __name__=='__main__':main()
