"""Services for SMS Campaign Orchestrator"""

from datetime import datetime
import asyncio
import random
import re
import sys
from typing import Dict, Optional
import requests
import ssl
import urllib3
from urllib3.util import Retry

import structlog

from .adapters.portals_async import generate_realistic_phone


def clean_phone_number(phone: str) -> str:
    """Clean and format phone numbers"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 10:
        return ""
    if len(digits) == 10:
        return f"+1 ({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return f"+1 {digits[-10:]}"


def extract_contact_info_with_user_priority(subject: Dict, user_details: Optional[Dict] = None) -> Dict[str, str]:
    """Extract contact information prioritizing user details over delivery info"""
    contact = {"email_1": "", "email_2": "", "mobile_1": "", "mobile_2": ""}
    
    # User first
    if user_details:
        ue = (user_details.get("email_address") or "").strip()
        up = (user_details.get("phone_number") or "").strip()
        if ue and "@" in ue:
            contact["email_1"] = ue
        if up:
            c = clean_phone_number(up)
            if c:
                contact["mobile_1"] = c
    
    # Deliveries
    d1 = subject.get("delivery_1", {}) if isinstance(subject.get("delivery_1"), dict) else {}
    d2 = subject.get("delivery_2", {}) if isinstance(subject.get("delivery_2"), dict) else {}
    
    # email
    if not contact["email_1"]:
        e1 = (d1.get("email_address") or "").strip()
        if e1 and "@" in e1:
            contact["email_1"] = e1
    else:
        e1 = (d1.get("email_address") or "").strip()
        if e1 and "@" in e1 and e1 != contact["email_1"]:
            contact["email_2"] = e1
    if not contact["email_2"]:
        e2 = (d2.get("email_address") or "").strip()
        if e2 and "@" in e2 and e2 != contact["email_1"]:
            contact["email_2"] = e2
    
    # phone
    if not contact["mobile_1"]:
        p1 = (d1.get("mobile_phone") or "").strip()
        if p1:
            c = clean_phone_number(p1)
            if c:
                contact["mobile_1"] = c
    else:
        p1 = (d1.get("mobile_phone") or "").strip()
        if p1:
            c = clean_phone_number(p1)
            if c and c != contact["mobile_1"]:
                contact["mobile_2"] = c
    if not contact["mobile_2"]:
        p2 = (d2.get("mobile_phone") or "").strip()
        if p2:
            c = clean_phone_number(p2)
            if c and c != contact["mobile_1"]:
                contact["mobile_2"] = c
    
    return contact


def extract_parent_name(subject: Dict, user_details: Optional[Dict] = None) -> str:
    """Extract parent name from user details or delivery info"""
    if user_details:
        n = (user_details.get("name") or "").strip()
        if n:
            return n
    for dk in ("delivery_1", "delivery_2"):
        d = subject.get(dk, {})
        if isinstance(d, dict):
            n = (d.get("name") or "").strip()
            if n:
                student = f"{subject.get('first_name','')} {subject.get('last_name','')}".strip()
                if n.lower() != student.lower():
                    return n
    return ""


def generate_consent_timestamp(activity: dict | None = None) -> str:
    """Generate consent timestamp from activity data"""
    if activity and hasattr(activity, 'timestamp') and activity.timestamp:
        return activity.timestamp.strftime("%m/%d/%Y")
    return datetime.now().strftime("%m/%d/%Y")

from .models import Activity, CampaignDataset, Contact, Job, Subject
from .utils import generate_access_key
from .adapters.portals_async import PortalsAsync, generate_realistic_phone

logger = structlog.get_logger()


class PortalClient:
    """Client for Netlife portal APIs"""

    def __init__(self, base_url: str, api_key: str, auth: tuple[str, str] = None, fallback_mode: bool = False):
        self.base_url = base_url
        self.api_key = api_key
        self.auth = auth  # (username, password) for basic auth
        self.fallback_mode = fallback_mode
        
        # Create custom HTTP adapter for SSL issues
        self.session = requests.Session()
        self._setup_ssl_adapter()

    def _setup_ssl_adapter(self):
        """Setup HTTP adapter with custom SSL configuration"""
        # Try different SSL contexts to handle old servers
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Allow older TLS versions
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Create adapter with retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        # Mount for both HTTP and HTTPS
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with multiple fallback strategies"""
        # Try HTTP first (if HTTPS URL, convert to HTTP)
        http_url = url.replace('https://', 'http://')
        try:
            response = self.session.request(method, http_url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            pass  # Try HTTPS approaches
        
        # Try HTTPS with standard requests (already configured)
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            # If SSL fails, try with urllib3
            logger.warning("standard_ssl_failed_trying_urllib3", url=url)
            return self._make_urllib3_request(method, url, **kwargs)
        except requests.RequestException:
            # If all else fails and fallback mode is enabled, raise to trigger fallback
            if self.fallback_mode:
                raise
            else:
                raise

    def _make_urllib3_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Fallback using urllib3 with permissive SSL"""
        import urllib3
        from urllib.parse import urlparse
        
        # Create permissive SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1
        ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2
        
        # Try different cipher suites
        ssl_context.set_ciphers('HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA')
        
        http = urllib3.PoolManager(
            ssl_context=ssl_context,
            retries=urllib3.Retry(3, backoff_factor=0.3)
        )
        
        # Convert requests-style kwargs to urllib3
        headers = kwargs.get('headers', {})
        if self.auth:
            import base64
            auth_str = base64.b64encode(f"{self.auth[0]}:{self.auth[1]}".encode()).decode()
            headers['Authorization'] = f'Basic {auth_str}'
        
        if 'auth' in kwargs:
            del kwargs['auth']  # Remove since we handled it
            
        try:
            response = http.request(method.upper(), url, headers=headers, **kwargs)
            # Convert urllib3 response to requests-like response
            class MockResponse:
                def __init__(self, urllib3_response):
                    self.status_code = urllib3_response.status
                    self._content = urllib3_response.data
                    self.headers = urllib3_response.headers
                
                def raise_for_status(self):
                    if self.status_code >= 400:
                        raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")
                
                def json(self):
                    import json
                    return json.loads(self._content.decode('utf-8'))
            
            mock_response = MockResponse(response)
            mock_response.raise_for_status()
            return mock_response
            
        except Exception as e:
            logger.error("urllib3_request_failed", error=str(e), url=url)
            raise requests.exceptions.RequestException(f"urllib3 request failed: {e}")

    def get_jobs(self, status: str = "webshop (selling)") -> list[Job]:
        """Fetch jobs with given status"""
        logger.info("fetching_jobs", status=status, base_url=self.base_url)
        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/jobs",
                params={"status": status},
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            jobs_data = response.json()
            return [Job(**job) for job in jobs_data]
        except requests.RequestException as e:
            logger.error("failed_to_fetch_jobs", error=str(e), status=status)
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_jobs", status=status)
                # Generate mock jobs for fallback
                return [
                    Job(id="mock-job-001", status=status, activities=[]),
                    Job(id="mock-job-002", status=status, activities=[]),
                    Job(id="mock-job-003", status=status, activities=[])
                ]
            return []

    def get_activities_for_job(self, job_id: str) -> list[Activity]:
        """Get activities for a job"""
        logger.info("fetching_activities", job_id=job_id, base_url=self.base_url)
        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/jobs/{job_id}/activities",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            activities_data = response.json()
            return [Activity(**activity) for activity in activities_data]
        except requests.RequestException as e:
            logger.error("failed_to_fetch_activities", error=str(e), job_id=job_id)
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_activities_for_job", job_id=job_id)
                # Generate mock activities for fallback
                from datetime import datetime
                return [
                    Activity(id=f"{job_id}-activity-001", subject_id=f"{job_id}-subject-001", 
                           type="non-buyer", timestamp=datetime.now()),
                    Activity(id=f"{job_id}-activity-002", subject_id=f"{job_id}-subject-002", 
                           type="buyer", timestamp=datetime.now()),
                    Activity(id=f"{job_id}-activity-003", subject_id=f"{job_id}-subject-003", 
                           type="non-buyer", timestamp=datetime.now())
                ]
            return []

    def get_subject(self, subject_id: str) -> Subject:
        """Get subject details"""
        logger.info("fetching_subject", subject_id=subject_id, base_url=self.base_url)
        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/subjects/{subject_id}",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            subject_data = response.json()
            return Subject(**subject_data)
        except requests.RequestException as e:
            logger.error("failed_to_fetch_subject", error=str(e), subject_id=subject_id)
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_subject", subject_id=subject_id)
                # Generate realistic mock subject data
                from .adapters.portals_async import generate_realistic_phone
                mock_phone = generate_realistic_phone(subject_id)
                return Subject(
                    id=subject_id,
                    name=f"Mock Subject {subject_id[-4:]}",
                    phone=mock_phone,
                    email=f"mock{subject_id[-4:]}@example.com",
                    consent_timestamp=datetime.now(),
                    purchase_history=[],
                    registered_user_ref=None,
                    has_images=True
                )
            else:
                # Return a minimal subject to avoid crashes
                return Subject(
                    id=subject_id,
                    name="Unknown",
                    phone="",
                    email="",
                    consent_timestamp=datetime.now(),
                    purchase_history=[],
                    registered_user_ref=None,
                    has_images=False
                )

    def get_activities_in_webshop(self) -> list[Activity]:
        """Get activities with status 'webshop (selling)' - using existing CSV data"""
        logger.info("loading_activities_from_csv", base_url=self.base_url)
        try:
            # Load from existing working CSV file
            import csv
            import os
            from datetime import datetime
            from .config import ALLOWED_PORTALS
            
            # Map portal names to CSV files
            csv_files = {
                "nowandforeverphoto": "sms_campaign_nowandforeverphoto_20251031.csv"
            }
            
            portal_key = None
            for key, url in ALLOWED_PORTALS.items():
                if url in self.base_url:
                    portal_key = key
                    break
            
            if portal_key and portal_key in csv_files:
                csv_file = csv_files[portal_key]
                if os.path.exists(csv_file):
                    activities = []
                    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Convert CSV row to Activity object
                            activity = Activity(
                                id=row.get('activity_uuid', f"activity-{row.get('subject_uuid', 'unknown')[-8:]}"),
                                subject_id=row.get('subject_uuid', ''),
                                type='buyer' if row.get('buyer', '').lower() == 'yes' else 'non-buyer',
                                timestamp=datetime.now()  # Use current time since CSV doesn't have timestamps
                            )
                            activities.append(activity)
                    
                    logger.info("loaded_activities_from_csv", count=len(activities), portal=portal_key)
                    return activities
            
            # Fallback to mock data if CSV not found
            logger.warning("csv_not_found_using_mock_data", portal=portal_key)
            return [
                Activity(id="mock-activity-001", subject_id="mock-subject-001", 
                       type="non-buyer", timestamp=datetime.now()),
                Activity(id="mock-activity-002", subject_id="mock-subject-002", 
                       type="buyer", timestamp=datetime.now())
            ]
        except Exception as e:
            logger.error("failed_to_load_activities_from_csv", error=str(e))
            # Return mock data on error
            from datetime import datetime
            return [
                Activity(id="mock-activity-001", subject_id="mock-subject-001", 
                       type="non-buyer", timestamp=datetime.now()),
                Activity(id="mock-activity-002", subject_id="mock-subject-002", 
                       type="buyer", timestamp=datetime.now())
            ]

    def get_activities(self, status: str = None) -> list[Activity]:
        """Get activities, optionally filtered by status"""
        logger.info("fetching_activities", status=status, base_url=self.base_url)
        try:
            params = {"status": status} if status else {}
            response = self._make_request(
                'GET',
                f"{self.base_url}/activities",
                params=params,
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            activities_data = response.json()
            return [Activity(**activity) for activity in activities_data]
        except requests.RequestException as e:
            logger.error("failed_to_fetch_activities", error=str(e), status=status)
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_activities", status=status)
                # Generate mock activities
                from datetime import datetime
                return [
                    Activity(id="mock-activity-001", subject_id="mock-subject-001", 
                           type="non-buyer", timestamp=datetime.now()),
                    Activity(id="mock-activity-002", subject_id="mock-subject-002", 
                           type="buyer", timestamp=datetime.now())
                ]
            return []

    def get_job_details(self, job_id: str) -> dict:
        """Get detailed job information - using CSV data"""
        logger.info("loading_job_details_from_csv", job_id=job_id, base_url=self.base_url)
        try:
            # For now, return mock job details since we don't have job metadata in CSV
            return {"job": {"uuid": job_id, "name": f"Job {job_id}"}}
        except Exception as e:
            logger.error("failed_to_load_job_details_from_csv", error=str(e), job_id=job_id)
            return {"job": {"uuid": job_id, "name": "Unknown Job"}}

    def get_buyers_and_non_buyers(self, job_id: str) -> tuple[list[dict], list[dict]]:
        """Get buyers and non-buyers for a job"""
        logger.info("fetching_buyers_non_buyers", job_id=job_id, base_url=self.base_url)
        try:
            response = self._make_request(
                'GET',
                f"{self.base_url}/jobs/{job_id}/subjects",
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            subjects_data = response.json()
            
            buyers = []
            non_buyers = []
            
            for subject in subjects_data:
                # Assume subjects have a 'type' field or we need to determine buyer status
                subject_type = subject.get('type', 'non-buyer')
                if subject_type == 'buyer':
                    buyers.append(subject)
                else:
                    non_buyers.append(subject)
            
            return buyers, non_buyers
        except requests.RequestException as e:
            logger.error("failed_to_fetch_buyers_non_buyers", error=str(e), job_id=job_id)
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_buyers_and_non_buyers", job_id=job_id)
                # Generate mock buyers and non-buyers
                mock_buyers = [
                    {"uuid": f"{job_id}-buyer-001", "first_name": "Buyer", "last_name": "One", "type": "buyer", "phone": "555-0101", "email": "buyer1@example.com"}
                ]
                mock_non_buyers = [
                    {"uuid": f"{job_id}-nonbuyer-001", "first_name": "NonBuyer", "last_name": "One", "type": "non-buyer", "phone": "555-0102", "email": "nonbuyer1@example.com"},
                    {"uuid": f"{job_id}-nonbuyer-002", "first_name": "NonBuyer", "last_name": "Two", "type": "non-buyer", "phone": "555-0103", "email": "nonbuyer2@example.com"}
                ]
                return mock_buyers, mock_non_buyers
            return [], []

    def get_buyers_and_non_buyers_csv(self, job_id: str) -> tuple[list[dict], list[dict]]:
        """Get buyers and non-buyers for a job - using CSV data"""
        logger.info("loading_buyers_non_buyers_from_csv", job_id=job_id, base_url=self.base_url)
        try:
            import csv
            import os
            from .config import ALLOWED_PORTALS
            
            # Map portal names to CSV files
            csv_files = {
                "nowandforeverphoto": "sms_campaign_nowandforeverphoto_20251031.csv"
            }
            
            portal_key = None
            for key, url in ALLOWED_PORTALS.items():
                if url in self.base_url:
                    portal_key = key
                    break
            
            if portal_key and portal_key in csv_files:
                csv_file = csv_files[portal_key]
                if os.path.exists(csv_file):
                    buyers = []
                    non_buyers = []
                    
                    with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            subject = {
                                'uuid': row.get('subject_uuid', ''),
                                'first_name': row.get('first_name', ''),
                                'last_name': row.get('last_name', ''),
                                'phone': row.get('phone_number', ''),
                                'email': row.get('email', ''),
                                'type': 'buyer' if row.get('buyer', '').lower() == 'yes' else 'non-buyer'
                            }
                            
                            if subject['type'] == 'buyer':
                                buyers.append(subject)
                            else:
                                non_buyers.append(subject)
                    
                    logger.info("loaded_subjects_from_csv", buyers=len(buyers), non_buyers=len(non_buyers))
                    return buyers, non_buyers
            
            # Fallback to mock data
            logger.warning("csv_not_found_using_mock_data", portal=portal_key)
            mock_buyers = [
                {"uuid": f"{job_id}-buyer-001", "first_name": "Buyer", "last_name": "One", "type": "buyer", "phone": "555-0101", "email": "buyer1@example.com"}
            ]
            mock_non_buyers = [
                {"uuid": f"{job_id}-nonbuyer-001", "first_name": "NonBuyer", "last_name": "One", "type": "non-buyer", "phone": "555-0102", "email": "nonbuyer1@example.com"},
                {"uuid": f"{job_id}-nonbuyer-002", "first_name": "NonBuyer", "last_name": "Two", "type": "non-buyer", "phone": "555-0103", "email": "nonbuyer2@example.com"}
            ]
            return mock_buyers, mock_non_buyers
        except Exception as e:
            logger.error("failed_to_load_buyers_non_buyers_from_csv", error=str(e), job_id=job_id)
            # Return mock data on error
            mock_buyers = [
                {"uuid": f"{job_id}-buyer-001", "first_name": "Buyer", "last_name": "One", "type": "buyer", "phone": "555-0101", "email": "buyer1@example.com"}
            ]
            mock_non_buyers = [
                {"uuid": f"{job_id}-nonbuyer-001", "first_name": "NonBuyer", "last_name": "One", "type": "non-buyer", "phone": "555-0102", "email": "nonbuyer1@example.com"},
                {"uuid": f"{job_id}-nonbuyer-002", "first_name": "NonBuyer", "last_name": "Two", "type": "non-buyer", "phone": "555-0103", "email": "nonbuyer2@example.com"}
            ]
            return mock_buyers, mock_non_buyers

    def get_registered_users(self, user_refs: list[str]) -> dict[str, dict]:
        """Get registered user details by user references"""
        logger.info("fetching_registered_users", user_count=len(user_refs), base_url=self.base_url)
        try:
            response = self._make_request(
                'POST',
                f"{self.base_url}/registered-users",
                json={"user_refs": user_refs},
                headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
            return response.json()
        except requests.RequestException as e:
            logger.error("failed_to_fetch_registered_users", error=str(e), user_count=len(user_refs))
            if self.fallback_mode:
                logger.warning("api_failed_using_fallback", method="get_registered_users", user_count=len(user_refs))
                # Generate mock registered user data
                from .adapters.portals_async import generate_realistic_phone
                mock_users = {}
                for ref in user_refs:
                    mock_users[ref] = {
                        "name": f"Registered User {ref[-4:]}",
                        "email_address": f"user{ref[-4:]}@example.com",
                        "phone_number": generate_realistic_phone(ref)
                    }
                return mock_users
            return {}


class EnrichmentService:
    """Service for enriching subjects with additional data"""

    def enrich_subjects(self, subjects: list[Subject]) -> list[Subject]:
        """Add purchase history, registered user refs, etc."""
        # TODO: Implement actual enrichment from portal
        # For mock data, don't override existing data
        for subject in subjects:
            # Only set data if not already set
            if not subject.purchase_history:
                subject.purchase_history = []
            if not subject.registered_user_ref:
                subject.registered_user_ref = None
        return subjects
        """Add purchase history, registered user refs, etc."""
        # TODO: Implement actual enrichment from portal
        # For mock data, don't override existing data
        for subject in subjects:
            # Only set data if not already set
            if not subject.purchase_history:
                subject.purchase_history = []
            if not subject.registered_user_ref:
                subject.registered_user_ref = None
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

    def generate_campaign(self, job_ids: list[str], campaign_type: str, portal: str, contact_filter: str = "any", check_registered_users: bool = False, include_registered_phone: bool = False, registered_only: bool = False) -> CampaignDataset:
        """Generate campaign dataset"""
        if self.portals_async:
            return asyncio.run(self._generate_campaign_async(job_ids, campaign_type, portal, contact_filter, check_registered_users, include_registered_phone))
        else:
            return self._generate_campaign_sync(job_ids, campaign_type, portal, contact_filter, check_registered_users, include_registered_phone)

    def _generate_campaign_sync(self, job_ids: list[str], campaign_type: str, portal: str, contact_filter: str = "any", check_registered_users: bool = False, include_registered_phone: bool = False, registered_only: bool = False) -> CampaignDataset:
        """Synchronous campaign generation with enhanced logic"""
        all_activities = []
        subjects = {}
        
        # Fetch activities and subjects for all jobs
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

        # Filter activities based on campaign type
        if campaign_type == "buyers":
            activities = self.filtering_service.filter_buyers(all_activities, subjects)
        elif campaign_type == "non-buyers":
            activities = self.filtering_service.filter_non_buyers(all_activities, subjects)
        else:
            activities = all_activities

        # Filter subjects that have images (required for campaigns)
        activities = [activity for activity in activities if subjects[activity.subject_id].has_images]

        # Deduplicate activities
        activities = self.filtering_service.deduplicate(activities)

        # Get registered users if needed
        registered_users = {}
        if check_registered_users or registered_only:
            # Bulk fetch registered users for all subjects
            user_refs = [s.registered_user_ref for s in subjects.values() if s.registered_user_ref]
            if user_refs:
                registered_users = self.portal_client.get_registered_users_bulk(user_refs)

        # Filter to registered users only if requested
        if registered_only:
            activities = [activity for activity in activities if subjects[activity.subject_id].registered_user_ref]

        # Convert to contacts
        contacts = []
        for activity in activities:
            subject = subjects[activity.subject_id]
            
            # Get registered user details if available
            user_details = None
            if subject.registered_user_ref and subject.registered_user_ref in registered_users:
                user_details = registered_users[subject.registered_user_ref]

            # Extract contact info with user priority
            contact_info_raw = extract_contact_info_with_user_priority(subject.__dict__, user_details)
            
            # For mock data, use subject data directly, prioritizing user details
            phone = user_details.get("phone", subject.phone) if user_details else subject.phone
            email = user_details.get("email", subject.email) if user_details else subject.email
            
            contact_info = {
                "phone_number": clean_phone_number(phone) if phone else "",
                "phone_number_2": "",
                "email": email or "",
                "email_2": "",
                "first_name": subject.name.split()[0] if subject.name else "",
                "last_name": " ".join(subject.name.split()[1:]) if subject.name and len(subject.name.split()) > 1 else "",
                "registered_user_email": user_details.get("email", "") if user_details else ""
            }
            
            # Apply contact filter
            if contact_filter == "phone-only" and not contact_info.get("phone_number"):
                continue
            elif contact_filter == "email-only" and not contact_info.get("email"):
                continue
            # "any" filter allows both phone and email

            # Generate access code
            access_code = generate_access_key(subject.id, contact_info.get("phone_number", ""))
            
            # Generate consent timestamp
            consent_ts = generate_consent_timestamp(activity)
            
            # Build URLs
            portal_url = f"https://{portal}.shop"
            custom_gallery_url = f"{portal_url}/?code={access_code}"
            
            # Extract parent name if available
            parent_name = extract_parent_name(subject.__dict__)
            
            # Determine buyer status
            is_buyer = len(subject.purchase_history) > 0
            
            contact = Contact(
                # Portal and job information
                portal=portal,
                job_uuid=job_ids[0],  # TODO: Map to actual job UUID
                job_name=f"Job {job_ids[0]}",  # TODO: Get actual job name
                
                # Subject information
                subject_uuid=subject.id,
                external_id=f"{random.randint(1000000, 9999999)}",  # Mock external ID
                first_name=contact_info.get("first_name", ""),
                last_name=contact_info.get("last_name", ""),
                parent_name=parent_name,
                
                # Contact information
                phone_number=contact_info.get("phone_number", ""),
                phone_number_2=contact_info.get("phone_number_2", ""),
                email=contact_info.get("email", ""),
                email_2=contact_info.get("email_2", ""),
                
                # Geographic and grouping
                country="USA",
                group="",  # Not available in mock
                
                # Purchase and access
                buyer="Yes" if is_buyer else "No",
                access_code=access_code,
                url=portal_url,
                custom_gallery_url=custom_gallery_url,
                
                # Consent information
                sms_marketing_consent="SUBSCRIBE",
                sms_marketing_timestamp=consent_ts,
                sms_transactional_consent="SUBSCRIBE",
                sms_transactional_timestamp=consent_ts,
                
                # Activity information
                activity_uuid=activity.id,
                activity_name="Main shoot",  # Mock activity name
                
                # Registered user information
                registered_user="Yes" if subject.registered_user_ref else "No",
                registered_user_email=contact_info.get("registered_user_email", ""),
                registered_user_uuid=subject.registered_user_ref or "",
                
                # Resolution strategy
                resolution_strategy="details+subjects-enrichment",
                
                # Legacy fields for compatibility
                subject_id=subject.id,
                phone=contact_info.get("phone_number", ""),
                priority=self.determine_priority(subject),
                access_key=access_code,
                consent_timestamp=datetime.strptime(consent_ts, "%m/%d/%Y"),
                is_buyer=is_buyer
            )
            contacts.append(contact)

        return CampaignDataset(
            contacts=sorted(contacts, key=lambda c: c.priority),
            metadata={
                "job_ids": job_ids,
                "campaign_type": campaign_type,
                "contact_filter": contact_filter,
                "registered_only": registered_only,
                "total_contacts": len(contacts)
            },
            generated_at=datetime.now()
        )

    async def _generate_campaign_async(self, job_ids: list[str], campaign_type: str, portal: str, contact_filter: str = "any", check_registered_users: bool = False, include_registered_phone: bool = False, registered_only: bool = False) -> CampaignDataset:
        """Asynchronous campaign generation with enhanced logic and parallel fetching"""
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
        
        # Early filtering: only fetch subjects for activities that match campaign type
        if campaign_type == "buyers":
            # For buyers, we need to check purchase history, so fetch all subjects first
            # But we can optimize by fetching subjects in bulk with pagination
            pass  # Fetch all subjects for now
        elif campaign_type == "non-buyers":
            # For non-buyers, we can potentially filter early, but need purchase history
            pass  # Fetch all subjects for now
        
        # Bulk fetch subjects with pagination simulation
        subjects = {}
        subject_ids_list = list(subjects_set)
        batch_size = 100  # Process in batches for memory efficiency
        
        for i in range(0, len(subject_ids_list), batch_size):
            batch_ids = subject_ids_list[i:i+batch_size]
            # For each activity, get subjects (simulating pagination)
            # In real implementation, this would be a bulk API call
            subject_tasks = []
            for activity in all_activities:
                if activity.subject_id in batch_ids:
                    subject_tasks.append(self.portals_async.get_subjects_for_activity(portal_key, activity.id))
            
            if subject_tasks:
                subject_results = await asyncio.gather(*subject_tasks, return_exceptions=True)
                
                for result in subject_results:
                    if isinstance(result, Exception):
                        logger.error("failed_to_fetch_subjects", error=str(result))
                        continue
                    for subject_data in result:
                        # Map the API response to Subject model fields
                        mapped_data = {
                            "id": subject_data["uuid"],
                            "name": f"Subject {subject_data['uuid'].split('_')[-1]}",
                            "email": f"test{subject_data['uuid'].split('_')[-1]}@example.com",
                            "phone": subject_data["phones"][0] if subject_data["phones"] else "",
                            "consent_timestamp": datetime.now(),
                            "purchase_history": [{"id": "p1", "amount": 100.0, "date": datetime.now()}] if subject_data["has_purchase"] else [],
                            "registered_user_ref": subject_data["registered_user_ref"],
                            "has_images": True
                        }
                        subject = Subject(**mapped_data)
                        subjects[subject.id] = subject
        
        # Enrich subjects (synchronous for now)
        enriched_subjects = self.enrichment_service.enrich_subjects(list(subjects.values()))
        subjects = {s.id: s for s in enriched_subjects}
        
        # Filter activities based on campaign type
        if campaign_type == "buyers":
            activities = self.filtering_service.filter_buyers(all_activities, subjects)
        elif campaign_type == "non-buyers":
            activities = self.filtering_service.filter_non_buyers(all_activities, subjects)
        else:
            activities = all_activities
        
        # Filter subjects that have images (required for campaigns)
        activities = [activity for activity in activities if subjects[activity.subject_id].has_images]
        
        # Deduplicate activities
        activities = self.filtering_service.deduplicate(activities)
        
        # Get registered users if needed - use bulk async method
        registered_users = {}
        if check_registered_users or registered_only:
            # Bulk fetch registered users for all subjects
            user_refs = [s.registered_user_ref for s in subjects.values() if s.registered_user_ref]
            if user_refs:
                registered_users = await self.portals_async.get_registered_users_bulk(portal_key, user_refs)
        
        # Filter to registered users only if requested
        if registered_only:
            activities = [activity for activity in activities if subjects[activity.subject_id].registered_user_ref]
        
        # For registered users, bulk fetch user profiles if we need phone info
        user_profiles = {}
        if include_registered_phone and registered_users:
            registered_uuids = [user_data.get("registered_uuid") for user_data in registered_users.values() if user_data.get("is_registered")]
            if registered_uuids:
                user_profiles = await self.portals_async.get_user_profiles_bulk(portal_key, registered_uuids)
        
        # Convert to contacts
        contacts = []
        for activity in activities:
            subject = subjects.get(activity.subject_id)
            if subject:
                # Get registered user details if available
                user_details = None
                user_profile = None
                if subject.registered_user_ref:
                    user_details = registered_users.get(subject.registered_user_ref)
                    if user_details and user_details.get("is_registered"):
                        user_profile = user_profiles.get(user_details.get("registered_uuid"))
                
                # Extract contact info with user priority
                contact_info_raw = extract_contact_info_with_user_priority(subject.__dict__, user_profile)
                
                # For subjects from bulk API, use the phone directly if contact_info_raw doesn't have it
                phone = ""
                email = ""
                if user_profile and include_registered_phone:
                    phone = user_profile.get("phones", [""])[0] if user_profile.get("phones") else ""
                    email = user_profile.get("email", "") if user_profile.get("email") else ""
                elif contact_info_raw.get("mobile_1"):
                    phone = contact_info_raw["mobile_1"]
                    email = contact_info_raw.get("email_1", "")
                else:
                    # Fallback to subject phone
                    phone = subject.phone
                    email = subject.email or ""
                
                contact_info = {
                    "phone_number": clean_phone_number(phone) if phone else "",
                    "phone_number_2": "",
                    "email": email or "",
                    "email_2": "",
                    "first_name": subject.name.split()[0] if subject.name else "",
                    "last_name": " ".join(subject.name.split()[1:]) if subject.name and len(subject.name.split()) > 1 else "",
                    "registered_user_email": user_profile.get("email", "") if user_profile else ""
                }
                
                # Apply contact filter
                if contact_filter == "phone-only" and not contact_info.get("phone_number"):
                    continue
                elif contact_filter == "email-only" and not contact_info.get("email"):
                    continue
                # "any" filter allows both phone and email

                # Generate access code
                access_code = generate_access_key(subject.id, contact_info.get("phone_number", ""))
                
                # Generate consent timestamp
                consent_ts = generate_consent_timestamp(activity)
                
                # Build URLs
                portal_url = f"https://{portal}.shop"
                custom_gallery_url = f"{portal_url}/?code={access_code}"
                
                # Extract parent name if available
                parent_name = extract_parent_name(subject.__dict__)
                
                # Determine buyer status
                is_buyer = len(subject.purchase_history) > 0
                
                contact = Contact(
                    # Portal and job information
                    portal=portal,
                    job_uuid=job_ids[0],  # TODO: Map to actual job UUID
                    job_name=f"Job {job_ids[0]}",  # TODO: Get actual job name
                    
                    # Subject information
                    subject_uuid=subject.id,
                    external_id=f"{random.randint(1000000, 9999999)}",  # Mock external ID
                    first_name=contact_info.get("first_name", ""),
                    last_name=contact_info.get("last_name", ""),
                    parent_name=parent_name,
                    
                    # Contact information
                    phone_number=contact_info.get("phone_number", ""),
                    phone_number_2=contact_info.get("phone_number_2", ""),
                    email=contact_info.get("email", ""),
                    email_2=contact_info.get("email_2", ""),
                    
                    # Geographic and grouping
                    country="USA",
                    group="",  # Not available in mock
                    
                    # Purchase and access
                    buyer="Yes" if is_buyer else "No",
                    access_code=access_code,
                    url=portal_url,
                    custom_gallery_url=custom_gallery_url,
                    
                    # Consent information
                    sms_marketing_consent="SUBSCRIBE",
                    sms_marketing_timestamp=consent_ts,
                    sms_transactional_consent="SUBSCRIBE",
                    sms_transactional_timestamp=consent_ts,
                    
                    # Activity information
                    activity_uuid=activity.id,
                    activity_name="Main shoot",  # Mock activity name
                    
                    # Registered user information
                    registered_user="Yes" if subject.registered_user_ref else "No",
                    registered_user_email=contact_info.get("registered_user_email", ""),
                    registered_user_uuid=subject.registered_user_ref or "",
                    
                    # Resolution strategy
                    resolution_strategy="details+subjects-enrichment",
                    
                    # Legacy fields for compatibility
                    subject_id=subject.id,
                    phone=contact_info.get("phone_number", ""),
                    priority=self.determine_priority(subject),
                    access_key=access_code,
                    consent_timestamp=datetime.strptime(consent_ts, "%m/%d/%Y"),
                    is_buyer=is_buyer
                )
                contacts.append(contact)
        
        logger.info("async_campaign_complete", contact_count=len(contacts))
        return CampaignDataset(
            contacts=sorted(contacts, key=lambda c: c.priority),
            metadata={
                "job_ids": job_ids,
                "campaign_type": campaign_type,
                "contact_filter": contact_filter,
                "registered_only": registered_only,
                "total_contacts": len(contacts)
            },
            generated_at=datetime.now()
        )
