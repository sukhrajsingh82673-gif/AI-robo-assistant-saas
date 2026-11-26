## Summary

Describe the purpose of this pull request and reference any relevant ADRs (`docs/adr/`) or issues.

## Change Type

- [ ] Bug fix
- [ ] New feature / enhancement
- [ ] Security hardening / remediation
- [ ] Documentation / CI maintenance

## Verification Checklist

- [ ] `python3 -m compileall -q .` passes
- [ ] `python3 scripts/anti_evasion_linter.py` and `python3 scripts/anti_bypass_linter.py` pass
- [ ] `node --check web/*.js web/pwa/*.js` passes
- [ ] Relevant `pytest` suites (including preservation contract tests) pass locally
- [ ] No plaintext secrets, live keys, or real tenant/customer data added
- [ ] Changes adhere to the Truth Rule (`NOT_CONFIGURED` / `NOT_IMPLEMENTED` where external services are absent)
