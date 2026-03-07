# Google OAuth Setup Guide for StudyFlow

## Overview
This guide explains how to set up Google OAuth 2.0 authentication for your StudyFlow application.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (if you don't have one already)
3. In the top bar, select your project name
4. Click the **Create Project** button (if needed)
5. Enter your project name (e.g., "StudyFlow") and click **Create**

## Step 2: Enable Google OAuth 2.0 API

1. In the Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Google+ API" or "OAuth 2.0"
3. Click on **Google+ API**
4. Click the **Enable** button
5. Wait for activation (usually takes a few seconds)

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure the consent screen first:
   - Choose **External** for User Type
   - Fill in required fields:
     - App name: "StudyFlow"
     - User support email: your email
     - Developer contact: your email
   - Add the following scopes:
     - `openid`
     - `email`
     - `profile`
   - Click **Save and Continue** through all steps
4. After consent screen setup, select **Web application** as Application type
5. In the **Authorized redirect URIs** section, add:
   - For local development:
     ```
     http://localhost:5000/auth/google/callback
     http://127.0.0.1:5000/auth/google/callback
     ```
   - For production, replace `localhost:5000` with your domain:
     ```
     https://yourdomain.com/auth/google/callback
     ```
6. Click **Create**
7. A popup shows your **Client ID** and **Client Secret**
   - Copy these values (you'll need them next)

## Step 4: Configure Environment Variables

Create a `.env` file in your project root (same directory as `app.py`):

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

Replace `your_client_id_here` and `your_client_secret_here` with the actual values from Step 3.

## Step 5: Load Environment Variables

Update your app to load `.env` variables. Add this to the top of `app.py` after the imports:

```python
from dotenv import load_dotenv
load_dotenv()
```

Also add `python-dotenv` to `requirements.txt`:

```
python-dotenv
```

Then run:
```bash
pip install -r requirements.txt
```

## Step 6: Test the Setup

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Visit `http://localhost:5000/login`

3. Click the **"Continue with Google"** button

4. You should be redirected to Google's login page

5. After logging in, you'll be redirected back to your dashboard

## Features Implemented

✅ Google OAuth 2.0 login
✅ Automatic user account creation
✅ Email and Google ID stored in database
✅ Existing username/password login still works
✅ User redirected to dashboard after login
✅ Styled "Continue with Google" button

## Database Changes

The `User` model now includes:
- `email`: Stores user's email address
- `google_id`: Stores Google's unique user identifier
- `username`: Made optional (for Google OAuth users)
- `password`: Made optional (for Google OAuth users)

## Troubleshooting

**Issue: "client_id or client_secret is missing"**
- Ensure `.env` file exists and is in the correct location
- Check that `python-dotenv` is installed
- Verify environment variable names are exactly: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

**Issue: "Redirect URI mismatch"**
- The callback URL you registered in Google Cloud Console must match exactly
- Check for `http` vs `https`, port numbers, and trailing slashes

**Issue: "User gets logged out after callback"**
- Verify session configuration in Flask
- Ensure cookies are being set properly (check browser dev tools)

**Issue: "Email/Google ID not stored in database"**
- Run database migrations if you have an existing database
- Delete your `instance/database.db` file if this is development

## Security Notes

⚠️ **Development vs Production:**
- Never commit `.env` file to version control
- Use environment variables for production deployments
- Generate a strong `app.secret_key` for production (don't use `os.urandom()`)
- Use HTTPS in production

## Additional Resources

- [Authlib Documentation](https://docs.authlib.org/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Flask Authlib Integration](https://docs.authlib.org/en/latest/flask/index.html)
