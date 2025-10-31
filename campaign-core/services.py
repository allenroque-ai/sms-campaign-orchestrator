"""Services for SMS Campaign Orchestrator"""

from datetime import datetime
import structlog
from typing import List, Dict, Any
from .models import Job, Activity, Subject, Contact, CampaignDataset

logger = structlog.get_logger()


class PortalClient:
    """Client for Netlife portal APIs"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def get_jobs(self, status: str = "webshop (selling)") -> List[Job]:
        """Fetch jobs with given status"""
        # TODO: Implement actual API call
        logger.info("fetching_jobs", status=status)
        return []

    def get_activities_for_job(self, job_id: str) -> List[Activity]:
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

    def enrich_subjects(self, subjects: List[Subject]) -> List[Subject]:
        """Add purchase history, registered user refs, etc."""
        # TODO: Implement actual enrichment from portal
        for subject in subjects:
            # Mock enrichment
            subject.purchase_history = [{"id": "p1", "amount": 100.0, "date": datetime.now()}] if subject.id.endswith("buyer") else []
            subject.registered_user_ref = f"user_{subject.id}" if subject.id.startswith("reg") else None
        return subjects


class FilteringService:
    """Service for filtering and deduplicating contacts"""

    def filter_buyers(self, activities: List[Activity], subjects: Dict[str, Subject]) -> List[Activity]:
        """Filter activities for buyers (subjects with completed purchases)"""
        buyer_activities = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject and subject.purchase_history:
                buyer_activities.append(activity)
        return buyer_activities

    def filter_non_buyers(self, activities: List[Activity], subjects: Dict[str, Subject]) -> List[Activity]:
        """Filter activities for non-buyers (subjects with no completed purchases)"""
        non_buyer_activities = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject and not subject.purchase_history:
                non_buyer_activities.append(activity)
        return non_buyer_activities

    def deduplicate(self, activities: List[Activity]) -> List[Activity]:
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

    def __init__(self, portal_client: PortalClient, enrichment_service: EnrichmentService, filtering_service: FilteringService):
        self.portal_client = portal_client
        self.enrichment_service = enrichment_service
        self.filtering_service = filtering_service

    def determine_priority(self, subject: Subject) -> int:
        """Determine contact priority: 1=highest (registered user), 2=deliveries, 3=anonymous"""
        if subject.registered_user_ref:
            return 1
        # TODO: Check if deliveries contact
        return 2  # Assume deliveries for now

    def generate_campaign(self, job_ids: List[str], campaign_type: str) -> CampaignDataset:
        """Generate campaign dataset"""
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
                access_key=self.generate_access_key(subject.id, subject.phone),
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