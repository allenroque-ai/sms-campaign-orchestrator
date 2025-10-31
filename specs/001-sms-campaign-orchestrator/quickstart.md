# Quickstart: SMS Campaign Orchestrator

## Test Scenarios

### Scenario 1: Basic Buyer Campaign
**Input**: 2 jobs with 5 buyer activities each
**Command**: `campaign-cli build --buyers --jobs test_jobs.json`
**Expected Output**: CSV with 10 contacts, all buyers, deduplicated
**Success Criteria**: Output matches schema, no duplicates, <500ms

### Scenario 2: Non-Buyer Campaign with Filters
**Input**: Mixed buyer/non-buyer data
**Command**: `campaign-cli build --non-buyers --job-id 12345`
**Expected Output**: JSON with only non-buyer contacts
**Success Criteria**: Correct filtering, JSON schema validation

### Scenario 3: Large Dataset Performance
**Input**: 100 jobs, 1000 subjects
**Command**: `campaign-cli build --both --concurrency 4`
**Expected Output**: Complete dataset within SLA
**Success Criteria**: Performance metrics logged, no failures

### Scenario 4: Error Handling
**Input**: Invalid job data
**Command**: `campaign-cli build --buyers`
**Expected Output**: Error exit code, structured error log
**Success Criteria**: Graceful failure, no data leakage

### Scenario 5: Dry Run
**Input**: Sample data
**Command**: `campaign-cli build --dry-run --json`
**Expected Output**: Validation report, no actual processing
**Success Criteria**: Input validation, no side effects</content>
<parameter name="filePath">/home/allenroque/netlife-env/sms_quick/specs/001-sms-campaign-orchestrator/quickstart.md