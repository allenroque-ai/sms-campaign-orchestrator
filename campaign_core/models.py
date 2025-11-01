"""Data models for SMS Campaign Orchestrator"""

from datetime import datetime

from pydantic import BaseModel


class Job(BaseModel):
    id: str
    status: str  # Must be "webshop (selling)"
    activities: list["Activity"]


class Activity(BaseModel):
    id: str
    subject_id: str
    type: str  # "buyer" or "non-buyer"
    timestamp: datetime


class Subject(BaseModel):
    id: str
    name: str
    email: str | None = None
    phone: str
    consent_timestamp: datetime
    purchase_history: list[dict] = []
    registered_user_ref: str | None = None
    has_images: bool = True  # Default to True for mock data


class Contact(BaseModel):
    # Portal and job information
    portal: str
    job_uuid: str
    job_name: str
    
    # Subject information
    subject_uuid: str
    external_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    parent_name: str | None = None
    
    # Contact information
    phone_number: str
    phone_number_2: str | None = None
    email: str | None = None
    email_2: str | None = None
    
    # Geographic and grouping
    country: str = "USA"
    group: str | None = None
    
    # Purchase and access
    buyer: str  # "Yes" or "No"
    access_code: str
    url: str
    custom_gallery_url: str
    
    # Consent information
    sms_marketing_consent: str = "SUBSCRIBE"
    sms_marketing_timestamp: str
    sms_transactional_consent: str = "SUBSCRIBE"
    sms_transactional_timestamp: str
    
    # Activity information
    activity_uuid: str
    activity_name: str
    
    # Registered user information
    registered_user: str  # "Yes" or "No"
    registered_user_email: str | None = None
    registered_user_uuid: str | None = None
    
    # Resolution strategy
    resolution_strategy: str = "details+subjects-enrichment"
    
    # Legacy field aliases for compatibility (optional, derived from main fields)
    subject_id: str | None = None  # alias for subject_uuid
    phone: str | None = None  # alias for phone_number
    priority: int = 1  # 1=user, 2=deliveries (optional, defaults to 1)
    access_key: str | None = None  # alias for access_code
    consent_timestamp: datetime | None = None  # optional
    is_buyer: bool | None = None  # derived from buyer field (optional)


class CampaignDataset(BaseModel):
    contacts: list[Contact]
    metadata: dict
    generated_at: datetime


# Resolve forward references
Job.model_rebuild()
Activity.model_rebuild()
