"""Current-HTML SEO improvements. No authentication or media changes."""
import re,json,hashlib
from html import escape
from urllib.parse import urlsplit,urljoin
ORIGIN='https://mediastudio.velaurlabs.com'
PAGES={'index.html':'/','pricing.html':'/pricing','privacy.html':'/privacy','terms.html':'/terms','login.html':'/login'}
META={
 'index.html':('Online Video Trimmer & MP3 Converter | Velaur Media Studio','Trim uploaded videos or supported public links online. Export MP4 video or extract MP3 audio from a clip. Google sign-in and plan limits apply.'),
 'pricing.html':('Plans & Free Trial | Velaur Media Studio','Compare Creator, Pro and Studio export allowances, upload sizes and processing limits. Check trial availability, planned pricing and account access.'),
 'privacy.html':('Privacy Policy | Velaur Media Studio','Read how Velaur Media Studio handles Google sign-in, server-side video processing, usage records, cookies and account data requests.'),
 'terms.html':('Terms & Conditions | Velaur Media Studio','Read the terms for media processing, trial access, planned subscriptions, usage limits and export availability in Velaur Media Studio.')}
STYLE_RE=re.compile(r'<link\b[^>]*\brel="stylesheet"[^>]*>',re.I)
WORKFLOWS='''<!-- seo-workflows-1:start -->
<section class="seo-workflows" aria-labelledby="seo-workflows-title">
 <h2 id="seo-workflows-title" class="section-title">Trim video or extract audio online</h2>
 <p class="section-description">Velaur Media Studio is a browser-based video tool by VELAUR LABS. Previews and exports are prepared on our server. Sign in with Google, check your access, then open the Studio.</p>
 <div class="benefits">
  <article><h3>How do I trim a video?</h3><p>Upload a video or paste a supported public link. Click Preview, set the start and end timestamps, choose MP4, then click Export media. Follow the processing status and save the file when it is ready.</p></article>
  <article><h3>How do I extract MP3 audio?</h3><p>Select MP3 instead of MP4. Keep the full video or choose a clip, then export. The source needs an audio track. MP3 conversion creates an audio file; it does not improve the source recording.</p></article>
  <article><h3>Why can a video link fail?</h3><p>Private, removed or region-restricted videos may be unavailable. A source service can also refuse access. Upload an authorized local copy as an alternative. Processing time depends on the source, clip length and server capacity.</p></article>
 </div>
 <p class="seo-workflow-links"><a href="/studio">Open the video studio</a> · <a href="/pricing">Compare plans and trial access</a> · <a href="/privacy">How media processing uses your data</a></p>
</section>
<!-- seo-workflows-1:end -->'''
def attributes(tag):
 return dict(re.findall(r'([\w:-]+)=["\']([^"\']*)["\']',tag))
def image_dimensions(text):
 def fix(m):
  tag=m[0];d=attributes(tag);src=urlsplit(d.get('src','')).path
  dims={'/static/brand-wordmark.webp':(720,240),'/static/velaur-labs-original.png':(860,198)}.get(src)
  if not dims:return tag
  for k,v in zip(('width','height'),dims):
   if k not in d:tag=tag[:-1]+f' {k}="{v}">'
  if 'decoding' not in d:tag=tag[:-1]+' decoding="async">'
  return tag
 return re.sub(r'<img\b[^>]*>',fix,text)
def metadata(text,name):
 if name in META:
  title,desc=META[name]
  text=re.sub(r'<title>.*?</title>','<title>'+escape(title)+'</title>',text,count=1,flags=re.S)
  for attr,key,value in [('name','description',desc),('property','og:title',title),('property','og:description',desc),('name','twitter:title',title),('name','twitter:description',desc)]:
   pattern=r'<meta\b[^>]*\b'+attr+'="'+re.escape(key)+r'"[^>]*>'
   tag=f'<meta {attr}="{key}" content="{escape(value,quote=True)}">'
   text=re.sub(pattern,lambda m:tag,text,count=1)
 return text
def schema(text,name):
 if name=='login.html':return text
 def fix(m):
  data=json.loads(m[1]);nodes=data.get('@graph',[data])
  for node in nodes:
   if node.get('@type')=='Organization' and node.get('name')=='VELAUR LABS':
    node['logo']=ORIGIN+'/static/velaur-labs-original.png'
  return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+'</script>'
 text=re.sub(r'<script\s+type="application/ld\+json">(.*?)</script>',fix,text,flags=re.S)
 text=re.sub(r'<!-- seo-page-schema:start -->.*?<!-- seo-page-schema:end -->','',text,flags=re.S)
 title=META[name][0]
 page={'@context':'https://schema.org','@type':'WebPage','@id':ORIGIN+PAGES[name]+'#webpage','url':ORIGIN+PAGES[name],'name':title,'inLanguage':'en','isPartOf':{'@id':ORIGIN+'/#website'},'about':{'@id':ORIGIN+'/#app'}}
 return text.replace('</head>','<!-- seo-page-schema:start --><script type="application/ld+json">'+json.dumps(page,separators=(',',':'))+'</script><!-- seo-page-schema:end --></head>')
def patch(text,name):
 if text.count('</head>')!=1 or text.count('</body>')!=1:raise ValueError('Unexpected HTML structure: '+name)
 text=metadata(text,name);text=image_dimensions(text);text=schema(text,name)
 if name=='pricing.html':
  text=re.sub(r'<h2([^>]*\bid="pricing-title"[^>]*)>(.*?)</h2>',r'<h1\1>\2</h1>',text,count=1,flags=re.S)
 if name=='index.html':
  text=re.sub(r'<!-- seo-workflows-1:start -->.*?<!-- seo-workflows-1:end -->','',text,flags=re.S)
  if '<section id="media-faq"' not in text:raise ValueError('Expected homepage FAQ not found')
  text=text.replace('<section id="media-faq"',WORKFLOWS+'<section id="media-faq"',1)
 text=re.sub(r'<link\b[^>]*href="/static/seo-content-v1\.css[^"<>]*"[^>]*>','',text)
 return text.replace('</head>','<link rel="stylesheet" href="/static/seo-content-v1.css?v=1"></head>')
def bundle_styles(text,read_asset):
 matches=list(STYLE_RE.finditer(text))
 if len(matches)<2:return text,{},'No bundle needed'
 between=text[matches[0].start():matches[-1].end()]
 between=re.sub(r'<script\s+type="application/ld\+json">.*?</script>','',between,flags=re.S)
 if re.search(r'<style\b|<script\b',between,re.I):return text,{},'Skipped: interleaved styles/scripts'
 parts=[];sources=[];seen=set()
 def add(path):
  css=read_asset(path.removeprefix('/static/'))
  header=re.match(r'/\* seo-bundle-sources:(.*?) \*/',css,re.S)
  if header:
   for source in json.loads(header[1]):add(source)
   return
  if path in seen:return
  seen.add(path);sources.append(path)
  if re.search(r'@import\b|@layer\s*;',css,re.I):raise ValueError('Cannot bundle imported/layer-order CSS')
  css=re.sub(r'@charset\s+[^;]+;','',css,flags=re.I)
  def urlfix(q):
   value=q[1].strip().strip('\"\'')
   if value.startswith(('/','#','data:','http:','https:','//')):return q[0]
   return 'url("'+urljoin(path,value)+'")'
  css=re.sub(r'url\(([^)]+)\)',urlfix,css)
  parts.append('/* Source: '+path+' */\n'+css)
 for m in matches:
  d=attributes(m[0]);u=urlsplit(d.get('href',''))
  if u.scheme or u.netloc or not u.path.startswith('/static/') or d.get('media') or 'disabled' in m[0]:return text,{},'Skipped: nonlocal/conditional stylesheet'
  try:add(u.path)
  except ValueError:return text,{},'Skipped: import or cascade layer order'
 merged='/* seo-bundle-sources:'+json.dumps(sources,separators=(',',':'))+' */\n'+'\n'.join(parts)+'\n';name='seo-style-'+hashlib.sha256(merged.encode()).hexdigest()[:16]+'.css'
 # Keep the first stylesheet position, preserve all rule/source ordering.
 first=True
 def swap(m):
  nonlocal first
  if first:first=False;return '<link rel="stylesheet" href="/static/'+name+'?v=1">'
  return ''
 return STYLE_RE.sub(swap,text),{name:merged},f'{len(parts)} stylesheet requests -> 1 (same rules/order)'
