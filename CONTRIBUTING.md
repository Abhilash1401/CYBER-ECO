# Contributing to Cyber Eco

Thank you for your interest in contributing to Cyber Eco! As a security-sensitive platform, we maintain rigorous engineering, testing, and security standards.

## Code of Conduct

Please be respectful, collaborative, and professional in all interactions across issues, pull requests, and discussions.

## Development Workflow

1. **Fork & Branch**:
   - Create a feature branch off `main`:
     ```bash
     git checkout -b feat/your-feature-name
     ```

2. **Environment Setup**:
   - Ensure you have pre-commit hooks installed:
     ```bash
     pre-commit install
     ```
   - All commits must pass:
     - `black` formatting
     - `ruff` linting
     - `bandit` static security analysis
     - `pip-audit` vulnerability scanning

3. **Writing Code & Conventions**:
   - Backend logic follows standard Django REST Framework patterns with explicit services layers.
   - All tenant queries MUST use scoped querysets to prevent cross-tenant object access.
   - Unauthorized access attempts to scoped objects must return `404 Not Found`, not `403`.
   - Untrusted inputs (Markdown/HTML) must be sanitized with `nh3`.

4. **Testing is Mandatory**:
   - Every bug fix or new endpoint must include test coverage covering:
     - Positive execution path
     - Cross-tenant / IDOR attempts (expecting 404)
     - Unauthenticated access attempts (expecting 401)
     - Wrong role access attempts (expecting 403 or 404)
   - Ensure all tests pass:
     ```bash
     pytest backend -v
     ```

5. **Submitting Pull Requests**:
   - Provide a clear PR title and summary detailing what changed and why.
   - Reference related issues.
   - Ensure CI checks pass.
