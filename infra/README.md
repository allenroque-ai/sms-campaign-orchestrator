# SMS Campaign Infrastructure

## Overview

This directory contains Terraform modules for deploying the SMS Campaign Orchestrator with CodeDeploy blue/green deployments.

## Modules

### ecs_service
- ALB-backed ECS service for health checks only
- Blue/green target groups
- CloudWatch logging

### iam
- ECS task execution and task roles
- Permissions for Secrets Manager, S3, and CloudWatch

### ssm_parameter
- Stores task definition ARN for Step Functions RunTask
- Updated by promotion Lambda after prod deployment

### lambda_promote
- Updates SSM parameter with new task def ARN
- Triggered after prod deployment approval

### codepipeline (to be created)
- Source → Build → DeployStaging → IntegrationTest → Approval → DeployProd → PromoteRunTask

### codebuild (to be created)
- Build project: Docker build/push, emit image.json
- Integration test project: Step Functions canary run

## Environment Variables

Set these before deployment:

```bash
export NETLIFE_SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789012:secret:sms-campaign/netlife-dev-abc123"
export PORTALS="legacyphoto,nowandforeverphoto"
```

## Deployment

1. Initialize Terraform:
```bash
cd infra/envs/staging
terraform init
```

2. Plan and apply:
```bash
terraform plan -var-file=staging.tfvars
terraform apply -var-file=staging.tfvars
```

## Pre-deploy Checklist

- [ ] ECR repo exists with push permissions
- [ ] SSM parameter `/sms-campaign/task-def-arn` set to safe default
- [ ] Secrets Manager has Basic Auth JSON
- [ ] S3 artifact bucket with SSE-KMS
- [ ] CodeStar connection for GitHub
- [ ] Step Functions state machine ARN

## Pipeline Flow

1. **Source**: GitHub main branch
2. **Build**: CodeBuild creates ECR image, emits image.json
3. **DeployStaging**: CodeDeploy blue/green on ECS
4. **IntegrationTest**: CodeBuild runs Step Functions canary
5. **Approval**: Manual approval required
6. **DeployProd**: CodeDeploy blue/green on ECS
7. **PromoteRunTask**: Lambda updates SSM parameter

## Rollback

To rollback:
1. Update SSM `/sms-campaign/task-def-arn` to previous ARN
2. Optionally redeploy previous service via CodeDeploy