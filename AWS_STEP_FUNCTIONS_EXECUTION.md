#!/usr/bin/env bash
# AWS STEP FUNCTIONS - EXECUTION GUIDE
# Run: nowandforeverphoto.shop, non-buyers, phone-only, registered users check

## STEP 1: Build and Push Docker Image

### 1a. Build the image locally
```bash
cd /home/allenroque/netlife-env/sms_quick
docker build -t netlife-sms-campaign:live .
```

### 1b. Get ECR login
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 754102187132.dkr.ecr.us-east-1.amazonaws.com
```

### 1c. Tag the image for ECR
```bash
docker tag netlife-sms-campaign:live \
  754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live
```

### 1d. Push to ECR
```bash
docker push 754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live
```

Verify in console:
```bash
aws ecr describe-images --repository-name netlife-sms-campaign --region us-east-1 | grep live
```

---

## STEP 2: Update/Create ECS Task Definition

### 2a. Register new task definition
```bash
aws ecs register-task-definition \
  --family sms-campaign-live \
  --network-mode awsvpc \
  --requires-compatibilities FARGATE \
  --cpu 256 \
  --memory 512 \
  --container-definitions '[
    {
      "name": "sms-campaign",
      "image": "754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live",
      "essential": true,
      "environment": [
        {
          "name": "NETLIFE_SECRET_ARN",
          "value": "arn:aws:secretsmanager:us-east-1:754102187132:secret:nws/netlife-api-dev-tsm19Z"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/sms-campaign-live",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]' \
  --execution-role-arn arn:aws:iam::754102187132:role/ecsTaskExecutionRole
```

Or use the JSON file:
```bash
aws ecs register-task-definition --cli-input-json file://taskdef_live.json
```

Verify:
```bash
aws ecs list-task-definitions --family-prefix sms-campaign-live
```

---

## STEP 3: Update Step Functions State Machine

The state machine has been updated in `state_machine.asl.json` to:
- Call `cli_live` instead of `cli`
- Use new task definition `sms-campaign-live`
- Pass all required parameters

Check the updated file:
```bash
cat state_machine.asl.json | grep -A 5 "cli_live\|command"
```

---

## STEP 4: Run Test Execution in AWS Step Functions

### 4a. Go to AWS Console

URL: https://console.aws.amazon.com/states/home?region=us-east-1

### 4b. Find your state machine

Look for: `sms-campaign-orchestrator` or similar name

### 4c. Click "Start execution"

### 4d. Enter input JSON:

```json
{
  "portals": "nowandforeverphoto",
  "audience": "non-buyers",
  "contact_filter": "phone-only",
  "check_registered_users": true,
  "output_path": "s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv"
}
```

### 4e. Click "Start execution"

### 4f. Monitor execution

- Watch "Execution name" and "Status"
- Click "Execution input" to see parameters
- Check "Execution history" for step-by-step progress
- View "Execution output" when complete

---

## STEP 5: Monitor CloudWatch Logs

### 5a. View logs in real-time

```bash
# Find log stream
aws logs describe-log-streams \
  --log-group-name /ecs/sms-campaign-live \
  --region us-east-1 \
  --query 'logStreams[0].logStreamName' \
  --output text

# Tail logs
aws logs tail /ecs/sms-campaign-live --follow --region us-east-1
```

### 5b. What to look for in logs

✅ Success indicators:
```
[nowandforeverphoto] Connection test successful
[nowandforeverphoto] Found X activities
[nowandforeverphoto] Jobs extracted: Y
[nowandforeverphoto] Registered users fetched: Z
Campaign data saved to s3://sms-campaign-output/...
```

❌ Error indicators:
```
Connection test failed
No activities found
Request failed
HTTP error
```

---

## STEP 6: Verify Results in S3

### 6a. List files in output bucket

```bash
aws s3 ls s3://sms-campaign-output/ --recursive
```

### 6b. Download output file

```bash
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv - | head -5
```

### 6c. Validate file

```bash
# Check file size
aws s3 ls s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv

# Count lines
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv - | wc -l

# Check headers
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv - | head -1 | tr ',' '\n' | nl

# View sample data
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv - | head -3
```

---

## EXPECTED RESULTS

### File Size
✅ > 1 KB (real data, not empty)
❌ < 1 KB (no data or test data only)

### Data Content
✅ Real phone numbers (e.g., +1 (555) 123-4567)
✅ Real names (e.g., John Doe, Jane Smith)
✅ Real emails (e.g., john@company.com)
❌ Test data (Subject 1, +1 (000) 000-0001, test1@example.com)

### Columns Present
✅ portal: nowandforeverphoto
✅ buyer: No (for all rows - non-buyers filter)
✅ phone_number: populated (phone-only filter)
✅ registered_user: Yes/No (checked)
✅ registered_user_email: populated if registered

### Sample Row
```csv
portal,job_uuid,job_name,subject_uuid,first_name,last_name,phone_number,email,buyer,registered_user,registered_user_email,resolution_strategy
nowandforeverphoto,job-abc123,Job Title,subject-xyz789,John,Doe,+1 (555) 123-4567,john@example.com,No,Yes,john@example.com,netlife-api-live
```

---

## TROUBLESHOOTING

### If file is empty or no data:

1. **Check CloudWatch logs for errors**
   ```bash
   aws logs tail /ecs/sms-campaign-live --follow
   ```

2. **Verify portal credentials**
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id arn:aws:secretsmanager:us-east-1:754102187132:secret:nws/netlife-api-dev-tsm19Z
   ```

3. **Check if activities exist in portal**
   - Activities must have status "in-webshop"
   - Must have non-buyers available
   - Must have phone numbers

4. **Verify Step Functions is using new task definition**
   - Check state machine definition
   - Confirm it references `sms-campaign-live:1` or higher revision

### If connection fails:

1. **Check network connectivity**
   - ECS task must be in VPC with internet access
   - Security group must allow outbound HTTPS (port 443)

2. **Check SSL certificate issues**
   - NetlifeAPIClient has `verify=False`
   - Should handle self-signed certificates
   - Contact AWS team if still failing

3. **Verify portal is accessible**
   - Try portal URL in browser
   - Check portal API status
   - Confirm portal is in ALLOWED_PORTALS

### If registered users not found:

1. **This is normal!** 
   - Not all subjects have registered users
   - registered_user column will show "No" for unregistered

2. **To see only registered users**
   - Use `--registered-only` flag in CLI
   - Will filter to only subjects with registration

---

## QUICK COMMANDS SUMMARY

```bash
# 1. Build and push
docker build -t netlife-sms-campaign:live .
docker tag netlife-sms-campaign:live 754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live
docker push 754102187132.dkr.ecr.us-east-1.amazonaws.com/netlife-sms-campaign:live

# 2. Register task
aws ecs register-task-definition --cli-input-json file://taskdef_live.json

# 3. Monitor logs
aws logs tail /ecs/sms-campaign-live --follow

# 4. Check output
aws s3 ls s3://sms-campaign-output/
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv - | head -5

# 5. View data
aws s3 cp s3://sms-campaign-output/nowandforeverphoto-non-buyers-phone-live.csv data.csv
cat data.csv | column -t -s','
```

---

## FILES READY FOR DEPLOYMENT

✅ /campaign_core/netlife_client.py - API client (665 lines)
✅ /campaign_cli/cli_live.py - New CLI (300+ lines)
✅ /campaign_core/config.py - Configuration (70 lines)
✅ /state_machine.asl.json - Updated Step Functions definition
✅ /taskdef_live.json - ECS task definition (to be created from above)

---

## TIMELINE

- **Build & Push:** 5-10 minutes
- **Register Task:** 2 minutes
- **Update Step Functions:** Already done
- **Run Execution:** 2-5 minutes (depends on data volume)
- **Verify Results:** 5 minutes

**Total: 15-25 minutes to live data**

---

## SUCCESS CRITERIA

✅ Step Functions execution completes successfully
✅ CSV file appears in S3 output bucket
✅ File size > 1 KB
✅ File contains real data (not test data)
✅ All rows have: portal, phone, email, buyer status, registered user status
✅ Buyer column = "No" for all rows (non-buyers filter working)
✅ CloudWatch logs show successful completion

**When all criteria met: LIVE DATA RETRIEVAL SUCCESSFUL! 🎉**

---

## NEXT STEPS AFTER SUCCESS

1. **Schedule Regular Runs**
   - Use CloudWatch Events to trigger Step Functions
   - Set schedule (hourly/daily/weekly)
   - Monitor for failures

2. **Monitor Data Quality**
   - Track record counts over time
   - Alert if counts drop significantly
   - Validate phone numbers are real

3. **Scale to Other Portals**
   - Test with other portals (legacyphoto, etc.)
   - Adjust contact filters as needed
   - Add to regular pipeline

4. **Use Data for SMS Campaigns**
   - Export CSV to SMS provider
   - Send campaigns to non-buyers
   - Track response rates

---

**Ready to deploy? Start with Step 1 above!**
