# SMS Campaign Orchestrator - Release Notes

## v1.0.0-prod-taskdef-v12 (October 31, 2025)

### Deployment Details
- **Task Definition**: v12
- **CodeDeploy ID**: d-VXNO3U8WF
- **ECR Image**: SHA from CodeBuild (see pipeline logs)
- **Infrastructure**: Terraform applied to prod environment

### Features
- On-demand SMS campaign generation via Step Functions
- Blue/green deployments with CodeDeploy
- Async portal fetching with retries and backoff
- CLI with CSV/JSON output and S3 upload
- CloudWatch monitoring and alarms

### Contracts Frozen
- CSV Schema: Unchanged from legacy tool
- JSON Output: Array of objects matching CSV columns
- Checksums: To be computed post-first production run

### Known Issues
- CLI services partially implemented; full enrichment/filtering pending
- SharePoint upload lambda not deployed (canary skips upload)

### Operations
See OPS_QUICK_START.md for runbook snippets.