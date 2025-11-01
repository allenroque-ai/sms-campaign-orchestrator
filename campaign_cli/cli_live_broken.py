#!/usr/bin/env python3
"""
sms_buyer_campaign_enchancment.py

Enhanced runner for SMS Buyer vs Non-Buyer Campaign Script.

Key features:
- Starts from activities in WEB SHOP (selling) status
- Requires PHOTOS by default (subjects must have images)
- Bulk registered-users endpoint once per job (optional via flags)
- Optional --registered-only filter (keeps only subjects with a registered user)
- Conditional user detail calls (only if phone is required & missing)
- Registered user columns in CSV: registered_user, registered_user_email, registered_user_uuid
- Strict-selling shortcut flag
- Safe concurrency: one client per worker
- Queue-based logging
"""

import argparse
import csv
import logging
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# Suppress urllib3 SSL warnings
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Project modules expected in the same env
from config import (
    LOGGING_CONFIG,
    OUTPUT_CONFIG,
    PERFORMANCE_CONFIG,
    PORTAL_GROUPS,
    PORTALS,
    TESTING_CONFIG,
    get_log_filename,
    get_output_filename,
    validate_config,
)
from netlife_client import NetlifeAPIClient

# ----------------------- Dataclass -----------------------


@dataclass
class SubjectRecord:
    portal: str
    job_uuid: str
    job_name: str
    subject_uuid: str
    external_id: str
    first_name: str
    last_name: str
    parent_name: str
    phone_number: str
    phone_number_2: str
    email: str
    email_2: str
    country: str
    group: str
    buyer: str
    access_code: str
    url: str
    custom_gallery_url: str
    sms_marketing_consent: str
    sms_marketing_timestamp: str
    sms_transactional_consent: str
    sms_transactional_timestamp: str
    activity_uuid: str
    activity_name: str
    # NEW registered user summary columns
    registered_user: str  # "Yes" or "No"
    registered_user_email: str  # from bulk users (userUsername)
    registered_user_uuid: str  # from bulk users
    registered_user_phone: str  # NEW: from /users/{user_uuid}, informational only
    resolution_strategy: str


# ----------------------- In-memory caches -----------------------

_user_details_cache: Dict[str, Dict[str, str]] = {}
_access_key_cache: Dict[Tuple[str, str], str] = {}

# ----------------------- Utilities -----------------------


def clean_phone_number(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return ""
    if len(digits) == 10:
        return f"+1 ({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return f"+1 {digits[-10:]}"


def extract_contact_info_with_user_priority(
    subject: Dict, user_details: Optional[Dict] = None
) -> Dict[str, str]:
    """
    Extract contact info with proper priority:
    1. user_details (if provided) - highest priority
    2. delivery_1 - primary delivery
    3. delivery_2 - secondary delivery (only if different from delivery_1)
    4. Direct subject fields - fallback
    
    Returns: {"email_1": str, "email_2": str, "mobile_1": str, "mobile_2": str}
    """
    contact = {"email_1": "", "email_2": "", "mobile_1": "", "mobile_2": ""}
    
    # STEP 1: Extract from user_details (highest priority)
    if user_details:
        ue = (user_details.get("email_address") or "").strip()
        up = (user_details.get("phone_number") or "").strip()
        
        if ue and "@" in ue:
            contact["email_1"] = ue
        
        if up:
            c = clean_phone_number(up)
            if c:
                contact["mobile_1"] = c
    
    # STEP 2: Extract from delivery_1 (primary delivery)
    d1 = (
        subject.get("delivery_1", {})
        if isinstance(subject.get("delivery_1"), dict)
        else {}
    )
    
    if d1:
        # Email from delivery_1
        d1_email = (d1.get("email_address") or "").strip()
        if d1_email and "@" in d1_email:
            if not contact["email_1"]:
                contact["email_1"] = d1_email
            elif d1_email != contact["email_1"]:
                contact["email_2"] = d1_email
        
        # Phone from delivery_1
        d1_phone = (d1.get("mobile_phone") or "").strip()
        if d1_phone:
            c = clean_phone_number(d1_phone)
            if c:
                if not contact["mobile_1"]:
                    contact["mobile_1"] = c
                elif c != contact["mobile_1"]:
                    contact["mobile_2"] = c
    
    # STEP 3: Extract from delivery_2 (secondary delivery)
    d2 = (
        subject.get("delivery_2", {})
        if isinstance(subject.get("delivery_2"), dict)
        else {}
    )
    
    if d2:
        # Email from delivery_2
        d2_email = (d2.get("email_address") or "").strip()
        if d2_email and "@" in d2_email:
            if not contact["email_1"]:
                contact["email_1"] = d2_email
            elif not contact["email_2"] and d2_email != contact["email_1"]:
                contact["email_2"] = d2_email
        
        # Phone from delivery_2
        d2_phone = (d2.get("mobile_phone") or "").strip()
        if d2_phone:
            c = clean_phone_number(d2_phone)
            if c:
                if not contact["mobile_1"]:
                    contact["mobile_1"] = c
                elif not contact["mobile_2"] and c != contact["mobile_1"]:
                    contact["mobile_2"] = c
    
    # STEP 4: Fallback to direct subject fields
    if not contact["email_1"]:
        se = (subject.get("email") or "").strip()
        if se and "@" in se:
            contact["email_1"] = se
    
    if not contact["mobile_1"]:
        sp = (subject.get("phone_number") or "").strip()
        if sp:
            c = clean_phone_number(sp)
            if c:
                contact["mobile_1"] = c
    
    return contact


def setup_logging(test_mode: bool = False) -> str:
    """Setup file and console logging"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = f"sms_campaign_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_path = os.path.join(log_dir, log_filename)
    
    log_level = logging.DEBUG if test_mode else logging.INFO
    
    # Create formatters and handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    
    logger = logging.getLogger('sms-campaign')
    logger.setLevel(log_level)
    logger.handlers = [file_handler, stream_handler]
    
    return log_path

logger = logging.getLogger('sms-campaign')


def log_campaign_summary(records: List[Contact], title: str):
    """Log detailed summary statistics for campaign records"""
    if not records:
        logger.info(f"{title}: No records")
        return
    
    buyers = sum(1 for r in records if r.buyer == "Yes")
    non_buyers = sum(1 for r in records if r.buyer == "No")
    with_phone = sum(1 for r in records if r.phone_number or r.phone_number_2)
    with_email = sum(1 for r in records if r.email or r.email_2)
    with_both = sum(
        1 for r in records 
        if (r.phone_number or r.phone_number_2) and (r.email or r.email_2)
    )
    with_phone_2 = sum(1 for r in records if r.phone_number_2)
    with_email_2 = sum(1 for r in records if r.email_2)
    registered_yes = sum(1 for r in records if r.registered_user == "Yes")
    registered_with_email = sum(1 for r in records if r.registered_user_email)
    
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


def deduplicate_records(
    records: List[Contact],
) -> Tuple[List[Contact], int]:
    """Deduplicate records by (activity_uuid, subject_uuid)"""
    seen, out, dups = set(), [], 0
    for r in records:
        key = (r.activity_uuid, r.subject_uuid)
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        out.append(r)
    return out, dups


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
@click.option("--test", is_flag=True, default=False, help="Enable test mode with verbose logging")
def build(portals, buyers, non_buyers, both, contact_filter,
          check_registered_users, registered_only, out, concurrency, timeout, test):
    """Generate SMS campaign datasets from LIVE portal APIs"""
    
    # Setup logging
    log_path = setup_logging(test)
    logger.info("="*80)
    logger.info("SMS CAMPAIGN GENERATION (Live Data - NetlifeAPIClient)")
    logger.info("="*80)
    
    start_time = datetime.now()
    logger.info(f"Start Time: {start_time}")
    
    try:
        # Load credentials from AWS Secrets Manager
        logger.info("\nLoading credentials from AWS Secrets Manager...")
        username, password, timeout_s, rate_limit = load_basic_auth(NETLIFE_SECRET_ARN)
        logger.info(f"Credentials loaded successfully for user: {username}")
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
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

    # Log configuration
    logger.info(f"\nConfiguration:")
    logger.info(f"  Portals: {', '.join(portal_list)}")
    logger.info(f"  Audience Filter: {audience}")
    logger.info(f"  Contact Filter: {contact_filter}")
    logger.info(f"  Check Registered Users: {check_registered_users}")
    logger.info(f"  Registered-Only Filter: {registered_only}")
    logger.info(f"  Output Path: {out or 'stdout'}")
    logger.info(f"  Max Concurrency: {concurrency}")
    
    # Collect all results
    all_records: List[Contact] = []
    portal_results: Dict[str, Dict[str, Any]] = {}

    # Process each portal
    logger.info(f"\n{'='*80}")
    logger.info("PROCESSING PORTALS")
    logger.info(f"{'='*80}\n")
    
    for portal_key in portal_list:
        base_url = ALLOWED_PORTALS[portal_key]
        portal_start = datetime.now()
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING PORTAL: {portal_key}")
        logger.info(f"{'='*60}")
        logger.info(f"Base URL: {base_url}")
        
        portal_records = []
        
        try:
            # Initialize API client
            client = NetlifeAPIClient(
                portal_name=portal_key,
                base_url=base_url,
                username=username,
                password=password
            )

            # Test connection
            logger.info("Testing connection...")
            if not client.test_connection():
                logger.error(f"Connection test FAILED for portal {portal_key}")
                click.echo(f"ERROR: Could not connect to portal {portal_key}", err=True)
                continue

            logger.info(f"✓ Connection test PASSED for {portal_key}")

            # Get activities in webshop status
            logger.info("Fetching activities in webshop status...")
            activities = client.get_activities_in_webshop()
            if not activities:
                logger.warning(f"No activities found in webshop status for {portal_key}")
                portal_results[portal_key] = {"records": 0, "jobs": 0}
                continue

            logger.info(f"✓ Found {len(activities)} activities in webshop status")

            # Group activities by job UUID
            logger.info("Grouping activities by job UUID...")
            jobs_map: Dict[str, List[Dict]] = {}
            for activity in activities:
                job_data = activity.get('job', {})
                job_uuid = job_data.get('uuid')
                if job_uuid:
                    if job_uuid not in jobs_map:
                        jobs_map[job_uuid] = []
                    jobs_map[job_uuid].append(activity)

            logger.info(f"✓ Extracted {len(jobs_map)} unique jobs from {len(activities)} activities")

            # Process each job
            logger.info(f"\nProcessing {len(jobs_map)} jobs...")
            for job_idx, (job_uuid, job_activities) in enumerate(jobs_map.items(), 1):
                logger.info(f"\n  [{job_idx}/{len(jobs_map)}] Job: {job_uuid}")
                logger.info(f"         Activities in job: {len(job_activities)}")
                
                try:
                    # Get job details
                    job_details = client.get_job_details(job_uuid)
                    job_name = job_details.get('name', f'Job {job_uuid}')
                    logger.info(f"         Name: {job_name}")

                    # Get subjects (with buyer/non-buyer split)
                    buyers_list, non_buyers_list = client.get_buyers_and_non_buyers(job_uuid)
                    logger.info(f"         Subjects: {len(buyers_list)} buyers, {len(non_buyers_list)} non-buyers")

                    # Select subjects based on audience filter
                    if audience == "buyers":
                        subjects_to_process = buyers_list
                    elif audience == "non-buyers":
                        subjects_to_process = non_buyers_list
                    else:  # both
                        subjects_to_process = buyers_list + non_buyers_list

                    logger.info(f"         After audience filter: {len(subjects_to_process)} subjects")

                    # Get registered users map if needed (bulk, efficient!)
                    registered_users_map = {}
                    if check_registered_users or registered_only:
                        registered_users_map = client.get_job_registered_users_map(job_uuid)
                        logger.info(f"         Registered users: {len(registered_users_map)} found")

                    # Build subject-to-activity mapping
                    subject_activity_map = client.build_subject_activity_mapping(
                        job_details, subjects_to_process
                    )

                    # Process each subject
                    subjects_passed = 0
                    for subject in subjects_to_process:
                        subject_uuid = subject.get('uuid')
                        if not subject_uuid:
                            continue

                        # Filter by registered user if requested
                        if registered_only and subject_uuid not in registered_users_map:
                            continue

                        # Get contact info - extract from deliveries first
                        phone = ''
                        email = ''
                        
                        # Try primary delivery (delivery_1)
                        delivery_1 = subject.get('delivery_1', {})
                        if isinstance(delivery_1, dict):
                            email = email or (delivery_1.get('email_address') or '').strip()
                            phone = phone or (delivery_1.get('mobile_phone') or '').strip()
                        
                        # Try secondary delivery (delivery_2)
                        delivery_2 = subject.get('delivery_2', {})
                        if isinstance(delivery_2, dict):
                            email = email or (delivery_2.get('email_address') or '').strip()
                            phone = phone or (delivery_2.get('mobile_phone') or '').strip()
                        
                        # Fallback to subject direct fields
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

                        subjects_passed += 1

                        # Get registered user info
                        reg_user_info = registered_users_map.get(subject_uuid, {})
                        registered_user_uuid = reg_user_info.get('userUuid')
                        registered_user_email = reg_user_info.get('email')
                        has_registered_user = bool(registered_user_uuid)

                        # Extract secondary contact info
                        phone_2 = ''
                        email_2 = ''
                        
                        delivery_1 = subject.get('delivery_1', {})
                        delivery_2 = subject.get('delivery_2', {})
                        
                        if isinstance(delivery_1, dict) and isinstance(delivery_2, dict):
                            # Get secondary from delivery_2 if delivery_1 was primary
                            d1_email = (delivery_1.get('email_address') or '').strip()
                            d1_phone = (delivery_1.get('mobile_phone') or '').strip()
                            d2_email = (delivery_2.get('email_address') or '').strip()
                            d2_phone = (delivery_2.get('mobile_phone') or '').strip()
                            
                            if d1_email and d2_email and d1_email != d2_email:
                                email_2 = d2_email
                            if d1_phone and d2_phone and d1_phone != d2_phone:
                                phone_2 = d2_phone

                        # Get activities for this subject
                        activity_uuids = subject_activity_map.get(subject_uuid, set())
                        
                        for activity_uuid in (activity_uuids or {job_activities[0].get('uuid') if job_activities else None}):
                            if not activity_uuid:
                                continue
                            
                            # Find activity details
                            activity = next((a for a in job_activities 
                                           if a.get('uuid') == activity_uuid), 
                                          job_activities[0] if job_activities else {})
                            activity_name = activity.get('name', '')

                            # Get or create access key
                            has_images = bool(subject.get('images') or subject.get('group_images'))
                            access_key = None
                            if has_images:
                                access_key = client.get_or_create_access_key(
                                    job_uuid, subject_uuid, subject.get('name', ''), has_images
                                )

                            # Build gallery URL
                            gallery_url = f"{base_url.split('/api')[0]}/gallery/{subject_uuid}" if base_url else ""

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
                                phone_number_2=phone_2,
                                email=email,
                                email_2=email_2,
                                country=subject.get('country', ''),
                                group=subject.get('group', ''),
                                buyer="Yes" if is_buyer else "No",
                                access_code=access_key or '',
                                url=gallery_url,
                                custom_gallery_url=subject.get('custom_gallery_url', ''),
                                sms_marketing_consent=subject.get('sms_marketing_consent', ''),
                                sms_marketing_timestamp=subject.get('sms_marketing_timestamp', ''),
                                sms_transactional_consent=subject.get('sms_transactional_consent', ''),
                                sms_transactional_timestamp=subject.get('sms_transactional_timestamp', ''),
                                activity_uuid=activity_uuid,
                                activity_name=activity_name,
                                registered_user="Yes" if has_registered_user else "No",
                                registered_user_email=registered_user_email or '',
                                registered_user_uuid=registered_user_uuid or '',
                                resolution_strategy='netlife-api-live'
                            )
                            
                            portal_records.append(contact)
                            all_records.append(contact)
                            
                            # Update stats
                            client.add_subject_stats(
                                has_phone=bool(phone),
                                has_email=bool(email),
                                has_images=has_images
                            )

                    logger.info(f"         ✓ Processed {subjects_passed} subjects, {len(portal_records)} records generated")
                    client.increment_job_processed()

                except Exception as e:
                    logger.error(f"         ✗ Job processing failed: {e}")
                    continue

            # Log final stats for portal
            logger.info(f"\n{portal_key} FINAL STATS:")
            client.log_final_stats()
            
            portal_duration = datetime.now() - portal_start
            logger.info(f"Portal duration: {portal_duration}")
            portal_results[portal_key] = {
                "records": len(portal_records),
                "jobs": len(jobs_map),
                "duration": str(portal_duration)
            }

        except Exception as e:
            logger.error(f"Portal processing FAILED: {e}")
            portal_results[portal_key] = {"records": 0, "jobs": 0, "error": str(e)}
            continue

    # Final filtering and deduplication
    logger.info(f"\n{'='*80}")
    logger.info("FINAL PROCESSING")
    logger.info(f"{'='*80}")
    
    logger.info(f"\nTotal records before deduplication: {len(all_records)}")
    
    # Apply deduplication
    deduped_records, dup_count = deduplicate_records(all_records)
    logger.info(f"Records after deduplication: {len(deduped_records)} (removed {dup_count} duplicates)")
    
    # Log final campaign summary
    log_campaign_summary(deduped_records, "Final Campaign")

    # Output results
    if deduped_records:
        output_contract = OutputContract(contacts=deduped_records)
        csv_content = output_contract.format_csv()

        if out:
            # Save to file or S3
            if out.startswith('s3://'):
                logger.info(f"Saving to S3: {out}")
                import boto3
                s3 = boto3.client('s3')
                # Parse s3://bucket/key
                parts = out.split('/', 3)
                bucket = parts[2]
                key = parts[3] if len(parts) > 3 else 'output.csv'
                s3.put_object(Bucket=bucket, Key=key, Body=csv_content.encode())
                logger.info(f"✓ Campaign data saved to {out}")
                click.echo(f"Campaign data saved to {out}")
            else:
                # Save to local file
                logger.info(f"Saving to local file: {out}")
                Path(out).write_text(csv_content, encoding='utf-8')
                logger.info(f"✓ Campaign data saved to {out}")
                click.echo(f"Campaign data saved to {out}")
        else:
            # Print to stdout
            click.echo(csv_content)

    else:
        click.echo("WARNING: No records generated", err=True)
        logger.warning("No records generated after all processing")

    # Summary statistics
    end_time = datetime.now()
    total_duration = end_time - start_time
    
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


if __name__ == '__main__':
    cli()
