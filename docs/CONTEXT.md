# Cyber Eco — Development Context & Feature Implementation History

**Target Repository:** `https://github.com/Abhilash1401/CYBER-ECO.git`
**Current State:** Phases 1 through 4 Completed, Fully Tested (74 / 74 tests passing), Hardened, and Prepared for Git Synchronization.

---

## 1. What Changes Were Made (Phases 1–4 Summary)

### Phase 1: Core Scaffolding & Infrastructure
- Set up Docker Compose environment with 7 services: Django, Next.js, PostgreSQL, Redis, Celery worker, MinIO, and Mailpit.
- Implemented `apps.common.models.TimestampedModel` and custom `ScopedQuerySet` for tenant safety.
- Implemented `apps.audit` with immutable `AuditLog` model and `log_audit_event()` service.
- Local SQLite / production PostgreSQL automated settings configuration.

### Phase 2: Authentication & Account Security
- Email-based custom `User` model with `argon2` password hashing.
- Role architecture: `PLATFORM_ADMIN`, `COMPANY_ADMIN`, `COMPANY_TRIAGER`, `COMPANY_VIEWER`, and `HUNTER`.
- Mandatory Time-based One-Time Password (TOTP) MFA for company & platform admins using `django-otp`.
- Recovery codes with single-use consumption.
- Anti-enumeration protection on registration and password reset.
- Token revocation and session cycling on credential updates.

### Phase 3: Organization & Bug Bounty Program Management
- Multi-tenant `Organization` model with membership management (`OrganizationMember`).
- DNS TXT record domain verification with SSRF protections.
- Invite token generation with expiration and single-use security.
- `Program` model with lifecycle transitions: `DRAFT` ➔ `IN_REVIEW` ➔ `ACTIVE` ➔ `PAUSED` ➔ `CLOSED`.
- Scoping engine (`ProgramScope`): CIDR, domain, IP, URL, and mobile apps with SSRF loopback protections.
- Reward tiers (`ProgramReward`) with severity-to-bounty matrix.
- Complete Company Dashboard UI built in Next.js (layout, members, programs, scope).

### Phase 4: Vulnerability Reports, Evidence Vault, & Triage Desk
- **Report Engine**: `Report`, `ReportStatusHistory`, `ReportComment`, and `ReportEvidence` models.
- **Centralized State Machine**: Governed strictly via `apps.reports.services.transition_report_status()`.
- **Dual-Visibility Discussion Threads**:
  - `SHARED`: Visible to both the researcher and company triagers.
  - `INTERNAL`: Privileged company-only internal discussions concealed from external hunters.
- **Separated Serializers**: Dual serializer pattern (`HunterReportDetailSerializer` vs `CompanyReportDetailSerializer`) preventing any internal notes, triager identity, or internal comments from ever reaching the hunter API response.
- **Evidence Vault**:
  - Storage engine (`apps.reports.storage.py`) validating true magic bytes for PNG/JPEG/WEBP/TXT.
  - Quarantined download pipeline (`scan_status=PENDING` blocks download until explicitly approved).
  - SHA-256 integrity verification.
  - Disabled PDF uploads to prevent PDF-embedded JS and SSRF risks.
- **Stored XSS Sanitization**:
  - Integrated Rust-backed **`nh3`** library for HTML/Markdown sanitization.
- **Frontend Portals**:
  - Hunter submission & report tracking pages (`/reports`, `/reports/new`, `/reports/[id]`).
  - Company triage desk (`/dashboard/company/reports`, `/dashboard/company/reports/[id]`).

---

## 2. Complete File Structure

```
cybereco/
├── .github/
│   ├── workflows/
│   │   └── ci.yml                     # Automated CI test & lint pipeline
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.yml             # Structured bug reporting form
│   │   └── feature_request.yml        # Feature proposal form
│   └── pull_request_template.md       # PR checklist with security criteria
├── backend/
│   ├── apps/
│   │   ├── accounts/                  # Authentication, TOTP MFA, User roles
│   │   ├── audit/                     # Centralized immutable audit logs
│   │   ├── common/                    # ScopedQuerySet, permissions, throttles
│   │   ├── companies/                 # Organizations, DNS TXT verification
│   │   ├── programs/                  # Programs, scoping, reward matrix
│   │   ├── reports/                   # Vulnerability reports, state machine, evidence
│   │   ├── notifications/             # System activity notifications
│   │   └── bounties/                  # Zero-escrow bounty tracking (Phase 5 skeleton)
│   ├── config/                        # Django project configuration & settings
│   ├── requirements/                  # Dependencies (base.txt, dev.txt, prod.txt)
│   └── tests/                         # 24 test suites with 74 comprehensive tests
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── dashboard/company/     # Company dashboard & triage desk
│   │   │   ├── reports/               # Hunter report submission & detail
│   │   │   ├── programs/              # Public & private program directory
│   │   │   ├── login/                 # Authentication & MFA challenge
│   │   │   ├── register/              # Hunter & company registration
│   │   │   └── settings/              # MFA setup & profile controls
│   │   ├── components/                # Reusable UI widgets
│   │   ├── lib/                       # API client with token management
│   │   └── types/                     # TypeScript definitions
│   └── package.json                   # Next.js 16 dependencies
├── docs/
│   ├── ARCHITECTURE.md                # System design & architecture
│   ├── CONTEXT.md                     # Feature history & structural reference
│   └── phase3_coverage_report.md      # Phase 3 testing coverage matrix
├── scripts/                           # Shell scripts & container utilities
├── .gitignore                         # Comprehensive ignore rules
├── .pre-commit-config.yaml            # Black, Ruff, Bandit, pip-audit hooks
├── docker-compose.yml                 # Local multi-service infrastructure
├── Makefile                           # Quick development commands
├── pyproject.toml                     # Python tool configurations
├── README.md                          # Repository documentation
├── LICENSE                            # Apache 2.0 License
└── SECURITY.md                        # Responsible disclosure policy
```

---

## 3. Key Endpoints Reference

### Authentication (`/api/v1/auth/`)
- `POST /api/v1/auth/register/` — Hunter & company registration
- `POST /api/v1/auth/login/` — Password login (returns MFA challenge if enabled)
- `POST /api/v1/auth/mfa/verify/` — TOTP verification & JWT issuance
- `POST /api/v1/auth/password/reset/` — Anti-enumeration password recovery

### Companies & Organizations (`/api/v1/companies/`)
- `GET/POST /api/v1/companies/` — Organization management
- `POST /api/v1/companies/{id}/verify-domain/` — Trigger DNS TXT verification
- `GET/POST /api/v1/companies/{id}/members/` — Member team management

### Programs & Scope (`/api/v1/programs/`)
- `GET /api/v1/programs/` — Public active program directory
- `GET/POST /api/v1/programs/company/` — Company program management
- `POST /api/v1/programs/company/{id}/submit-review/` — Submit program for review
- `POST /api/v1/programs/company/{id}/scope/` — In-scope / out-of-scope asset definition

### Vulnerability Reports (`/api/v1/reports/`)
- `POST /api/v1/reports/` — Submit report (with in-scope asset check & nh3 sanitization)
- `GET /api/v1/reports/` — Hunter's own report list
- `GET /api/v1/reports/{id}/` — Dual-serializer detail endpoint
- `POST /api/v1/reports/{id}/transition/` — Company state transition engine
- `POST /api/v1/reports/{id}/comments/` — Add comment (`SHARED` or `INTERNAL`)
- `POST /api/v1/reports/{id}/evidence/` — Magic-byte verified attachment upload
- `GET /api/v1/reports/{id}/evidence/{evidence_id}/download/` — Presigned download (gated by scan status)

---

## 4. Test Suite Summary

- Total Automated Tests: **74**
- Test Coverage:
  - Multi-tenant cross-org & cross-hunter isolation (100% return HTTP 404)
  - SSRF prevention & DNS TXT verification
  - Unscanned evidence download blocking
  - Magic-byte spoofing rejection
  - Stored XSS neutralization (SVG onload, iframe, script tags)
  - Duplicate reporting zero-leakage guarantee
