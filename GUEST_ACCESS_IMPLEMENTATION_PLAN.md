# VELAUR Media Studio — Guest-first access and manual approval (implementation specification)
Status: design only; no production changes. Feature branch: feature/guest-access-manual-approval.

## User journey
1. Visitor opens / or /studio; no required login and no public pricing page. Site navbar: brand left, centered mobile menu, right-side "Studio" or minimal action; no public Login or Pricing. Existing gradients, typography, iconography, hover and layout remain unchanged.
2. First visit issues a secure, opaque, HttpOnly, SameSite=Lax, Secure guest session cookie and CSRF token. Server stores hashed guest ID and coarse audit metadata. Do not use persistent fingerprinting, MAC/IMEI/device filesystem access, or covert surveillance.
3. User previews/exports within finite **lifetime** guest quota; proposed defaults: 3 previews total, 1 export total, maximum 60 seconds output, 720p output, one concurrent job, 250 MB upload. Admin-configurable. Quota enforced atomically server-side across concurrent requests; no hidden resets and no counter clearing on deleting cookies. A guest identity is not robust proof of one physical device: IP/network signals plus anti-abuse throttling are only approximate, handle shared networks carefully.
4. On quota exhaustion return structured HTTP 403/429 with code GUEST_LIMIT_REACHED and safe remaining-count metadata. UI opens existing VELAUR quota modal, with "Request access" WhatsApp contact and optional email request. Do not auto-initiate chat. Include plaintext explanation about data recorded and manual approval.
5. Admin reviews pending request in protected /admin panel, verifies email ownership via Google sign-in or one-time email link, grants access with explicit period and quotas, or blocks request. Never use entered email alone as authentication.
6. Approved users sign in with Google (existing OIDC) using the exact approved verified email; access binds to verified email and user ID. Non-approved login must not provide processing privileges. Preserve admin sign-in (e.g. /login) even though hidden from public navigation.
7. Admin views per-user device sessions: browser/device type (parsed user-agent), last seen, approx time, optional coarse network metadata, session count, guest -> verified-email linkage only with valid ownership verification; revoke selected/all sessions, block/unblock users, override quotas. **No remote access to users' devices**, cameras, messages, files, or precise location.

## Engineering constraints
- Current code in identity.AccountGuard authenticates all processing routes with Google db.authenticate. Removing login links without refactoring access guard, accounts reservation logic, and media ownership would break the studio.
- Store guest principals separately; never forge Google accounts with placeholder google_sub or fake email. Link guest jobs to account on verified login only if ownership proof is established. Add database migrations additive with indexes and foreign keys; backup DB first.
- Build guest/principal authorization as explicit typed state; enforce rights on /api/jobs, /api/files, /api/stream, /api/upload-export and CSRF checks before processing. Preserve admin-only endpoints.
- Quotas in backend atomic transactions: count reservations, failed jobs released per current policy; prevent replay/races. Anonymous traffic also gets global rate limits to protect 1GB Oracle VM, bandwidth and disk.
- Expose /api/public/guest-session for initial guest token and remaining limits. JS account bootstraps guest profile and allows Studio without sign-in. Account ownership and output download remain bound to original guest session.
- Extend admin UI for email requests and session views. Restrict audit logging and collection to minimum; publish retention/consent in Privacy page, allow deletion/cleanup. Do not promise perfect physical device identification.
- Hide pricing from public navigation and landing page only once guest backend works. Keep /pricing serving a redirect or 410 and remove SEO links/sitemap entries after reviewing index implications; admin pages remain accessible to staff.
- Keep Google sign-in internally for approved users and admin. No raw device fingerprint, IP, or session credential exposure to other users.
- Add integration tests: guest creates and resumes session, quota exhaustion, concurrent jobs, CSRF, consent and privacy, approval only after verified email, admin blocks, logout, expiry, revocation, files ownership isolation, no public admin exposure, mobile navbar tests, failed migration/rollback.
- Stage on an isolated PostgreSQL test DB; preserve Oracle live DB/volumes/cookies, run tests and rollback plan. GitHub commits alone do not deploy Oracle server.

## Current implementation status
- Design and branch prepared only. No guest authorization middleware, DB schema, approval API or UI has yet been deployed; current live production still requires sign-in.
