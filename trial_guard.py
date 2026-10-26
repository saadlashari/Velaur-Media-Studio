"""One introductory trial per network/browser. Identity remains Google OIDC."""
import hashlib,hmac,ipaddress,re,secrets,time
from fastapi import HTTPException
COOKIE='__Host-velaur-trial-device'
_key=None

def initialize():
 import accounts as db
 global _key
 with db.tx(True) as c:
  c.execute('CREATE TABLE IF NOT EXISTS trial_guard_config(id INTEGER PRIMARY KEY, secret TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS trial_claims(kind TEXT NOT NULL, token_hash TEXT NOT NULL, owner TEXT NOT NULL REFERENCES users(id), created DOUBLE PRECISION NOT NULL, PRIMARY KEY(kind,token_hash))')
  c.execute('INSERT INTO trial_guard_config(id,secret) VALUES(1,?) ON CONFLICT(id) DO NOTHING',(secrets.token_hex(32),))
  _key=bytes.fromhex(c.execute('SELECT secret FROM trial_guard_config WHERE id=1').fetchone()['secret'])

def fingerprint(kind,value):
 if _key is None:raise RuntimeError('Trial guard not initialized')
 return hmac.new(_key,(kind+':'+value).encode(),hashlib.sha256).hexdigest()

def prepare(request):
 raw=request.cookies.get(COOKIE,'')
 token,sep,signature=raw.partition('.')
 if not sep or not re.fullmatch(r'[a-f0-9]{64}',token) or not hmac.compare_digest(signature,fingerprint('sign',token)):
  token=secrets.token_hex(32);raw=token+'.'+fingerprint('sign',token)
 request.state.trial_cookie=raw
 request.state.trial_cookie_new=raw!=request.cookies.get(COOKIE)
 request.state.trial_device=fingerprint('device',token)

def context(request):
 if not getattr(request.state,'trial_device',None):prepare(request)
 try:
  address=ipaddress.ip_address(request.client.host)
  if isinstance(address,ipaddress.IPv6Address) and address.ipv4_mapped:address=address.ipv4_mapped
  if not address.is_global:raise ValueError('Missing public address')
 except (ValueError,AttributeError):
  raise HTTPException(503,'Your network could not be verified. Contact support to activate your trial.')
 return {'network':fingerprint('network',address.compressed),'browser':request.state.trial_device}

def issue_cookie(request,message):
 if message['type']=='http.response.start' and getattr(request.state,'trial_cookie_new',False):
  from http.cookies import SimpleCookie
  cookie=SimpleCookie();cookie[COOKIE]=request.state.trial_cookie
  value=cookie[COOKIE];value['path']='/';value['secure']=True;value['httponly']=True;value['samesite']='Lax';value['max-age']=31536000
  message.setdefault('headers',[]).append((b'set-cookie',value.OutputString().encode('latin-1')))

def check(c,user,signals):
 if user['role']=='admin':return
 if not signals or set(signals)!={'network','browser'} or not all(re.fullmatch(r'[a-f0-9]{64}',str(v)) for v in signals.values()):
  raise HTTPException(403,'Trial verification is required. Refresh this page and retry.')
 for kind,value in signals.items():
  claimed=c.execute('SELECT owner FROM trial_claims WHERE kind=? AND token_hash=?',(kind,value)).fetchone()
  if claimed and claimed['owner']!=user['id']:
   raise HTTPException(409,'A free trial has already been used on this network or browser. Sign in to your original account, or view plans for more access.')

def claim(c,user,signals):
 if user['role']=='admin':return
 for kind,value in signals.items():
  c.execute('INSERT INTO trial_claims(kind,token_hash,owner,created) VALUES(?,?,?,?) ON CONFLICT(kind,token_hash) DO NOTHING',(kind,value,user['id'],time.time()))

def remember_existing(request,user):
 # Preserve existing access, but associate previous trials on their next visit.
 if user['role']=='admin' or not user.get('trial_used'):return
 import accounts as db
 try:signals=context(request)
 except HTTPException:return
 with db.tx(True) as c:claim(c,user,signals)

def activate(request,user):
 import accounts as db
 signals=context(request)
 try:return db.start_trial(user['id'],trial_signals=signals)
 except HTTPException as error:
  if error.status_code==409 and 'network or browser' in str(error.detail):
   with db.tx(True) as c:db.audit(c,user['id'],'trial.repeat_blocked',user['id'],{'policy':'one-trial-per-network-and-browser'})
  raise
