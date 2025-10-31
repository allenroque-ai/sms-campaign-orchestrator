# SMS Campaign Operations FAQ

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | None |
| 10 | Contract error | Check CSV/JSON schema compliance |
| 20 | Upstream error | Check portal API status, retry later |
| 30 | I/O error | Check S3 permissions, disk space |

## Common Errors

### "ImportError: No module named 'campaign_core'"
- **Cause**: Package not installed in editable mode
- **Fix**: `pip install -e campaign_core campaign_cli campaign_contracts`

### "httpx.ConnectError: Connection refused"
- **Cause**: Portal API down or network issue
- **Fix**: Check portal status, retry with `--retries 5`

### "boto3.exceptions.NoCredentialsError"
- **Cause**: AWS credentials not configured
- **Fix**: `aws configure` or use IAM roles

### "botocore.exceptions.ClientError: AccessDenied"
- **Cause**: Missing S3 or Secrets Manager permissions
- **Fix**: Check IAM role policies for `s3:PutObject`, `secretsmanager:GetSecretValue`

### "json.decoder.JSONDecodeError"
- **Cause**: Malformed JSON from portal API
- **Fix**: Check portal API response format, retry

## Re-running Failed Days

### Via Step Functions (Production)
```bash
aws stepfunctions start-execution \
  --state-machine-arn "$PROD_SM_ARN" \
  --input '{"mode":"production","date":"2025-10-31"}'
```

### Via CLI (Testing)
```bash
campaign-cli build --job-id J1,J2 --both \
  --concurrency 8 --retries 3 \
  --out s3://bucket/retry/2025-10-31.csv
```

### Via ECS RunTask (Emergency)
```bash
aws ecs run-task \
  --cluster sms-campaign-prod \
  --task-definition $(aws ssm get-parameter --name /sms-campaign/task-def-arn --query Parameter.Value --output text) \
  --overrides '{
    "containerOverrides": [{
      "name": "campaign",
      "command": ["campaign-cli","build","--job-id","J1","--out","s3://bucket/retry/2025-10-31.csv"]
    }]
  }'
```

## CSV Diffing During Shadow Runs

### Quick Diff (Line Count)
```bash
wc -l legacy.csv new.csv
# Should match exactly
```

### Full Diff (Content)
```bash
# Sort both files (stable sort by all columns)
sort legacy.csv > legacy_sorted.csv
sort new.csv > new_sorted.csv

# Diff the sorted files
diff legacy_sorted.csv new_sorted.csv
```

### Schema Validation
```bash
# Check headers match
head -1 legacy.csv
head -1 new.csv

# Check row counts
wc -l legacy.csv
wc -l new.csv
```

### Sample Diff Script
```bash
#!/bin/bash
LEGACY=$1
NEW=$2

echo "=== Header Check ==="
diff <(head -1 "$LEGACY") <(head -1 "$NEW")

echo "=== Row Count Check ==="
wc -l "$LEGACY" "$NEW"

echo "=== Content Diff (first 10 lines) ==="
diff <(sort "$LEGACY" | head -10) <(sort "$NEW" | head -10)
```

## Performance Tuning

### Rate Limit Issues
- **Symptom**: High 429 errors in logs
- **Fix**: Reduce `--concurrency` or increase backoff
- **Monitor**: `event="retry"` log count

### Slow Runs
- **Symptom**: `latency_ms_total` > 5000
- **Fix**: Increase `--concurrency` if CPU-bound
- **Monitor**: CloudWatch metrics

### Memory Issues
- **Symptom**: ECS task OOM killed
- **Fix**: Increase task memory or reduce batch size

## Log Analysis

### Success Indicators
```json
{"event": "summary", "rows_out": 1500, "latency_ms_total": 2500, "retries": 2}
{"event": "campaign_complete", "contact_count": 1500}
```

### Warning Signs
```json
{"event": "retry", "attempt": 3, "error": "429 Too Many Requests"}
{"level": "ERROR", "error": "Connection timeout"}
```

### PII Safety
- Phone numbers: Never logged
- Subject IDs: Hashed as `hash:8`
- Message text: Never logged
- Consent timestamps: Logged as-is (not PII)

## Health Checks

### ECS Service Health
```bash
aws ecs describe-services --cluster sms-campaign-prod --services sms-campaign-prod
# Check runningCount == desiredCount
```

### ALB Health
```bash
aws elbv2 describe-target-health --target-group-arn $TG_ARN
# Should show "healthy" for all targets
```

### Step Functions Health
```bash
aws stepfunctions list-executions --state-machine-arn $SM_ARN --status-filter SUCCEEDED --max-results 5
# Recent executions should succeed
```

## Emergency Contacts

- **Portal API Issues**: Check Netlife status page
- **AWS Issues**: AWS Service Health Dashboard
- **Code Issues**: Check GitHub repository for recent commits
- **Data Issues**: Compare with legacy tool output

## Rollback Procedures

### Fast Rollback (SSM Only)
```bash
# Get previous ARN from CloudWatch logs or deployment history
aws ssm put-parameter \
  --name /sms-campaign/task-def-arn \
  --value "arn:aws:ecs:us-east-1:123456789012:task-definition/sms-campaign-prod:42" \
  --type String \
  --overwrite
```

### Full Rollback (CodeDeploy)
```bash
# Redeploy previous service
aws deploy create-deployment \
  --application-name sms-campaign \
  --deployment-group-name prod \
  --revision '{"revisionType": "S3", "s3Location": {"bucket": "artifacts", "key": "previous/image.json"}}'
```

## Monitoring Dashboard

### Key Metrics
- Step Functions execution success rate
- Average campaign latency
- Retry rate per portal
- S3 artifact size vs expected

### Alerts
- Execution failure > 0 in 5 minutes
- Latency > 10 seconds
- Retry rate > 10%
- S3 upload failures

## Version Tracking

### Current Versions
- CLI: Check `campaign-cli --version`
- Core: Check package version in ECS logs
- Contracts: Check test output in CI

### Deployment History
```bash
aws deploy list-deployments --application-name sms-campaign --deployment-group-name prod --max-items 10
aws stepfunctions list-executions --state-machine-arn $SM_ARN --max-results 10
```