# Cyber Eco — Enterprise Bug Bounty Platform

<div align="center">

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2+-092E20.svg?logo=django)](https://www.djangoproject.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.4+-black.svg?logo=next.js)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-4.0+-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com/)
[![Security Standards](https://img.shields.io/badge/Security-Hardened-success.svg?logo=shield)](SECURITY.md)

*A privacy-first, zero-escrow Bug Bounty and Coordinated Vulnerability Disclosure platform connecting security researchers with organizations.*

[Key Features](#-key-features) •
[Architecture](#-architecture) •
[Quick Start](#-quick-start) •
[Security Model](#-security-model) •
[Testing](#-testing--quality) •
[Contributing](#-contributing)

</div>

---

## 🌟 Overview

**Cyber Eco** is an enterprise-grade Vulnerability Disclosure and Bug Bounty platform. Designed with zero-trust architectural principles, Cyber Eco provides organizations with full control over programs and assets while empowering security researchers (hunters) with streamlined reporting, dual-visibility triage communication, and off-platform, zero-escrow bounty attribution.

### Core Philosophy:
- **Zero Escrow**: Cyber Eco does **not** handle or escrow funds. Organizations pay researchers directly through their chosen financial rails; the platform tracks commitments, approvals, and proof-of-payment receipts transparently.
- **Strict Tenant Isolation**: Complete data segregation between organizations and security researchers. Cross-tenant or unauthorized accesses strictly yield `404 Not Found` rather than `403 Forbidden` to prevent object enumeration.
- **Defense in Depth**: DNS TXT asset verification, SSRF-safe scope policies, anti-enumeration authentication, magic-byte inspection on evidence uploads, and strict HTML sanitization via `nh3`.

---

## ✨ Key Features

### 🏢 Company & Program Management
- **Organization Onboarding**: Strict domain ownership verification via automated DNS TXT record checks.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions (`company_admin`, `company_triager`, `company_viewer`).
- **Scope Definition**: Rigorous in-scope/out-of-scope asset definition preventing wildcard ambiguities and SSRF loopback abuse.
- **Dual Program Modes**: Public programs accessible to all verified hunters or invite-only Private programs.

### 🎯 Vulnerability Reporting & Triage Desk
- **State Machine Lifecycle**: Deterministic report lifecycles:
  `NEW` ➔ `TRIAGED` ➔ `NEEDS_INFO` / `ACCEPTED` / `DUPLICATE` / `REJECTED` / `INFORMATIVE` ➔ `FIXED` ➔ `REWARDED` ➔ `CLOSED`.
- **Dual-Visibility Discussion Threads**:
  - **Shared Comments**: Collaborative discussions between hunter and triage teams.
  - **Internal Comments**: Privileged, company-only internal deliberations concealed from external researchers.
- **Evidence Vault**: Secure file attachment pipeline with MIME magic-byte verification, SHA-256 integrity validation, presigned single-use URLs, and an automated scanning quarantine gate.
- **Sanitized Markdown Rendering**: Hardened input pipelines powered by Rust-backed `nh3` HTML sanitization to neutralize stored XSS payloads.

### 🛡️ Authentication & Account Security
- **MFA / TOTP Enforcement**: Mandatory TOTP Two-Factor Authentication for privileged organizational roles.
- **Session Cycling**: Automatic session invalidation across devices upon password reset or security credential modifications.
- **Anti-Enumeration Protection**: Constant-time responses on authentication, registration, and password recovery endpoints.

---

## 🏛 Architecture

```
                       ┌─────────────────────────┐
                       │   Next.js 16 (App Router)│
                       │   Tailwind CSS 4        │
                       └────────────┬────────────┘
                                    │ Reverse Proxy / API Client
                                    ▼
                       ┌─────────────────────────┐
                       │   Django 5.2 REST API   │
                       │   (DRF + Scoped QuerySet)│
                       └─────┬──────────────┬────┘
                             │              │
             ┌───────────────┴────┐   ┌─────┴────────────────┐
             ▼                    ▼   ▼                      ▼
    ┌─────────────────┐ ┌───────────────┐ ┌───────────────┐ ┌────────────────┐
    │ PostgreSQL 16   │ │ Redis 7       │ │ Celery Worker │ │ MinIO (S3 API) │
    │ (Relational DB) │ │ (Cache/Broker)│ │ (Async Tasks) │ │ (Evidence Vault│
    └─────────────────┘ └───────────────┘ └───────────────┘ └────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Alternatively for local dev: Python 3.13+, Node.js 20+, PostgreSQL 16, Redis 7

### Single-Command Startup (Recommended)

Clone the repository and run the startup script:

```bash
git clone https://github.com/YOUR_ORGANIZATION/cybereco.git
cd cybereco
```

**Windows (PowerShell / Command Prompt):**
```powershell
.\run.bat
# or: .\run.ps1
```

**Linux / macOS / Git Bash:**
```bash
chmod +x run.sh scripts/wait-for-it.sh
./run.sh
```

**Using Makefile:**
```bash
make start
```

*The startup script automatically initializes `.env` from template, generates cryptographically strong random secrets, and brings up all containers with pending database migrations applied.*

---

## 🌐 Service Ports & Dashboard Endpoints

| Component | Target URL | Description |
|-----------|------------|-------------|
| **Frontend Portal** | `http://127.0.0.1:3000` | Hunter Portal & Company Dashboard |
| **Backend REST API** | `http://127.0.0.1:8000/api/v1/` | Core API Root |
| **API Documentation** | `http://127.0.0.1:8000/api/v1/docs/` | Interactive OpenAPI Schema |
| **MinIO Object Console** | `http://127.0.0.1:9001` | Evidence Attachment Object Storage |
| **Mailpit Web UI** | `http://127.0.0.1:8025` | Local SMTP capture inbox for verification emails |
| **PostgreSQL** | `127.0.0.1:5432` | Relational Database (bound to localhost) |
| **Redis** | `127.0.0.1:6379` | Broker & Cache (bound to localhost) |

---

## 🧪 Testing & Quality

Cyber Eco maintains a rigorous test suite covering tenant isolation, role barriers, anti-enumeration, SSRF validation, state transitions, and XSS sanitization:

### Running Backend Tests
```bash
# Inside Docker
docker compose exec backend pytest

# Local Virtual Environment
.\.venv\Scripts\pytest.exe backend -v
```

### Code Formatting & Security Linting
```bash
# Run all pre-commit hooks (Black, Ruff, Bandit, pip-audit)
pre-commit run --all-files
```

### Frontend Build & Linting
```bash
cd frontend
npm run lint
npm run build
```

---

## 🔒 Security Model & Best Practices

- **Zero Object Leakage**: Access to objects outside the authenticated user's organization or ownership scope returns HTTP 404 to block IDOR probing.
- **Evidence Storage Quarantine**: Attachments default to `scan_status=PENDING` and are quarantined from download until passed by a malware scanning pipeline.
- **Strict SSRF Mitigation**: Scopes undergo strict validation to block loopback addresses (`127.0.0.1`, `::1`), private ranges (RFC 1918), and cloud metadata endpoints (`169.254.169.254`).
- **Production Guardrails**: Development seed scripts (`seed_dev_users`) are strictly gated by `DEBUG=True` and disabled in production settings.

For details on responsible vulnerability disclosure regarding Cyber Eco itself, see [SECURITY.md](SECURITY.md).

---

## 📂 Project Structure

```
cybereco/
├── .github/                 # GitHub Actions workflows & issue templates
├── backend/                 # Django 5.2 API Backend
│   ├── apps/
│   │   ├── accounts/        # Authentication, TOTP MFA, User Models
│   │   ├── audit/           # Audit logging service
│   │   ├── common/          # Scoped querysets, base models, permissions
│   │   ├── companies/       # Organizations, memberships, DNS verification
│   │   ├── programs/        # Bug bounty programs, scope, reward matrix
│   │   ├── reports/         # Vulnerability reports, state machine, evidence
│   │   ├── notifications/   # System and activity notifications
│   │   └── bounties/        # Zero-escrow reward tracking
│   ├── config/              # Django settings & URL routing
│   └── tests/               # Test suites
├── frontend/                # Next.js 16 Frontend
│   └── src/
│       ├── app/             # App router pages (dashboard, reports, programs)
│       ├── components/      # Reusable UI components
│       └── lib/             # API client & utilities
├── docs/                    # Technical architecture & verification specs
├── scripts/                 # Automation & utility scripts
├── docker-compose.yml       # Production/Local infrastructure orchestration
├── Makefile                 # Development command interface
└── pyproject.toml           # Formatting and tooling configuration
```

---

## 📄 License

Cyber Eco is open-source software licensed under the [Apache License 2.0](LICENSE).
