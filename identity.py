"""Google OIDC, session protection and administrative endpoints."""
import os, json, time, secrets, hashlib, base64, hmac, math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from starlette.concurrency import run_in_threadpool
import accounts as db
import trial_guard

router=APIRouter()
SITE=os.getenv("SITE_URL","https://mediastudio.velaurlabs.com").rstrip("/")
COOKIE="__Host-velaur-session"
BINDER="__Host-velaur-login"
CLIENT=os.getenv("GOOGLE_CLIENT_ID","")
SECRET=os.getenv("GOOGLE_CLIENT_SECRET","")
BASE=Path(__file__).resolve().parent
def current(r): return r.state.user
def admin(r):
 u=current(r)
 if u["role"]!="admin":raise HTTPException(403,"Administrator access is required.")
 return u
def state_key(state):return db.digest(state)
def validated_claims(token,nonce):
 from google.oauth2 import id_token
 from google.auth.transport.requests import Request as GoogleRequest
 claims=id_token.verify_oauth2_token(token,GoogleRequest(),CLIENT,clock_skew_in_seconds=10)
 if not isinstance(claims.get("sub"),str) or not claims["sub"]:raise ValueError("Missing subject")
 if claims.get("email_verified") is not True or not claims.get("email"):raise ValueError("Google email is not verified")
 if not hmac.compare_digest(str(claims.get("nonce","")),nonce):raise ValueError("Invalid nonce")
 if claims.get("azp") and claims["azp"]!=CLIENT:raise ValueError("Invalid authorized party")
 return claims
@router.get("/login")
def login_page(request:Request):
 try:
  db.authenticate(request.cookies.get(COOKIE))
 except HTTPException as error:
  if error.status_code!=401:raise
 else:return RedirectResponse("/dashboard",status_code=303)
 return FileResponse(BASE/"login.html",headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex"})

@router.get("/auth/google/start")
def google_start(request:Request):
 if not CLIENT or not SECRET:return RedirectResponse("/login?error=unavailable",status_code=303)
 db.rate("oauth:"+(request.client.host if request.client else "unknown"),10,600)
 state=secrets.token_urlsafe(32);binder=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
 with db.tx(True) as c:
  c.execute("DELETE FROM oauth_transactions WHERE expires<?",(time.time(),))
  c.execute("INSERT INTO oauth_transactions(state_hash,binder_hash,nonce,verifier,expires) VALUES(?,?,?,?,?)",(state_key(state),db.digest(binder),nonce,verifier,time.time()+600))
 challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
 params=dict(client_id=CLIENT,redirect_uri=SITE+"/auth/google/callback",response_type="code",scope="openid email profile",state=state,nonce=nonce,code_challenge=challenge,code_challenge_method="S256",prompt="select_account")
 response=RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(params),status_code=303)
 response.set_cookie(BINDER,binder,secure=True,httponly=True,samesite="lax",max_age=600,path="/")
 response.headers["Cache-Control"]="no-store";response.headers["Referrer-Policy"]="no-referrer"
 return response
@router.get("/auth/google/callback")
def google_callback(request:Request,state:str="",code:str="",error:str=""):
 try:
  with db.tx(True) as c:
   record=db.row(c.execute("SELECT * FROM oauth_transactions WHERE state_hash=?",(state_key(state),)).fetchone())
   if not record or record["expires"]<time.time() or not hmac.compare_digest(record["binder_hash"],db.digest(request.cookies.get(BINDER,""))):raise ValueError("Invalid login transaction")
   c.execute("DELETE FROM oauth_transactions WHERE state_hash=?",(state_key(state),))
  if error or not code:raise ValueError("Login cancelled")
  form=urlencode(dict(client_id=CLIENT,client_secret=SECRET,code=code,code_verifier=record["verifier"],grant_type="authorization_code",redirect_uri=SITE+"/auth/google/callback")).encode()
  req=URLRequest("https://oauth2.googleapis.com/token",data=form,headers={"Content-Type":"application/x-www-form-urlencoded"})
  with urlopen(req,timeout=15) as r:tokens=json.loads(r.read(1024*1024))
  claims=validated_claims(tokens["id_token"],record["nonce"])
  token=db.login(claims,request.cookies.get(COOKIE))
 except HTTPException as e:
  if e.status_code==403:raise
  raise HTTPException(400,"Google sign-in could not be completed. Please start again.")
 except Exception:
  response=RedirectResponse("/login?login_error=1",status_code=303)
  response.delete_cookie(BINDER,path="/",secure=True,httponly=True,samesite="lax")
  return response
 response=RedirectResponse("/dashboard",status_code=303)
 response.set_cookie(COOKIE,token,max_age=7*86400,path="/",secure=True,httponly=True,samesite="lax")
 response.delete_cookie(BINDER,path="/",secure=True,httponly=True,samesite="lax")
 response.headers["Cache-Control"]="no-store";response.headers["Referrer-Policy"]="no-referrer"
 return response
@router.post("/auth/logout")
def logout(request:Request):
 with db.tx(True) as c:
  c.execute("DELETE FROM sessions WHERE token_hash=?",(db.digest(request.cookies.get(COOKIE,"")),))
  db.audit(c,current(request)["id"],"auth.logout",current(request)["id"])
 response=JSONResponse({"ok":True});response.delete_cookie(COOKIE,path="/",secure=True,httponly=True,samesite="lax");return response
@router.get("/api/public/plans")
def plans():
 s=db.settings()
 return dict(plans=s["plans"],trial_days=s["trial_days"],trial_hours=s["plans"]["creator"]["seconds"]/3600,new_trials=s["new_trials"] and s["mode"]!="paused",billing_enabled=False)
@router.get("/api/me")
def me(request:Request):
 u=current(request)
 with db.tx() as c:return dict(user=db.user_info(u),csrf=request.state.csrf,access=db.access(c,u),usage=db.usage(c,u))
@router.post("/api/me/trial")
def trial(request:Request):return trial_guard.activate(request,current(request))
@router.get("/api/me/jobs")
def my_jobs(request:Request,offset:int=0):
 # dashboard-activity-labels-1: caller may see only their own activity.
 from admin_tools import job_detail
 from activity_labels import describe
 owner=current(request)["id"]
 if offset<0 or offset>100000:raise HTTPException(400,"Invalid activity page.")
 with db.tx() as c:
  rows=[db.row(r) for r in c.execute("SELECT * FROM media_usage WHERE owner=? ORDER BY created DESC LIMIT 26 OFFSET ?",(owner,offset)).fetchall()]
  deliveries={r["job_id"]:db.row(r) for r in c.execute("SELECT * FROM media_deliveries WHERE owner=?",(owner,)).fetchall()}
 result=[]
 for row in rows[:25]:
  item=job_detail(row);d=deliveries.get(row["id"],{})
  item.update(download_requests=d.get("requests",0),last_download_request=d.get("last_requested"),last_completed=d.get("last_completed"),completed_transfers=d.get("completed",0))
  item.update(describe(item));result.append(item)
 return {"jobs":result,"next_offset":offset+25 if len(rows)>25 else None}
@router.get("/studio")
def studio_page(request:Request):
 return FileResponse(BASE/"studio.html",headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex"})

@router.get("/dashboard")
def dashboard(request:Request):
 return FileResponse(BASE/"dashboard.html",headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex"})
@router.get("/admin")
def admin_page(request:Request):
 admin(request);return FileResponse(BASE/"admin.html",headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex"})
@router.get("/api/admin/overview")
def overview(request:Request):
 admin(request);day=int(time.time()//86400)*86400
 with db.tx() as c:
  totals=db.row(c.execute("SELECT count(*) AS users, COALESCE(SUM(CASE WHEN status='active' THEN 1 ELSE 0 END),0) AS active, COALESCE(SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END),0) AS blocked FROM users").fetchone())
  totals["exports_today"]=c.execute("SELECT count(*) AS n FROM media_usage WHERE state='done' AND kind='export' AND created>=?",(day,)).fetchone()["n"]
  totals["active_jobs"]=c.execute("SELECT count(*) AS n FROM media_usage WHERE state IN ('queued','running')").fetchone()["n"]
  return totals

@router.get("/api/admin/users")
def users(request:Request,q:str="",offset:int=0,status:str="all"):
 admin(request)
 if offset<0 or len(q)>150 or status not in ("all","active","blocked"):raise HTTPException(400,"Invalid search.")
 with db.tx() as c:
  where="(lower(email) LIKE ? OR lower(name) LIKE ?) AND (?='all' OR status=?)"
  args=("%"+q.strip().lower()+"%","%"+q.strip().lower()+"%",status,status)
  total=c.execute("SELECT count(*) AS n FROM users WHERE "+where,args).fetchone()["n"]
  rows=c.execute("SELECT * FROM users WHERE "+where+" ORDER BY created DESC LIMIT 50 OFFSET ?",args+(offset,)).fetchall()
  result=[]
  for item in rows:
   u=db.row(item);result.append(dict(user=db.user_info(u),access=db.access(c,u),usage=db.usage(c,u)))
  return dict(users=result,total=total,offset=offset,next_offset=offset+50 if offset+len(rows)<total else None)
def reason(body):
 value=str(body.get("reason","")).strip()
 if len(value)<3 or len(value)>300:raise HTTPException(400,"Give a reason between 3 and 300 characters.")
 return value
@router.post("/api/admin/users/{uid}/block")
async def block(uid:str,request:Request):
 actor=admin(request);body=await request.json();why=reason(body)
 if uid==actor["id"]:raise HTTPException(400,"You cannot block your own administrator account.")
 with db.tx(True) as c:
  u=db.row(c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone())
  if not u:raise HTTPException(404,"User not found.")
  if u["role"]=="admin":raise HTTPException(403,"Administrator accounts must be managed from the server.")
  c.execute("UPDATE users SET status='blocked' WHERE id=?",(uid,))
  c.execute("DELETE FROM sessions WHERE user_id=?",(uid,))
  db.audit(c,actor["id"],"user.block",uid,dict(reason=why,previous=u["status"]))
 return {"ok":True}
@router.post("/api/admin/users/{uid}/unblock")
async def unblock(uid:str,request:Request):
 actor=admin(request);why=reason(await request.json())
 with db.tx(True) as c:
  u=db.row(c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone())
  if not u:raise HTTPException(404,"User not found.")
  c.execute("UPDATE users SET status='active' WHERE id=?",(uid,))
  db.audit(c,actor["id"],"user.unblock",uid,dict(reason=why,previous=u["status"]))
 return {"ok":True}
@router.patch("/api/admin/users/{uid}/trial")
async def grant_access(uid:str,request:Request):
 actor=admin(request);body=await request.json();why=reason(body)
 plan=body.get("plan","creator");days=body.get("days",30)
 if plan not in db.PLANS or not isinstance(days,int) or isinstance(days,bool) or not 1<=days<=366:raise HTTPException(400,"Select a valid plan and 1-366 days.")
 # This is a manual access grant, never a payment/subscription claim.
 with db.tx(True) as c:
  u=db.get_user(c,uid)
  if c.execute("SELECT id FROM media_usage WHERE owner=? AND state IN ('queued','running')",(uid,)).fetchone():raise HTTPException(409,"Wait for this user's current jobs to finish.")
  now=time.time()
  c.execute("UPDATE users SET plan=?,access_kind='manual',period_start=?,period_end=? WHERE id=?",(plan,now,now+days*86400,uid))
  db.audit(c,actor["id"],"access.grant",uid,dict(reason=why,plan=plan,days=days,previous_plan=u["plan"],previous_end=u["period_end"]))
 return {"ok":True}
@router.get("/api/admin/settings/trial")
def admin_settings(request:Request):admin(request);return db.settings()
@router.patch("/api/admin/settings/trial")
async def update_settings(request:Request):
 actor=admin(request);body=await request.json();why=reason(body);s=body.get("settings")
 if not isinstance(s,dict) or set(s)!={"mode","trial_days","new_trials","plans"}:raise HTTPException(400,"Invalid settings.")
 if s["mode"] not in ("timed","open","paused") or type(s["new_trials"]) is not bool or type(s["trial_days"]) is not int or not 1<=s["trial_days"]<=366:raise HTTPException(400,"Invalid trial controls.")
 if set(s["plans"])!=set(db.PLANS):raise HTTPException(400,"Three plans are required.")
 bounds=dict(mp3_exports=(0,10000),exports=(1,1000),previews=(1,2000),active=(1,4),upload_gb=(1,8),seconds=(60,3600000),height=(720,2160),source_seconds=(60,10800))
 for key,p in s["plans"].items():
  if set(p)!=set(db.PLANS[key]):raise HTTPException(400,"Invalid plan fields.")
  for field,(lo,hi) in bounds.items():
   value=p[field]
   if type(value) is not int or not lo<=value<=hi:raise HTTPException(400,"Invalid "+field+" limit.")
  if p["height"] not in (720,1080,2160):raise HTTPException(400,"Invalid resolution.")
  for field in ("name","monthly","yearly"):
   if p[field]!=db.PLANS[key][field]:raise HTTPException(400,"Pricing is fixed while billing is disabled.")
 with db.tx(True) as c:
  previous=db.settings(c)
  c.execute("UPDATE app_settings SET value=? WHERE id=1",(json.dumps(s),))
  db.audit(c,actor["id"],"settings.update",None,dict(reason=why,before=previous,after=s))
 return {"ok":True}
@router.get("/api/admin/audit-logs")
def audit_logs(request:Request,offset:int=0):
 admin(request)
 if offset<0:raise HTTPException(400)
 with db.tx() as c:
  rows=c.execute("SELECT a.*, actor.email AS actor_email, target.email AS target_email FROM audit_log a LEFT JOIN users actor ON a.actor=actor.id LEFT JOIN users target ON a.target=target.id ORDER BY a.created DESC LIMIT 25 OFFSET ?",(offset,)).fetchall()
  return {"logs":[db.row(r) for r in rows]}
class AccountGuard:
 """Authenticate before multipart parsing; protect cookie-authenticated mutations."""
 def __init__(self,app):self.app=app
 async def __call__(self,scope,receive,send):
  if scope["type"]!="http":return await self.app(scope,receive,send)
  request=Request(scope);path=scope["path"]
  if path in ("/api/me","/api/me/trial"):
   await run_in_threadpool(trial_guard.prepare,request)
  protected=path.startswith(("/api/me","/api/admin","/api/jobs","/api/files","/api/stream","/api/upload-export")) or path in ("/auth/logout","/dashboard","/admin","/studio")
  async def safe_send(message):
   if message["type"]=="http.response.start":
    trial_guard.issue_cookie(request,message)
    message.setdefault("headers",[]).extend([(b"x-content-type-options",b"nosniff"),(b"referrer-policy",b"strict-origin-when-cross-origin")])
    if protected:message["headers"].append((b"cache-control",b"no-store"))
   await send(message)
  if not protected:return await self.app(scope,receive,safe_send)
  try:
   u,csrf=await run_in_threadpool(db.authenticate,request.cookies.get(COOKIE))
   scope.setdefault("state",{}).update(user=u,csrf=csrf)
   if path=="/api/me":await run_in_threadpool(trial_guard.remember_existing,request,u)
   if path.startswith("/api/admin") or path=="/admin":
    if u["role"]!="admin":raise HTTPException(403,"Administrator access is required.")
   if request.method not in ("GET","HEAD","OPTIONS"):
    if request.headers.get("origin")!=SITE or not hmac.compare_digest(request.headers.get("x-csrf-token",""),csrf):raise HTTPException(403,"Invalid request verification. Refresh the page and retry.")
    await run_in_threadpool(db.rate,"mutate:"+u["id"],30,60)
   if path=="/api/upload-export":
    with db.tx() as c:
     a=db.access(c,u);v=db.usage(c,u)
    if not a["enabled"]:raise HTTPException(403,"Activate your trial before uploading.")
    if u["role"]!="admin" and v["active_jobs"]>=a["limits"]["active"]:raise HTTPException(429,"Your processing slot is busy.")
    limit=a["limits"]["upload_gb"]*1000**3+1024*1024
    length=request.headers.get("content-length")
    if not length or not length.isdigit():raise HTTPException(411,"An upload Content-Length is required.")
    if int(length)>limit:raise HTTPException(413,"This upload exceeds your plan's file-size limit.")
    total=0
    async def limited_receive():
     nonlocal total
     msg=await receive();total+=len(msg.get("body",b""))
     if total>limit:raise HTTPException(413,"Upload exceeds your plan's limit.")
     return msg
    return await self.app(scope,limited_receive,safe_send)
  except HTTPException as e:
   if e.status_code==401 and path in ("/dashboard","/admin","/studio"):
    return await RedirectResponse("/login",status_code=303)(scope,receive,safe_send)
   return await JSONResponse({"detail":e.detail},status_code=e.status_code)(scope,receive,safe_send)
  except Exception:
   # DB/configuration errors fail closed, without exposing connection details.
   return await JSONResponse({"detail":"Account service is temporarily unavailable."},status_code=503)(scope,receive,safe_send)
  return await self.app(scope,receive,safe_send)

# activity-outcomes-2

# trial-network-guard-1
