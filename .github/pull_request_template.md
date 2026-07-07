## Summary

<!-- 1-3 bullets: what changed and why -->

## Type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [ ] Documentation
- [ ] Deployment / config
- [ ] Tests

## Test plan

- [ ] Backend tests pass (`pytest app/tests/ -v`)
- [ ] Frontend tests pass (`cd frontend && npx vitest run`)
- [ ] Production build succeeds (`cd frontend && npm run build`)
- [ ] Verified on infra01 (if deployment change)

## Security checklist

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] No new environment variables with default values containing URLs or keys
- [ ] Container runs as non-root (USER 1001)
- [ ] SecurityContext preserved (runAsNonRoot, drop ALL, no privilege escalation)
