# Phase 8 Credential Rotation - YOUR ACTION ITEMS

## 🎯 Summary
I've generated the new security keys. Now I need credentials from your existing accounts.

---

## ✅ What I've Already Done:

1. **New Django SECRET_KEY** ✅
   ```
   )%0it4=!$6(uvg7u-b%2^$1(vn%fsrgtut#rggku7=hr_@4hf^
   ```
   - Already in: `.env` (line 4)
   - Impact: New sessions will use this key

2. **New Field Encryption Key** ✅
   ```
   7T1eC7-Rd5a-Ra-krFBTlrg2Wyq-3kUWKQziNa-qW4c=
   ```
   - Already in: `.env` (line 10)
   - Impact: New PII encryption uses this key

3. **Updated .env file** ✅
   - All settings structured with clear section headers
   - Old credentials backed up in comments
   - New keys in place

---

## ❓ What I Need From You:

### 1️⃣ BulkSMS Credentials
**Source**: https://www.bulksms.co.za/

Steps:
1. Log into your BulkSMS account
2. Go to: Account Settings → API Credentials → Integration
3. Copy your **Username** and **Password/API Key**
4. Provide both to me

**Where it goes in .env:**
```
BULKSMS_USERNAME=<paste-here>
BULKSMS_PASSWORD=<paste-here>
```

---

### 2️⃣ OpenAI API Key
**Source**: https://platform.openai.com/api-keys

Steps:
1. Log into your OpenAI account
2. Go to: API Keys → Create new secret key
3. Copy the key (looks like: `sk-proj-xxx...`)
4. Provide to me

**Where it goes in .env:**
```
OPENAI_API_KEY=sk-<paste-here>
```

---

### 3️⃣ Easypay Setup (Different per Scheme)
**Source**: https://www.easypay.co.za/

You mentioned: "Easypay numbers will be different from each scheme when they get their login details"

**What I understand:**
- Each scheme will get unique Easypay credentials
- These will come later when schemes register

**For now:**
- Leave EASYPAY_API_KEY as placeholder
- When schemes get their credentials, provide them to me
- I'll update the .env and set up per-scheme configuration

---

## 📝 DECISION NEEDED: PII Re-encryption

The existing data in the database is encrypted with the OLD key. We have two options:

### Option A: Re-encrypt Everything (Recommended - Clean Start)
```python
# Pros:
- Complete key rotation
- Old key can be removed immediately
- Strong security posture

# Cons:
- Takes time if large dataset
- All PII needs to be re-encrypted
- Need downtime

# How: I'll create migration script after credentials are ready
```

### Option B: Dual-Key for 30 Days (Gradual Migration)
```python
# Pros:
- No downtime
- Records gradually migrate as accessed
- Gradual process

# Cons:
- Two keys in system for 30 days
- More complex to manage
- Slower full rotation

# How: Keep old key, add new key, migrate over time
```

**Your preference?** Option A or Option B?

---

## 🔒 Git Security

After you provide credentials, I'll need to:

```bash
# 1. Make sure .env is ignored
# 2. Remove .env from git history (if accidentally committed)
# 3. Create secure backup of credentials
```

---

## ✅ Next Immediate Steps:

1. **Get credentials from BulkSMS dashboard** → Send to me
2. **Get API key from OpenAI dashboard** → Send to me
3. **Choose PII re-encryption strategy** → Option A or B?
4. Then I'll:
   - Update .env with your real credentials
   - Run full testing suite
   - Create security audit log
   - Complete Phase 8

---

## ❓ Questions?

Current Status:
- ✅ Security keys generated
- ✅ .env file structure created
- ⏳ Awaiting BulkSMS credentials
- ⏳ Awaiting OpenAI API key
- ⏳ Awaiting PII re-encryption decision
- ⏳ Then testing and completion
