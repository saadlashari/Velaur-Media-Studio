# Velaur Media Studio: SEO, GEO and AEO audit and implementation

Audit date: 26 October 2026 (Pakistan). Website: https://mediastudio.velaurlabs.com/

## Executive result and implementation status

The public site already has a sound basic search foundation: initial HTML includes useful text, unique metadata, canonical URLs, social cards and FAQs. The sitemap contains four relevant public URLs. Private tools redirect guests to a noindex login page. No critical indexing failure, broken internal target or broken referenced asset was found in the sampled crawl.

Actual code improvements have been implemented and source-tested in the accompanying package, including current-HTML transformation, a transactional installer, backup/rollback and a public post-deployment verifier. **They have not been applied to the live VPS.** This environment has public HTTP and connected GitHub access, but no usable authenticated VPS filesystem/deployment access. The connected Media Studio repository contains an old 4,975-byte backend with only three root files; it is not the deployed v4 application. Replacing live code from that repository would be unsafe. The installer instead reads the then-current container pages and CSS at deployment time.

SEO/GEO/AEO eligibility is improved by accurate crawlable information and clear entity relationships, not promises of rankings or AI citations. This audit provides no invented traffic, keyword volume, ranking, backlink or conversion numbers.

## Discovery and architecture

- Live public website: English static HTML served by Python/FastAPI; navigation routes include /, /pricing, /studio, /login, /dashboard, /admin, /privacy and /terms.
- Existing deployment from the established project configuration: Oracle VPS, Docker container velaur-api, Uvicorn, PostgreSQL and Nginx TLS reverse proxy. Private server configuration was not re-read in this session; current HTTP confirms the running application and v4 health fields, not every infrastructure detail.
- UI: plain HTML/CSS and vanilla JavaScript, no React/Vue bundle observed. Rendering is mixed: important marketing content and plan fallback values are in initial HTML; account state, billing toggle and enhanced plan cards use JavaScript.
- Video processing: public policy and UI describe server-side preparation/export; health confirms FFmpeg/ffprobe and TikWM resolver. This audit did not run authenticated media jobs or inspect current main.py.
- Conversion goals: useful visit -> understand supported task -> Google sign-in -> access/trial -> preview/export -> file retrieval; paid interest goes to WhatsApp. No automated checkout is enabled according to the public plans response and visible pricing explanation.
- Likely audience: English-speaking creators, students and people extracting clips/audio. International targeting is an inference; no regional/language variants were found. No hreflang was added.
- Connected resources: GitHub inspected; no Search Console, Analytics, backlink or keyword-volume integration was exposed. Public PageSpeed API returned HTTP 429.

## Verified baseline and sources

Evidence files are in baseline/ in this package, captured from public GET requests. They contain public pages and response metadata, not sessions, cookies or credentials. Raw timings include this environment's proxy, DNS/network and request scheduling overhead; they are **not** origin-only TTFB or Core Web Vitals.

| Measurement | Observed baseline | Source / scope |
|---|---:|---|
| Discovery targets fetched | 14 | responses.json: 8 primary routes, index.html alias, robots, sitemap, public health/plans, missing URL |
| Primary public indexable URLs | 4 | /, /pricing, /privacy, /terms; sitemap and initial meta robots |
| Referenced assets checked | 28 unique | crawl.json across fetched pages, including login |
| Internal link targets checked | 10 unique | crawl.json, follows redirects |
| Broken assets/internal link targets | 0 in sample | all checked targets returned successful final responses |
| Home initial HTML | 19,793 bytes | public GET, uncompressed body |
| Home stylesheet links | 13 | initial HTML source |
| Home stylesheet body bytes | 112,692 bytes | referenced CSS responses; not total page weight |
| Login stylesheet links | 15 | initial HTML source |
| Home external JavaScript files | 10 | initial HTML; no framework runtime detected |
| Pricing H1 count | 0 | initial HTML and live DOM |
| Public pages missing image dimensions | footer product logo | source image tag lacks width/height |
| Home GET duration | 7.468 seconds | single measurement, proxy-influenced; not a field percentile |
| Pricing GET duration | 6.858 seconds | same limitation |
| CSS/JS caching | no-cache observed | public response headers through this network path |
| CSS content encoding | none observed with gzip requested | origin/proxy cause not established |
| Unknown URL | 404 | /does-not-exist-seo-check |
| Private route behavior | redirects to /login | /studio, /dashboard, /admin for guest |
| Private account API behavior | 401 | /api/me and /api/me/jobs |
| Share image | 200 | /share-preview-v33.jpg; OG dimensions declared 1731 x 909 |
| Live desktop overflow | none at 1363 x 936 | read-only browser DOM inspection |
| Live app console errors | none observed during Home/Pricing checks | extension-origin errors were excluded from app findings |
| LCP / INP / CLS / Lighthouse score | unavailable | PSI 429; browser interface does not expose performance entries |
| Organic clicks/impressions/rankings/CVR | unavailable | no connected analytics/Search Console |
| Backlink profile and AI citations | unavailable | no connected provider; no claim of zero visibility |

The metrics are snapshots, not representative user distributions. Search engine indexing cannot be inferred reliably from a site: search or a 200 response. Google-selected canonicals require Search Console inspection.

## Crawl, robots, indexation and redirects

Verified correct and preserved:

- robots.txt allows public pages and blocks /api/ and /downloads/. Sitemap directive is present.
- Sitemap XML is well-formed and lists only /, /pricing, /privacy, /terms. No private tool, account or admin URLs are included.
- Home, pricing and legal pages return 200 with self-referencing production canonicals and index/follow metadata.
- /index.html returns a duplicate home representation canonicalized to /. This is a low-priority consolidation consideration, not an established critical fault. No new redirect was introduced.
- Guest redirects to /login are intentional. Login has meta noindex and X-Robots-Tag noindex/no-store. Keeping account pages private takes precedence over making the tool indexable.
- Unknown URL returns a real 404, not a soft-404 homepage.
- No observed redirect loop or broken crawlable target. No pagination exists in public marketing pages.
- No mixed HTTP resource was found among referenced page assets. The HTTPS connection used by the crawler validated successfully.
- Wildcard robots rules permit Googlebot, Bingbot and OAI-SearchBot on public pages and deny API/download paths. This is robots-policy eligibility, not verification that these bots have crawled or cited the site. GPTBot training policy was not changed.

Potential orphan routes outside discovered links, the sitemap and known application routes cannot be ruled out without complete current server source and Search Console coverage.

## Prioritized findings and disposition

Effort estimates are working estimates, not fixed quotes. 'Implemented locally' means packaged/source-tested, awaiting VPS application.

| ID | Finding | Severity | Expected impact | Confidence | Effort | Dependency | Status |
|---|---|---|---|---|---|---|---|
| P1 | 13 public / 15 login stylesheet requests with layered overrides | High performance opportunity | Medium | Verified requests; speed benefit needs investigation | 1–2 h | Current CSS and post-deploy lab test | Exact-rule bundle implemented locally |
| P2 | No representative CWV or organic baseline | High measurement gap | High | Verified access gap | 1–2 h plus data collection | Search Console/PSI or local Chrome profiler | Blocked; no scores invented |
| P3 | GitHub Media Studio source is older than deployed runtime | High release risk | High | Verified repo/source comparison | 1–3 h | Current source sync excluding secrets | No stale code deployed; installer reads live files |
| S1 | Pricing page has no H1 | Medium | Medium | Verified | <30 min | pricing.html | Implemented locally, same heading text/ID/style |
| S2 | Organization schema uses Media Studio logo for VELAUR LABS | Medium | Medium | Verified | <30 min | original Labs asset already live | Corrected locally |
| S3 | Footer product image lacks intrinsic dimensions | Low | Low | Verified | <30 min | known logo dimensions | Corrected locally; CLS benefit unmeasured |
| S4 | Descriptions can better explain actual task and access | Medium | Medium | Verified copy opportunity | 1 h | public product facts | Home/pricing/legal metadata improved locally |
| A1 | Task answers can make server processing/access clearer | Medium | Medium | Verified content opportunity | 1 h | current visible capabilities | Concise home workflow content added locally |
| G1 | WebPage identity/relationships absent on secondary public pages | Low | Low | Verified | <30 min | existing Website/App entity IDs | Added locally |
| P4 | no-cache assets and no encoding observed on audit path | Medium | Medium | Headers verified; origin cause needs investigation | 1–2 h | current nginx -T, origin/proxy measurements | Review note only, no infrastructure edit |
| S5 | /index.html duplicate home URL | Low | Low | Verified canonical already correct | <1 h | server route review | Retained; no unnecessary redirect |
| C1 | Paid-plan fallback HTML says coming soon; JS adds WhatsApp links | Low | Medium | Verified source and working live JS | 1–2 h | server renderer source | Deferred to preserve pricing/access behavior |
| M1 | End-to-end signed-in media conversion not tested | High QA dependency | High | Verified missing session/access | 30–60 min | authorized test user on deployed site | Pending; public gates verified |
| O1 | Backlinks, unlinked mentions, AI referrals unmeasured | Low | Medium | Needs investigation | 2–4 h | reporting provider/access | No outreach/disavow executed |

No critical issue was verified. These findings are not a blanket certification of security or product reliability.

## Exact implementation

Changes target **current** index.html, pricing.html, privacy.html, terms.html and login.html. They do not replace main.py or any account/media logic.

1. Home/pricing/legal title-description and matching OG/Twitter text are aligned. Pricing metadata is evergreen: exact trial days/prices remain in the existing product-controlled UI rather than newly hard-coded schema.
2. Existing pricing h2#pricing-title becomes h1#pricing-title; its content, CSS class, ID and event hooks are preserved.
3. Existing Organization JSON-LD points to the original /static/velaur-labs-original.png already used by the footer. No fabricated ratings, reviews, offers or rich-result promises are added.
4. Public pages gain WebPage JSON-LD with canonical URL, English language and existing Website/App references. Login remains noindex and receives no new schema graph.
5. Recognized logo tags gain missing intrinsic dimensions and async decoding, without replacing pixels or filters. Header priority is preserved; images are not all blindly lazy-loaded.
6. Home gains a concise, visible server-rendered section explaining video trimming, MP3 extraction and source failures, with links to Studio, pricing and privacy. It expressly says processing is on the server, requires access, and cannot promise instant processing or unrestricted sources.
7. Original CSS is concatenated **in the same cascade order**, with no purging/minification/design rewrite. Relative resource URLs are made absolute under /static/. Fingerprinted bundles are generated from the actual current files; originals remain available. Conditional/imported/interleaved executable styles are safely skipped. Repeated installations flatten existing bundle metadata rather than duplicating rules.
8. Existing script tags, IDs, actions and authentication controls are checked for preservation before application. No tracking collection, pricing, sessions, quotas, database or Nginx changes.

Implementation files: seo_patch.py, seo-content-v1.css, apply-seo.py, verify-live.py. Each installation also creates a hash-named seo-style-*.css bundle. The report, tests and evidence are included. nginx-performance-review.txt is a review aid, not an applied fix.

## Before/after and tests

**After means locally transformed source, not the still-running production site.**

| Check | Before | Packaged local result |
|---|---|---|
| Home / pricing / legal CSS links | 13 each | 1 each, including new content CSS |
| Login CSS links | 15 | 1 |
| Pricing H1 count | 0 | 1 |
| Organization logo in Home graph | Media Studio wordmark | Original Labs wordmark |
| Home body bytes | 19,793 | 20,742 |
| Pricing body bytes | 11,444 | 11,166 |
| Shared public CSS body | 112,692 | 114,669 bytes including new rules and provenance |
| Scripts and existing element IDs | baseline | preserved by assertions |
| CSS rule/media order | original chain | equivalent parsed top-level rule sequence |
| Workflow answers | existing general FAQs | additional visible task instructions and internal links |
| LCP, INP, CLS, conversions | unavailable | unavailable; no improvement claimed |

The stylesheet consolidation cuts request count, not necessarily total bytes; it is a diagnostic optimization that still needs real rendering/performance retesting. Login has a separate larger bundle because of its existing login CSS.

Tests performed:

- Public HTTP baseline crawl: 14 discovery targets, 28 referenced assets, 10 internal link targets.
- Live Home -> Pricing navigation and Yearly toggle; observed $20/$50/$100 yearly prices, crossed originals and correct WhatsApp plan links. No WhatsApp message sent.
- Live DOM showed loaded original header/footer images and no desktop horizontal overflow at 1363 x 936.
- Guest /studio, /dashboard, /admin final destination /login; account APIs returned 401.
- Python compilation of installer/patch/verifier.
- Four unittest cases (with sub-checks across five pages): repeated patch/bundle idempotence; script preservation; exactly one H1; JSON-LD parsing; logo entity check; login noindex retained; conditional CSS safety; relative URL rewriting; unexpected-HTML guard.
- CSS parser validates generated bundles. Parsed top-level rule serialization equals each original stylesheet in original order plus the new scoped content CSS.

Not performed: post-deployment live recrawl, external Rich Results Test, current mobile screenshots, a complete responsive/browser matrix, logged-in exports, real RUM/CWV or authenticated admin actions. The public verifier is supplied for after application. It does not certify rich results or video downloads.

## SEO, GEO and AEO completed separately

**SEO:** page metadata, pricing heading semantics, image dimensions, crawlable internal task links and exact-order CSS request consolidation implemented locally. Existing canonical/sitemap/robots/privacy gates preserved.

**GEO:** consistent VELAUR LABS organization logo and existing app/website identities; WebPage references; clear visible description of who operates the service, where processing happens, what outputs are supported and why restricted links fail. No fabricated mentions, authority signals or AI files were added.

**AEO:** concise answers to 'How do I trim a video?', 'How do I extract MP3 audio?' and 'Why can a video link fail?' in initial HTML, using real UI labels. Existing FAQs remain crawlable in native details elements. No FAQPage or HowTo markup was added merely to chase rich results.

Google's AI guidance emphasizes normal search eligibility and useful accessible content. Structured data must accurately represent the page; software rich results have additional requirements, so the existing WebApplication graph without ratings/offers is not claimed eligible for a specific rich-result treatment. See sources below.

## Keyword-to-URL mapping and research limits

Research used public search results and primary product documentation from Clideo and Adobe. These establish real task vocabulary and workflow intent, not search volume or ranking difficulty. No paid keyword dataset, Search Console queries or locale-specific SERP study was available. Candidate priority is qualitative.

| Current target | Primary intent / term | Secondary topics | Action |
|---|---|---|---|
| / | online video trimmer | trim video online; video to MP3; extract audio from video; MP4 export | Main product page and task answers; keep one principal broad target |
| /#seo-workflows-title | how to trim a video / extract MP3 | selected clip; server processing; inaccessible public links | Home section, same canonical /; not a separate thin landing page |
| /pricing | Velaur Media Studio pricing | Creator trial; export hours; upload limits | Accurate plan comparison; preserve live admin-controlled values |
| /privacy | Velaur Media Studio privacy policy | processing; sessions; trial-protection cookies | Trust/legal page, not a keyword acquisition page |
| /terms | Velaur Media Studio terms | authorized media; access; planned subscriptions | Trust/legal page |
| /studio, /login, /dashboard, /admin | account/tool actions | signed-in workflows | Keep protected/noindex; do not target as public landing pages |

Avoid separate pages for every social URL pattern or format unless genuinely useful and supported. Do not claim universal private downloads, no-signup access, local-only processing, unlimited free use or three-second exports. The product does not support those claims.

## Prioritized content calendar

These are proposed future URLs, not already published routes. Only the small home enhancement is in this release. Each new page requires current backend route integration, product review and a substantive original walkthrough.

| Timing | Proposed URL / placement | Working title | Intent | Business value / evidence needed |
|---|---|---|---|---|
| Days 1–14 | Existing home section (implemented) | Trim video or extract audio online | task answer | Reduce uncertainty before sign-in |
| Days 15–30 | Existing FAQ expansion after user tests | Why a video preview or export can fail | troubleshooting | Reduce support load; use actual anonymized failure categories |
| Days 31–45 | /guides/trim-video | How to trim a video in Velaur Media Studio | informational + product | Original steps and verified screenshots; link home/tool |
| Days 46–60 | /video-to-mp3, only if search data supports it | Extract MP3 audio from a video | transactional | Distinct audio example, bitrate behavior, limitations; then move audio focus here and avoid duplicating home copy |
| Days 61–75 | /guides/export-limits | Export hours, daily limits and active jobs explained | product support | Use current plan/config source, no stale hard-coded quotas |
| Days 76–90 | /guides/mp4-vs-mp3 | MP4 or MP3: which should I export? | comparison | Explain actual outputs and quality, not generic filler |

No fabricated case study, original research or review was published. A real performance case study can be written only after repeatable before/after measurements on authorized media.

## 30 / 60 / 90-day plan

**First 30 days:** apply package and run public verifier; check desktop/mobile appearance; test one short MP4, one MP3 and local upload/trim after sign-in; establish a private source-control repository matching production; verify Search Console ownership and submit the existing sitemap; gather indexing and query baselines; obtain valid PSI/Chrome lab measurements; inspect real Nginx compression before any config edit.

**Days 31–60:** use query/impression data to refine priorities; publish one verified trim guide; investigate field/Lighthouse bottlenecks (CSS delivery, fonts if present, CPU cost of glass effects, account hydration). Keep appearance changes separate and measured. If actual query data supports a dedicated audio page, implement its real route and distinct useful content. Review 403/geo/private-source error rates using authorized, minimized server records.

**Days 61–90:** publish the supported audio/limits material only after review; compare organic sign-ins and successful exports, not only visits; review mobile field percentiles when enough data exists; assess relevant editorial/resource mentions; run another crawl and evaluate query/citation/referral changes. No bulk publishing or spam acquisition.

## Monitoring and AI visibility evaluation

Organic: Search Console clicks, impressions, query/page CTR, index coverage and selected canonical. Segment country/device once data exists. Conversion: visits -> sign-in -> trial/access -> preview success -> export ready -> download request/file response. A server file response does not prove that a user saved the file.

Performance: p75 field LCP/INP/CLS by device when available; lab LCP/CLS/TBT for diagnosis; response headers, CSS request count, compressed bytes and source preparation time separately. Website rendering and remote-media download latency are different systems.

Operational: preview/export failures by platform and stage; media job durations; account/API errors; quota rejection rate. Read only properly authorized logs and avoid exporting user URLs, emails or cookies to analytics.

Repeatable AI/search prompt set, recorded monthly with date, market, engine and exact cited URL:

- What is Velaur Media Studio and who operates it?
- Does Velaur Media Studio process files on my device or on a server?
- How do I trim a video and export MP4 with Velaur Media Studio?
- How can I extract MP3 audio from a selected video clip?
- Does Media Studio charge automatically after a trial?
- Why might a public video link fail in Media Studio?

No authenticated AI-engine evaluation or citation/referral dataset was available here. The prompt set is a protocol, not measured visibility. Do not treat an assistant's uncited answer as a ranking or citation.

## Authority and outreach

No backlink profile was accessible. No harmful-link judgment, disavow, paid directory purchase or external outreach was performed. Legitimate next steps: inspect existing referring domains in Search Console; look for relevant creator-workflow/resource pages and real brand mentions; prepare one truthful product listing using actual screenshots and limitations. Outreach recipients and messages require explicit authorization before sending. Do not invent endorsements or ratings.

## Access and approvals required

1. VPS application: run the supplied installer from the existing authorized SSH session; current files are backed up automatically. No password/private key needs to be sent in chat.
2. Search Console: verify ownership via your own account/DNS and provide read access/export through a suitable connection. Analytics is optional; no tracker was added without a privacy/access decision.
3. Performance: functioning PSI quota or a local Chrome/Lighthouse report. The current request returned 429; field metrics are not known.
4. Signed-in QA: authorized test account; do not paste session cookies/secrets. Admin mutation tests need a safe test user and explicit scope.
5. Nginx/CDN changes: review current config and baseline first; no speculative caching of authenticated responses.
6. Public outreach/paid products/high-impact off-site changes: separate specific authorization. None are required to apply this local HTML/CSS package.

## Deployment and rollback

Save Velaur-SEO-Implementation.zip to Windows Downloads. Upload it using the existing SSH key, extract into seo-implementation, run apply-seo.py, then verify-live.py. Exact commands are in the accompanying response/README. The installer prints the backup and rollback.py path. It performs no Docker rebuild, restart, database migration or background-job cancellation. It copies new public files to both container and host project.

A failed verification automatically restores previous container pages. Manual rollback restores previous container and host copies. New unused CSS bundles can remain safely unreferenced. Keep backups private. If any later UI update replaces the stylesheet tags, re-run this patch against the current source rather than copying old pages.

## Primary references consulted

- Google, JavaScript SEO basics: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Google, AI features and your website: https://developers.google.com/search/docs/appearance/ai-features
- Google, software application structured data: https://developers.google.com/search/docs/appearance/structured-data/software-app
- Google, structured-data policies: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Google, robots.txt introduction: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- Web.dev, Web Vitals: https://web.dev/articles/vitals
- Clideo, actual video-cut workflow documentation: https://help.clideo.com/hc/en-us/articles/4412575026322-How-to-cut-my-video
- Adobe, actual trim-video workflow documentation: https://helpx.adobe.com/express/web/video-creation-and-editing/edit-videos/trim-videos.html

References support method and search intent; they do not prove Velaur's implementation, rankings or performance. Velaur-specific findings are grounded in the captured public site evidence and source tests.
