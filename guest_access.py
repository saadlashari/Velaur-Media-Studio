"""Anonymous, quota-limited visitor sessions. Do not collect invasive device fingerprints."""
import hashlib
import os
import secrets
import time
import uuid
from fastapi import HTTPException

DEV = os.getenv("VELAUR_SQLITE_DEV") == "1"
# Insecure cookies are permitted only in explicitly opted-in local HTTP tests.
LOCAL_HTTP = DEV and os.getenv("VELAUR_LOCAL_HTTP_TEST") == "1"
COOKIE = "velaur-guest-local" if LOCAL_HTTP else "__Host-velaur-guest"
MAX_AGE = 30 * 86400

def initialize():
    import accounts as db
    with db.tx(True) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS guest_sessions(
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          csrf TEXT NOT NULL, created DOUBLE PRECISION NOT NULL,
          expires DOUBLE PRECISION NOT NULL, seen DOUBLE PRECISION NOT NULL,
          device_label TEXT NOT NULL DEFAULT '')""")
        c.execute("CREATE INDEX IF NOT EXISTS guest_session_user ON guest_sessions(user_id)")
        c.execute("""CREATE TABLE IF NOT EXISTS access_invitations(
          email TEXT PRIMARY KEY, plan TEXT NOT NULL, days INTEGER NOT NULL,
          status TEXT NOT NULL, created DOUBLE PRECISION NOT NULL,
          updated DOUBLE PRECISION NOT NULL, approved_by TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS plan_requests(
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          email TEXT NOT NULL, plan TEXT NOT NULL, billing TEXT NOT NULL,
          status TEXT NOT NULL, created DOUBLE PRECISION NOT NULL,
          updated DOUBLE PRECISION NOT NULL, decided_by TEXT NOT NULL DEFAULT '')""")
        c.execute("CREATE INDEX IF NOT EXISTS plan_requests_user ON plan_requests(user_id,status)")


def _hash(value):
    return hashlib.sha256(value.encode()).hexdigest()

def device_label(user_agent):
    """Coarse browser and platform, not a unique device identifier."""
    ua=(user_agent or "").lower()
    browser=next((name for name,marker in (("Edge","edg/"),("Firefox","firefox/"),("Chrome","chrome/"),("Safari","safari/")) if marker in ua),"Browser")
    platform="Android" if "android" in ua else "iOS" if any(x in ua for x in ("iphone","ipad","ipod")) else "Windows" if "windows" in ua else "macOS" if "mac os" in ua else "Linux" if "linux" in ua else "Unknown OS"
    return browser+" / "+platform

def begin(token=None, create=True, user_agent=""):
    """Authenticate existing guest; issue a new one only when requested."""
    import accounts as db
    now=time.time()
    if token:
        with db.tx() as c:
            r=db.row(c.execute("SELECT * FROM guest_sessions WHERE token_hash=?",(_hash(token),)).fetchone())
            if r and r["expires"]>now:
                u=db.get_user(c,r["user_id"])
                if u["role"]!="guest":raise HTTPException(401,"Invalid guest session")
                if now-r["seen"]>300:
                    c.execute("UPDATE guest_sessions SET seen=? WHERE token_hash=?",(now,_hash(token)))
                return u,r["csrf"],None
    if not create:raise HTTPException(401,"Guest session expired")
    raw=secrets.token_urlsafe(40)
    csrf=secrets.token_urlsafe(32)
    uid=uuid.uuid4().hex
    # Guest principals are explicitly role=guest; they cannot authenticate via Google OAuth.
    with db.tx(True) as c:
        from accounts import settings
        s=settings(c)
        if s["mode"]=="paused":raise HTTPException(503,"Media processing is temporarily paused")
        c.execute("""INSERT INTO users
          (id,google_sub,email,name,role,status,created,last_login,trial_used,plan,access_kind,period_start,period_end)
          VALUES(?,?,?,?,'guest','active',?,?,1,'creator','guest',?,?)""",
          (uid,"guest:"+uid,"","Guest",now,now,now,now+s["trial_days"]*86400))
        c.execute("""INSERT INTO guest_sessions(token_hash,user_id,csrf,created,expires,seen,device_label)
          VALUES(?,?,?,?,?,?,?)""",(_hash(raw),uid,csrf,now,now+MAX_AGE,now,device_label(user_agent)))
    with db.tx() as c:
        u=db.get_user(c,uid)
    return u,csrf,raw

def cookie_header(raw):
    from http.cookies import SimpleCookie
    c=SimpleCookie()
    c[COOKIE]=raw
    m=c[COOKIE];m["path"]="/";m["secure"]=not LOCAL_HTTP;m["httponly"]=True
    m["samesite"]="Lax";m["max-age"]=MAX_AGE
    return m.OutputString().encode("latin-1")
