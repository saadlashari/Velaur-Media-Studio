"""Staging-only guest quota popup test.

Run INSIDE the isolated dev container:
    python -m scripts.staging_quota_check --set --kind mp4
    python -m scripts.staging_quota_check --clear

This NEVER runs on production/PostgreSQL. It creates fake *completed* usage
records only for the most recently created guest session. Use a clean staging
browser when testing, and refresh the Studio after each command.
"""
import argparse
import os
import time
import uuid


def main():
    if (
        os.getenv("VELAUR_SQLITE_DEV") != "1"
        or os.getenv("DATABASE_URL") != "sqlite:////tmp/velaur-guest-test.db"
    ):
        raise SystemExit("Refusing to run: this tool is restricted to the isolated staging SQLite database.")
    import accounts as db

    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--set", action="store_true")
    action.add_argument("--clear", action="store_true")
    parser.add_argument("--kind", choices=("mp4", "mp3", "preview"), default="mp4")
    args = parser.parse_args()

    # Require ONE guest account only to avoid accidentally affecting the wrong browser.
    with db.tx() as c:
        active = [db.row(r) for r in c.execute(
            "SELECT u.* FROM users u JOIN guest_sessions s ON s.user_id=u.id "
            "WHERE u.role='guest' AND s.expires>? ORDER BY s.created DESC",
            (time.time(),)).fetchall()]
    if len(active) != 1:
        raise SystemExit("Expected exactly one active guest session in staging, found "
                         + str(len(active)) + ". Restart the disposable test container and open Studio in one browser.")
    user = active[0]
    prefix = "guest-qa-" + user["id"] + "-"
    with db.tx(True) as c:
        c.execute("DELETE FROM media_usage WHERE owner=? AND id LIKE ?",
                  (user["id"], prefix+"%"))

    if args.clear:
        print("Removed staging-only synthetic quota records for guest "+user["id"][:8])
        return

    with db.tx() as c:
        limits = db.access(c,user)["limits"]
    kind = "preview" if args.kind=="preview" else "export"
    count = limits["previews"] if kind=="preview" else limits["mp3_exports"] if args.kind=="mp3" else limits["exports"]
    fmt = "mp3" if args.kind=="mp3" else "mp4"
    # Add only enough completed synthetic jobs to meet the configured daily cap.
    if count == 0:
        raise SystemExit("The selected quota is unlimited.")
    for _ in range(count):
        jid = prefix + uuid.uuid4().hex
        db.reserve(user["id"],kind,jid,output_format=fmt)
        db.finish(jid,"done")
    print("Staging-only "+args.kind+" limit reached for guest "+user["id"][:8]
          +". Refresh /studio to inspect the ORIGINAL VELAUR contact popup.")
    print("To reset: python -m scripts.staging_quota_check --clear")


if __name__ == "__main__":
    main()
