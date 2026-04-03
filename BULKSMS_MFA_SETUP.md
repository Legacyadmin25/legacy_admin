# BulkSMS MFA Setup - Generate API Token

## ⚠️ Issue Found

Your BulkSMS account has **MFA enabled**. The API requires either:
1. ✅ **API Token** (recommended) - Generate from BulkSMS dashboard
2. App passwords - Generate from BulkSMS security settings
3. Disable MFA - Not recommended for security

## ✅ Solution: Generate API Token (Recommended)

### Step 1: Login to BulkSMS Dashboard
1. Go to: https://www.bulksms.com/dashboard/
2. Login with:
   - Username: `legacy_guard`
   - Password: `Greytown@3250`

### Step 2: Navigate to API Tokens
1. Click on your profile/settings
2. Look for "API" or "API Settings" section
3. Find "Tokens" or "API Keys" option

### Step 3: Create New Token
1. Click "Generate Token" or "Create API Key"
2. Name it: `LegacyAdmin-OTP-System` (or similar)
3. Grant permissions: Send SMS (all you need)
4. Generate the token
5. **Copy the token immediately** (won't show again)

### Step 4: Update Your .env File

Once you have the token, update `.env`:

```env
# Option A: Using API Token (Recommended)
BULKSMS_USERNAME=YOUR_BULKSMS_USERNAME_OR_EMAIL
BULKSMS_API_TOKEN=your_generated_api_token_here

# OR Option B: If they support app passwords
BULKSMS_USERNAME=legacy_guard
BULKSMS_PASSWORD=your_generated_app_password
```

### Step 5: Update Django Settings

We'll need to update the SMS sender to use the new token format.

---

## 📊 BulkSMS Authentication Methods

| Method | Auth Type | MFA Required | Status |
|--------|-----------|--------------|--------|
| Username/Password | Basic Auth | ❌ Required | ❌ Blocked (your acc) |
| API Token | Bearer Token | ❌ No | ✅ Recommended |
| App Password | Basic Auth | ❌ No | ✅ Alternative |

---

## 🔧 Code Update Needed

Once you provide the API token, we'll update:

```python
# members/communications.py - BulkSMS Sender

class BulkSMSSender:
    """Send SMS via BulkSMS API"""
    
    # Old method (with MFA issue)
    auth = HTTPBasicAuth(username, password)  # ❌ Won't work
    
    # New method (with API token)
    headers = {'Authorization': f'Bearer {api_token}'}  # ✅ Works
```

---

## 📞 Quick Steps to Get Your API Token

**For BulkSMS.com Users:**

1. Login: https://www.bulksms.com/dashboard/
2. Settings → API Settings or Integrations
3. Create API Token
4. Copy the full token
5. Send it to me (or update .env directly)

**Already have it?** Just provide the token and I'll update the code.

---

## Alternative: Use App Password

If you prefer not to generate a new token:

1. Login to BulkSMS: https://www.bulksms.com/dashboard/
2. Go to Security Settings
3. Look for "App Passwords" section
4. Generate password for "API Access"
5. Use that password instead

---

## ⏭️ What Happens After

Once you provide the API token (or app password):

1. ✅ Update `.env` file
2. ✅ Update SMS sender code
3. ✅ Test OTP delivery
4. ✅ Enable public enrollment
5. ✅ Create database migrations
6. ✅ Go live with OTP system

---

## 🚀 Temporary Workaround (Development Only)

For testing without real SMS:

```python
# settings.py
OTP_TEST_MODE = True  # Will print OTP to console instead of sending SMS

# In development, user will see: "OTP Code: 123456" in terminal
# In production, set OTP_TEST_MODE = False to send real SMS
```

---

## Questions?

- **Lost your BulkSMS password?** Click "Forgot Password" on login page
- **Can't find API settings?** Check under "Developer" or "Integrations"
- **Getting rate limited?** BulkSMS has per-minute send limits (varies by plan)

Once you have the API token, reply with it and I'll complete the setup! 🎯
