# Production Deployment Guide - SMS Campaign Orchestrator

## 🎯 Production Cutover Plan (Happy Path)

### 1. Apply Production Infrastructure

```bash
cd infra/envs/prod
terraform apply -var='lambda_zip_path=../../dist/lambda_promote.zip' \
                -var='tags={Project="sms-campaign",Env="prod",Owner="ops"}'
```

### 2. Trigger Pipeline Deployment

**Automated (push to main):**
- Push code changes to trigger CodePipeline

**Manual trigger:**
- Start pipeline manually via AWS Console

**Pipeline Stages:**
1. **Source** → GitHub webhook trigger
2. **Build** → Docker build + ECR push (:git-$SHA)
3. **DeployProd** → CodeDeploy blue/green via ALB health checks
4. **PromoteRunTask** → Lambda updates `/sms-campaign/task-def-arn`

### 3. Production Canary Testing

**Start one Step Functions execution with tiny job:**
```bash
# Verify S3 artifact creation and clean logs
aws stepfunctions start-execution --state-machine-arn <PROD_SFN_ARN> \
  --input '{"jobId": "CANARY_JOB", "concurrency": 1, "retries": 1}'
```

### 4. Operator Smoke Tests

**JSON output test:**
```bash
campaign-cli build --job-id J1 --concurrency 8 --retries 3 --json | head
```

**CSV to S3 test:**
```bash
campaign-cli build --job-id J1 --concurrency 8 --retries 3 \
  --out s3://sms-campaign-artifacts-prd/dryrun/$(date +%F).csv
```

## 🔄 Rollback Procedures (Fast Recovery)

### Option 1: Parameter Flip (Fastest)
```bash
aws ssm put-parameter \
  --name "/sms-campaign/task-def-arn" \
  --type String --value "<PREVIOUS_TASK_DEF_ARN>" \
  --overwrite --region us-east-1
```

### Option 2: Full Service Redeploy
```bash
# Redeploy last-known-good service via CodeDeploy
aws deploy create-deployment \
  --application-name sms-campaign-prod \
  --deployment-group-name sms-campaign-prod-dg \
  --revision '{"revisionType": "AppSpecContent", "appSpecContent": {"content": "{\"version\": 1, \"Resources\": [{\"TargetService\": {\"Type\": \"AWS::ECS::Service\", \"Properties\": {\"TaskDefinition\": \"<PREVIOUS_TASK_DEF_ARN>\", \"LoadBalancerInfo\": {\"ContainerName\": \"campaign\", \"ContainerPort\": 8080}}}}]}"}}' \
  --region us-east-1
```

## 🛡️ Guardrails to Enable Before Production Traffic

### Monitoring & Alarms

**Critical Alarms to Configure:**
- Step Functions `ExecutionFailed > 0`
- CodeDeploy deployment failures
- ECS service health (running count < desired)

**Log Metric Filters:**
- `event="retry"` surge patterns
- `event="summary"` p95 latency above target
- PII masking validation

### Security & Cost Optimizations

**Network Security:**
- Prefer `AssignPublicIp=DISABLED` when feasible (VPC endpoints added ✅)
- Validate VPC endpoint coverage for all AWS service calls

**Image Management:**
- Use immutable tags: `:git-$SHA` only
- Avoid `:latest` in production task definitions
- Implement ECR lifecycle policies for old images

**Secrets Management:**
- Rotate Basic Auth secrets on 90-day schedule
- Validate rotation testing in staging
- Use AWS Secrets Manager with automatic rotation

## 📋 Post-Launch Checklist (First 24 Hours)

### Performance Validation
- [ ] Verify canary & first full run latencies
- [ ] Tune `--concurrency` if 429 rate limits spike
- [ ] Monitor Step Functions execution times

### Data Quality
- [ ] Confirm CSV determinism (shadow vs previous day's run)
- [ ] Validate S3 artifact structure and permissions
- [ ] Check data completeness for sample jobs

### Observability
- [ ] Review CloudWatch logs for PII masking compliance
- [ ] Analyze retry patterns and failure modes
- [ ] Validate structured logging format

### Operational Readiness
- [ ] Test rollback procedures in staging
- [ ] Document runbook for common failure scenarios
- [ ] Establish on-call rotation and escalation paths

## 🚨 Emergency Contacts

**Primary On-Call:** [Team/SRE Contact]
**Secondary:** [DevOps Lead]
**Escalation:** [Engineering Manager]

**Runbook Location:** [Link to operational runbook]
**Monitoring Dashboard:** [Link to CloudWatch/Grafana dashboard]

---

## 📊 Success Metrics

**Deployment Success Criteria:**
- ✅ All pipeline stages complete without manual intervention
- ✅ Production canary executes successfully
- ✅ Smoke tests pass with expected output format
- ✅ No PII leakage in logs
- ✅ Latency within target SLAs
- ✅ Cost within budgeted limits

**Post-Launch Validation:**
- 24h: Zero critical alarms
- 72h: Successful full production run
- 1 week: Performance baseline established