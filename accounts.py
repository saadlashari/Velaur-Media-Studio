"""Persistent accounts, entitlements and atomic quota reservations.
PostgreSQL in production. Explicit SQLite mode exists only for local tests.
"""
import os, json, time, uuid, hashlib, secrets, sqlite3
from contextlib import contextmanager
from fastapi import HTTPException

PLANS = {
 "creator": dict(name="Creator", monthly=2, yearly=20, exports=10, previews=30, active=1, upload_gb=1, seconds=36000, height=1080, source_seconds=10800),
 "pro": dict(name="Pro", monthly=5, yearly=50, exports=25, previews=75, active=1, upload_gb=2, seconds=108000, height=1080, source_seconds=10800),
 "studio": dict(name="Studio", monthly=10, yearly=100, exports=50, previews=150, active=2, upload_gb=4, seconds=270000, height=2160, source_seconds=10800),
}
for _plan, _audio_limit in (("creator",30),("pro",75),("studio",0)):
 PLANS[_plan]["mp3_exports"] = _audio_limit
DEFAULTS = dict(mode="timed", trial_days=30, new_trials=True, plans=PLANS)
URL=os.getenv("DATABASE_URL","")
DEV=os.getenv("VELAUR_SQLITE_DEV")=="1"
def digest(value): return hashlib.sha256(value.encode()).hexdigest()
class Conn:
 def __init__(self, raw): self.raw=raw
 def execute(self, sql, args=()):
  return self.raw.execute(sql.replace("?", "%s") if not DEV else sql,args)
@contextmanager
def tx(write=False):
 if DEV:
  raw=sqlite3.connect(URL.removeprefix("sqlite:///"),timeout=20)
  raw.row_factory=sqlite3.Row
  raw.execute("PRAGMA foreign_keys=ON")
  raw.execute("BEGIN IMMEDIATE" if write else "BEGIN")
 else:
  if not URL.startswith(("postgresql://","postgres://")): raise RuntimeError("A PostgreSQL DATABASE_URL is required")
  import psycopg
  from psycopg.rows import dict_row
  raw=psycopg.connect(URL,row_factory=dict_row,connect_timeout=8)
 c=Conn(raw)
 try:
  if write and not DEV: c.execute("SELECT id FROM app_settings WHERE id=1 FOR UPDATE").fetchone()
  yield c
  raw.commit()
 except BaseException:
  raw.rollback();raise
 finally: raw.close()
def row(r): return dict(r) if r else None
def audit(c,actor,action,target=None,details=None):
 c.execute("INSERT INTO audit_log(id,actor,action,target,details,created) VALUES(?,?,?,?,?,?)",
           (uuid.uuid4().hex,actor,action,target,json.dumps(details or {}),time.time()))
def initialize():
 schema=[
 "CREATE TABLE IF NOT EXISTS app_settings(id INTEGER PRIMARY KEY, value TEXT NOT NULL)",
 "CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,google_sub TEXT UNIQUE NOT NULL,email TEXT NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',status TEXT NOT NULL DEFAULT 'active',created DOUBLE PRECISION NOT NULL,last_login DOUBLE PRECISION NOT NULL,trial_used INTEGER NOT NULL DEFAULT 0,plan TEXT,access_kind TEXT,period_start DOUBLE PRECISION,period_end DOUBLE PRECISION)",
 "CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,expires DOUBLE PRECISION NOT NULL,seen DOUBLE PRECISION NOT NULL)",
 "CREATE TABLE IF NOT EXISTS oauth_transactions(state_hash TEXT PRIMARY KEY,binder_hash TEXT NOT NULL,nonce TEXT NOT NULL,verifier TEXT NOT NULL,expires DOUBLE PRECISION NOT NULL)",
 "CREATE TABLE IF NOT EXISTS media_usage(id TEXT PRIMARY KEY,owner TEXT NOT NULL REFERENCES users(id),kind TEXT NOT NULL,state TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,updated DOUBLE PRECISION NOT NULL,period_start DOUBLE PRECISION NOT NULL,seconds DOUBLE PRECISION NOT NULL DEFAULT 0)",
 "CREATE INDEX IF NOT EXISTS usage_owner_created ON media_usage(owner,created)",
 "CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(user_id)",
 "CREATE TABLE IF NOT EXISTS audit_log(id TEXT PRIMARY KEY,actor TEXT,action TEXT NOT NULL,target TEXT,details TEXT NOT NULL,created DOUBLE PRECISION NOT NULL)",
 "CREATE TABLE IF NOT EXISTS rate_limits(bucket TEXT PRIMARY KEY,hits INTEGER NOT NULL,expires DOUBLE PRECISION NOT NULL)",
 "CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY,applied DOUBLE PRECISION NOT NULL)",
 ]
 # Initialization intentionally avoids the settings row lock until the table exists.
 with tx() as c:
  for statement in schema:c.execute(statement)
  c.execute("INSERT INTO app_settings(id,value) VALUES(1,?) ON CONFLICT(id) DO NOTHING",(json.dumps(DEFAULTS),))
  c.execute("INSERT INTO schema_versions(version,applied) VALUES(1,?) ON CONFLICT(version) DO NOTHING",(time.time(),))
 with tx(True) as c:
  c.execute("UPDATE media_usage SET state='error',seconds=0,updated=? WHERE state IN ('queued','running')",(time.time(),))
  c.execute("DELETE FROM oauth_transactions WHERE expires<?",(time.time(),))
  c.execute("DELETE FROM sessions WHERE expires<?",(time.time(),))
  c.execute("DELETE FROM rate_limits WHERE expires<?",(time.time(),))

 ensure_audio_schema()

 ensure_user_controls()

 import trial_guard
 trial_guard.initialize()

def ensure_audio_schema():
 # Additive migration; all existing jobs, settings and accounts are preserved.
 with tx(True) as c:
  if DEV:
   exists=any(r["name"]=="output_format" for r in c.execute("PRAGMA table_info(media_usage)").fetchall())
   if not exists:c.execute("ALTER TABLE media_usage ADD COLUMN output_format TEXT NOT NULL DEFAULT 'mp4'")
  else:
   c.execute("ALTER TABLE media_usage ADD COLUMN IF NOT EXISTS output_format TEXT NOT NULL DEFAULT 'mp4'")
  s=json.loads(c.execute("SELECT value FROM app_settings WHERE id=1").fetchone()["value"])
  changed=False
  for key,limit in (("creator",30),("pro",75),("studio",0)):
   if "mp3_exports" not in s["plans"][key]:s["plans"][key]["mp3_exports"]=limit;changed=True
  if changed:
   c.execute("UPDATE app_settings SET value=? WHERE id=1",(json.dumps(s),))
   audit(c,None,"settings.audio_limits.initialize",None,{"creator":30,"pro":75,"studio":"unlimited","period":"day"})
  c.execute("INSERT INTO schema_versions(version,applied) VALUES(2,?) ON CONFLICT(version) DO NOTHING",(time.time(),))


def ensure_user_controls():
 with tx(True) as c:
  c.execute("CREATE TABLE IF NOT EXISTS user_limit_overrides(owner TEXT PRIMARY KEY REFERENCES users(id), limits TEXT NOT NULL, updated DOUBLE PRECISION NOT NULL, actor TEXT NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS media_deliveries(job_id TEXT PRIMARY KEY REFERENCES media_usage(id),owner TEXT NOT NULL REFERENCES users(id),requests INTEGER NOT NULL,last_requested DOUBLE PRECISION NOT NULL)")
  c.execute("INSERT INTO schema_versions(version,applied) VALUES(3,?) ON CONFLICT(version) DO NOTHING",(time.time(),))

  # activity-outcomes-2
  columns={"completed":"INTEGER NOT NULL DEFAULT 0","last_completed":"DOUBLE PRECISION","bytes_completed":"BIGINT NOT NULL DEFAULT 0"}
  for name,definition in columns.items():
   if DEV:
    existing={r["name"] for r in c.execute("PRAGMA table_info(media_deliveries)").fetchall()}
    if name not in existing:c.execute("ALTER TABLE media_deliveries ADD COLUMN "+name+" "+definition)
   else:c.execute("ALTER TABLE media_deliveries ADD COLUMN IF NOT EXISTS "+name+" "+definition)

def settings(c=None):
 if c:return json.loads(c.execute("SELECT value FROM app_settings WHERE id=1").fetchone()["value"])
 with tx() as db:return settings(db)
def get_user(c,uid):
 u=row(c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone())
 if not u or u["status"]!="active":raise HTTPException(403,"This account is blocked or unavailable.")
 return u
def entitlements(c,u):
 s=settings(c);p=s["plans"].get(u.get("plan") or "creator")
 if not p:raise HTTPException(403,"No valid plan is assigned.")
 p=dict(p)
 custom=c.execute("SELECT limits FROM user_limit_overrides WHERE owner=?",(u["id"],)).fetchone()
 if custom:p.update(json.loads(custom["limits"]))
 return s,p
def access(c,u):
 s,p=entitlements(c,u);now=time.time()
 enabled=s["mode"]!="paused" and u.get("period_start") is not None and (
  s["mode"]=="open" or (u.get("period_end") or 0)>now)
 return dict(enabled=bool(enabled),mode=s["mode"],plan=u.get("plan"),
  access_kind=u.get("access_kind"),trial_used=bool(u["trial_used"]),
  starts_at=u.get("period_start"),expires_at=u.get("period_end"),limits=p,
  processing_slot_exempt=u["role"]=="admin")
def allowance_start(u):
 anchor=u.get("period_start") or 0
 return anchor+max(0,int((time.time()-anchor)//2592000))*2592000 if anchor else 0
def usage(c,u):
 a=access(c,u);start=allowance_start(u);day=int(time.time()//86400)*86400
 rows=[row(r) for r in c.execute("SELECT * FROM media_usage WHERE owner=? AND state IN ('queued','running','done')",(u["id"],)).fetchall()]
 exports=sum(r["kind"]=="export" and r.get("output_format","mp4")!="mp3" and r["created"]>=day for r in rows)
 mp3=sum(r["kind"]=="export" and r.get("output_format")=="mp3" and r["created"]>=day for r in rows)
 previews=sum(r["kind"]=="preview" and r["created"]>=day for r in rows)
 consumed=sum(r["seconds"] for r in rows if r["kind"]=="export" and r["state"]=="done" and r["period_start"]==start)
 reserved=sum(r["seconds"] for r in rows if r["kind"]=="export" and r["state"]!="done" and r["period_start"]==start)
 active=sum(r["state"]!="done" for r in rows)
 return dict(mp3_exports_today=mp3,mp3_limit=None if u["role"]=="admin" or a["limits"]["mp3_exports"]==0 else a["limits"]["mp3_exports"],exports_today=exports,previews_today=previews,active_jobs=active,
  used_seconds=consumed,reserved_seconds=reserved,
  remaining_seconds=max(0,a["limits"]["seconds"]-consumed-reserved),
  daily_resets_at=day+86400,period_ends_at=min(start+2592000,u.get("period_end") or start+2592000))
def start_trial(uid, trial_signals=None):
 with tx(True) as c:
  u=get_user(c,uid);s=settings(c)
  if not s["new_trials"] or s["mode"]=="paused":raise HTTPException(403,"New trials are currently paused.")
  if u["trial_used"]:raise HTTPException(409,"Your introductory trial has already been activated.")
  if access(c,u)["enabled"]:raise HTTPException(409,"Your account already has active access.")
  import trial_guard
  trial_guard.check(c,u,trial_signals)
  now=time.time();end=now+s["trial_days"]*86400
  c.execute("UPDATE users SET trial_used=1,plan='creator',access_kind='trial',period_start=?,period_end=? WHERE id=?",(now,end,uid))
  trial_guard.claim(c,u,trial_signals or {})
  audit(c,uid,"trial.activate",uid,dict(days=s["trial_days"]))
  return access(c,get_user(c,uid))
def reserve(uid,kind,jid,output_format="mp4"):
 if output_format not in ("mp3","mp4"):raise HTTPException(400,"Choose MP4 or MP3.")
 with tx(True) as c:
  u=get_user(c,uid);a=access(c,u);v=usage(c,u)
  if not a["enabled"]:raise HTTPException(403,"Unlock your trial, or contact support if your access has ended.")
  p=a["limits"]
  if u["role"]!="admin" and v["active_jobs"]>=p["active"]:raise HTTPException(429,"Your processing slot is busy. Wait for the current job to finish.")
  audio=kind=="export" and output_format=="mp3"
  if audio:
   cap=p["mp3_exports"]
   if u["role"]!="admin" and cap>0 and v["mp3_exports_today"]>=cap:raise HTTPException(429,"Your daily MP3 export allowance has been reached.")
  else:
   count=v["exports_today"] if kind=="export" else v["previews_today"]
   if count>=p["exports" if kind=="export" else "previews"]:raise HTTPException(429,"Your daily processing allowance has been reached.")
  if kind=="export" and v["remaining_seconds"]<=0:raise HTTPException(429,"Your export-duration allowance has been used.")
  c.execute("INSERT INTO media_usage(id,owner,kind,state,created,updated,period_start,seconds,output_format) VALUES(?,?,?,'queued',?,?,?,0,?)",
            (jid,uid,kind,time.time(),time.time(),allowance_start(u),output_format if kind=="export" else "mp4"))


def reserve_duration(uid,jid,source_duration,export_duration):
 import math
 with tx(True) as c:
  u=get_user(c,uid);a=access(c,u)
  if not a["enabled"]:raise ValueError("Your access is no longer active.")
  p=a["limits"]
  if not math.isfinite(source_duration) or source_duration<=0:raise ValueError("The source duration could not be verified.")
  if source_duration>p["source_seconds"]:raise ValueError("The maximum source duration is 3 hours.")
  if export_duration is not None:
   r=row(c.execute("SELECT * FROM media_usage WHERE id=? AND owner=?",(jid,uid)).fetchone())
   if not r:raise ValueError("Processing reservation is missing.")
   held=c.execute("SELECT COALESCE(SUM(seconds),0) AS total FROM media_usage WHERE owner=? AND kind='export' AND period_start=? AND state IN ('queued','running','done')",(uid,r["period_start"])).fetchone()["total"]
   if export_duration>p["seconds"]-held+r["seconds"]+.1:raise ValueError("This clip exceeds your remaining export-duration allowance.")
   c.execute("UPDATE media_usage SET seconds=?,updated=? WHERE id=?",(export_duration,time.time(),jid))
def finish(jid,state,actual=None):
 with tx(True) as c:
  r=row(c.execute("SELECT * FROM media_usage WHERE id=?",(jid,)).fetchone())
  if not r:return
  seconds=r["seconds"] if state=="done" else 0
  if state=="done" and actual is not None:
   if actual>r["seconds"]+1:raise ValueError("The exported duration exceeds its quota reservation.")
   seconds=min(actual,r["seconds"])
  c.execute("UPDATE media_usage SET state=?,seconds=?,updated=? WHERE id=?",(state,seconds,time.time(),jid))
def require_owner(uid,jid):
 with tx() as c:
  r=c.execute("SELECT owner FROM media_usage WHERE id=?",(jid,)).fetchone()
  if not r or r["owner"]!=uid:raise HTTPException(404,"This media job was not found.")
def rate(key,limit=20,window=60):
 now=time.time();bucket=digest(key)+":"+str(int(now//window))
 with tx(True) as c:
  r=c.execute("SELECT hits FROM rate_limits WHERE bucket=?",(bucket,)).fetchone()
  if r and r["hits"]>=limit:raise HTTPException(429,"Too many requests. Please wait a moment.")
  c.execute("INSERT INTO rate_limits(bucket,hits,expires) VALUES(?,1,?) ON CONFLICT(bucket) DO UPDATE SET hits=rate_limits.hits+1",(bucket,now+window*2))
  c.execute("DELETE FROM rate_limits WHERE expires<?",(now,))
def login(claims,previous_token=None):
 uid=uuid.uuid4().hex;token=secrets.token_urlsafe(32);now=time.time()
 with tx(True) as c:
  u=row(c.execute("SELECT * FROM users WHERE google_sub=?",(claims["sub"],)).fetchone())
  if u:
   uid=u["id"];get_user(c,uid)
   c.execute("UPDATE users SET email=?,name=?,last_login=? WHERE id=?",(claims["email"],claims.get("name") or "",now,uid))
  else:c.execute("INSERT INTO users(id,google_sub,email,name,created,last_login) VALUES(?,?,?,?,?,?)",(uid,claims["sub"],claims["email"],claims.get("name") or "",now,now))
  if previous_token:c.execute("DELETE FROM sessions WHERE token_hash=?",(digest(previous_token),))
  c.execute("INSERT INTO sessions(token_hash,user_id,csrf,created,expires,seen) VALUES(?,?,?,?,?,?)",(digest(token),uid,secrets.token_urlsafe(24),now,now+7*86400,now))
  audit(c,uid,"auth.login",uid)
 return token
def authenticate(token):
 if not token:raise HTTPException(401,"Sign in with Google to continue.")
 now=time.time()
 with tx() as c:
  session=row(c.execute("SELECT * FROM sessions WHERE token_hash=?",(digest(token),)).fetchone())
  if not session or session["expires"]<=now or session["seen"]<now-86400:raise HTTPException(401,"Your session expired. Please sign in again.")
  u=get_user(c,session["user_id"])
  if session["seen"]<now-300:c.execute("UPDATE sessions SET seen=? WHERE token_hash=?",(now,digest(token)))
  return u,session["csrf"]
def user_info(u):
 return {k:u.get(k) for k in ("id","email","name","role","status","created","last_login")}

# trial-network-guard-1
