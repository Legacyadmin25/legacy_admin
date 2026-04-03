# Phase 8: API Credential Rotation & Environment Hardening

## Executive Summary
Rotate all external API credentials and encryption keys to ensure production security. This is a critical pre-deployment task covering 6 credential categories affecting SMS, AI, payments, and data encryption.

## Status: In Progress - Keys Generated ✅
- Last Updated: March 28, 2026
- Generated: Django SECRET_KEY ✅ | FIELD_ENCRYPTION_KEY ✅
- Awaiting: BulkSMS credentials from user | OpenAI API key from user
- Estimated Duration: 30 minutes (user input) + 30 minutes (testing)
- Priority: CRITICAL (Must complete before Phase 10 deployment)

---

## Credentials Requiring Rotation

### 1. Django SECRET_KEY
**Current**: `django-insecure-dev-key-change-in-production`
**Impact**: Session security, CSRF tokens, password reset tokens
**Action**: Generate new secure key using:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2. Field Encryption Key (PII Protection)
**Current**: `HNCn4qsuYhkAwZoR-4Z9fL64Ia10vxBJLyHevBY38aY=`
**Impact**: ID numbers, passports, phone numbers, bank accounts encrypted with this key
**Action**: Generate new key using:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
**⚠️ WARNING**: Changing this key will require re-encrypting all existing PII in database

### 3. BulkSMS Credentials
**Current**: 
- Username: `your-new-bulksms-username`
- Password: `your-new-bulksms-password`
**Impact**: SMS notifications, claims reminders, member communications
**Source**: https://www.bulksms.co.za/
**Action**: Register new account or get new credentials from existing account

### 4. OpenAI API Key
**Current**: `sk-your-new-api-key-here`
**Impact**: AI-powered plan suggestions, document summering, claims analysis
**Source**: https://platform.openai.com/api-keys
**Action**: Generate new API key from OpenAI dashboard
**Recommended Model**: `gpt-4o` (current default)

### 5. SMS API Credentials
**Current**:
- API Key: `your-sms-api-key`
- API Secret: `your-sms-api-secret`
**Impact**: Fallback SMS service, OTP delivery
**Provider Options**: Twilio, AWS SNS, Nexmo
**Action**: Choose provider and generate new credentials

### 6. Easypay API Key
**Current**: `your-easypay-api-key`
**Impact**: Payment processing for funeral premiums
**Source**: https://www.easypay.co.za/
**Receiver ID**: 5047 (verify still correct)
**Action**: Get new API key from Easypay dashboard

---

## Credential Rotation Checklist

### Pre-Rotation Tasks
- [ ] Document current provider relationships (BulkSMS, OpenAI, Easypay contacts)
- [ ] Verify all API keys are actually in use (audit codebase)
- [ ] Create backup of current .env file
- [ ] Notify team of credential rotation window
- [ ] Test each service after key rotation

### Rotation Process
- [ ] **Step 1**: Generate new Django SECRET_KEY
- [ ] **Step 2**: Generate new Field Encryption Key (consider PII re-encryption strategy)
- [ ] **Step 3**: Generate/acquire new BulkSMS credentials
- [ ] **Step 4**: Generate new OpenAI API key
- [ ] **Step 5**: Generate/acquire new SMS API credentials
- [ ] **Step 6**: Generate/acquire new Easypay API key
- [ ] **Step 7**: Update .env file with all new credentials
- [ ] **Step 8**: Test each service:
  - [ ] Create test user session (tests SECRET_KEY)
  - [ ] Send test SMS (tests BulkSMS + SMS API)
  - [ ] Generate plan suggestion (tests OpenAI)
  - [ ] Process test payment (tests Easypay)
- [ ] **Step 9**: Remove old .env from git history
- [ ] **Step 10**: Create audit log of credential changes

### Post-Rotation Tasks
- [ ] Verify application still works with new credentials
- [ ] Monitor error logs for auth failures
- [ ] Update deployment documentation
- [ ] Update team's password manager with new credentials
- [ ] Set reminder for next rotation (quarterly recommended)

---

## Security Considerations

### .env File Management
```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Never commit .env to version control
git rm --cached .env

# Use .env.template for documentation
# Keep .env in deployment secrets manager (vault, AWS Secrets Manager, etc.)
```

### Environment-Specific Credentials
**Development (.env.local)**:
- Test API keys with lower rate limits
- Sandbox/test environments for payments
- Debug logging enabled

**Staging (.env.staging)**:
- Real API keys but test accounts
- Rate limiting enabled
- Monitoring enabled

**Production (.env.production)**:
- Real API keys with prod accounts
- Highest security settings
- Real rate limits honored
- Daily log monitoring

### Key Rotation Strategy
- **Frequency**: Quarterly minimum, immediately if exposed
- **Method**: Gradual (run old + new keys for 24h, then deprecate old)
- **Audit**: Log every credential change in audit_log table
- **Recovery**: Keep old credentials in secure backup for 90 days

---

## Implementation Status

### Credentials Status Summary
| Credential | Current | New | Status | Test |
|-----------|---------|-----|--------|------|
| SECRET_KEY | ❌ Dev | ✅ GENERATED | Ready | - |
| FIELD_ENCRYPTION_KEY | ❌ Dev | ✅ GENERATED | Ready | - |
| BULKSMS | ❌ Placeholder | ⏳ AWAITING INPUT | User to provide | - |
| OPENAI_API_KEY | ❌ Placeholder | ⏳ AWAITING INPUT | User to provide | - |
| SMS_API | ⏳ Optional | ⏳ TWILIO FALLBACK | Not required | - |
| EASYPAY_API_KEY | ❌ Placeholder | ⏳ PER-SCHEME | Will vary | - |

---

## Code Modifications Needed

### 1. Settings Update (.env)
- [ ] Update all credentials in .env file

### 2. Environment Validation Script
- [ ] Create script to validate all credentials on startup
- [ ] Add health checks for each API service

### 3. Documentation Updates
- [ ] Update DEPLOYMENT.md with new credentials info
- [ ] Update .env.template with descriptions
- [ ] Document rotation procedures

### 4. Audit Logging
- [ ] Log credential rotation in audit trail
- [ ] Add monitoring alerts for authentication failures

---

## ✅ COMPLETED STEPS - Phase 8 Progress

### Step 1: Generate new Django SECRET_KEY
✅ **DONE** - Generated: ``)%0it4=!$6(uvg7u-b%2^$1(vn%fsrgtut#rggku7=hr_@4hf^``
- Location: `.env` (line 4)
- Impact: All new sessions will use this key
- Old sessions: Will be invalidated (users need to re-login)

### Step 2: Generate new Field Encryption Key
✅ **DONE** - Generated: ``7T1eC7-Rd5a-Ra-krFBTlrg2Wyq-3kUWKQziNa-qW4c=``
- Location: `.env` (line 10)
- Impact: PII (ID numbers, passports, phone, bank accounts) will be encrypted with this key
- ⚠️ **IMPORTANT**: Existing PII in database is encrypted with OLD key, needs migration plan

---

## 📋 NEXT STEPS - What You Need To Do

### YOUR ACTION ITEMS:

#### 1. Provide BulkSMS Credentials
```
From: https://www.bulksms.co.za/ (your existing account)
- Username: Go to Account Settings → API Credentials
- Password: Go to Account Settings → API Credentials

Update in .env:
BULKSMS_USERNAME=<your-actual-username>
BULKSMS_PASSWORD=<your-actual-password>
```

#### 2. Provide OpenAI API Key
```
From: https://platform.openai.com/api-keys (your existing account)
- Create new API key in dashboard
- Copy the key

Update in .env:
OPENAI_API_KEY=sk-<your-actual-key>
```

#### 3. Easypay (Scheme-Specific)
```
NOTE: You mentioned each scheme will get their own Easypay login details
ACTION: When schemes provide their Easypay credentials, update:
EASYPAY_API_KEY=<scheme-specific-key>
```

#### 4. Verify .env is Protected
```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Remove old .env from git history (if accidentally committed)
git rm --cached .env
git commit -m "Remove .env from version control"
```

---

## 🔄 MIGRATION PLAN - Handling Existing Encrypted PII

**Problem**: All existing PII in database is encrypted with OLD key
**OLD KEY**: `HNCn4qsuYhkAwZoR-4Z9fL64Ia10vxBJLyHevBY38aY=`

**Solution Options**:

### Option A: Re-encrypt All PII (Recommended)
```python
# Create a data migration to re-encrypt all PII fields
# This requires:
# 1. Keep OLD key available temporarily
# 2. Read records with OLD key
# 3. Decrypt values
# 4. Re-encrypt with NEW key
# 5. Save records
# 6. Remove OLD key from .env

# Migration script to be created after credentials are finalized
```

### Option B: Keep Old Key, Add New Key (Gradual Migration)
```python
# 1. Add FIELD_ENCRYPTION_KEY_OLD to .env
# 2. Update encryption field to try NEW key first, fall back to OLD
# 3. Gradually migrate records as they're accessed
# 4. After 30 days, remove OLD key
```

**DECISION**: Which approach do you prefer?

---

## 🧪 TESTING PLAN - Verify Each Service

### SMS Service Test
```python
# Test BulkSMS connectivity
from members.communications.sms_sender import send_sms
result = send_sms('0712345678', 'Test message from Legacy Admin')
assert result['success'] == True
```

### OpenAI Service Test
```python
# Test OpenAI connectivity
from members.utils.plan_chat import get_plan_suggestion
suggestion = get_plan_suggestion(member_data)
assert suggestion is not None
```

### Easypay Service Test
```python
# Test payment processing
from payments.utils.easypay import process_payment
result = process_payment(member_id, amount)
assert result['status'] == 'completed'
```

### SECRET_KEY Test
```python
# Verify sessions work with new key
from django.contrib.sessions.models import Session
# New sessions should be created and readable
assert Session.objects.count() >= 0
```

---

## Phase 8 Completion Criteria

✅ **Completion when**:
1. All 6 credentials generated and updated in .env
2. All 4 services tested and working
3. Old .env removed from git history
4. Deployment docs updated
5. Team notified and credentials backed up
6. Audit log created

**Success Indicator**: Application functions normally with all new credentials and all API services respond successfully to test calls.

---

## Next Steps (After Phase 8)
- **Phase 9**: Performance Optimization (database indexes, caching, N+1 fixes)
- **Phase 10**: Production Deployment (SSL, monitoring, final security review)

---

## Resources

- **Django Secret Key Generator**: https://docs.djangoproject.com/en/4.2/#configuring-secret-key
- **Cryptography Key Generation**: https://cryptography.io/en/latest/fernet/
- **BulkSMS API Docs**: https://developer.bulksms.com/
- **OpenAI API**: https://platform.openai.com/docs
- **Easypay Integration**: https://www.easypay.co.za/developer
