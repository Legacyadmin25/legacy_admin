# Legacy Core System — Legacyadmin

> Multi-tenant funeral-policy administration platform built with Django.  
> Manages schemes, branches, members, policies, payments, claims, and reporting  
> for funeral underwriters and their distribution network.

---

## Table of Contents

1. [Overview](#overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Core Modules](#core-modules)
5. [Feature Flags](#feature-flags)
6. [Setup & Running Locally](#setup--running-locally)
7. [Environment Variables](#environment-variables)
8. [Running Tests](#running-tests)
9. [Deployment](#deployment)
10. [Outstanding & Unpushed Changes](#outstanding--unpushed-changes)

---

## Overview

Legacy Core is the internal administration system for **LegacyBit** — a South African funeral insurance platform.  
It provides:

- Scheme and branch management (multi-tenant data isolation)
- Member onboarding, policy creation, and lifecycle management
- Payment collection via Debit Orders, EasyPay, and Bank Reconciliation
- Claims processing and document generation (policy certificates, ID cards)
- Automated SMS/email notifications via BulkSMS
- AI-assisted reporting (`reports_ai/`)
- A public-facing self-enrollment wizard for scheme members
- Scheme self-onboarding wizard for branch staff (feature-flagged)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2 (Python 3.x) |
| Database | SQLite (dev) / PostgreSQL (production) |
| Task queue | Celery + Redis |
| SMS | BulkSMS REST API |
| PDF generation | WeasyPrint |
| Barcodes / QR | `python-barcode`, `qrcode` |
| Excel | `openpyxl`, `pandas` |
| Frontend | Django templates + Tailwind CSS (CDN) |
| Containerisation | Docker + Docker Compose |
| CI/CD | GitHub Actions (`.github/`) |
| Hosting | cPanel / Kubernetes (see `kubernetes/`, `nginx/`) |

---

## Project Structure

```
legacyadmin/          Django project settings & root URLs
accounts/             Custom user model, auth, permissions, context processors
branches/             Branch model, branch-scoped access control
schemes/              Scheme, Plan, PlanTier models + onboarding wizard
members/              Policy, Member, Beneficiary models + EasyPay utilities
claims/               Claims submission and processing
payments/             Payment allocation, debit-order imports
import_data/          Bulk data imports (members, agents, payments, plans)
reports/              Standard reports
reports_ai/           AI-powered reporting (ai_reports/)
audit/                Audit log models and views
dashboard/            Dashboard views and widgets
supplements/          Supplementary benefit management
settings_app/         Runtime settings management
utils/                Shared utilities
templates/            Global base templates
static/               Static assets
```

---

## Core Modules

### Schemes & Plans
- `Scheme` — insurer / intermediary entity; linked to branches
- `Plan` — premium/cover product offered by a scheme
- `PlanTier` — age-banded rates for Spouse / Child / Extended members
- `SchemeProduct` — retail product derived from a wholesale plan (with markup)

### Members & Policies
- `Member` — policyholder personal details
- `Policy` — links a member to a scheme plan; holds policy number, status, EasyPay number
- `Beneficiary` — up to N family members per policy

### Payments
- Debit-order batch import (CSV/XLSX)
- EasyPay barcode payment integration (`members/utils/easypay.py`)
- Bank reconciliation import and preview

### Import Data
- Unified import hub at `/import/`
- Supported import types: members, agents, debit orders, EasyPay, bank reconciliation, **plans (new)**

### Onboarding
- **Public enrollment wizard** — external link → OTP → plan selection → summary
- **Scheme self-onboarding** — branch-staff wizard (feature-flagged `SCHEME_SELF_ONBOARDING`)

---

## Feature Flags

Feature flags live in `legacyadmin/settings.py` under `FEATURE_FLAGS` and are toggled via `.env`:

| Flag key | Env variable | Default | Description |
|---|---|---|---|
| `SCHEME_SELF_ONBOARDING` | `ENABLE_SCHEME_SELF_ONBOARDING` | `False` | Enables the branch scheme onboarding wizard |
| `EASYPAY_INTEGRATION` | `ENABLE_EASYPAY_INTEGRATION` | `False` | Auto-generates EasyPay numbers on policy save; exposes EasyPay fields in the scheme admin form |

Both flags are injected into every template via `accounts/context_processors.py` as  
`feature_scheme_self_onboarding` and `feature_easypay`.

---

## Setup & Running Locally

```bash
# 1. Clone and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment
cp .env.template .env
# Edit .env — see Environment Variables section below

# 4. Apply migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Run development server
python manage.py runserver
```

---

## Environment Variables

Key variables (see `.env.template` for the full list):

```env
SECRET_KEY=...
DEBUG=True

# Database (leave blank for SQLite dev)
DATABASE_URL=

# BulkSMS
BULKSMS_API_TOKEN=
BULKSMS_FROM=LegacyCore

# EasyPay
EASYPAY_RECEIVER_ID=5047
ENABLE_EASYPAY_INTEGRATION=False

# Feature flags
ENABLE_SCHEME_SELF_ONBOARDING=False

# Email
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## Running Tests

```bash
# All tests
python manage.py test

# Specific test modules
python manage.py test import_data.tests
python manage.py test import_data.tests_lapsed
python manage.py test import_data.tests_plan_import   # new — see below

# Via pytest
pytest
```

---

## Deployment

- **Docker**: `docker-compose up --build`
- **Celery worker**: `Dockerfile.celery`
- **cPanel**: `passenger_wsgi.py` entry point; `requirements-cpanel.txt`
- **Kubernetes**: manifests in `kubernetes/`
- **Static files**: `python manage.py collectstatic`
- **PostgreSQL migration**: see `POSTGRESQL_MIGRATION.md`

---

## Outstanding & Unpushed Changes

> **Branch:** `main`  
> **Status:** 1 commit ahead of `origin/main` + 20 modified/new files not yet staged/committed.

---

### Unpushed Commit  
`8c645ee` — *style: Upgrade all onboarding templates to match dark professional theme*

Restyled all four scheme self-onboarding templates to match the dark professional design system:

| Template | Changes |
|---|---|
| `onboarding_step1.html` | Manrope font, card layout, blue gradient header, focus states |
| `onboarding_step2.html` | Same theme, step indicator, back-link |
| `onboarding_review.html` | Two-card detail review layout, green submit button |
| `branch_review_list.html` | Full-width table with hover effects |

Colour palette: dark primary `#0A2540`, secondary `#1E3A8A`.  
Responsive breakpoints: ≤620 px (forms), ≤1000 px (tables).

---

### Uncommitted Changes (20 files — not yet staged)

#### 1. EasyPay Integration (feature-flagged `ENABLE_EASYPAY_INTEGRATION`)

**`legacyadmin/settings.py`**  
- Added `EASYPAY_INTEGRATION` to `FEATURE_FLAGS`.

**`members/utils/easypay.py`**  
- Renamed global `RECEIVER_ID` → `DEFAULT_RECEIVER_ID` to clarify its role.  
- `generate_easypay_number()` now accepts an optional `receiver_id` parameter, enabling per-scheme biller codes.  
- Added `generate_qr_code_image()` — generates a QR code PNG (Django `ContentFile`) linking to the EasyPay payment URL.

**`members/models.py`** — `Policy.save()`  
- After primary-key assignment, if `EASYPAY_INTEGRATION` is `True` and the linked scheme has an `easypay_biller_code`, automatically calls `generate_easypay_number()` and persists the result to `policy.easypay_number`.

**`schemes/models.py`** — `Scheme`  
- New field: `easypay_biller_code` (CharField, optional) — per-scheme EasyPay biller code.  
- New field: `bypass_otp` (BooleanField, default `False`) — skips OTP verification step for public enrollment under this scheme.

**`schemes/templates/schemes/scheme_form.html`**  
- Added EasyPay biller code input and bypass OTP toggle to the scheme admin form.

---

#### 2. New Database Migrations (untracked — need `git add`)

| Migration | Model | Fields Added |
|---|---|---|
| `0015_plan_uw_and_fee_fields` | `Plan` | `penalty_fee`, `service_fee` |
| `0015_plan_uw_and_fee_fields` | `PlanTier` | `uw_cover`, `uw_premium`, `tier_admin_fee` |
| `0016_scheme_easypay_biller_code` | `Scheme` | `easypay_biller_code` |
| `0017_add_bypass_otp_to_scheme` | `Scheme` | `bypass_otp` |

> ⚠️ **Run `python manage.py migrate` after pulling/committing these migrations.**

---

#### 3. Plan Bulk Import (new feature — untracked files)

A complete bulk-import pipeline for funeral plans in the Net Christal 2-sheet XLSX format.

**New files:**
- `import_data/views/plan_import.py` — `PlanImportUploadView`, `PlanImportPreviewView`
- `import_data/templates/import_data/plan_import.html` — upload form UI
- `import_data/templates/import_data/plan_import_preview.html` — row-by-row preview before commit
- `import_data/tests_plan_import.py` — test coverage for the new views

**Modified files:**
- `import_data/urls.py` — three new URL patterns:
  - `GET/POST /import/plans/import/` → `PlanImportUploadView`
  - `POST /import/plans/import/preview/` → `PlanImportPreviewView`
  - `GET /import/plans/import/template/download/` → `download_plan_import_template`
- `import_data/root_views.py` — added `download_plan_import_template` view generating a styled XLSX with:
  - **Sheet 1 "Plan Setup"** — one row per plan (main member rates + fee breakdown across 26 columns)
  - **Sheet 2 "Plan Creator"** — one row per dependent tier (Spouse / Child / Extended) with age bands

**Import options:**
- Target scheme selector
- Mark plans as **Wholesale** (available for scheme owners to derive retail products from)
- **Update existing** plans (matched on Plan Name + Scheme) or insert only

---

#### 4. Scheme Self-Onboarding — Product Builder Enhancements

**`schemes/onboarding/views.py`** (+135 lines)  
- Extended onboarding wizard with bulk product import view (`BulkProductImportView`)
- Full `SchemeProductCreateView` and `SchemeProductEditView` with proper permission checks
- Improved session management for multi-step wizard state

**`schemes/onboarding/forms.py`** (+29 lines)  
- Added `BulkProductImportForm` — file upload form for CSV/XLSX product import
- Added `SchemeProductForm` — create/edit individual products with wholesale plan linkage and retail premium override

**`schemes/onboarding/urls.py`** (+3 routes)  
- `/onboarding/<token>/products/` — product list
- `/onboarding/<token>/products/bulk-import/` — bulk import
- `/onboarding/<token>/products/<pk>/edit/` — edit individual product

**`schemes/onboarding/bulk_import.py`** (new untracked file)  
- `parse_bulk_import_file()` — parses CSV/XLSX; validates required columns (`wholesale_plan_id`, `product_name`, `retail_premium`, `client_cover_amount`); returns `BulkImportResult` with row data and per-row errors
- `create_products_from_import()` — transactionally creates `SchemeProduct` records from validated rows

**`schemes/templates/schemes/onboarding/product_builder.html`**  
- Bulk import button and status indicators added to product builder page

**`schemes/templates/schemes/onboarding/bulk_import.html`** (new untracked file)  
- Upload form with field mapping guidance

---

#### 5. Context Processors — Feature Flags in Templates

**`accounts/context_processors.py`**  
- `user_permissions()` now also returns:
  - `feature_scheme_self_onboarding` — `True` when `SCHEME_SELF_ONBOARDING` flag is on
  - `feature_easypay` — `True` when `EASYPAY_INTEGRATION` flag is on  
- Both are available in every template for conditional rendering without manual flag lookups.

---

#### 6. Global Navigation Update

**`templates/base.html`** (+7 lines)  
- Navigation updated to conditionally show EasyPay and scheme onboarding menu items based on the feature flags above.

---

#### 7. Import Data — Tests & Misc Fixes

**`import_data/tests.py`** (+~191 lines refactored)  
- Expanded test coverage; split into clearer test classes.

**`import_data/tests_lapsed.py`** (+140 lines refactored)  
- Expanded lapsed policy reactivation test coverage.

**`import_data/views/lapsed_policy_reactivation.py`**  
- Minor fixes to status transition logic.

**`import_data/views/policy_amendments_import.py`**  
- Minor fixes.

**`schemes/forms.py`**  
- Minor form field additions.

---

### Summary — What Needs to Be Done Before Pushing

```bash
# 1. Stage all changes
git add .

# 2. Run migrations (new fields — 3 unapplied migrations)
python manage.py migrate

# 3. Run test suite
python manage.py test

# 4. Commit in logical groups (suggested splits):
git commit -m "feat: EasyPay per-scheme biller code + auto-assign on Policy save"
git commit -m "feat: Plan bulk import (Net Christal XLSX format)"
git commit -m "feat: Scheme onboarding — bulk product import + product CRUD views"
git commit -m "fix: Feature flags exposed to templates via context processor"
git commit -m "test: Expand import_data, lapsed reactivation, and plan import coverage"

# 5. Push
git push origin main
```

---

*Last updated: April 24, 2026*
