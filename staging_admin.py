"""Promote ONE already-Google-verified staging user to staging admin.

Example (inside staging container):
 python /app/staging_admin.py you@example.com

This script cannot be used against production databases or with non-staging
hostnames. It does not create accounts or bypass Google OAuth.
"""
import os
import sys

def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python /app/staging_admin.py YOUR_VERIFIED_GOOGLE_EMAIL")
    if (os.getenv("VELAUR_SQLITE_DEV") != "1"
        or os.getenv("DATABASE_URL") != "sqlite:////tmp/velaur-guest-test.db"
        or os.getenv("SITE_URL") != "https://staging.mediastudio.velaurlabs.com"):
        raise SystemExit("Refusing: requires isolated HTTPS staging SQLite configuration.")
    email=sys.argv[1].strip().lower()
    if not email or "@" not in email:
        raise SystemExit("Please supply the email used for staging Google sign-in.")
    import accounts as db
    with db.tx(True) as c:
        matches=[db.row(r) for r in c.execute(
            "SELECT * FROM users WHERE lower(email)=? AND role!='guest'",(email,)).fetchall()]
        if len(matches)!=1:
            raise SystemExit("Expected exactly one existing Google user with this email. Sign into HTTPS staging first.")
        u=matches[0]
        if not u["google_sub"] or u["google_sub"].startswith("guest:"):
            raise SystemExit("Not a verified Google identity.")
        if u["status"]!="active":
            raise SystemExit("Refusing to promote a blocked account.")
        if u["role"]=="admin":
            print("This staging account is already an admin.")
            return
        c.execute("UPDATE users SET role='admin' WHERE id=?",(u["id"],))
        db.audit(c,u["id"],"staging.admin.bootstrap",u["id"],
                 {"reason":"Manual verified Google staging admin bootstrap"})
    print("Staging admin role granted for "+email)
    print("Log out and sign back in, then open /admin to verify.")

if __name__=="__main__":
    main()
