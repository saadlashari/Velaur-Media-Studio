"""Run in an isolated container with: python -m unittest discover -s tests -v
Never run with the production DATABASE_URL.
"""
import os
import tempfile
import unittest
from pathlib import Path

_TEST_DIR = tempfile.TemporaryDirectory(prefix="velaur-guest-test-")
os.environ["VELAUR_SQLITE_DEV"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_TEST_DIR.name) / "test.sqlite3")

import accounts as db
import guest_access
from fastapi import HTTPException


class GuestAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.initialize()

    def test_guest_sessions_are_scoped_and_cookie_is_httponly(self):
        user, csrf, cookie = guest_access.begin(user_agent="Mozilla/5.0 (Android) Chrome/120.0")
        self.assertEqual(user["role"], "guest")
        self.assertNotIn("@", user["email"])
        self.assertEqual(guest_access.begin(cookie, create=False)[0]["id"], user["id"])
        self.assertEqual(guest_access.begin(cookie, create=False)[1], csrf)
        self.assertIn(b"HttpOnly", guest_access.cookie_header(cookie))
        self.assertEqual(guest_access.device_label("Mozilla/5.0 (Android) Chrome/120"), "Chrome / Android")
        with db.tx() as c:
            self.assertTrue(db.access(c, user)["enabled"])
            self.assertEqual(db.access(c, user)["limits"]["exports"], 10)
            self.assertEqual(db.access(c, user)["limits"]["previews"], 30)

    def test_creator_daily_preview_quota_is_enforced(self):
        user, _, _ = guest_access.begin()
        for i in range(30):
            jid=f"guest-preview-{user['id']}-{i}"
            db.reserve(user["id"], "preview", jid)
            db.finish(jid, "done")
        with self.assertRaises(HTTPException) as result:
            db.reserve(user["id"], "preview", f"blocked-{user['id']}")
        self.assertEqual(result.exception.status_code, 429)

    def test_creator_daily_mp4_quota_is_enforced(self):
        user, _, _ = guest_access.begin()
        for i in range(10):
            jid=f"guest-export-{user['id']}-{i}"
            db.reserve(user["id"], "export", jid)
            db.finish(jid, "done")
        with self.assertRaises(HTTPException) as result:
            db.reserve(user["id"], "export", f"blocked-{user['id']}")
        self.assertEqual(result.exception.status_code, 429)

    def test_approved_verified_email_gets_assigned_plan(self):
        email="approved-test@example.com"
        now=__import__("time").time()
        with db.tx(True) as c:
            c.execute("""INSERT INTO access_invitations
              (email,plan,days,status,created,updated,approved_by)
              VALUES(?,?,?,'approved',?,?,?)""",
              (email,"pro",45,now,now,"admin-test"))
        token=db.login({"sub":"google-approved-test","email":email,"name":"Approved Tester"})
        user,_=db.authenticate(token)
        with db.tx() as c:
            a=db.access(c,user)
            self.assertEqual(a["plan"],"pro")
            self.assertTrue(a["enabled"])
            self.assertEqual(a["access_kind"],"manual")

    def test_unapproved_google_account_cannot_process(self):
        token=db.login({"sub":"google-unapproved-test","email":"not-approved@example.com","name":"Unapproved"})
        user,_=db.authenticate(token)
        with db.tx() as c:
            self.assertFalse(db.access(c,user)["enabled"])
        with self.assertRaises(HTTPException):
            db.reserve(user["id"],"preview","no-approval")

    def test_revoked_guest_session_cannot_continue(self):
        user,_,cookie=guest_access.begin()
        with db.tx(True) as c:
            c.execute("DELETE FROM guest_sessions WHERE user_id=?",(user["id"],))
        with self.assertRaises(HTTPException):
            guest_access.begin(cookie,create=False)



class GuestHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.initialize()

    def test_first_visit_creates_guest_and_protects_admin(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        import identity
        app=FastAPI()
        app.include_router(identity.router)
        app.add_middleware(identity.AccountGuard)
        with TestClient(app,base_url=identity.SITE) as client:
            self.assertEqual(client.get("/studio").status_code,200)
            self.assertIn(guest_access.COOKIE,client.cookies)
            response=client.get("/api/me")
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual(data["user"]["role"],"guest")
            self.assertTrue(data["access"]["enabled"])
            self.assertEqual(data["access"]["limits"]["exports"],10)
            self.assertEqual(data["access"]["limits"]["previews"],30)
            self.assertEqual(client.get("/admin",follow_redirects=False).status_code,303)

    def test_localhost_staging_origin_and_csrf(self):
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        import identity
        app=FastAPI()
        app.include_router(identity.router)
        app.add_middleware(identity.AccountGuard)

        @app.post("/api/jobs/demo")
        def demo(request:Request):
            return {"owner":request.state.user["id"]}

        with TestClient(app,base_url="http://localhost:8012") as client:
            profile=client.get("/api/me").json()
            self.assertEqual(profile["user"]["role"],"guest")
            good={"Origin":"http://localhost:8012","X-CSRF-Token":profile["csrf"]}
            self.assertEqual(client.post("/api/jobs/demo",headers=good).status_code,200)
            self.assertEqual(client.post("/api/jobs/demo",headers={"Origin":"http://attacker.com:8012","X-CSRF-Token":profile["csrf"]}).status_code,403)
            self.assertEqual(client.post("/api/jobs/demo",headers={"Origin":"http://localhost:8012","X-CSRF-Token":"bad"}).status_code,403)

    def test_guest_mutations_need_same_origin_csrf(self):
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        import identity
        app=FastAPI()
        app.include_router(identity.router)
        app.add_middleware(identity.AccountGuard)
        @app.post("/api/jobs/demo")
        def demo(request:Request):
            return {"owner":request.state.user["id"]}
        with TestClient(app,base_url=identity.SITE) as client:
            data=client.get("/api/me").json()
            self.assertEqual(client.post("/api/jobs/demo").status_code,403)
            response=client.post("/api/jobs/demo",headers={
              "Origin":identity.SITE,"X-CSRF-Token":data["csrf"]})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()["owner"],data["user"]["id"])

if __name__=="__main__":
    unittest.main()
