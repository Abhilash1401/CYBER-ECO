# Cyber Eco — Architecture & System Design Document

**Repository:** `https://github.com/Abhilash1401/CYBER-ECO.git`
**Platform Classification:** Vulnerability Disclosure & Bug Bounty Platform
**Architecture Model:** Zero-Escrow, Privacy-First, Strict Multi-Tenant Separation

---

## 1. High-Level System Architecture

Cyber Eco couples a modern **Next.js (React 18 / TypeScript / Tailwind CSS 4)** client with a hardened **Django 5.2 (Django REST Framework)** API backend, backed by PostgreSQL, Redis, Celery, and MinIO.

```
                          ┌──────────────────────────────────────┐
                          │         Frontend (Next.js 16)        │
                          │   App Router • Tailwind CSS 4 • TS   │
                          └──────────────────┬───────────────────┘
                                             │ HTTP / JSON API
                                             ▼
                          ┌──────────────────────────────────────┐
                          │       Backend (Django 5.2 / DRF)     │
                          │       Custom Scoped QuerySet Layer    │
                          └──────┬───────────┬──────────┬────────┘
                                 │           │          │
                 ┌───────────────┘           │          └────────────────┐
                 ▼                           ▼                           ▼
      ┌────────────────────┐      ┌────────────────────┐      ┌────────────────────┐
      │   PostgreSQL 16    │      │      Redis 7       │      │   MinIO (S3 API)   │
      │ Relational Database│      │   Cache / Broker   │      │   Evidence Vault   │
      └────────────────────┘      └──────────┬─────────┘      └────────────────────┘
                                             │
                                             ▼
                                  ┌────────────────────┐
                                  │   Celery Workers   │
                                  │ DNS Checks & Scans │
                                  └────────────────────┘
```

---

## 2. Core Architectural Principles

### 2.1 Zero-Escrow Settlement Model
- Cyber Eco **never** holds, escrows, collects, or disburses money.
- No wallets, internal ledger balances, platform transaction fees, or integrated banking gateways.
- Organizations compensate researchers directly off-platform through their own financial rails.
- The platform strictly records:
  - Bounty commitments / awards
  - Payment status tracking (`UNPAID`, `PROCESSING`, `PAID`)
  - External transaction reference numbers / proof receipts

### 2.2 Strict Multi-Tenant Isolation & Anti-Enumeration
- Every model referencing tenant data is queried strictly through scoped querysets (`apps.common.models.ScopedQuerySet`).
- Attempts to query or mutate resources belonging to another tenant or outside the user's role authorization **strictly return `404 Not Found`**, not `403 Forbidden`. This completely prevents object ID enumeration and IDOR exploitation.
- Authentication and email-verification endpoints use constant-time operations and anti-enumeration response envelopes to prevent user reconnaissance.

### 2.3 Defense-in-Depth File & Input Sanitization
- **Evidence Vault**:
  - File uploads undergo MIME inspection by inspecting true magic-bytes (not file extension trusts).
  - SHA-256 cryptographic hashing guarantees integrity.
  - Files are saved with random UUID keys under MinIO object storage.
  - By default, new uploads enter `scan_status=PENDING` and are quarantined; downloads are denied until verified clean.
  - PDF uploads are strictly disabled to prevent PDF-embedded JS and SSRF vectors.
- **XSS Neutralization**:
  - All Markdown descriptions, steps to reproduce, and comment inputs are sanitized using Rust-backed **`nh3`** (Ammonia).
  - Dangerous HTML tags (`<script>`, `<iframe>`, `<object>`, `<embed>`, inline event handlers) are stripped before storage.

---

## 3. Data Models & Entity Relationships

```
                     ┌──────────────────┐
                     │       User       │
                     └─────────┬────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                                     ▼
┌────────────────────────┐              ┌──────────────────┐
│  OrganizationMember    │              │  HunterProfile   │
└───────────┬────────────┘              └─────────┬────────┘
            │                                     │
            ▼                                     │
┌────────────────────────┐                        │
│      Organization      │                        │
└───────────┬────────────┘                        │
            │                                     │
            ▼                                     │
┌────────────────────────┐                        │
│        Program         │                        │
└─────┬────────────┬─────┘                        │
      │            │                              │
      ▼            ▼                              ▼
┌───────────┐ ┌───────────┐             ┌──────────────────┐
│ProgramScope ProgramReward             │      Report      │◄────┘
└───────────┘ └───────────┘             └─────────┬────────┘
                                                  │
                                ┌─────────────────┼─────────────────┐
                                ▼                 ▼                 ▼
                     ┌────────────────────┐ ┌───────────┐ ┌───────────────────┐
                     │ReportStatusHistory │ │ReportComm.│ │  ReportEvidence   │
                     └────────────────────┘ └───────────┘ └───────────────────┘
```

---

## 4. State Machines

### 4.1 Vulnerability Report Lifecycle

```
       [ NEW ] ────────────────────────────────────────┐ (Hunter withdraws)
          │                                            ▼
          ▼                                     [ WITHDRAWN ] (Terminal)
     [ TRIAGED ] ◄──────────────┐                      ▲
       │      │                 │                      │ (Hunter withdraws)
       │      ▼                 │                      │
       │   [ NEEDS_INFO ] ──────┘                      │
       │                                               │
       ├───────────────────────────────────────────────┘
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
  [ ACCEPTED ]   [ DUPLICATE ]  [ REJECTED ]  [ INFORMATIVE ]
       │            (Terminal)     (Terminal)    (Terminal)
       ▼
   [ FIXED ]
       │
       ▼
  [ REWARDED ]
       │
       ▼
   [ CLOSED ] (Terminal)
```

### 4.2 Program Lifecycle
- `DRAFT` ➔ `IN_REVIEW` ➔ `ACTIVE` ➔ `PAUSED` ➔ `CLOSED`
- Submission requires: verified organization domain, at least 1 in-scope asset, defined reward tiers, and non-empty policy rules.
