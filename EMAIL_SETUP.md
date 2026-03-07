# StudyFlow Email Setup Guide

## Overview
This guide explains how to set up email functionality for StudyFlow so that welcome emails are automatically sent to new users upon registration.

## Step 1: Update Dependencies

Make sure you have the latest dependencies installed:

```bash
pip install -r requirements.txt
```

This includes:
- `Flask-Mail`: For sending emails
- `python-dotenv`: For loading environment variables

## Step 2: Configure Email Service

### Option A: Gmail SMTP (Recommended for Development)

#### 2A.1 Enable 2-Factor Authentication

1. Go to your [Google Account](https://myaccount.google.com/)
2. Click **Security** on the left
3. Enable **2-Step Verification** if not already enabled

#### 2A.2 Generate App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Find **App passwords** (appears only if 2-Step Verification is enabled)
3. Select **Mail** and **Windows Computer** (or your device)
4. Google will generate a 16-character password
5. Copy this password (you'll use it in step 3)

### Option B: SendGrid (Recommended for Production)

1. Sign up at [SendGrid](https://sendgrid.com/)
2. Create a new API key
3. Copy the API key (you'll use it in step 3)

### Option C: Other SMTP Providers

You can use any SMTP provider. Get these details from your email provider:
- MAIL_SERVER (e.g., smtp.yourprovider.com)
- MAIL_PORT (usually 587 for TLS, 465 for SSL)
- MAIL_USERNAME (your email address)
- MAIL_PASSWORD (your password or app-specific password)

## Step 3: Create .env File

Create a `.env` file in your project root (same directory as `app.py`):

### For Gmail:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### For SendGrid:
```
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=apikey
MAIL_PASSWORD=SG.xxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER=noreply@studyflow.com
```

### For Other Providers:
```
MAIL_SERVER=smtp.yourprovider.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-username
MAIL_PASSWORD=your-password
MAIL_DEFAULT_SENDER=noreply@studyflow.com
```

## Step 4: Test Email Configuration

Run this test script to verify your email settings:

```python
from app import app, mail, Message

with app.app_context():
    msg = Message(
        subject='Test Email from StudyFlow',
        recipients=['your-email@example.com'],
        body='If you see this, email configuration is working!'
    )
    try:
        mail.send(msg)
        print("✓ Test email sent successfully!")
    except Exception as e:
        print(f"✗ Error sending test email: {str(e)}")
```

Save this as `test_email.py` and run:
```bash
python test_email.py
```

## Step 5: Test Registration with Email

1. Start your Flask app:
   ```bash
   python app.py
   ```

2. Go to `http://localhost:5000/register`

3. Fill in:
   - Email: your test email
   - Username: testuser
   - Password: test1234

4. Click **Create account**

5. Check your email inbox for the welcome message

## Features Implemented

✅ Registration with email, username, and password  
✅ Automatic welcome email on registration  
✅ Beautiful HTML email template  
✅ Email validation  
✅ Duplicate email prevention  
✅ Enhanced error messages  
✅ Fallback messages if email fails  

## Email Content

The welcome email includes:
- Personalized greeting with the user's name
- Introduction to StudyFlow
- List of key features
- Call-to-action button to start studying
- Professional HTML styling

## Troubleshooting

### Issue: "Failed to send email"

**For Gmail:**
- Verify you generated an App Password (not your regular Gmail password)
- Check that 2-Factor Authentication is enabled
- Verify the 16-character App Password is copied exactly (with spaces)

**For SendGrid:**
- Verify API key is correct and active
- Check SendGrid account has sending quota
- Ensure MAIL_USERNAME is set to `apikey`

**General:**
- Check `.env` file is in the correct location (project root)
- Verify `python-dotenv` is installed: `pip install python-dotenv`
- Check Flask-Mail is installed: `pip install Flask-Mail`

### Issue: "ModuleNotFoundError: No module named 'flask_mail'"

```bash
pip install Flask-Mail
```

### Issue: ".env file not loading"

Make sure:
1. File is named `.env` (not `.env.txt`)
2. It's in the project root directory (same as `app.py`)
3. No spaces around the `=` sign: `MAIL_SERVER=smtp.gmail.com` ✓
4. Lines don't have leading spaces

### Issue: "Authentication failed"

- Verify username and password are correct
- Check for typos in the `.env` file
- Test credentials manually with another email client
- For Gmail: ensure App Password is used, not regular password

## Development vs Production

### Development (Local)
- Use Gmail with App Password for testing
- `.env` file in project root
- Secret key can be randomly generated each time

### Production (Deployment)
- Use dedicated email service (SendGrid, AWS SES, etc.)
- Set environment variables on your hosting platform
- Do NOT commit `.env` file to version control
- Use strong secret key (don't use `os.urandom()`)
- Use HTTPS and secure cookies

## Example Production Setup (Render.com)

If deploying to Render.com:

1. Go to your Render service settings
2. Click **Environment**
3. Add these variables:
   ```
   MAIL_SERVER=smtp.sendgrid.net
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=apikey
   MAIL_PASSWORD=[your-sendgrid-api-key]
   MAIL_DEFAULT_SENDER=noreply@studyflow.com
   ```

4. Deploy your app

## Security Notes

⚠️ **Important:**
- Never commit `.env` file to git
- Never share your email credentials
- Use app-specific passwords when available
- Store environment variables securely on production servers
- Don't hardcode credentials in your code

## Additional Resources

- [Flask-Mail Documentation](https://pypi.org/project/Flask-Mail/)
- [Gmail App Passwords Setup](https://support.google.com/accounts/answer/185833)
- [SendGrid Email API](https://sendgrid.com/)
- [Environment Variables Best Practices](https://12factor.net/config)
