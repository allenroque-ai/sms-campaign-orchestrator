"""Services for SMS Campaign Orchestrator"""

from datetime import datetime
import asyncio

import structlog

from .models import Activity, CampaignDataset, Contact, Job, Subject
from .utils import generate_access_key
from .campaign_core.adapters.portals_async import PortalsAsync

logger = structlog.get_logger()


class PortalClient:
    """Client for Netlife portal APIs"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def get_jobs(self, status: str = "webshop (selling)") -> list[Job]:
        """Fetch jobs with given status"""
        # TODO: Implement actual API call
        logger.info("fetching_jobs", status=status)
        return []

    def get_activities_for_job(self, job_id: str) -> list[Activity]:
        """Get activities for a job"""
        # TODO: Implement
        return []

    def get_subject(self, subject_id: str) -> Subject:
        """Get subject details"""
        # TODO: Implement
        return Subject(
            id=subject_id,
            name="Test Subject",
            phone="+1234567890",
            consent_timestamp=datetime.now()
        )


class EnrichmentService:
    """Service for enriching subjects with additional data"""

    def enrich_subjects(self, subjects: list[Subject]) -> list[Subject]:
        """Add purchase history, registered user refs, etc."""
        # TODO: Implement actual enrichment from portal
        for subject in subjects:
            # Mock enrichment
            subject.purchase_history = [{"id": "p1", "amount": 100.0, "date": datetime.now()}] if subject.id.endswith("buyer") else []
            subject.registered_user_ref = f"user_{subject.id}" if subject.id.startswith("reg") else None
        return subjects


class FilteringService:
    """Service for filtering and deduplicating contacts"""

    def filter_buyers(self, activities: list[Activity], subjects: dict[str, Subject]) -> list[Activity]:
        """Filter activities for buyers (subjects with completed purchases)"""
        buyer_activities = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject and subject.purchase_history:
                buyer_activities.append(activity)
        return buyer_activities

    def filter_non_buyers(self, activities: list[Activity], subjects: dict[str, Subject]) -> list[Activity]:
        """Filter activities for non-buyers (subjects with no completed purchases)"""
        non_buyer_activities = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject and not subject.purchase_history:
                non_buyer_activities.append(activity)
        return non_buyer_activities

    def deduplicate(self, activities: list[Activity]) -> list[Activity]:
        """Deduplicate by activity+subject"""
        seen = set()
        deduped = []
        for activity in activities:
            key = f"{activity.id}_{activity.subject_id}"
            if key not in seen:
                seen.add(key)
                deduped.append(activity)
        return deduped


class CampaignService:
    """Main service for generating campaign datasets"""

    def __init__(self, portal_client: PortalClient, enrichment_service: EnrichmentService, filtering_service: FilteringService, portals_async: PortalsAsync | None = None):
        self.portal_client = portal_client
        self.enrichment_service = enrichment_service
        self.filtering_service = filtering_service
        self.portals_async = portals_async

    def determine_priority(self, subject: Subject) -> int:
        """Determine contact priority: 1=highest (registered user), 2=deliveries, 3=anonymous"""
        if subject.registered_user_ref:
            return 1
        # TODO: Check if deliveries contact
        return 2  # Assume deliveries for now

    def generate_campaign(self, job_ids: list[str], campaign_type: str) -> CampaignDataset:
        """Generate campaign dataset"""
        if self.portals_async:
            return asyncio.run(self._generate_campaign_async(job_ids, campaign_type))
        else:
            return self._generate_campaign_sync(job_ids, campaign_type)

    def _generate_campaign_sync(self, job_ids: list[str], campaign_type: str) -> CampaignDataset:
        """Synchronous campaign generation"""
        all_activities = []
        subjects = {}
        for job_id in job_ids:
            activities = self.portal_client.get_activities_for_job(job_id)
            all_activities.extend(activities)
            # Collect unique subjects
            for activity in activities:
                if activity.subject_id not in subjects:
                    subjects[activity.subject_id] = self.portal_client.get_subject(activity.subject_id)

        # Enrich subjects
        enriched_subjects = self.enrichment_service.enrich_subjects(list(subjects.values()))
        subjects = {s.id: s for s in enriched_subjects}

        # Filter activities
        if campaign_type == "buyers":
            activities = self.filtering_service.filter_buyers(all_activities, subjects)
        elif campaign_type == "non-buyers":
            activities = self.filtering_service.filter_non_buyers(all_activities, subjects)
        else:
            activities = all_activities

        activities = self.filtering_service.deduplicate(activities)

        # Convert to contacts
        contacts = []
        for activity in activities:
            subject = subjects[activity.subject_id]
            contact = Contact(
                subject_id=subject.id,
                phone=subject.phone,
                priority=self.determine_priority(subject),
                access_key=generate_access_key(subject.id, subject.phone),
                consent_timestamp=subject.consent_timestamp,
                is_buyer=len(subject.purchase_history) > 0
            )
            contacts.append(contact)

        return CampaignDataset(
            contacts=sorted(contacts, key=lambda c: c.priority),
            metadata={
                "job_ids": job_ids,
                "campaign_type": campaign_type,
                "total_contacts": len(contacts)
            },
            generated_at=datetime.now()
        )

    async def _generate_campaign_async(self, job_ids: list[str], campaign_type: str) -> CampaignDataset:
        """Asynchronous campaign generation with parallel fetching"""
        logger.info("starting_async_campaign", job_ids=job_ids, campaign_type=campaign_type)
        
        # For now, assume all jobs are from the first portal (simplified)
        # TODO: Map job_ids to portals
        portal_key = list(self.portals_async._base.keys())[0] if self.portals_async._base else "legacyphoto"
        
        # Concurrently fetch activities for all jobs
        activities_tasks = [self.portals_async.get_activities_for_job(portal_key, job_id) for job_id in job_ids]
        activities_results = await asyncio.gather(*activities_tasks, return_exceptions=True)
        
        all_activities = []
        subjects_set = set()
        for result in activities_results:
            if isinstance(result, Exception):
                logger.error("failed_to_fetch_activities", error=str(result))
                continue
            for activity_data in result:
                activity = Activity(**activity_data)
                all_activities.append(activity)
                subjects_set.add(activity.subject_id)
        
        # Concurrently fetch subjects
        subject_tasks = [self.portals_async.get_subject(portal_key, subject_id) for subject_id in subjects_set]
        subject_results = await asyncio.gather(*subject_tasks, return_exceptions=True)
        
        subjects = {}
        for result in subject_results:
            if isinstance(result, Exception):
                logger.error("failed_to_fetch_subject", error=str(result))
                continue
            subject_data = result
            subject = Subject(**subject_data)
            subjects[subject.id] = subject
        
        # Enrich subjects (synchronous for now)
        enriched_subjects = self.enrichment_service.enrich_subjects(list(subjects.values()))
        subjects = {s.id: s for s in enriched_subjects}
        
        # Filter activities (synchronous)
        if campaign_type == "buyers":
            activities = self.filtering_service.filter_buyers(all_activities, subjects)
        elif campaign_type == "non-buyers":
            activities = self.filtering_service.filter_non_buyers(all_activities, subjects)
        else:
            activities = all_activities
        
        activities = self.filtering_service.deduplicate(activities)
        
        # Convert to contacts
        contacts = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject:
                contact = Contact(
                    subject_id=subject.id,
                    phone=subject.phone,
                    priority=self.determine_priority(subject),
                    access_key=generate_access_key(subject.id, subject.phone),
                    consent_timestamp=subject.consent_timestamp,
                    is_buyer=len(subject.purchase_history) > 0
                )
                contacts.append(contact)
        
        logger.info("async_campaign_complete", contact_count=len(contacts))
        return CampaignDataset(
            contacts=sorted(contacts, key=lambda c: c.priority),
            metadata={
                "job_ids": job_ids,
                "campaign_type": campaign_type,
                "total_contacts": len(contacts)
            },
            generated_at=datetime.now()
        )
