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


def mask_log_record(record, handler):
    """Mask PII in log records"""
    if "message" in record:
        record["message"] = mask_pii(record["message"])
    return record
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
@click.option("--jobs", type=click.Path(exists=True), help="JSON file with jobs data")
@click.option("--jobs-url", help="URL to fetch jobs from")
@click.option("--job-id", multiple=True, help="Specific job IDs")
@click.option("--buyers", is_flag=True, help="Generate buyer campaign")
@click.option("--non-buyers", is_flag=True, help="Generate non-buyer campaign")
@click.option("--both", is_flag=True, help="Generate both types")
@click.option("--json", is_flag=True, help="Output as JSON instead of CSV")
@click.option("--out", help="Output file path")
@click.option("--concurrency", default=8, help="Parallel processing concurrency")
@click.option("--retries", default=3, help="Number of retries for failed requests")
@click.option("--dry-run", is_flag=True, help="Validate inputs without processing")
def build(jobs, jobs_url, job_id, buyers, non_buyers, both, json, out, concurrency, retries, dry_run):
    """Build SMS campaign dataset"""

    logger.info("starting_campaign_build", options=locals())

    # Determine campaign type
    if buyers:
        campaign_type = "buyers"
    elif non_buyers:
        campaign_type = "non-buyers"
    elif both:
        campaign_type = "both"
    else:
        campaign_type = "both"  # default

    # Get job IDs
    job_ids = list(job_id)
    if jobs:
        with open(jobs) as f:
            jobs_data = json.load(f)
            job_ids.extend([j["id"] for j in jobs_data])

    if not job_ids:
        logger.error("no_jobs_specified")
        click.echo("Error: No jobs specified", err=True)
        sys.exit(1)

    if dry_run:
        logger.info("dry_run_complete", job_ids=job_ids, campaign_type=campaign_type)
        click.echo("Dry run successful")
        return

    # Load configuration
    username, password, timeout_s, rate_limit = load_basic_auth(NETLIFE_SECRET_ARN)
    allowed_urls = {k: v for k, v in ALLOWED_PORTALS.items() if k in PORTALS_FILTER}

    logger.info("config_loaded", portals=len(allowed_urls), concurrency=concurrency, retries=retries)

    # Initialize services (TODO: integrate async adapter)
    portal_client = PortalClient(base_url="https://api.example.com", api_key="dummy")  # placeholder
    enrichment_service = EnrichmentService()
    filtering_service = FilteringService()
    
    portals_async = None
    if concurrency > 1:
        portals_async = PortalsAsync(
            base_urls=allowed_urls,
            creds=(username, password),
            concurrency=concurrency,
            timeout_s=timeout_s,
            retries=retries
        )
    
    campaign_service = CampaignService(portal_client, enrichment_service, filtering_service, portals_async)

    try:
        dataset = campaign_service.generate_campaign(job_ids, campaign_type)

        if json:
            output = OutputContract.format_json(dataset.contacts, dataset.metadata)
        else:
            output = OutputContract.format_csv(dataset.contacts)

        if out:
            Path(out).write_text(output)
            logger.info("output_written", path=out)
        else:
            click.echo(output)

        logger.info("campaign_build_complete", contact_count=len(dataset.contacts))

    except Exception as e:
        logger.error("campaign_build_failed", error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
