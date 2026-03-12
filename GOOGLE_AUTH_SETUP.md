# Google OAuth Setup Guide for StudyFlow

This guide matches the current StudyFlow implementation.

## Current OAuth Endpoints

- Start login: `/login/google`
- OAuth callback (fixed): `/auth/google/callback`

Important: Google must be configured with the exact callback URL(s) shown below.

## 1. Create Google Cloud Project

1. Open Google Cloud Console: https://console.cloud.google.com/
2. Create/select a project.

## 2. Configure OAuth Consent Screen

1. Go to APIs & Services > OAuth consent screen.
2. Choose External (or Internal if your org requires it).
3. Fill required fields.
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Save and publish/test as needed.

## 3. Create OAuth Client Credentials

1. Go to APIs & Services > Credentials.
2. Create Credentials > OAuth client ID.
3. Application type: Web application.
4. Add Authorized redirect URIs:

For local development:

```
http://localhost:5000/auth/google/callback
http://127.0.0.1:5000/auth/google/callback
```

For production:

```
https://yourdomain.com/auth/google/callback
```

5. Save and copy Client ID + Client Secret.

## 4. Set Environment Variables

Create/update `.env` in project root:

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

Also ensure a stable secret key is set:

```
SECRET_KEY=replace_with_a_long_random_secret
```

## 5. Install Dependencies

If needed:

```bash
pip install -r requirements.txt
```

## 6. Verify in App

1. Start app:

```bash
python app.py
```

2. Open:
   - `/login`
   - `/register`

Both pages include "Continue with Google".

3. Click Google button:
   - You should go to Google consent/login.
   - After success, you should return to dashboard.

## Expected Behavior

- If Google env vars are missing:
  - Google route does not crash.
  - User is redirected back with a clear flash message.

- If Google env vars are present:
  - New Google users get an account created.
  - Existing users are matched by `google_id` or email.

## Quick Troubleshooting

### "redirect_uri_mismatch"

- Most common issue.
- Ensure Google Console redirect URI is exactly:
  - `http://localhost:5000/auth/google/callback`
  - or the exact deployed domain URL.

### "Google login is not configured yet"

- `.env` missing or wrong key names.
- Required names:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`

### Callback works but session/login feels broken

- Ensure `SECRET_KEY` is fixed and not rotating between restarts.
- Clear browser cookies after changing auth config.

## Security Notes

- Never commit `.env` to git.
- Use HTTPS in production.
- Keep OAuth credentials secret.

## References

- Authlib Flask: https://docs.authlib.org/en/latest/flask/index.html
- Google OAuth 2.0: https://developers.google.com/identity/protocols/oauth2
