# Data Model: SMS Campaign Orchestrator

## Entities

### Job
- **id**: string (portal job ID)
- **status**: string (must be "webshop (selling)")
- **activities**: list[Activity]

### Activity
- **id**: string
- **subject_id**: string
- **type**: string (buyer/non-buyer)
- **timestamp**: datetime

### Subject
- **id**: string
- **name**: string
- **email**: string (optional)
- **phone**: string (primary contact)
- **consent_timestamp**: datetime
- **purchase_history**: list[dict] (for buyers)
- **registered_user_ref**: string (optional)

### Contact
- **subject_id**: string
- **phone**: string
- **priority**: int (1=user, 2=deliveries)
- **access_key**: string (generated)

### Campaign Dataset
- **contacts**: list[Contact]
- **metadata**: dict (job_ids, filters_applied, dedup_count)
- **generated_at**: datetime

## Relationships

- Job 1:N Activity
- Activity 1:1 Subject
- Subject 1:N Contact (multiple phones)
- Campaign Dataset contains filtered/deduped Contacts

## Validation Rules

- Job status must be "webshop (selling)"
- Subject must have valid phone
- Consent timestamp must be present and recent
- Deduplication by activity+subject
- Prioritization: user contacts over delivery contacts

## State Transitions

- Subject: prospect → buyer (on purchase)
- Activity: created → processed → included/excluded</content>
<parameter name="filePath">/home/allenroque/netlife-env/sms_quick/specs/001-sms-campaign-orchestrator/data-model.md