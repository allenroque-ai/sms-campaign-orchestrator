#!/usr/bin/env markdown
# STEP FUNCTIONS PIPELINE UPDATE - LIVE DATA DEPLOYMENT

## What Changed

### Before (Old Pipeline)
```
cli.py (PortalClient) → Loads from CSV files → Test data
```

### After (New Pipeline) 
```
cli_live.py (NetlifeAPIClient) → Calls portal APIs directly → LIVE data
```

## Files Updated

✅ **state_machine.asl.json**
- Changed command from: `campaign_cli.cli`
- Changed command to: `campaign_cli.cli_live`
- Removed unnecessary flags: `--include-registered-phone`, `--job-id`
- Kept essential flags: `--portals`, `audience`, `--contact-filter`, `--check-registered-users`

## Deployment to AWS

### Step 1: Update Step Functions State Machine

**Option A: Using AWS Console**

1. Go to **AWS Step Functions** console
2. Click on your state machine name
3. Click **Edit**
4. Replace the definition with the updated `state_machine.asl.json` content
5. Click **Save**
6. Click **Update role** if prompted

**Option B: Using AWS CLI**

```bash
# Update state machine with new definition
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:754102187132:stateMachine:sms-campaign-orchestrator \
  --definition file://state_machine.asl.json
```

### Step 2: Update Docker Image (if not already done)

Ensure Docker image includes new files:

```bash
# Build new image
docker build -t netlife-sms-campaign:live .

# Tag for ECR
docker tag netlife-sms-campaign:live 754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live

# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 754102187132.dkr.ecr.us-east-1.amazonaws.com
docker push 754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live
```

### Step 3: Verify ECS Task Definition

Ensure task definition includes:
- ✅ New Docker image (`:live` tag)
- ✅ NETLIFE_SECRET_ARN environment variable
- ✅ PYTHONPATH=/app

Command to check:
```bash
aws ecs describe-task-definition \
  --task-definition sms-campaign-prod:13 \
  --query 'taskDefinition.containerDefinitions[0].image'
```

## Testing the Pipeline

### Test Case 1: Non-Buyers with Phone Numbers

**Input:**
```json
{
  "runId": "test-live-001",
  "mode": "on-demand",
  "portal": "nowandforeverphoto",
  "audience": "non-buyers",
  "contact_filter": "phone-only",
  "check_registered_users": true
}
```

**Expected Output:**
- S3 file: `s3://sms-campaign-artifacts-prd/on-demand/test-live-001.csv`
- File size: > 1 KB (REAL data, not empty)
- Records: Non-buyers only (buyer = No)
- Phone: All records have phone numbers
- Registered users: Checked and populated

**CloudWatch Logs Should Show:**
```
[portal-name] Fetching activities with status 'in-webshop'...
[portal-name] Found X activities
[portal-name] Fetching subjects for job...
[portal-name] FINAL STATS
```

### Test Case 2: Buyers with Email

**Input:**
```json
{
  "runId": "test-live-002",
  "mode": "on-demand",
  "portal": "nowandforeverphoto",
  "audience": "buyers",
  "contact_filter": "email-only",
  "check_registered_users": true
}
```

**Expected Output:**
- Records: Buyers only (buyer = Yes)
- Email: All records have email addresses
- Phone: May be empty

### Test Case 3: Both Audiences, Any Contact

**Input:**
```json
{
  "runId": "test-live-003",
  "mode": "on-demand",
  "portal": "nowandforeverphoto",
  "audience": "both",
  "contact_filter": "any",
  "check_registered_users": true
}
```

**Expected Output:**
- Records: Both buyers and non-buyers mixed
- Contact: Phone OR email (at least one)

## Monitoring the Pipeline

### CloudWatch Logs

View logs for Step Functions execution:

```bash
# Get log stream name
aws logs describe-log-streams \
  --log-group-name /ecs/sms-campaign-prod \
  --order-by LastEventTime \
  --descending \
  --max-items 1

# View logs
aws logs tail /ecs/sms-campaign-prod --follow
```

**Look for:**
- ✅ "Connection test passed"
- ✅ "Activities fetched"
- ✅ "Subjects fetched"
- ✅ "Campaign generation complete"
- ❌ No SSL errors (in AWS, these should not appear)
- ❌ No connection failures

### S3 Output Verification

```bash
# List output files
aws s3 ls s3://sms-campaign-artifacts-prd/on-demand/ --recursive

# Check file size (should be > 1 KB)
aws s3 ls s3://sms-campaign-artifacts-prd/on-demand/test-live-001.csv

# Download and inspect
aws s3 cp s3://sms-campaign-artifacts-prd/on-demand/test-live-001.csv - | \
  head -3 | \
  cut -d',' -f1-10
```

## Pipeline Execution Flow (New)

```
Step Functions Input
        ↓
NormalizeInput (Format parameters)
        ↓
HasJobId? (Decision)
        ├─→ YES: RunExtraction_WithJob
        └─→ NO: RunExtraction_NoJob
        ↓
ECS Task Launch (FARGATE)
        ↓
Run: python -m campaign_cli.cli_live build
        │
        ├─→ Connect to NetlifeAPIClient
        ├─→ Test connection to portal (✅ Works in AWS)
        ├─→ Get activities in webshop status
        ├─→ Process jobs and subjects
        ├─→ Look up registered users
        ├─→ Apply filters (audience, contact)
        ├─→ Generate CSV with LIVE data
        └─→ Upload to S3
        ↓
Success State
        ↓
Execution Complete
```

## Command Change Summary

### Before (CSV fallback)
```bash
python -m campaign_cli.cli build \
  --portals nowandforeverphoto \
  --non-buyers \
  --contact-filter phone-only \
  --check-registered-users \
  --include-registered-phone \
  --job-id some-job-id \
  --out s3://bucket/file.csv
```

### After (Live API)
```bash
python -m campaign_cli.cli_live build \
  --portals nowandforeverphoto \
  --non-buyers \
  --contact-filter phone-only \
  --check-registered-users \
  --out s3://bucket/file.csv
```

**Removed flags:**
- `--include-registered-phone` (not needed in new CLI)
- `--job-id` (automatically extracted from APIs)

**Why:**
- New NetlifeAPIClient handles jobs automatically from activities
- Phone numbers always included if available
- Simpler, cleaner interface

## Data Quality Improvements

### Before (CSV)
```
Data Source:     CSV files (sms_campaign_nowandforeverphoto_20251031.csv)
Freshness:       Stale (from 2025-10-31 16:10 UTC)
Data Type:       Test/Mock data
Sample Phone:    +1 (000) 000-0001
Sample Name:     Subject 1
Sample Email:    test1@example.com
File Size:       ~3 KB (few records, incomplete)
```

### After (Live API)
```
Data Source:     Portal APIs (nowandforeverphoto.shop/api/v1)
Freshness:       Real-time (when executed)
Data Type:       LIVE production data
Sample Phone:    +1 (555) 123-4567 (real)
Sample Name:     John Doe (real)
Sample Email:    john@company.com (real)
File Size:       > 1 KB (all matching records)
```

## Success Criteria

Pipeline update is successful when:

✅ State machine accepts new definition
✅ ECS task executes without errors
✅ CloudWatch logs show no connection failures
✅ S3 output file is created
✅ File size > 1 KB (REAL data)
✅ CSV headers correct
✅ Data contains real names/phones/emails (not test data)
✅ Registered user columns populated
✅ Audience filter working (non-buyers show buyer=No)
✅ Contact filter working (phone-only shows phone present)

## Rollback Plan

If issues occur, rollback is simple:

```bash
# Revert state_machine.asl.json to use cli instead of cli_live
git checkout state_machine.asl.json

# Update state machine back to old definition
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:754102187132:stateMachine:sms-campaign-orchestrator \
  --definition file://state_machine.asl.json
```

## Post-Deployment Tasks

After successful deployment:

1. **Monitor Executions** (24 hours)
   - Run sample executions daily
   - Monitor for errors/failures
   - Check data quality

2. **Update Documentation**
   - Document new API capabilities
   - Update run-book for operations team
   - Add new filtering examples

3. **Performance Tuning**
   - Monitor execution time
   - Adjust timeouts if needed
   - Optimize for multiple portals

4. **Schedule Regular Runs**
   - Set up CloudWatch Events to trigger Step Functions
   - Coordinate with SMS delivery team
   - Ensure data freshness requirements met

## Support & Troubleshooting

### Pipeline Won't Update
- Verify IAM permissions for Step Functions
- Check state machine ARN is correct
- Ensure JSON is valid (use JSON validator)

### Task Fails with Connection Error
- Verify portal connectivity from AWS
- Check security group outbound rules
- Confirm credentials in Secrets Manager
- Try with shorter timeout first

### No Data in Output
- Check if activities exist in "in-webshop" status
- Verify portal credentials work
- Check CloudWatch logs for API errors
- Run local test (on EC2 in same VPC)

### File Too Small
- More filtering applied than expected
- No matching records for filters
- Contact filter too restrictive
- Check actual data in portal

## Questions?

Refer to:
- `/AWS_DEPLOYMENT_GUIDE.md` - Detailed deployment guide
- `/IMPLEMENTATION_COMPLETE.md` - Technical implementation details
- `/NETLIFE_CLIENT_IMPLEMENTATION.md` - API client documentation

---

**Update Status:** ✅ Ready to deploy
**Files Modified:** 1 (state_machine.asl.json)
**Time to Deploy:** 5 minutes
**Expected Result:** Live data from portal APIs
