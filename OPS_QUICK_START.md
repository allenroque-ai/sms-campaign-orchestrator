# SMS Campaign Orchestrator - Ops Quick Start

## Overview
On-demand SMS campaign generation with blue/green deployments, monitoring, and CLI tooling.

## On-Demand Execution
Start a campaign run with custom runId for idempotency:

```bash
RUNID="run-$(date +%Y%m%d-%H%M%S)"
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:754102187132:stateMachine:sms-campaign-orchestrator \
  --input "{\"mode\":\"on_demand\",\"job_id\":\"J1\",\"portals\":[\"legacyphoto\"],\"runId\":\"$RUNID\"}"
```

Artifacts:
- S3: `s3://sms-campaign-artifacts-prd/on-demand/$RUNID.csv`
- SharePoint: `OnDemand/$RUNID.csv`

## Rollback (Zero-Downtime)
Flip SSM parameter to previous task def ARN:

```bash
aws ssm put-parameter \
  --region us-east-1 \
  --name "/sms-campaign/task-def-arn" \
  --type String \
  --value "<PREVIOUS_TASK_DEF_ARN>" \
  --overwrite
```

## Local Smoke Testing
Validate CLI locally:

```bash
make smoke-json  # JSON output
make smoke-csv   # CSV output + preview
```

## Monitoring
- **Alarms**: StepFunctions-Failures, CodeDeploy-Failed, Retry-Spikes, HighLatency
- **Logs**: /ecs/sms-campaign-prod with RetryEvents & HighLatency metrics
- **Dashboard**: Import CW_DASHBOARD.json for key metrics

## Deployment
CodePipeline: Source → Build → DeployStaging → IntegrationTest → Approval → DeployProd → PromoteRunTask

## Secrets
- Basic Auth: Rotate every 90 days in Secrets Manager
- S3: SSE-KMS if AWS_KMS_KEY_ID set

## Cost Guardrails
Budget alarm for ECR/ECS/States monthly spend.