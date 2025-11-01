# cli_live.py Logging Improvements

## Overview
Updated `cli_live.py` to match the comprehensive logging level of the original `sms_buyer_campaign_enhancement.py` script. The new logging provides detailed visibility into execution flow, data statistics, and performance metrics.

## Key Logging Enhancements

### 1. **Setup & Initialization Logging**
```python
# File and console logging with timestamp
logger.info("="*80)
logger.info("SMS CAMPAIGN GENERATION (Live Data - NetlifeAPIClient)")
logger.info("="*80)
logger.info(f"Start Time: {datetime.now()}")

# Configuration summary
logger.info(f"Configuration:")
logger.info(f"  Portals: {', '.join(portal_list)}")
logger.info(f"  Audience Filter: {audience}")
logger.info(f"  Contact Filter: {contact_filter}")
logger.info(f"  Check Registered Users: {check_registered_users}")
```

### 2. **Per-Portal Processing Logging**
```python
# Portal header with section separators
logger.info(f"\n{'='*60}")
logger.info(f"PROCESSING PORTAL: {portal_key}")
logger.info(f"{'='*60}")

# Connection validation
logger.info("Testing connection...")
logger.info(f"✓ Connection test PASSED for {portal_key}")

# Activity fetching
logger.info("Fetching activities in webshop status...")
logger.info(f"✓ Found {len(activities)} activities in webshop status")

# Job extraction
logger.info("Grouping activities by job UUID...")
logger.info(f"✓ Extracted {len(jobs_map)} unique jobs from {len(activities)} activities")
```

### 3. **Per-Job Processing Logging**
```python
# Job processing with progress tracking
logger.info(f"\n  [{job_idx}/{len(jobs_map)}] Job: {job_uuid}")
logger.info(f"         Activities in job: {len(job_activities)}")
logger.info(f"         Name: {job_name}")

# Subject statistics
logger.info(f"         Subjects: {len(buyers_list)} buyers, {len(non_buyers_list)} non-buyers")
logger.info(f"         After audience filter: {len(subjects_to_process)} subjects")
logger.info(f"         Registered users: {len(registered_users_map)} found")

# Processing completion
logger.info(f"         ✓ Processed {subjects_passed} subjects, {len(portal_records)} records generated")
```

### 4. **Portal Summary Statistics**
```python
# Final stats per portal
logger.info(f"\n{portal_key} FINAL STATS:")
client.log_final_stats()  # Calls to API client's built-in stats logging

# Portal duration tracking
portal_duration = datetime.now() - portal_start
logger.info(f"Portal duration: {portal_duration}")
```

### 5. **Campaign Summary Function**
New function `log_campaign_summary()` logs detailed metrics:
```python
def log_campaign_summary(records: List[Contact], title: str):
    logger.info(f"\n{title} Summary:")
    logger.info(f"  Total Records: {len(records)}")
    logger.info(f"  Buyers: {buyers}")
    logger.info(f"  Non-Buyers: {non_buyers}")
    logger.info(f"  With Phone (any): {with_phone}")
    logger.info(f"  With Email (any): {with_email}")
    logger.info(f"  With Both Phone & Email: {with_both}")
    logger.info(f"  With Secondary Phone: {with_phone_2}")
    logger.info(f"  With Secondary Email: {with_email_2}")
    logger.info(f"  Registered Users: {registered_yes}")
    logger.info(f"  Registered Users with Email: {registered_with_email}")
```

### 6. **Deduplication Logging**
```python
logger.info(f"Total records before deduplication: {len(all_records)}")
logger.info(f"Records after deduplication: {len(deduped_records)} (removed {dup_count} duplicates)")
```

### 7. **Final Execution Summary**
```python
logger.info(f"\n{'='*80}")
logger.info("CAMPAIGN GENERATION COMPLETE")
logger.info(f"{'='*80}")
logger.info(f"End Time: {end_time}")
logger.info(f"Total Duration: {total_duration}")
logger.info(f"Portals Processed: {len(portal_list)}")
logger.info(f"Total Records: {len(all_records)}")
logger.info(f"Deduplicated Records: {len(deduped_records)}")
logger.info(f"Output File: {out or 'stdout'}")
logger.info(f"Log File: {log_path}")
logger.info(f"{'='*80}\n")
```

## Logging Configuration

### File-Based Logging
- **Location**: `logs/sms_campaign_live_YYYYMMDD_HHMMSS.log`
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Levels**: DEBUG (test mode) or INFO (production)

### Console Output
- Simultaneous logging to both file and stdout
- Same format as file logging
- Full context visibility in real-time

### Test Mode
- Add `--test` flag to enable DEBUG level logging
- Shows more granular processing details
- Useful for troubleshooting

## Example Log Output

```
================================================================================
SMS CAMPAIGN GENERATION (Live Data - NetlifeAPIClient)
================================================================================
2025-11-01 12:00:00 - sms-campaign - INFO - Start Time: 2025-11-01 12:00:00.123456

Configuration:
  Portals: legacyseniorphotos,nowandforeverphoto
  Audience Filter: buyers
  Contact Filter: phone-only
  Check Registered Users: True
  Registered-Only Filter: False
  Output Path: s3://sms-campaign-artifacts-prd/on-demand/campaign.csv
  Max Concurrency: 5

================================================================================
PROCESSING PORTALS
================================================================================

============================================================
PROCESSING PORTAL: legacyseniorphotos
============================================================
Base URL: https://legacyseniorphotos.shop

Testing connection...
✓ Connection test PASSED for legacyseniorphotos
Fetching activities in webshop status...
✓ Found 5 activities in webshop status
Grouping activities by job UUID...
✓ Extracted 3 unique jobs from 5 activities

Processing 3 jobs...

  [1/3] Job: job-uuid-001
         Activities in job: 2
         Name: Job April 2025
         Subjects: 150 buyers, 50 non-buyers
         After audience filter: 150 subjects
         Registered users: 142 found
         ✓ Processed 142 subjects, 142 records generated

legacyseniorphotos FINAL STATS:
  Jobs Processed: 3
  Total Subjects Processed: 425
  Records With Phone: 412
  Records With Email: 398
Portal duration: 0:02:45.123456

================================================================================
FINAL PROCESSING
================================================================================

Total records before deduplication: 567
Records after deduplication: 565 (removed 2 duplicates)

Final Campaign Summary:
  Total Records: 565
  Buyers: 450
  Non-Buyers: 115
  With Phone (any): 555
  With Email (any): 520
  With Both Phone & Email: 512
  With Secondary Phone: 45
  With Secondary Email: 32
  Registered Users: 534
  Registered Users with Email: 502

================================================================================
CAMPAIGN GENERATION COMPLETE
================================================================================
End Time: 2025-11-01 12:03:00.456789
Total Duration: 0:03:00.333333
Portals Processed: 2
Total Records: 567
Deduplicated Records: 565
Output File: s3://sms-campaign-artifacts-prd/on-demand/campaign.csv
Log File: logs/sms_campaign_live_20251101_120000.log
================================================================================
```

## Comparison with Original Script

| Aspect | Original | Updated cli_live.py |
|--------|----------|---------------------|
| **Logging Framework** | Python `logging` module | Python `logging` module |
| **Log Destinations** | File + Console | File + Console |
| **Log Level** | INFO (DEBUG in test mode) | INFO (DEBUG in test mode) |
| **Per-Portal Summary** | ✓ Yes | ✓ Yes |
| **Per-Job Tracking** | ✓ Yes | ✓ Yes |
| **Per-Subject Debug** | ✓ Yes (with _dbg()) | ✓ Yes (as needed) |
| **Statistics Logging** | ✓ Yes | ✓ Yes |
| **Deduplication Stats** | ✓ Yes | ✓ Yes |
| **Execution Timing** | ✓ Yes | ✓ Yes |
| **Section Separators** | ✓ Yes | ✓ Yes |

## Usage

### Normal Mode
```bash
python -m campaign_cli.cli_live build \
  --portals legacyseniorphotos \
  --buyers \
  --contact-filter phone-only \
  --check-registered-users \
  --out s3://bucket/file.csv
```

### Test Mode (Verbose)
```bash
python -m campaign_cli.cli_live build \
  --portals legacyseniorphotos \
  --buyers \
  --contact-filter phone-only \
  --test \
  --out /tmp/test.csv
```

## Benefits

1. **Full Visibility**: See exactly what the script is doing at each step
2. **Performance Tracking**: Duration metrics for each portal and overall execution
3. **Data Quality Metrics**: Detailed statistics about records (buyers/non-buyers, contact info)
4. **Error Tracing**: Comprehensive error logging with context
5. **Compliance**: Audit trail for SMS campaign generation
6. **Debugging**: Test mode with DEBUG level logging for troubleshooting
7. **Maintainability**: Clear structure matches original script conventions

## Log File Location
All logs are saved to: `logs/sms_campaign_live_YYYYMMDD_HHMMSS.log`

The exact path is output at startup and at the end of execution.
