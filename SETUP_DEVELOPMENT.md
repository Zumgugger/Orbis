# Local Development Setup Guide

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Get credentials from production server:**
   ```bash
   ssh root@1078 "cat /var/www/orbis/.env.production | grep GOOGLE"
   ```

3. **Update your local `.env` with production Google credentials:**
   ```dotenv
   GOOGLE_CLIENT_ID=1053107847673-9vner5tnjrihnrckd1fb3sdbebqtls0m.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=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
   # Leave GOOGLE_REDIRECT_URI commented out - app auto-detects for localhost
   ```

4. **Ensure these settings in `.env`:**
   ```dotenv
   ORBIS_CONFIG=development
   DEVELOPMENT_MODE=False  # Set to True only if you don't need Google OAuth
   DEFAULT_TIMEZONE=Europe/Zurich
   ```

5. **Important: Verify Google Cloud Console setup**
   - Project: `glass-world-209910`
   - OAuth Client ID: `1053107847673-9vner5tnjrihnrckd1fb3sdbebqtls0m.apps.googleusercontent.com`
   - Authorized redirect URIs include:
     - `http://localhost:5001/auth/callback`
     - `http://127.0.0.1:5001/auth/callback`
     - `https://orbis.zumgugger.ch/auth/callback` (production)
   - Test users: `markus.gugger@gmail.com` is added

6. **Run Flask:**
   ```bash
   python app.py
   # or
   flask run
   ```

## Why This Matters

- ✅ Using production credentials ensures your local app behaves identically to production
- ✅ OAuth Client ID must match where test users are configured
- ✅ `.env` is git-ignored, preventing accidental credential leaks
- ✅ Dynamic redirect URIs (when not set) adapt to `localhost:5001` or `127.0.0.1:5001`

## Troubleshooting

**Error 403: Access blocked - App not verified**
- Verify you're using the CORRECT Client ID from Google Cloud
- Check that your email is added as a test user
- Ensure redirect URIs in Google Cloud match your local URL

**Cannot import database modules**
- Check `ORBIS_CONFIG=development` is set
- Verify all Python dependencies: `pip install -r requirements.txt`

**Calendar integration not working**
- Ensure Google OAuth credentials are from production
- Check calendar scope is configured in Google Cloud OAuth consent screen

## Remember

- **Never commit `.env` or `.env.production` to git**
- **Always get credentials from production server** (via SSH or ask Markus)
- **Credentials sync between local and production uses the same OAuth Client**
- **When adding new dependencies or env vars, update `.env.example`**
