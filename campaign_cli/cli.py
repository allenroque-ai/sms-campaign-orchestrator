"""CLI commands for SMS Campaign Orchestrator"""

import json
import sys
from pathlib import Path

import click
import structlog
from campaign_core.contracts import OutputContract
from campaign_core.services import (
    CampaignService,
    EnrichmentService,
    FilteringService,
    PortalClient,
)
from campaign_core.utils import mask_pii
from campaign_core.config import ALLOWED_PORTALS, NETLIFE_SECRET_ARN, PORTALS_FILTER
from campaign_core.adapters.secrets import load_basic_auth
from campaign_core.adapters.portals_async import PortalsAsync


def json_load(path):
    import json, sys
    if path == "-":
        return json.load(sys.stdin)
    with open(path, "rb") as fh:
        return json.load(fh)

def json_dumps(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

def mask_log_record(logger, method_name, event_dict):
    """Mask PII in log records"""
    if "message" in event_dict:
        event_dict["message"] = mask_pii(event_dict["message"])
    return event_dict

from campaign_core.utils import mask_pii

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        mask_log_record,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@click.group()
def cli():
    """SMS Campaign Orchestrator CLI"""


@cli.command()
@click.option("--jobs", type=str, required=False,
              help="Path to jobs JSON; use '-' for stdin. If omitted, tool may fetch from portals.")
# Audience flags (mutually exclusive)
@click.option("--buyers", is_flag=True, default=False, help="Generate for buyers only.")
@click.option("--non-buyers", is_flag=True, default=False, help="Generate for non-buyers only.")
@click.option("--both", is_flag=True, default=False, help="Generate for both buyers and non-buyers (default).")
# New: portals flag (csv list)
@click.option("--portals", type=str, required=False,
              help="Comma-separated portal keys, e.g. 'nowandforeverphoto,legacyphoto'.")
# Contact filter
@click.option("--contact-filter", type=click.Choice(["phone-only","email-only","any"]),
              default="any", show_default=True)
# Registered users
@click.option("--check-registered-users", is_flag=True, default=False)
@click.option("--include-registered-phone", is_flag=True, default=False)
@click.option("--registered-only", is_flag=True, default=False,
              help="Include only subjects that have a registered user mapping")
# Output & format
@click.option("--out", type=str, default=None, help="Optional s3://... or file path for CSV.")
# Perf
@click.option("--concurrency", type=int, default=1, show_default=True)
@click.option("--retries", type=int, default=3, show_default=True)
# Fallback mode
@click.option("--fallback", is_flag=True, default=False, 
              help="Use mock data when live API calls fail (useful for SSL issues)")
# Legacy flags for backward compatibility
@click.option("--portal", type=str, required=False,
              help="[DEPRECATED] Single portal key. Use --portals instead.")
@click.option("--buyer-filter", type=click.Choice(["buyers","non-buyers","both"]), required=False,
              help="[DEPRECATED] Audience filter. Use --buyers/--non-buyers/--both instead.")
def build(jobs, buyers, non_buyers, both, portals, contact_filter,
          check_registered_users, include_registered_phone, registered_only,
          out, concurrency, retries, portal, buyer_filter, fallback):
    """Generate SMS campaign datasets."""
    # --- Backward compatibility for legacy flags
    if portal and portals:
        click.echo("ERROR: Cannot use both --portal and --portals. Use --portals only.", err=True)
        sys.exit(10)
    if portal:
        click.echo("WARNING: --portal is deprecated. Use --portals instead.", err=True)
        portals = portal  # Map single portal to portals string
    
    if buyer_filter and any([buyers, non_buyers, both]):
        click.echo("ERROR: Cannot use both --buyer-filter and audience flags (--buyers/--non-buyers/--both). Use audience flags only.", err=True)
        sys.exit(10)
    if buyer_filter:
        click.echo("WARNING: --buyer-filter is deprecated. Use --buyers/--non-buyers/--both instead.", err=True)
        if buyer_filter == "buyers":
            buyers = True
        elif buyer_filter == "non-buyers":
            non_buyers = True
        elif buyer_filter == "both":
            both = True
    
    # Ensure portals is provided (either new or legacy)
    if not portals:
        click.echo("ERROR: --portals must be provided (or --portal for legacy compatibility).", err=True)
        sys.exit(10)

    # --- resolve audience
    audience = "both"
    flags = [buyers, non_buyers, both]
    if sum(1 for f in flags if f) > 1:
        click.echo("ERROR: Use only one of --buyers, --non-buyers, --both.", err=True)
        sys.exit(10)
    if buyers: audience = "buyers"
    elif non_buyers: audience = "non-buyers"

    # --- parse portals CSV
    portal_list = [p.strip() for p in portals.split(",") if p.strip()]
    if not portal_list:
        click.echo("ERROR: --portals must include at least one portal key.", err=True)
        sys.exit(10)

    def _json_load(path):
        if not path or path == "-":
            return json.load(sys.stdin)
        with open(path, "rb") as fh:
            return json.load(fh)
    jobs_data = None
    if jobs:
        try:
            jobs_data = _json_load(jobs)
        except FileNotFoundError:
            click.echo(f"ERROR: jobs file not found: {jobs}", err=True); sys.exit(30)
        except json.JSONDecodeError as e:
            click.echo(f"ERROR: invalid JSON in jobs file: {jobs}: {e}", err=True); sys.exit(10)

    from campaign_core.adapters.secrets import load_basic_auth
    from campaign_core.config import ALLOWED_PORTALS, NETLIFE_SECRET_ARN
    from campaign_core.adapters.portals_async import PortalsAsync
    from campaign_core.services import CampaignService
    from campaign_core.contracts import OutputContract
    import boto3, os

    # validate portals against allow-list
    base_urls = {}
    for k in portal_list:
        if k not in ALLOWED_PORTALS:
            click.echo(f"ERROR: portal '{k}' not allowed.", err=True); sys.exit(10)
        base_urls[k] = ALLOWED_PORTALS[k]

    try:
        username, password, timeout_s, rate_limit = load_basic_auth(NETLIFE_SECRET_ARN)
        logger.info("Successfully loaded credentials from AWS Secrets Manager")
    except Exception as e:
        logger.error("Failed to load auth from secrets", error=str(e))
        click.echo(f"ERROR: Could not load credentials from AWS Secrets Manager: {e}", err=True)
        sys.exit(1)
    
    portals_async = None if concurrency == 1 else PortalsAsync(base_urls=base_urls, creds=(username, password),
                                 concurrency=concurrency, timeout_s=timeout_s)
    
    portal_client = PortalClient(base_url="", api_key="", auth=(username, password), fallback_mode=fallback)
    enrichment_service = EnrichmentService()
    filtering_service = FilteringService()
    svc = CampaignService(portal_client, enrichment_service, filtering_service, portals_async)

    # For now, assume job_ids are provided or fetch from portals
    job_ids = jobs_data["jobs"] if jobs_data else []
    
    # If no jobs provided, fetch activities in webshop status from portals
    if not job_ids:
        for portal in portal_list:
            portal_client.base_url = base_urls[portal]
            portal_client.api_key = ""  # TODO: Set proper API key
            activities = portal_client.get_activities_in_webshop()
            # Extract unique job IDs from activities
            job_ids_from_activities = set()
            for activity in activities:
                # Extract job_id from activity.id (format: activity_jobX_Y)
                if hasattr(activity, 'id') and activity.id.startswith('activity_job'):
                    try:
                        job_num = activity.id.split('_')[1]  # Extract 'job1' from 'activity_job1_1'
                        job_ids_from_activities.add(job_num)  # Add just 'job1', not 'jobjob1'
                    except:
                        pass
                # Fallback: check if activity has job_id field
                elif hasattr(activity, 'job_id'):
                    job_ids_from_activities.add(activity.job_id)
            job_ids.extend(list(job_ids_from_activities))
        
        # If still no jobs and using fallback, generate mock jobs
        if not job_ids and fallback:
            job_ids = ["mock-job-001", "mock-job-002", "mock-job-003"]
    
    # Remove duplicates
    job_ids = list(set(job_ids))
    
    # Generate campaign data using the new logic
    campaign_data = []
    
    for portal in portal_list:
        portal_client.base_url = base_urls[portal]
        portal_client.api_key = ""  # TODO: Set proper API key
        
        for job_id in job_ids:
            # Get job details
            job_details = portal_client.get_job_details(job_id)
            
            # Get buyers and non-buyers for this job
            buyers, non_buyers = portal_client.get_buyers_and_non_buyers_csv(job_id)
            
            # Process based on audience filter
            subjects_to_process = []
            if audience == "buyers":
                subjects_to_process = buyers
            elif audience == "non-buyers":
                subjects_to_process = non_buyers
            else:  # both
                subjects_to_process = buyers + non_buyers
            
            # Get registered users if needed
            registered_users = {}
            if check_registered_users or include_registered_phone or registered_only:
                user_refs = []
                for subject in subjects_to_process:
                    if subject.get('registered_user_ref'):
                        user_refs.append(subject['registered_user_ref'])
                
                if user_refs:
                    registered_users = portal_client.get_registered_users(user_refs)
            
            # Build campaign entries
            for subject in subjects_to_process:
                # Skip if registered_only and no registered user
                if registered_only and not subject.get('registered_user_ref'):
                    continue
                
                # Get contact info
                contact_info = {}
                if subject.get('registered_user_ref') and subject['registered_user_ref'] in registered_users:
                    user_data = registered_users[subject['registered_user_ref']]
                    if include_registered_phone:
                        contact_info['phone'] = user_data.get('phone_number', '')
                    contact_info['email'] = user_data.get('email_address', '')
                    contact_info['name'] = user_data.get('name', '')
                else:
                    contact_info['phone'] = subject.get('phone', '')
                    contact_info['email'] = subject.get('email', '')
                    contact_info['name'] = f"{subject.get('first_name', '')} {subject.get('last_name', '')}".strip()
                
                # Apply contact filter
                has_phone = bool(contact_info.get('phone', '').strip())
                has_email = bool(contact_info.get('email', '').strip())
                
                if contact_filter == "phone-only" and not has_phone:
                    continue
                elif contact_filter == "email-only" and not has_email:
                    continue
                elif contact_filter == "any" and not (has_phone or has_email):
                    continue
                
                # Create campaign entry
                entry = {
                    'job_id': job_id,
                    'job_name': job_details.get('job', {}).get('name', 'Unknown Job'),
                    'portal': portal,
                    'subject_id': subject.get('uuid', ''),
                    'name': contact_info['name'],
                    'phone': contact_info['phone'],
                    'email': contact_info['email'],
                    'type': subject.get('type', 'unknown'),
                    'priority': 1 if subject.get('registered_user_ref') else 2
                }
                campaign_data.append(entry)
    
    # Convert to CampaignDataset format
    from campaign_core.models import CampaignDataset, Contact
    from datetime import datetime
    
    contacts = []
    for entry in campaign_data:
        contact = Contact(
            portal=entry['portal'],
            job_uuid=entry['job_id'],
            job_name=entry['job_name'],
            subject_uuid=entry['subject_id'],
            external_id=None,
            first_name=entry['name'].split()[0] if entry['name'] else None,
            last_name=' '.join(entry['name'].split()[1:]) if entry['name'] and len(entry['name'].split()) > 1 else None,
            parent_name=None,
            phone_number=entry['phone'],
            phone_number_2=None,
            email=entry['email'],
            email_2=None,
            country="USA",
            group=None,
            buyer="Yes" if entry['type'] == 'buyer' else "No",
            access_code=f"access-{entry['subject_id'][-8:]}",
            url=f"https://{entry['portal']}.shop/gallery/{entry['subject_id']}",
            custom_gallery_url="",
            sms_marketing_consent="SUBSCRIBE",
            sms_marketing_timestamp=datetime.now().isoformat(),
            sms_transactional_consent="SUBSCRIBE", 
            sms_transactional_timestamp=datetime.now().isoformat(),
            activity_uuid=f"activity-{entry['subject_id'][-8:]}",
            activity_name=f"Activity for {entry['name']}",
            registered_user="Yes" if entry.get('registered_user_ref') else "No",
            registered_user_email=entry.get('registered_email'),
            registered_user_uuid=entry.get('registered_user_ref'),
            resolution_strategy="netlife-api-integration",
            subject_id=entry['subject_id'],
            phone=entry['phone'],
            priority=entry['priority'],
            access_key=f"access-{entry['subject_id'][-8:]}",
            consent_timestamp=datetime.now(),
            is_buyer=entry['type'] == 'buyer'
        )
        contacts.append(contact)
    
    campaign_dataset = CampaignDataset(
        contacts=contacts,
        metadata={"source": "netlife-api", "portal": portal_list[0], "audience": audience},
        generated_at=datetime.now()
    )

    # --- output CSV
    csv_str = OutputContract.format_csv(campaign_dataset.contacts)
    csv_bytes = csv_str.encode('utf-8')
    if out and out.startswith("s3://"):
        s3 = boto3.client("s3")
        from urllib.parse import urlparse
        u = urlparse(out); bucket, key = u.netloc, u.path.lstrip("/")
        extra = {}
        if (k := os.getenv("AWS_KMS_KEY_ID")):
            extra.update(ServerSideEncryption="aws:kms", SSEKMSKeyId=k)
        s3.put_object(Bucket=bucket, Key=key, Body=csv_bytes, **extra)
        # one-line JSON for Step Functions
        click.echo(json.dumps({"s3_uri": out}))
    elif out:
        # Local file output
        with open(out, 'wb') as f:
            f.write(csv_bytes)
        click.echo(f"Campaign data saved to {out}")
    else:
        sys.stdout.buffer.write(csv_bytes)


if __name__ == "__main__":
    cli()
