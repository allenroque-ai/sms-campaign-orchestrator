"""Data models for SMS Campaign Orchestrator"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class Job(BaseModel):
    id: str
    status: str  # Must be "webshop (selling)"
    activities: List["Activity"]


class Activity(BaseModel):
    id: str
    subject_id: str
    type: str  # "buyer" or "non-buyer"
    timestamp: datetime


class Subject(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    phone: str
    consent_timestamp: datetime
    purchase_history: List[dict] = []
    registered_user_ref: Optional[str] = None


class Contact(BaseModel):
    subject_id: str
    phone: str
    priority: int  # 1=user, 2=deliveries
    access_key: str
    consent_timestamp: datetime
    is_buyer: bool


class CampaignDataset(BaseModel):
    contacts: List[Contact]
    metadata: dict
    generated_at: datetime


# Resolve forward references
Job.update_forward_refs()
Activity.update_forward_refs()