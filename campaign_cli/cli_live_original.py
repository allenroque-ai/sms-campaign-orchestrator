#!/usr/bin/env python3
"""
CLI for live SMS campaign data using NetlifeAPIClient (not CSV fallback)
Connects directly to Netlife portal APIs for real-time data retrieval
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
import click
import structlog
from concurrent.futures import ThreadPoolExecutor, as_completed

from campaign_core.netlife_client import NetlifeAPIClient
from campaign_core.contracts import OutputContract, Contact
from campaign_core.config import ALLOWED_PORTALS, NETLIFE_SECRET_ARN
from campaign_core.adapters.secrets import load_basic_auth

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

                        # Get contact info
                        phone = subject.get('phone_number', '')
                        email = subject.get('email', '')
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
                        
                        for activity_uuid in (activity_uuids or {client._get_first_activity_uuid(job_activities)}):
                            # Find activity details
                            activity = next((a for a in job_activities 
                                           if a.get('uuid') == activity_uuid), 
                                          job_activities[0] if job_activities else {})
                            activity_name = activity.get('name', '')

                            # Get or create access key
                            has_images = bool(subject.get('images') or subject.get('group_images'))
                            access_key = client.get_or_create_access_key(
                                job_uuid, subject_uuid, subject.get('name', ''), has_images
                            ) if has_images else None

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
                                phone_number_2=subject.get('phone_number_2', ''),
                                email=email,
                                email_2=subject.get('email_2', ''),
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
        output_contract = OutputContract(contacts=all_records)
        csv_content = output_contract.format_csv()

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
