# Deploy Checklist — {service} v{X.Y.Z}

Tick only what was actually done; write who and when next to each group.

## Pre-deploy ({name}, YYYY-MM-DD HH:MM)

- [ ] All tests in test-result.md pass on the release commit
- [ ] Environment variables in manifest.md §4 set in {environment}
- [ ] Database backup taken: {where}
- [ ] Migrations reviewed; irreversible ones flagged in rollback-plan.md
- [ ] Rollback plan read by the person deploying
- [ ] Stakeholders told the time window

## Deploy

- [ ] Run migrations ({order})
- [ ] Deploy {image:tag}
- [ ] {feature flag / config switch}

## Post-deploy Verification

- [ ] Health / readiness endpoints OK
- [ ] Smoke test: {critical flows}
- [ ] Logs and error rate normal for {minutes}
- [ ] {jobs / consumers} running, lag normal

## Rollback Readiness

- [ ] Previous image `{image:tag}` still available
- [ ] Rollback decision owner on call: {name}

## Sign-off

| Role | Name | Date | Result |
|---|---|---|---|
| Deployer | {name} | YYYY-MM-DD | ✅ / ❌ |
| Reviewer | {name} | YYYY-MM-DD | ✅ / ❌ |
