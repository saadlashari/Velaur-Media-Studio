Velaur Brand + Glass Fix 1.3

Changes:
- Larger original Media Studio logo. Header has a light cyan area behind the logo, blending into branded blue/violet; no white logo box or color filter.
- More transparent pricing glass, directional reflections, stronger lower rim and underside shadow, including mobile. Existing layout, prices and action handlers stay in place.
- Footer uses the original VELAUR LABS transparent wordmark from https://velaurlabs.com/velaur-wordmark-light-transparent.png, with original artwork/colors. Replaces the typed substitute and symbol combination.

Ubuntu:
cd ~/Velaur-Media-Studio
python3 -m zipfile -e Velaur-Brand-Glass-Fix.zip brand-glass-fix
python3 brand-glass-fix/apply-update.py

No rebuild/restart/database changes. Patches current live HTML and adds two assets. Previous files backed up automatically. Rollback command is printed after installation. Hard-refresh after updating.

Validation: patch idempotence, footer replacement, retention of scripts/actions, CSS parsing and Python compilation checked locally against current public Home/Pricing HTML. Browser visual verification could not run in this environment because a Chromium download was unavailable; check mobile/desktop after deployment. Live deployment has not been performed by this package's author.
