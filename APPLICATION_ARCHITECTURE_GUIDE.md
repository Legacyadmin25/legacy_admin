# Legacy Admin - Funeral Insurance System: Complete Architecture & Workflow Guide

## 📊 APPLICATION OVERVIEW

This is a **Django-based funeral insurance management system** handling:
- Member/policyholder management
- Policy creation and lifecycle
- Payment processing
- Claims handling
- Reporting and analytics
- Multi-tenant scheme support

---

## 🏗️ SYSTEM ARCHITECTURE

### Data Model Relationships

```
BRANCHES (Bank Branches)
    ├── SCHEMES (Insurance schemes per branch)
    │   ├── PLANS (Insurance plans per scheme)
    │   │   └── PLAN TIERS (Main member, spouse, children, extended)
    │   └── POLICIES
    │       ├── MEMBERS (Main member)
    │       ├── DEPENDENTS (Spouse, children, extended family)
    │       ├── BENEFICIARIES (Death benefit recipients)
    │       ├── PAYMENTS (Premium payments)
    │       └── CLAIMS (Death/benefit claims)
    └── AGENTS (Sales agents)
```

### Key Models

| Model | Purpose | Fields |
|-------|---------|--------|
| **Member** | Individual person | Name, ID, DOB, Contact, Address, PII (encrypted) |
| **Policy** | Insurance contract | Policy#, Scheme, Plan, Premium, Start/Cover date, Status |
| **Plan** | Insurance product | Name, Premium, Cover amount, Age limits, Tiers |
| **Dependent** | Family members | Relationship, ID, DOB, Coverage type |
| **Beneficiary** | Death benefit recipient | Name, ID, Relationship, Share % |
| **Payment** | Premium payment | Amount, Date, Method, Status, Reference |
| **Claim** | Benefit claim | Type, Amount, Status, Documents |
| **Scheme** | Insurance scheme | Branch, Name, Registration, Bank account |

---

## 🔄 HOW THE APPLICATION WORKS

### Step 1: MEMBER ENROLLMENT (Create Personal Details)

**Location**: `members/views.py` → `create_personal()` / `step1_personal()`

**Form Used**: `PersonalDetailsForm`

**What Happens:**
1. User (agent) enters member personal details:
   - Title, first/last name
   - ID number (SA: validated with Luhn check; Foreign: passport)
   - Gender, DOB (auto-extracted from SA ID)
   - Contact info (phone, email, WhatsApp)
   - Address details
   - Marital status

2. **Validation**:
   - SA ID: Luhn check + DOB/gender extraction
   - Passport: Required for foreigners
   - Email: Optional but recommended
   - Phone: Required, format validated

3. **Result**: `Member` object created
4. **Next Step**: Policy details selection

---

### Step 2: POLICY DETAILS SELECTION (Choose Plan)

**Location**: `members/views_multi_step.py` → `step2_policy_details()`

**What Happens:**
1. System shows eligible plans based on:
   - Member's age (within plan min/max age)
   - Selected scheme
   - Available coverage types

2. Agent selects:
   - Scheme (funeral scheme)
   - Plan (insurance product)
   - Coverage type (main member only, main + spouse, main + children, etc.)

3. **Auto-filled Data**:
   - Premium amount (from plan)
   - Cover amount (from plan)
   - Payment method options

4. **Result**: Policy created, linked to member
5. **Next Step**: Dependents (if applicable)

---

### Step 3: ADD DEPENDENTS (Family Members)

**Location**: `members/views_multi_step.py` → Step handling

**What Happens:**
1. If plan allows dependents (spouse, children), agent adds:
   - **Spouse Info** (if coverage includes spouse):
     - Name, ID, DOB, Gender, Contact
   - **Children Info** (if coverage includes children):
     - Multiple children with Name, ID, DOB, Gender

2. **Each Dependent**:
   - Creates a `Dependent` record linked to policy
   - Stores relationship type and encrypted ID

3. **Validation**:
   - Age limits per dependent type
   - Max count per type (e.g., max 4 children)

4. **Result**: Policy now has dependents
5. **Next Step**: Beneficiaries

---

### Step 4: ADD BENEFICIARIES (Death Benefit Recipients)

**Location**: `members/models.py` → `Beneficiary` model

**What Happens:**
1. Agent specifies who receives death benefit:
   - Relationship to main member
   - Name, ID, DOB, Gender
   - **Share %** (how much of benefit each person gets)

2. **Example:**
   - Spouse: 50%
   - Child 1: 25%
   - Child 2: 25%
   - Total: 100%

3. **Validation**:
   - Shares must total 100%
   - At least one beneficiary required

4. **Result**: Beneficiary records created
5. **Next Step**: Payment method selection

---

### Step 5: PAYMENT METHOD SELECTION

**Location**: `members/views.py` → Payment options form

**Payment Methods Supported**:

| Method | Details | Status |
|--------|---------|--------|
| **DEBIT_ORDER** | Automatic monthly bank debit | ✅ Built |
| **EFT** | Manual bank transfer | ✅ Built |
| **EASYPAY** | EasyPay collection system | ✅ Built (needs Easypay account) |

**What Happens:**
1. Agent selects payment method
2. If **Debit Order**:
   - Collects: Bank, Branch code, Account holder, Account#, Debit day
   - Bank details stored (encrypted)

3. If **EFT**:
   - Manual transfer - agent records when payment received

4. If **EASYPAY**:
   - System generates unique Easypay # (for member to pay at stores)
   - Creates QR code + barcode for payment slip

5. **Result**: Payment method configured
6. **Next Step**: Policy completion

---

### Step 6: POLICY COMPLETION & ACTIVATION

**What Happens:**
1. System verifies all required fields complete:
   - Member info ✓
   - Policy details ✓
   - Dependents (if applicable) ✓
   - Beneficiaries ✓
   - Payment method ✓

2. Policy marked as `is_complete = True`

3. **Auto-generated**:
   - Unique policy number: `POL-XXXXXXXX`
   - Membership number: `{SCHEME_PREFIX}-{ID:06d}`
   - PDF policy document (if applicable)

4. **Documentation**:
   - PDF sent to member email
   - SMS notification sent (BulkSMS or Twilio)

5. **Status**: Policy → ACTIVE (if payment received)

---

## 💰 PAYMENT PROCESSING WORKFLOW

### Recording a Payment

**Location**: `payments/views.py` → `policy_payment()`

**Data Entry**:
1. Admin/agent searches for member/policy
2. Selects payment method from dropdown:
   - Cash
   - Check
   - Credit card
   - Bank transfer
   - Debit order
   - EasyPay
   - Other

3. Enters:
   - Amount (pre-filled with plan premium suggestion)
   - Payment date
   - Reference number (for bank transfers, EasyPay receipts)
   - Notes (optional)

4. **Validation**:
   - Amount > 0
   - Date not in future
   - Reference required for some methods

5. **Result**: Payment record created, status = COMPLETED

---

### Payment Reconciliation

**Location**: `payments/utils.py` → `update_policy_status()`

**What Happens Automatically**:
1. Each payment triggers policy status update
2. **Calculations**:
   - Total paid = Sum of all payments
   - Outstanding = Premium - Total paid
   - Days since last payment vs grace period (default 30 days)

3. **Policy Status Updated**:
   ```
   - ACTIVE: Payment current (< 30 days since payment)
   - ON_TRIAL: Grace period active (1-30 days overdue)
   - LAPSED: Overdue > 30 days (no payment)
   ```

4. Policy lapse warning flag set

---

### Payment Receipts

**Location**: `payments/models.py` → `PaymentReceipt`

**Auto-generated**:
1. Receipt created when payment confirmed
2. Unique receipt number assigned
3. PDF generated from template
4. **Delivery Options**:
   - Email to member
   - WhatsApp (via Twilio)
   - Manual print
   - SMS link

---

## 📋 CLAIMS PROCESSING WORKFLOW

### Submit a Claim

**Location**: `claims/views.py` → `submit_claim()`

**What Happens**:
1. Member/agent submits claim:
   - Member selection
   - Claim type (death, disability, etc.)
   - Amount claimed
   - Description
   - Supporting documents (PDF, DOC, DOCX - max 20MB)

2. **Validation**:
   - Member has active policy
   - Amount reasonable
   - Document size/type checked

3. **Result**: Claim created, status = PENDING

---

### Claim Processing

**Statuses**:
- **PENDING**: Awaiting review
- **APPROVED**: Approved, ready to payout
- **REJECTED**: Denied with reason

**Audit Trail**: Every status change logged to audit system

---

## 📊 REPORTING & ANALYTICS

### Available Reports

1. **Full Policy Report** (`reports/views.py`)
   - All policies by scheme, status (active/lapsed)
   - Filter by date range, agent, branch

2. **Plan Fee Report** (`reports/views.py`)
   - Agent commissions breakdown
   - Admin fees, cash payouts
   - Annotates premium from plan data

3. **Payment Reports** (`payments/views.py`)
   - Payment history searchable by date range, method, status
   - Payment summary statistics
   - Outstanding balances

4. **Operational Reports** (`reports/views.py`)
   - Payment allocation reports with admin and scheme-facing modes
   - All members report grouped by scheme and policy/member data
   - Amendments report for imported and audited policy/member changes

---

## 🔑 WHAT'S BUILT & FUNCTIONAL ✅

### Core Features
- ✅ Member management (create, edit, search)
- ✅ Multi-step policy enrollment wizard
- ✅ Dependent & beneficiary management
- ✅ Encrypted PII storage (ID#, passport, account numbers)
- ✅ Payment recording & reconciliation
- ✅ Policy status management (active/lapsed)
- ✅ Claims submission & tracking
- ✅ Receipt generation & delivery
- ✅ Payment import from CSV/Excel
- ✅ Basic reporting
- ✅ Audit logging for compliance

### Integration Points
- ✅ BulkSMS integration (SMS notifications)
- ✅ Twilio integration (WhatsApp, SMS)
- ✅ EasyPay integration (payment collection)
- ✅ Operational reporting for payments, members, and amendments
- ✅ AWS S3 (document storage)
- ✅ Email (policy documents, receipts)

### Security
- ✅ Encrypted sensitive fields (PII)
- ✅ Role-based access control (agents, admins, scheme managers)
- ✅ Multi-tenancy (per-scheme isolation)
- ✅ Audit trail (all significant actions logged)
- ✅ User authentication

---

## ❌ WHAT'S NEEDED TO BE FULLY FUNCTIONAL

### 1. **Payment Gateway Integration** (CRITICAL)
   - [ ] Implement actual EasyPay API calls (currently placeholder)
   - [ ] Add payment webhook handlers (payment confirmations)
   - [ ] Automated bank reconciliation

### 2. **Claim Payout Processing** (CRITICAL)
   - [ ] Implement claim approval workflow
   - [ ] Add death certificate validation
   - [ ] Automate payout to beneficiaries (bank transfer)
   - [ ] Compliance checks & flags

### 3. **Policy Document Generation** (IMPORTANT)
   - [ ] Generate PDF policy documents (currently basic)
   - [ ] Include terms & conditions per plan
   - [ ] Digital signatures

### 4. **Underwriting Engine** (IMPORTANT)
   - [ ] Age verification automation
   - [ ] Health screening questions (optional based on cover)
   - [ ] Underwriting decision logic
   - [ ] Risk flagging system

### 5. **Member Self-Service Portal** (NICE-TO-HAVE)
   - [ ] Member login & account access
   - [ ] View policy details
   - [ ] Download documents
   - [ ] Track payments
   - [ ] Submit claims

### 6. **Mobile App** (NICE-TO-HAVE)
   - [ ] Agent app for policy sales
   - [ ] Member app for claims
   - [ ] Offline capability

### 7. **Data Validation & Cleaning**
   - [ ] Fuzzy matching for duplicate detection
   - [ ] Data quality checks
   - [ ] Reporting on data issues

### 8. **Performance Optimization**
   - [ ] Database indexes for large datasets
   - [ ] Caching strategy (Redis)
   - [ ] Batch processing for imports

### 9. **Compliance & Reporting**
   - [ ] FSP (Financial Services Provider) regulatory reports
   - [ ] GEPF compliance (if applicable)
   - [ ] Anti-fraud monitoring
   - [ ] POPIA compliance (privacy)

### 10. **Testing & QA**
   - [ ] Unit tests (models, utilities)
   - [ ] Integration tests (full workflows)
   - [ ] UAT scenarios
   - [ ] Load testing

---

## 📱 HOW TO CAPTURE A POLICY: Step-by-Step

### Agent Flow

**1. Go to Policy Enrollment**
```
Dashboard → Members → Add New Policy
```

**2. Step 1 - Personal Details**
- Enter member name, ID, contact
- System validates SA ID (Luhn check) or accepts passport
- Save & continue

**3. Step 2 - Select Plan**
- Choose scheme (e.g., "Chegutu Scheme")
- Select plan based on member age
- Confirm premium amount

**4. Step 3 - Add Family (if applicable)**
- Add spouse info (name, ID, DOB)
- Add children (up to max allowed)
- Each validated for age requirements

**5. Step 4 - Beneficiaries**
- Specify who gets death benefit
- Set percentage shares (must total 100%)
- Can be same as dependents or different

**6. Step 5 - Payment Method**
- Select: Debit Order, EFT, or Easypay
- If debit order: collect bank details (encrypted)
- If Easypay: system generates unique # + QR code

**7. Review & Complete**
- System verifies all fields
- Policy number auto-generated
- Document sent to member
- Policy status = ACTIVE (if payment received)

**8. Record Payment**
- Go to Payments section
- Search for member/policy
- Record first premium received
- Policy status updated automatically

---

## 💾 HOW TO RECORD PAYMENTS: Step-by-Step

**1. Go to Payment Recording**
```
Dashboard → Payments → Record Payment
```

**2. Search for Member**
- By name, ID number, or policy number
- View member's payment history
- See outstanding balance

**3. Enter Payment Details**
- **Amount**: Pre-filled with plan premium
- **Date**: When payment received
- **Method**: Cash, Check, Bank transfer, Debit order, EasyPay
- **Reference**: Bank ref# or EasyPay receipt#
- **Notes**: Optional (e.g., "Late payment, member called")

**4. Validation**
- System checks: Amount > 0, Date ≤ today
- If amount < premium: policy still active but flagged as partial

**5. Receipt Generation**
- Auto-generated receipt with unique #
- Sent to member via email/WhatsApp
- Stored in system

**6. Policy Status Updated**
- Days since payment calculated
- If current: ACTIVE
- If overdue: LAPSED (after grace period)

---

## 📊 HOW TO GENERATE REPORTS: Step-by-Step

### Simple Reports

**1. Go to Reports**
```
Dashboard → Reports → Select Report Type
```

**2. Full Policy Report**
- Select scheme filter
- Select status (active/lapsed)
- Click generate
- Shows: All policies, members, premium, status

**3. Payment Report**
- Date range (from - to)
- Payment method filter
- Status filter (completed/pending/failed)
- Shows: All payments, totals, outstanding

### Operational Reports

**1. Go to Reports**
```
Dashboard → Reports
```

**2. Use the report menu**
```
- Payment Report: Admin
- Payment Report: Scheme
- All Members Report
- Amendments Report
```

**3. System:**
- Uses allocation-backed payment reporting
- Separates admin and scheme-facing payment views
- Groups policy/member data in the all-members report
- Tracks import and audit-driven amendments

---

## 🚀 QUICK START CHECKLIST

### For System to Be Operational:

#### Phase 1: Core Setup (DONE)
- [x] Database schema
- [x] User management
- [x] Member management
- [x] Policy creation
- [x] Payment recording
- [x] Reports

#### Phase 2: Integration (PHASE 8 - IN PROGRESS)
- [ ] Secure all API keys (BulkSMS, OpenAI, EasyPay)
- [ ] Test SMS sending
- [ ] Test payment processing flow

#### Phase 3: Compliance (NEEDED)
- [ ] Audit logging verification
- [ ] Access control by role
- [ ] Data privacy checks
- [ ] Encryption validation

#### Phase 4: Testing (NEEDED)
- [ ] Full policy enrollment workflow
- [ ] Payment recording & updates
- [ ] Report generation
- [ ] Edge cases (lapsed policies, partial payments, etc.)

---

## 🔐 SECURITY CONSIDERATIONS

### Encrypted Fields
- ID numbers (all members, dependents, beneficiaries)
- Passport numbers
- Bank account numbers
- Data encrypted with `FIELD_ENCRYPTION_KEY`

### Access Control
- **Member**: Limited to own policy
- **Agent**: Own schemes only
- **Branch Owner**: All agents + schemes in branch
- **Scheme Manager**: Own scheme only
- **Admin**: Full access

### Audit Trail
- All payments logged
- All claim status changes logged
- User action tracking
- IP address capture

---

## 📞 API ENDPOINTS

Main endpoints available:

```
GET  /members/find_policy/           # Search members
POST /members/create_personal/        # Create new member
GET  /members/policy/<id>/            # View policy
POST /payments/policy_payment/        # Record payment
GET  /payments/                       # Payment history
POST /claims/submit_claim/            # Submit claim
GET  /reports/full_policy_report/     # Generate report
GET  /reports/payment_allocation_report/   # Allocation-backed payment reports
GET  /reports/all_members_report/          # Grouped policy/member report
GET  /reports/amendments_report/           # Policy/member amendments report
```

---

## 🎯 NEXT PRIORITY ACTIONS

1. **Complete Phase 8 Credential Rotation** (You're here!)
   - Get BulkSMS credentials from your account
   - Get OpenAI API key
   - Update .env file
   - Run credential tests

2. **Test Full Workflow** (After Phase 8)
   - Create a test member
   - Capture a complete policy
   - Record a payment
   - Generate a report

3. **Configure Easypay per Scheme** (Next)
   - Each scheme will need unique Easypay credentials
   - When schemes provide login details, update system

4. **Go Live Preparation** (After testing)
   - Set real credentials in production .env
   - Enable SSL/HTTPS
   - Monitor logs
   - Train agents on system
