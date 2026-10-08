## Summary of Changes
Provide a brief summary of what this pull request introduces or fixes.

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to not work as expected)
- [ ] Security hardening or policy update
- [ ] Documentation update

## Testing Performed
- [ ] Unit & integration tests added / passing (`pytest backend/ -v`)
- [ ] Pre-commit hooks passed (`pre-commit run --all-files`)
- [ ] Tenant isolation verified (cross-tenant requests return 404)
- [ ] Frontend builds without TypeScript or ESLint errors (`npm run build`)

## Security Checklist
- [ ] No hardcoded secrets, API keys, or private tokens committed
- [ ] Input data sanitized (nh3 for markdown/html)
- [ ] All scoped models filtered through tenant querysets
