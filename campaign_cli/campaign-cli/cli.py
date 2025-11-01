"""CLI commands for SMS Campaign Orchestrator"""

import click
import sys
import json
from pathlib import Path
from campaign_core.services import PortalClient, EnrichmentService, FilteringService, CampaignService
from campaign_core.contracts import OutputContract
from campaign_core.utils import mask_pii
import structlog

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
        lambda record, handler: mask_pii(json.dumps(record, default=str)),
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
    pass


@cli.command()
@click.option('--jobs', type=click.Path(exists=True), help='JSON file with jobs data')
@click.option('--jobs-url', help='URL to fetch jobs from')
@click.option('--job-id', multiple=True, help='Specific job IDs')
@click.option('--buyers', is_flag=True, help='Generate buyer campaign')
@click.option('--non-buyers', is_flag=True, help='Generate non-buyer campaign')
@click.option('--both', is_flag=True, help='Generate both types')
@click.option('--json', is_flag=True, help='Output as JSON instead of CSV')
@click.option('--out', help='Output file path')
@click.option('--concurrency', default=1, help='Parallel processing concurrency')
@click.option('--dry-run', is_flag=True, help='Validate inputs without processing')
def build(jobs, jobs_url, job_id, buyers, non_buyers, both, json, out, concurrency, dry_run):
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
            job_ids.extend([j['id'] for j in jobs_data])

    if not job_ids:
        logger.error("no_jobs_specified")
        click.echo("Error: No jobs specified", err=True)
        sys.exit(1)

    if dry_run:
        logger.info("dry_run_complete", job_ids=job_ids, campaign_type=campaign_type)
        click.echo("Dry run successful")
        return

    # Initialize services
    portal_client = PortalClient(base_url="https://api.example.com", api_key="dummy")
    enrichment_service = EnrichmentService()
    filtering_service = FilteringService()
    campaign_service = CampaignService(portal_client, enrichment_service, filtering_service)

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


if __name__ == '__main__':
    cli()