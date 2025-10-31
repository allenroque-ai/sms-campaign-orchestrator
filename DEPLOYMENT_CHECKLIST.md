# SMS Campaign Deployment Checklist

## Pre-Deploy Setup ✅

### AWS Resources
- [ ] ECR repository: `sms-campaign` (push permissions granted)
- [ ] S3 buckets:
  - [ ] `sms-campaign-artifacts-stg` (SSE-KMS enabled)
  - [ ] `sms-campaign-artifacts-prd` (SSE-KMS enabled)
- [ ] Secrets Manager: `NETLIFE_SECRET_ARN` with Basic Auth JSON
- [ ] CodeStar connection: GitHub repository connection
- [ ] SSM parameter: `/sms-campaign/task-def-arn` (set to safe default)

### Environment Variables
- [ ] `NETLIFE_SECRET_ARN` set in ECS task environment
- [ ] `PORTALS` filter configured (staging: limited set, prod: all)

### Code Quality
- [ ] `pytest -q` passes (contracts + determinism)
- [ ] `ruff check` clean
- [ ] `mypy --strict` clean
- [ ] Dependencies pinned and scanned

## Staging Deployment 🚀

### Pipeline Variables
```hcl
codestar_connection_arn = "arn:aws:codestar-connections:us-east-1:123456789012:connection/12345678-1234-1234-1234-123456789012"
artifact_bucket_staging = "sms-campaign-artifacts-stg"
artifact_bucket_prod    = "sms-campaign-artifacts-prd"
```

### Deployment Steps
1. [ ] Push code to `main` branch
2. [ ] CodePipeline triggers automatically
3. [ ] **Build Stage**: ECR image created, `image.json` emitted
4. [ ] **DeployStaging**: CodeDeploy blue/green on ECS (health checks only)
5. [ ] **IntegrationTest**: Step Functions canary run
6. [ ] Verify CloudWatch logs (JSON, PII-safe)
7. [ ] Verify S3 artifact exists
8. [ ] **Manual Approval**: Review and approve in CodePipeline

## Production Promotion 🎯

### Post-Approval Steps
1. [ ] **DeployProd**: CodeDeploy blue/green on ECS
2. [ ] **PromoteRunTask**: Lambda updates SSM parameter
3. [ ] Manual prod canary: Small job via Step Functions
4. [ ] Verify prod artifact and logs

## Smoke Tests 🧪

### JSON Output Test
```bash
campaign-cli build --job-id J1 --concurrency 8 --retries 3 --json | jq '.[0]'
```

### S3 Output Test
```bash
campaign-cli build --job-id J1 --concurrency 8 --retries 3 \
  --out s3://sms-campaign-artifacts-stg/dryrun/$(date +%F).csv
```

## Observability Setup 📊

### CloudWatch Alarms
- [ ] Step Functions ExecutionFailed > 0
- [ ] CodeDeploy deployment failures
- [ ] ECS unhealthy hosts

### Log Metric Filters
- [ ] `event="retry"` spike detection
- [ ] `event="summary"` latency monitoring
- [ ] Error rate monitoring

## Performance Tuning ⚡

### Initial Settings
- Concurrency: 8
- Retries: 3
- Backoff: Exponential (200ms base, 5s cap)

### Monitoring
- [ ] 429 rate in logs
- [ ] Average latency per campaign
- [ ] Memory/CPU usage in ECS

## Rollback Procedures 🔄

### Fast Rollback (SSM)
```bash
aws ssm put-parameter \
  --name /sms-campaign/task-def-arn \
  --value "$PREVIOUS_ARN" \
  --type String \
  --overwrite
```

### Full Rollback (CodeDeploy)
- Redeploy previous service via CodeDeploy
- Keeps health parity with RunTask

## Governance & Compliance ✅

### Constitution Compliance
- [ ] Library-first architecture
- [ ] CLI-driven interface
- [ ] TDD enforcement
- [ ] Contract tests passing
- [ ] Integration tests included

### Security
- [ ] Secrets via AWS Secrets Manager
- [ ] PII masking in logs
- [ ] Least privilege IAM
- [ ] SBOM generated
- [ ] Dependency scanning

### Operational Readiness
- [ ] Runbooks documented
- [ ] Monitoring alerts configured
- [ ] On-call rotation defined
- [ ] Backup/restore procedures tested

## Go-Live Checklist 🎉

- [ ] Staging deployment successful
- [ ] Prod promotion completed
- [ ] Smoke tests passing
- [ ] Observability active
- [ ] Team trained on operations
- [ ] Rollback procedures verified
- [ ] Emergency contacts documented

---

**Status**: Ready for staging deployment 🚀

**Next**: Push to main branch to trigger CodePipeline