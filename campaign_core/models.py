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


class Contact(BaseModel):
    subject_id: str
    phone: str
    priority: int  # 1=user, 2=deliveries
    access_key: str
    consent_timestamp: datetime
    is_buyer: bool


class CampaignDataset(BaseModel):
    contacts: list[Contact]
    metadata: dict
    generated_at: datetime


# Resolve forward references
Job.model_rebuild()
Activity.model_rebuild()
