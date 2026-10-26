# Velaur Media Studio — source reconciliation

This repository is being reconciled with the running Oracle deployment.

**The root `main.py`, `requirements.txt` and `Dockerfile.txt` are legacy files from 22 October 2026. They are not the current production application. Do not rebuild production from these files.**

## Verified current files

`live-public/` contains a point-in-time HTTP snapshot of the live public pages and their referenced styles/scripts/brand assets. See `SYNC-STATUS.json` for capture time, URLs and SHA-256 hashes. This preserves recent public UI changes without inventing protected server source. `/studio`, `/dashboard` and `/admin` redirect guests to login; their source is deliberately not represented by login-page copies.

The snapshot alone is not a deployable full application. Existing absolute `/static/` paths and API handlers require the real server. HTML may contain session-dependent fallback content; the VPS files remain authoritative.

## Pending updates

`updates/seo-implementation/` contains the tested, reversible SEO implementation, report and verifier. It reads current VPS files, preserves original scripts/IDs and writes a backup. It is not assumed deployed. Other update folders preserve the preceding branding and navigation patches; do not reinstall an older UI patch after SEO without rerunning SEO against the new source.

No automatic deployment workflow is added. A GitHub push does not deploy this Oracle container.

## Complete the protected-source sync

Download `scripts/export-current-source.py` at the pinned commit and run it on the existing VPS. It exports allowlisted app code/assets and excludes environment files, cookies, databases, downloads and backups. It rejects some obvious embedded credentials and never prints their values. Review the resulting ZIP; automated scanning is not proof that all secrets are absent.

The ZIP is `~/Velaur-Media-Studio/Velaur-current-source-safe.zip`. Once this current export is available, protected Python/HTML/admin modules can be reconciled accurately. Do not substitute old files from a previous release or upload server configuration/private keys.

## Deployment

Use the installer README in the selected update folder. No Docker Compose file exists in the known setup. The SEO and recent UI patches require no container rebuild or restart. Never commit `.env`, source-service cookies, database dumps, runtime images, private SSH keys, account exports or user media.
