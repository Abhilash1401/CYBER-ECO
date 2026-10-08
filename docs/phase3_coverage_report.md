# Phase 3 Review & Tenant Isolation Verification Report

## 1. Tenant Isolation & Access Control Coverage Matrix

The table below documents every Phase 3 endpoint against tests covering cross-tenant data access, wrong-role access, unauthenticated attempts, and private/draft program visibility. Unauthorized and cross-tenant attempts strictly return **404 Not Found** (or 401/403 for authentication/permission boundaries).

| Endpoint (Method & Path) | Cross-Org Read | Cross-Org Update | Cross-Org Delete | Wrong-Role Access | Unauthenticated Access | Private / Draft Hunter Visibility |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `POST /api/v1/companies/` | N/A | N/A | N/A | 403 Forbidden | 401/403 | N/A |
| `GET /api/v1/companies/me/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `GET /api/v1/companies/me/members/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `POST /api/v1/companies/me/members/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `PATCH /api/v1/companies/me/members/<uuid>/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `DELETE /api/v1/companies/me/members/<uuid>/` | N/A | N/A | 404 Isolated | 403 (Viewer/Triager) | 401/403 | N/A |
| `POST /api/v1/companies/me/domains/<uuid>/verify-dns/` | N/A | 404 Isolated | N/A | 403 (Hunter/Viewer) | 401/403 | N/A |
| `POST /api/v1/companies/invitations/accept/` | N/A | N/A | N/A | Validated token | 401/403 | N/A |
| `POST /api/v1/companies/<uuid>/review/` | N/A | 403 Self-Verify | N/A | 403 (CompanyAdmin) | 401/403 | N/A |
| `GET /api/v1/programs/` | Scoped | N/A | N/A | Public (AllowAny) | 200 OK Public | Drafts/Uninvited hidden |
| `GET /api/v1/programs/<slug>/` | Scoped | N/A | N/A | Public (AllowAny) | 200 OK Public | 404 for Draft/Uninvited |
| `GET /api/v1/programs/manage/list/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `POST /api/v1/programs/manage/list/` | N/A | N/A | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `GET /api/v1/programs/manage/<slug>/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `PATCH /api/v1/programs/manage/<slug>/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/submit-review/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/approve-active/` | N/A | 403 Role Check | N/A | 403 (CompanyAdmin) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/transition-status/`| N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `GET /api/v1/programs/manage/<slug>/scopes/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/scopes/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `DELETE /api/v1/programs/manage/<slug>/scopes/<uuid>/`| N/A | N/A | 404 Isolated | 403 (Viewer/Triager) | 401/403 | N/A |
| `GET /api/v1/programs/manage/<slug>/rewards/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/rewards/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `DELETE /api/v1/programs/manage/<slug>/rewards/<uuid>/`| N/A | N/A | 404 Isolated | 403 (Viewer/Triager) | 401/403 | N/A |
| `GET /api/v1/programs/manage/<slug>/invites/` | 404 Isolated | N/A | N/A | 403 (Hunter) | 401/403 | N/A |
| `POST /api/v1/programs/manage/<slug>/invites/` | N/A | 404 Isolated | N/A | 403 (Viewer/Triager) | 401/403 | N/A |
| `DELETE /api/v1/programs/manage/<slug>/invites/<uuid>/`| N/A | N/A | 404 Isolated | 403 (Viewer/Triager) | 401/403 | N/A |

---

## 2. Test Suites Summary (62/62 Passing)

- `tests/test_phase3_cross_tenant_full.py`: Verifies cross-tenant attempts across all sub-resources return 404.
- `tests/test_phase3_wrong_role.py`: Verifies RBAC boundaries (hunter, viewer, triager, company admin vs platform admin).
- `tests/test_phase3_unauthenticated.py`: Verifies unauthenticated access blocks and public access permissions.
- `tests/test_phase3_publishing_validation.py`: Verifies publishing validation (unverified org, no in-scope asset, no rewards, empty rules).
- `tests/test_phase3_state_transitions.py`: Verifies program state machine and terminal states.
- `tests/test_phase3_invite_expiry_and_suspended.py`: Tests invite token expiry, reuse prevention, and hiding suspended org programs.
- `tests/test_program_scope_and_ssrf.py`: Tests SSRF IP/CIDR/URL guards and verified domain matching.
- `tests/test_organization_members.py`: Tests last-admin protections and member invitation token hashing.
- `tests/test_organizations.py`: Tests seed command prod protection and org review mechanisms.
- `tests/test_tenant_isolation_idor.py`: Tests IDOR isolation and field leak prevention.
