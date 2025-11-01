#!/usr/bin/env python3
"""
CLI for live SMS campaign data using NetlifeAPIClient (not CSV fallback)
Connects directly to Netlife portal APIs for real-time data retrieval
"""

import json
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
import click
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from campaign_core.netlife_client import NetlifeAPIClient
from campaign_core.contracts import OutputContract, Contact
from campaign_core.config import ALLOWED_PORTALS, NETLIFE_SECRET_ARN
from campaign_core.adapters.secrets import load_basic_auth

# Unbuffer stdout for immediate output
sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)

# Configure Python logging to ensure output goes to CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)

# Configure structlog
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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Immediate debug output to verify container is running
print("=" * 80)
print("CLI STARTED - Container is running successfully")
print("=" * 80)


# ----------------------- Helper Functions -----------------------

def generate_consent_timestamp(activity: Dict[str, Any]) -> str:
    """Extract SMS marketing timestamp from activity entry date (when job entered in-webshop)"""
    if not activity:
        from datetime import datetime
        return datetime.now().isoformat()
    
    # Try to get 'starting' field which is when the activity entered in-webshop status
    starting_date = activity.get('starting', '')
    if starting_date:
        # Return full ISO timestamp if available, or just date
        return starting_date
    
    # Fallback to current time if no starting date
    from datetime import datetime
    return datetime.now().isoformat()


def clean_phone_number(phone: str) -> str:
    """Format phone number consistently"""
    if not phone:
        return ""
    import re
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return ""
    if len(digits) == 10:
        return f"+1 ({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return f"+1 {digits[-10:]}"


def get_user_details_cached(cache: Dict, client: NetlifeAPIClient, user_uuid: str) -> Dict[str, Any]:
    """Get user details with caching"""
    if not user_uuid:
        return {}
    if user_uuid in cache:
        return cache[user_uuid]
    try:
        details = client.get_user_details(user_uuid) or {}
        cache[user_uuid] = details
        return details
    except Exception as e:
        logger.warning("error_fetching_user_details", user_uuid=user_uuid, error=str(e))
        return {}


def get_or_create_access_key_cached(cache: Dict, client: NetlifeAPIClient, 
                                     job_uuid: str, subject_uuid: str, 
                                     display_name: str, has_images: bool) -> str:
    """Get or create access key with caching"""
    key = (job_uuid, subject_uuid)
    if key in cache:
        return cache[key]
    try:
        code = client.get_or_create_access_key(job_uuid, subject_uuid, display_name, has_images)
        if code:
            cache[key] = code
        return code or ''
    except Exception as e:
        logger.warning("error_creating_access_key", subject_uuid=subject_uuid, error=str(e))
        return ''


@click.group()
def cli():
    """SMS Campaign Orchestrator CLI - LIVE DATA (NetlifeAPIClient)"""


@cli.command()
@click.option("--portals", type=str, required=True,
              help="Comma-separated portal keys, e.g. 'nowandforeverphoto,legacyphoto'.")
# Audience flags (mutually exclusive)
@click.option("--buyers", is_flag=True, default=False, help="Generate for buyers only.")
@click.option("--non-buyers", is_flag=True, default=False, help="Generate for non-buyers only.")
@click.option("--both", is_flag=True, default=False, help="Generate for both buyers and non-buyers (default).")
# Contact filter
@click.option("--contact-filter", type=click.Choice(["phone-only","email-only","any"]),
              default="any", show_default=True)
# Registered users
@click.option("--check-registered-users", is_flag=True, default=False,
              help="Lookup and include registered user information")
@click.option("--registered-only", is_flag=True, default=False,
              help="Include only subjects with registered users")
# Output
@click.option("--out", type=str, default=None, help="Optional s3://... or file path for CSV.")
# Performance
@click.option("--concurrency", type=int, default=5, show_default=True,
              help="Max concurrent jobs per portal")
@click.option("--timeout", type=int, default=30, show_default=True,
              help="API request timeout in seconds")
def build(portals, buyers, non_buyers, both, contact_filter,
          check_registered_users, registered_only, out, concurrency, timeout):
    """Generate SMS campaign datasets from LIVE portal APIs"""
    
    try:
        # Load credentials from AWS Secrets Manager
        logger.info("loading_credentials_from_aws_secrets_manager")
        username, password, timeout_s, rate_limit = load_basic_auth(NETLIFE_SECRET_ARN)
        logger.info("credentials_loaded_successfully", username=username)
    except Exception as e:
        logger.error("failed_to_load_credentials", error=str(e))
        click.echo(f"ERROR: Could not load credentials from AWS Secrets Manager: {e}", err=True)
        sys.exit(1)

    # Parse audience filter
    audience = "both"
    flags = [buyers, non_buyers, both]
    if sum(1 for f in flags if f) > 1:
        click.echo("ERROR: Use only one of --buyers, --non-buyers, --both.", err=True)
        sys.exit(10)
    if buyers: audience = "buyers"
    elif non_buyers: audience = "non-buyers"

    # Parse portals
    portal_list = [p.strip() for p in portals.split(",") if p.strip()]
    if not portal_list:
        click.echo("ERROR: --portals must include at least one portal key.", err=True)
        sys.exit(10)

    # Validate portals
    for portal_key in portal_list:
        if portal_key not in ALLOWED_PORTALS:
            click.echo(f"ERROR: portal '{portal_key}' not allowed.", err=True)
            sys.exit(10)

    # Collect all results
    all_records: List[Contact] = []
    
    # Initialize caches for access keys and user details (shared across portals)
    access_key_cache: Dict[tuple, str] = {}
    user_details_cache: Dict[str, Dict[str, Any]] = {}

    # Process each portal
    for portal_key in portal_list:
        base_url = ALLOWED_PORTALS[portal_key]
        logger.info("processing_portal", portal=portal_key, base_url=base_url)
        
        try:
            # Initialize API client
            client = NetlifeAPIClient(
                portal_name=portal_key,
                base_url=base_url,
                username=username,
                password=password
            )

            # Test connection
            if not client.test_connection():
                logger.error("connection_test_failed", portal=portal_key)
                click.echo(f"ERROR: Could not connect to portal {portal_key}", err=True)
                continue

            logger.info("connection_test_passed", portal=portal_key)

            # Get activities in webshop status
            activities = client.get_activities_in_webshop()
            if not activities:
                logger.warning("no_activities_found", portal=portal_key)
                continue

            logger.info("activities_fetched", portal=portal_key, count=len(activities))

            # Group activities by job UUID
            jobs_map: Dict[str, List[Dict]] = {}
            for activity in activities:
                job_data = activity.get('job', {})
                job_uuid = job_data.get('uuid')
                if job_uuid:
                    if job_uuid not in jobs_map:
                        jobs_map[job_uuid] = []
                    jobs_map[job_uuid].append(activity)

            logger.info("jobs_extracted", portal=portal_key, job_count=len(jobs_map))

            # Process each job
            for job_uuid, job_activities in jobs_map.items():
                logger.info("processing_job", portal=portal_key, job_uuid=job_uuid,
                           activity_count=len(job_activities))
                
                try:
                    # Get job details
                    job_details = client.get_job_details(job_uuid)
                    job_name = job_details.get('name', f'Job {job_uuid}')

                    # Get subjects (with buyer/non-buyer split)
                    buyers_list, non_buyers_list = client.get_buyers_and_non_buyers(job_uuid)

                    # Select subjects based on audience filter
                    if audience == "buyers":
                        subjects_to_process = buyers_list
                    elif audience == "non-buyers":
                        subjects_to_process = non_buyers_list
                    else:  # both
                        subjects_to_process = buyers_list + non_buyers_list

                    logger.info("subjects_fetched", portal=portal_key, job_uuid=job_uuid,
                               buyers=len(buyers_list), non_buyers=len(non_buyers_list),
                               to_process=len(subjects_to_process))

                    # Get registered users map if needed (bulk, efficient!)
                    registered_users_map = {}
                    if check_registered_users or registered_only:
                        registered_users_map = client.get_job_registered_users_map(job_uuid)
                        logger.info("registered_users_fetched", portal=portal_key, job_uuid=job_uuid,
                                   count=len(registered_users_map))

                    # Build subject-to-activity mapping
                    subject_activity_map = client.build_subject_activity_mapping(
                        job_details, subjects_to_process
                    )

                    # Process each subject
                    for subject in subjects_to_process:
                        subject_uuid = subject.get('uuid')
                        if not subject_uuid:
                            continue

                        # Filter by registered user if requested
                        if registered_only and subject_uuid not in registered_users_map:
                            continue

                        # Get contact info - FIXED: Extract from nested delivery objects, not flat fields
                        phone = ''
                        email = ''
                        phone_2 = ''
                        email_2 = ''
                        
                        # Try primary delivery (delivery_1) first
                        delivery_1 = subject.get('delivery_1', {})
                        if isinstance(delivery_1, dict):
                            email = email or (delivery_1.get('email_address') or '').strip()
                            phone = phone or (delivery_1.get('mobile_phone') or '').strip()
                        
                        # Try secondary delivery (delivery_2)
                        delivery_2 = subject.get('delivery_2', {})
                        if isinstance(delivery_2, dict):
                            # For secondary, get from delivery_2 if delivery_1 didn't have it
                            email = email or (delivery_2.get('email_address') or '').strip()
                            phone = phone or (delivery_2.get('mobile_phone') or '').strip()
                            # Also store secondary variants if different
                            d1_email = (delivery_1.get('email_address') or '').strip()
                            d1_phone = (delivery_1.get('mobile_phone') or '').strip()
                            d2_email = (delivery_2.get('email_address') or '').strip()
                            d2_phone = (delivery_2.get('mobile_phone') or '').strip()
                            if d1_email and d2_email and d1_email != d2_email:
                                email_2 = d2_email
                            if d1_phone and d2_phone and d1_phone != d2_phone:
                                phone_2 = d2_phone
                        
                        # Fallback to direct subject fields
                        phone = phone or (subject.get('phone_number') or '').strip()
                        email = email or (subject.get('email') or '').strip()
                        
                        is_buyer = subject_uuid in buyers_list

                        # Apply contact filter
                        if contact_filter == "phone-only" and not phone:
                            continue
                        elif contact_filter == "email-only" and not email:
                            continue
                        elif contact_filter == "any" and not (phone or email):
                            continue

                        # Get registered user info
                        reg_user_info = registered_users_map.get(subject_uuid, {})
                        registered_user_uuid = reg_user_info.get('userUuid')
                        registered_user_email = reg_user_info.get('email')
                        has_registered_user = bool(registered_user_uuid)

                        # Get activities for this subject
                        activity_uuids = subject_activity_map.get(subject_uuid, set())
                        
                        # Use subject's activities, or fallback to first job activity
                        if not activity_uuids and job_activities:
                            activity_uuids = {job_activities[0].get('uuid')}
                        
                        for activity_uuid in activity_uuids:
                            # Find activity details
                            activity = next((a for a in job_activities 
                                           if a.get('uuid') == activity_uuid), 
                                          job_activities[0] if job_activities else {})
                            activity_name = activity.get('name', '')
                            
                            # Get SMS marketing timestamp from activity entry time
                            sms_marketing_timestamp = generate_consent_timestamp(activity)

                            # Get or create access key (try for all subjects, not just those with images)
                            has_images = bool(subject.get('images') or subject.get('group_images'))
                            access_key = ''
                            try:
                                access_key = get_or_create_access_key_cached(
                                    access_key_cache, client,
                                    job_uuid, subject_uuid, subject.get('name', ''), has_images
                                ) or ''
                            except Exception as e:
                                logger.warning("error_getting_access_key", 
                                             subject_uuid=subject_uuid, error=str(e))

                            # Skip this contact if no access key available
                            if not access_key:
                                logger.debug("skipping_contact_no_access_key", subject_uuid=subject_uuid)
                                continue

                            # Build gallery URLs
                            # url: https://portal.shop/gallery/subject_uuid
                            # custom_gallery_url: url with access code parameter
                            # Extract portal root: remove /api/v1 or /api endpoints
                            portal_root = base_url.rstrip('/')
                            if '/api/v1' in portal_root:
                                portal_root = portal_root.split('/api/v1')[0]
                            elif '/api' in portal_root:
                                portal_root = portal_root.split('/api')[0]
                            
                            gallery_url = f"{portal_root}/gallery/{subject_uuid}"
                            custom_gallery_url = f"{portal_root}/?code={access_key}" if access_key else portal_root

                            # Get registered user phone if available
                            registered_user_phone = ''
                            if has_registered_user and check_registered_users:
                                # Try to get phone from registered user details
                                if registered_user_uuid:
                                    user_details = get_user_details_cached(
                                        user_details_cache, client, registered_user_uuid
                                    )
                                    if user_details:
                                        reg_phone = user_details.get('phone_number', '')
                                        if reg_phone:
                                            registered_user_phone = clean_phone_number(reg_phone)

                            # Create contact record
                            contact = Contact(
                                portal=portal_key,
                                job_uuid=job_uuid,
                                job_name=job_name,
                                subject_uuid=subject_uuid,
                                external_id=subject.get('external_id', ''),
                                first_name=subject.get('first_name', ''),
                                last_name=subject.get('last_name', ''),
                                parent_name=subject.get('parent_name', ''),
                                phone_number=phone,
                                phone_number_2=phone_2 or subject.get('phone_number_2', ''),
                                email=email,
                                email_2=email_2 or subject.get('email_2', ''),
                                country=subject.get('country', ''),
                                group=subject.get('group', ''),
                                buyer="Yes" if is_buyer else "No",
                                access_code=access_key,
                                url=gallery_url,
                                custom_gallery_url=custom_gallery_url,
                                sms_marketing_consent="SUBSCRIBE",  # Fixed: Always SUBSCRIBE when in webshop
                                sms_marketing_timestamp=sms_marketing_timestamp,  # From activity entry time
                                sms_transactional_consent="SUBSCRIBE",  # Fixed: Always SUBSCRIBE when in webshop
                                sms_transactional_timestamp=sms_marketing_timestamp,  # Fixed: SAME as marketing timestamp
                                activity_uuid=activity_uuid,
                                activity_name=activity_name,
                                registered_user="Yes" if has_registered_user else "No",
                                registered_user_email=registered_user_email or '',
                                registered_user_uuid=registered_user_uuid or '',
                                registered_user_phone=registered_user_phone,
                                resolution_strategy='netlife-api-live'
                            )
                            
                            all_records.append(contact)
                            
                            # Update stats
                            client.add_subject_stats(
                                has_phone=bool(phone),
                                has_email=bool(email),
                                has_images=has_images
                            )

                    client.increment_job_processed()

                except Exception as e:
                    logger.error("job_processing_failed", portal=portal_key, job_uuid=job_uuid,
                               error=str(e))
                    continue

            # Log final stats for portal
            client.log_final_stats()

        except Exception as e:
            logger.error("portal_processing_failed", portal=portal_key, error=str(e))
            continue

    # Output results
    if all_records:
        csv_content = OutputContract.format_csv(all_records)

        if out:
            # Save to file or S3
            if out.startswith('s3://'):
                logger.info("saving_to_s3", s3_path=out)
                # TODO: Implement S3 upload
                import boto3
                s3 = boto3.client('s3')
                # Parse s3://bucket/key
                parts = out.split('/', 3)
                bucket = parts[2]
                key = parts[3] if len(parts) > 3 else 'output.csv'
                s3.put_object(Bucket=bucket, Key=key, Body=csv_content.encode())
                click.echo(f"Campaign data saved to {out}")
            else:
                # Save to local file
                logger.info("saving_to_local_file", path=out)
                Path(out).write_text(csv_content, encoding='utf-8')
                click.echo(f"Campaign data saved to {out}")
        else:
            # Print to stdout
            click.echo(csv_content)

        logger.info("campaign_generation_complete", total_records=len(all_records))
    else:
        click.echo("WARNING: No records generated", err=True)
        logger.warning("no_records_generated")


if __name__ == '__main__':
    cli()
