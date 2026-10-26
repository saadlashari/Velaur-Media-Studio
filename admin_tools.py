"""Administrator-only user controls. Reuses existing session and CSRF middleware."""
import json,re,time,hashlib
from activity_labels import describe
# activity-labels-1
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import APIRouter,HTTPException,Request
import accounts as db
from identity import admin,reason
router=APIRouter()
BOUNDS={'exports':(1,1000),'previews':(1,2000),'mp3_exports':(0,10000),'active':(1,4),'upload_gb':(1,8),'seconds':(60,3600000),'height':(720,2160),'source_seconds':(60,10800)}

async def payload(request):
 try:body=await request.json()
 except (ValueError,TypeError):raise HTTPException(400,'Send a valid JSON object.')
 if type(body) is not dict:raise HTTPException(400,'Send a valid JSON object.')
 return body

def target(c,uid):
 u=db.row(c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())
 if not u:raise HTTPException(404,'User not found.')
 return u

def validate_limits(data):
 if type(data) is not dict or not set(data)<=set(BOUNDS):raise HTTPException(400,'Unknown user limit.')
 for key,value in data.items():
  low,high=BOUNDS[key]
  if type(value) is not int or not low<=value<=high:raise HTTPException(400,'Invalid '+key+' limit.')
  if key=='height' and value not in (720,1080,2160):raise HTTPException(400,'Choose 720p, 1080p or 2160p.')
 return data

@router.get('/api/admin/users/{uid}/detail')
def detail(uid:str,request:Request):
 admin(request)
 with db.tx() as c:
  u=target(c,uid);access=db.access(c,u);usage=db.usage(c,u)
  record=db.row(c.execute('SELECT * FROM user_limit_overrides WHERE owner=?',(uid,)).fetchone())
  session=c.execute('SELECT MAX(seen) AS latest FROM sessions WHERE user_id=?',(uid,)).fetchone()['latest']
  job=c.execute('SELECT MAX(updated) AS latest FROM media_usage WHERE owner=?',(uid,)).fetchone()['latest']
  count=c.execute('SELECT count(*) AS n FROM sessions WHERE user_id=? AND expires>? AND seen>?',(uid,time.time(),time.time()-86400)).fetchone()['n']
  s=db.settings(c);base=s['plans'][u.get('plan') or 'creator']
  return dict(user=db.user_info(u),access=access,usage=usage,base_limits=base,overrides=json.loads(record['limits']) if record else {},active_sessions=count,last_activity=max(u['last_login'],session or 0,job or 0),override_updated=record['updated'] if record else None)

@router.patch('/api/admin/users/{uid}/limits')
async def update_limits(uid:str,request:Request):
 actor=admin(request);body=await payload(request);why=reason(body)
 if set(body)-{'reason','limits'}:raise HTTPException(400,'Unknown request field.')
 limits=validate_limits(body.get('limits'))
 with db.tx(True) as c:
  u=target(c,uid)
  if u['role']=='admin' and uid!=actor['id']:raise HTTPException(403,'Other administrator accounts are managed from the server.')
  if c.execute("SELECT id FROM media_usage WHERE owner=? AND state IN ('queued','running')",(uid,)).fetchone():raise HTTPException(409,"Wait for this user's active jobs to finish before changing limits.")
  old=db.row(c.execute('SELECT limits FROM user_limit_overrides WHERE owner=?',(uid,)).fetchone())
  c.execute('INSERT INTO user_limit_overrides(owner,limits,updated,actor) VALUES(?,?,?,?) ON CONFLICT(owner) DO UPDATE SET limits=excluded.limits,updated=excluded.updated,actor=excluded.actor',(uid,json.dumps(limits),time.time(),actor['id']))
  db.audit(c,actor['id'],'user.limits.update',uid,dict(reason=why,before=json.loads(old['limits']) if old else {},after=limits))
 return {'ok':True}

@router.patch('/api/admin/users/{uid}/access-end')
async def extend_access(uid:str,request:Request):
 actor=admin(request);body=await payload(request);why=reason(body);days=body.get('days')
 if type(days) is not int or not 1<=days<=366:raise HTTPException(400,'Choose 1 to 366 additional days.')
 with db.tx(True) as c:
  u=target(c,uid)
  if u['role']=='admin' and uid!=actor['id']:raise HTTPException(403,'Other administrator accounts are managed from the server.')
  if not u.get('period_start'):raise HTTPException(409,'Grant a plan before extending its access period.')
  previous=u.get('period_end') or 0;new=max(time.time(),previous)+days*86400
  c.execute('UPDATE users SET period_end=? WHERE id=?',(new,uid))
  db.audit(c,actor['id'],'user.access.extend',uid,dict(reason=why,days=days,before=previous,after=new))
 return {'ok':True,'expires_at':new}

def session_ref(token_hash):return hashlib.sha256(token_hash.encode()).hexdigest()[:24]

@router.get('/api/admin/users/{uid}/sessions')
def sessions(uid:str,request:Request,offset:int=0):
 admin(request)
 if offset<0 or offset>100000:raise HTTPException(400,'Invalid page.')
 from identity import COOKIE
 current=db.digest(request.cookies.get(COOKIE) or '')
 with db.tx() as c:
  target(c,uid)
  total=c.execute('SELECT count(*) AS n FROM sessions WHERE user_id=?',(uid,)).fetchone()['n']
  rows=c.execute('SELECT token_hash,created,expires,seen FROM sessions WHERE user_id=? ORDER BY seen DESC LIMIT 50 OFFSET ?',(uid,offset)).fetchall()
  now=time.time()
  return dict(sessions=[dict(id=session_ref(r['token_hash']),created=r['created'],seen=r['seen'],expires=r['expires'],active=r['expires']>now and r['seen']>now-86400,current=r['token_hash']==current) for r in rows],next_offset=offset+50 if offset+len(rows)<total else None)

@router.post('/api/admin/users/{uid}/sessions/revoke')
async def revoke(uid:str,request:Request):
 actor=admin(request);body=await payload(request);why=reason(body);selection=body.get('session')
 if selection!='all' and (not isinstance(selection,str) or not re.fullmatch('[a-f0-9]{24}',selection)):raise HTTPException(400,'Select a valid session.')
 # Avoid accidentally signing the administrator out while operating the console.
 if uid==actor['id']:raise HTTPException(400,'Use Sign out for your own account. Session revocation here is for other users.')
 with db.tx(True) as c:
  u=target(c,uid)
  if u['role']=='admin':raise HTTPException(403,'Other administrator accounts are managed from the server.')
  rows=c.execute('SELECT token_hash FROM sessions WHERE user_id=?',(uid,)).fetchall()
  selected=[r['token_hash'] for r in rows if selection=='all' or session_ref(r['token_hash'])==selection]
  if selection!='all' and not selected:raise HTTPException(404,'This session no longer exists.')
  for token in selected:c.execute('DELETE FROM sessions WHERE user_id=? AND token_hash=?',(uid,token))
  db.audit(c,actor['id'],'user.sessions.revoke',uid,dict(reason=why,count=len(selected)))
 return {'ok':True,'revoked':len(selected)}

def record_download_request(uid,jid):
 with db.tx(True) as c:
  c.execute('INSERT INTO media_deliveries(job_id,owner,requests,last_requested) VALUES(?,?,1,?) ON CONFLICT(job_id) DO UPDATE SET requests=media_deliveries.requests+1,last_requested=excluded.last_requested',(jid,uid,time.time()))

def job_detail(row):
 import main as media
 result=dict(id=row['id'],kind=row['kind'],state=row['state'],created=row['created'],updated=row['updated'],seconds=row['seconds'],output_format=row.get('output_format','mp4'))
 with media.lock:status=dict(media.jobs.get(row['id']) or {})
 if not status:
  try:
   path=media.JOBS_DIR/row['id']/'status.json'
   if path.is_file() and path.stat().st_size<1024*1024:status=json.loads(path.read_text())
  except (OSError,ValueError):pass
 if status.get('_owner') not in (None,row['owner']):status={}
 info=status.get('media') or {};export=status.get('result') or {}
 parsed=urlsplit(status.get('_source_url') or '')
 source_url=parsed.geturl() if parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password else None
 result['source_url']=source_url
 result.update(failed_stage=status.get('failed_stage'),stage=status.get('stage') or row['state'],title=info.get('title') or export.get('filename') or 'Media job',percent=status.get('percent'),error=str(status.get('error') or '')[:1200],source_host=urlsplit(status.get('_source_url') or '').hostname)
 filename=str(export.get('filename') or status.get('_file') or '').lower()
 if row.get('kind')=='export':
  if filename.endswith('.mp3'):result['output_format']='mp3'
  elif filename.endswith('.mp4'):result['output_format']='mp4'
 result['file_ready']=row['state']=='done' and bool(status.get('_file')) and Path(status['_file']).is_file()
 return result

@router.get('/api/admin/users/{uid}/jobs')
def jobs(uid:str,request:Request,offset:int=0,state:str='all'):
 admin(request)
 if offset<0 or offset>100000 or state not in ('all','queued','running','done','error'):raise HTTPException(400,'Invalid job filter.')
 with db.tx() as c:
  target(c,uid);args=(uid,state,state)
  where="owner=? AND (?='all' OR state=?)"
  total=c.execute('SELECT count(*) AS n FROM media_usage WHERE '+where,args).fetchone()['n']
  rows=[db.row(r) for r in c.execute('SELECT * FROM media_usage WHERE '+where+' ORDER BY created DESC LIMIT 50 OFFSET ?',args+(offset,)).fetchall()]
  deliveries={r['job_id']:db.row(r) for r in c.execute('SELECT * FROM media_deliveries WHERE owner=?',(uid,)).fetchall()}
 result=[]
 for row in rows:
  item=job_detail(row);d=deliveries.get(row['id'],{});item.update(download_requests=d.get('requests',0),last_download_request=d.get('last_requested'),last_completed=d.get('last_completed'),completed_transfers=d.get('completed',0));item.update(describe(item));result.append(item)
 return {'jobs':result,'next_offset':offset+50 if offset+len(rows)<total else None,'total':total}

# activity-outcomes-2
def record_download_complete(uid,jid,size):
 with db.tx(True) as c:
  c.execute("INSERT INTO media_deliveries(job_id,owner,requests,last_requested,completed,last_completed,bytes_completed) VALUES(?,?,1,?,1,?,?) ON CONFLICT(job_id) DO UPDATE SET completed=media_deliveries.completed+1,last_completed=excluded.last_completed,bytes_completed=excluded.bytes_completed",(jid,uid,time.time(),time.time(),size))
