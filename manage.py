"""Run on the VPS/container terminal; never supply passwords in chat."""
import sys,getpass
import accounts as db

def main():
 if len(sys.argv)!=2 or sys.argv[1]!='promote':raise SystemExit('Usage: python manage.py promote')
 email=input('Verified Google email to make administrator: ').strip().lower()
 with db.tx(True) as c:
  users=c.execute('SELECT * FROM users WHERE lower(email)=?',(email,)).fetchall()
  if len(users)!=1:raise SystemExit('Sign in with Google first. Exactly one matching account is required.')
  u=db.row(users[0])
  if u['status']!='active':raise SystemExit('Account is blocked; unblock it before promotion.')
  if input('Type PROMOTE to grant administration: ').strip()!='PROMOTE':raise SystemExit('Cancelled.')
  c.execute("UPDATE users SET role='admin' WHERE id=?",(u['id'],))
  # Existing sessions are revoked: sign in again to use the admin role.
  c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
  db.audit(c,'server-cli','admin.promote',u['id'],dict(previous_role=u['role']))
 print('Administrator granted. Sign in again, then open /admin.')
if __name__=='__main__':main()
